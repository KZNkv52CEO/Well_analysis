# -*- coding: utf-8 -*-
"""
Petrophysical Well Log Analysis for Well #17.

Automated interpretation of well logging data (LAS 2.0 format) without
heavy external petrophysical libraries. Computes:
  - Shale volume (Vsh) using Larionov formula for young sediments
  - Effective porosity (Kn) from neutron log with shale correction
  - Permeability (Kpr) using Timur equation (1968)

Input: LAS file with curves GR, neutron, PZ, LLD
Output: 5-track visualization + CSV results

Reference well: Well #17, depth range 1068-1161.9 m
"""

import os
import sys
import re
import logging
from typing import Tuple, Optional
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import LogLocator, FuncFormatter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ============================================================================
# Configuration Constants
# ============================================================================

# Larionov formula coefficients for young/unconsolidated sediments
# Reference: Larionov, V.V. (1969). "Radioactive Well Logging"
LARIONOV_COEFFICIENT = 0.083
LARIONOV_EXPONENT = 3.7

# Timur equation coefficients for permeability estimation
# Reference: Timur, A. (1968). "An Investigation of Permeability, Porosity, 
# and Residual Water Saturation Relationships for Sandstone Reservoirs"
TIMUR_COEFFICIENT = 100.0
TIMUR_POROSITY_EXPONENT = 2.25
TIMUR_SATURATION_EXPONENT = 2

# Porosity constraints (fraction 0-1)
PHI_MAX = 0.30  # Maximum porosity (30%)
PHI_MIN = 0.02  # Minimum porosity (2%)
PHI_SHALE = 0.30  # Porosity in shale (for correction)

# Irreducible water saturation (Swir)
SWIR_DEFAULT = 0.25

# LAS file null value (default marker for missing data)
LAS_NULL_VALUE = -999.25

# Required curve names in LAS file
REQUIRED_CURVES = {"DEPT", "GR", "neutron", "PZ", "LLD"}

# ============================================================================
# LAS Parser
# ============================================================================


def read_las(file_path: str) -> pd.DataFrame:
    """
    Parse LAS 2.0 file using standard Python (no external LAS library).

    Reads LAS sections (~Curve, ~Well, ~Ascii) and extracts curve data
    into a pandas DataFrame. Automatically replaces null values with NaN.

    Args:
        file_path: Path to LAS file (must exist)

    Returns:
        DataFrame with columns as curve names and rows as measurements

    Raises:
        FileNotFoundError: If LAS file does not exist
        ValueError: If LAS file cannot be parsed or lacks ~Ascii section
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"LAS file not found: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except Exception as e:
        raise ValueError(f"Failed to read LAS file: {e}")

    # Split into LAS sections (marked by ~Section)
    sections = re.split(r"(?m)^~", text)
    curves = []
    null_val = LAS_NULL_VALUE
    data_text = ""

    for section in sections:
        if not section.strip():
            continue

        section_type = section.strip()[:1].upper()

        # Parse ~Curve section (column definitions)
        if section_type == "C":
            lines = section.splitlines()
            for line in lines[1:]:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # Extract curve name (before first dot)
                match = re.match(r"([^\.\s]+)\s*\.", line)
                if match:
                    curves.append(match.group(1))

        # Parse ~Well section (extract NULL value)
        elif section_type == "W":
            match = re.search(r"NULL\s*\.\s*([^\s:]+)", section, re.IGNORECASE)
            if match:
                try:
                    null_val = float(match.group(1))
                except ValueError:
                    pass

        # Parse ~Ascii section (numeric data)
        elif section_type == "A":
            data_text = "\n".join(section.splitlines()[1:])

    if not data_text:
        raise ValueError("No ~Ascii section found in LAS file")

    # Parse numeric rows
    rows = []
    for line in data_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            rows.append([float(x) for x in line.split()])
        except ValueError:
            continue

    if not rows:
        raise ValueError("No numeric data found in ~Ascii section")

    # Create DataFrame
    if len(curves) != len(rows[0]):
        logger.warning(
            f"Curve count ({len(curves)}) does not match data columns ({len(rows[0])}). "
            "Using numeric column names."
        )
        df = pd.DataFrame(rows)
    else:
        df = pd.DataFrame(rows, columns=curves)

    # Replace null markers with NaN
    df = df.replace(null_val, np.nan)

    logger.info(
        f"Loaded LAS: {df.shape[0]} measurements, {df.shape[1]} curves, "
        f"null value = {null_val}"
    )
    return df


def validate_curves(df: pd.DataFrame, required: set = None) -> None:
    """
    Validate that required curves exist in DataFrame.

    Args:
        df: Input DataFrame
        required: Set of required column names (default: REQUIRED_CURVES)

    Raises:
        ValueError: If any required curves are missing
    """
    if required is None:
        required = REQUIRED_CURVES

    missing = required - set(df.columns)
    if missing:
        available = ", ".join(sorted(df.columns))
        raise ValueError(
            f"Missing required curves: {', '.join(sorted(missing))}. "
            f"Available: {available}"
        )


# ============================================================================
# Petrophysical Calculations
# ============================================================================


def calc_vsh_larionov(
    gr: np.ndarray,
    gr_clean: Optional[float] = None,
    gr_shale: Optional[float] = None
) -> Tuple[np.ndarray, float, float]:
    """
    Compute shale volume fraction using Larionov formula.

    For young/unconsolidated sediments (typical for Tertiary/Quaternary).
    Reference: Larionov, V.V. (1969)

    Args:
        gr: Gamma ray log (API units), array
        gr_clean: Reference GR value for clean sand (default: 5th percentile)
        gr_shale: Reference GR value for shale (default: 95th percentile)

    Returns:
        Tuple of:
          - vsh: Shale volume fraction, clipped to [0, 1]
          - gr_clean: Clean sand calibration value
          - gr_shale: Shale calibration value
    """
    # Establish calibration points if not provided
    if gr_clean is None:
        gr_clean = float(np.nanpercentile(gr, 5))
    if gr_shale is None:
        gr_shale = float(np.nanpercentile(gr, 95))

    # Compute gamma ray index (normalized to 0-1)
    igr = (gr - gr_clean) / (gr_shale - gr_clean)
    igr = np.clip(igr, 0.0, 1.0)

    # Larionov formula: Vsh = 0.083 * (2^(3.7*Igr) - 1)
    vsh = LARIONOV_COEFFICIENT * (2.0 ** (LARIONOV_EXPONENT * igr) - 1.0)
    vsh = np.clip(vsh, 0.0, 1.0)

    logger.info(
        f"Shale volume (Larionov): min={vsh.min():.2%}, max={vsh.max():.2%}, "
        f"mean={np.nanmean(vsh):.2%}"
    )
    return vsh, gr_clean, gr_shale


def calc_porosity_from_neutron(
    nlog: np.ndarray,
    vsh: np.ndarray,
    phi_max: float = PHI_MAX,
    phi_min: float = PHI_MIN,
    phi_shale: float = PHI_SHALE
) -> Tuple[np.ndarray, float, float]:
    """
    Compute effective porosity from neutron log with shale correction.

    Converts neutron porosity to effective porosity by:
      1. Normalizing neutron log to reference points (5th/95th percentiles)
      2. Mapping to porosity range [phi_min, phi_max]
      3. Correcting for clay content: phi_eff = phi_n - vsh * phi_shale

    Args:
        nlog: Neutron log (raw values), array
        vsh: Shale volume fraction (from calc_vsh_larionov), array
        phi_max: Maximum porosity (default: 0.30 = 30%)
        phi_min: Minimum porosity (default: 0.02 = 2%)
        phi_shale: Porosity attributed to shale matrix (default: 0.30)

    Returns:
        Tuple of:
          - phi_eff: Effective porosity, clipped to [0, phi_max]
          - n_min: Neutron log reference minimum (5th percentile)
          - n_max: Neutron log reference maximum (95th percentile)
    """
    n_min = float(np.nanpercentile(nlog, 5))
    n_max = float(np.nanpercentile(nlog, 95))

    # Normalize to [0, 1], then scale to [phi_min, phi_max]
    # Assume higher neutron values = lower porosity (inverted axis)
    normalized = (nlog - n_min) / (n_max - n_min)
    phi_n = phi_max - (phi_max - phi_min) * normalized
    phi_n = np.clip(phi_n, phi_min, phi_max)

    # Subtract clay-bound water correction
    phi_eff = phi_n - vsh * phi_shale
    phi_eff = np.clip(phi_eff, 0.0, phi_max)

    logger.info(
        f"Effective porosity (neutron-derived): min={phi_eff.min():.2%}, "
        f"max={phi_eff.max():.2%}, mean={np.nanmean(phi_eff):.2%}"
    )
    return phi_eff, n_min, n_max


def calc_permeability_timur(
    phi: np.ndarray,
    swir: float = SWIR_DEFAULT
) -> np.ndarray:
    """
    Estimate permeability using Timur equation (1968).

    For sandstone reservoirs with water saturation consideration.
    Reference: Timur, A. (1968)

    Equation: K = 100 * (phi^2.25 / swir)^2 [millidarcies]

    Args:
        phi: Effective porosity (fraction 0-1), array
        swir: Irreducible water saturation (default: 0.25 = 25%)

    Returns:
        Permeability in millidarcies (mD), clipped to [0.01, 1000] for 
        physical validity. Returns NaN where porosity is invalid.
    """
    # Avoid division by zero and log(negative)
    phi_safe = np.where(phi > 0, phi, np.nan)

    # Timur equation: K = 100 * (phi^2.25 / swir)^2
    k_md = (TIMUR_COEFFICIENT * (phi_safe ** TIMUR_POROSITY_EXPONENT / swir)) ** TIMUR_SATURATION_EXPONENT

    # Clip to physically reasonable range
    k_md = np.clip(k_md, 0.01, 1000.0)

    k_nonzero = k_md[~np.isnan(k_md) & (k_md > 0)]
    if len(k_nonzero) > 0:
        logger.info(
            f"Permeability (Timur): min={k_nonzero.min():.2f} mD, "
            f"max={k_nonzero.max():.2f} mD, mean={np.nanmean(k_nonzero):.2f} mD"
        )
    return k_md


# ============================================================================
# Visualization
# ============================================================================


def plot_well(df: pd.DataFrame, output_path: str, well_number: str = "17") -> None:
    """
    Generate 5-track well log plot with petrophysical results.

    Tracks:
      1. Gamma Ray (GR) + Shale Volume (Vsh)
      2. Neutron Log (ННК)
      3. Shallow (PZ) + Deep (LLD) Resistivity (log scale)
      4. Effective Porosity (Kn) [fill background]
      5. Permeability (Kpr) (log scale)

    All depth scales are inverted (depth increases downward).

    Args:
        df: DataFrame with columns: DEPT, GR, neutron, PZ, LLD, Vsh, Kn, Kпр
        output_path: Path to save PNG (e.g., "well_17_logplot.png")
        well_number: Well identifier for title (default: "17")

    Raises:
        KeyError: If required columns are missing
    """
    try:
        depth = df["DEPT"].values
        gr = df["GR"].values
        nlog = df["neutron"].values
        pz = df["PZ"].values
        lld = df["LLD"].values
        vsh = df["Vsh"].values
        kn = df["Kn"].values
        kpr = df["Kпр"].values
    except KeyError as e:
        raise KeyError(f"Missing required column for plotting: {e}")

    fig, axes = plt.subplots(
        nrows=1, ncols=5, sharey=True,
        figsize=(15, 11),
        gridspec_kw={"wspace": 0.08},
    )

    fig.suptitle(
        f"Well #{well_number} | Petrophysical Interpretation",
        fontsize=14, fontweight="bold", y=0.995
    )

    # ========================================================================
    # Track 1: Gamma Ray + Shale Volume
    # ========================================================================
    ax1 = axes[0]
    ax1.plot(gr, depth, color="#3498db", lw=0.9, label="GR")
    ax1.set_xlabel("GR (API)", color="#3498db", labelpad=4)
    ax1.tick_params(axis="x", colors="#3498db", labelsize=8)
    ax1.set_xlim(np.floor(np.nanmin(gr)), np.ceil(np.nanmax(gr)))

    ax1b = ax1.twiny()
    ax1b.plot(vsh, depth, color="#e74c3c", lw=0.9, label="Vsh")
    ax1b.spines["top"].set_position(("outward", 36))
    ax1b.set_xlabel("Vsh (frac.)", color="#e74c3c", labelpad=4)
    ax1b.tick_params(axis="x", colors="#e74c3c", labelsize=8)
    ax1b.set_xlim(0, 1)

    # ========================================================================
    # Track 2: Neutron Log
    # ========================================================================
    ax2 = axes[1]
    ax2.plot(nlog, depth, color="#f39c12", lw=0.9)
    ax2.set_xlabel("Neutron (API)", color="#f39c12", labelpad=4)
    ax2.tick_params(axis="x", colors="#f39c12", labelsize=8)
    ax2.set_xlim(np.nanmin(nlog) * 0.95, np.nanmax(nlog) * 1.02)

    # ========================================================================
    # Track 3: Resistivity (PZ shallow, LLD deep) — Log Scale
    # ========================================================================
    ax3 = axes[2]
    ax3.plot(pz, depth, color="#27ae60", lw=0.9, label="PZ (shallow)")
    ax3.set_xlabel("PZ (Ω·m)", color="#27ae60", labelpad=4)
    ax3.tick_params(axis="x", colors="#27ae60", labelsize=8)
    ax3.set_xscale("log")
    ax3.set_xlim(1, 1000)
    ax3.xaxis.set_major_locator(LogLocator(base=10, numticks=4))
    ax3.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:g}"))

    ax3b = ax3.twiny()
    ax3b.plot(lld, depth, color="#2980b9", lw=0.9, label="LLD (deep)")
    ax3b.spines["top"].set_position(("outward", 36))
    ax3b.set_xlabel("LLD (Ω·m)", color="#2980b9", labelpad=4)
    ax3b.tick_params(axis="x", colors="#2980b9", labelsize=8)
    ax3b.set_xscale("log")

    # ========================================================================
    # Track 4: Effective Porosity (with fill)
    # ========================================================================
    ax4 = axes[3]
    ax4.plot(kn * 100, depth, color="#9b59b6", lw=1.0)
    ax4.fill_betweenx(depth, 0, kn * 100, where=~np.isnan(kn),
                      color="#9b59b6", alpha=0.15)
    ax4.set_xlabel("Porosity (%)", color="#9b59b6", labelpad=4)
    ax4.tick_params(axis="x", colors="#9b59b6", labelsize=8)
    ax4.set_xlim(0, 30)
    ax4.set_xticks([0, 10, 20, 30])

    # ========================================================================
    # Track 5: Permeability — Log Scale
    # ========================================================================
    ax5 = axes[4]
    ax5.plot(kpr, depth, color="#e67e22", lw=1.0)
    ax5.set_xscale("log")
    ax5.set_xlabel("Permeability (mD)", color="#e67e22", labelpad=4)
    ax5.tick_params(axis="x", colors="#e67e22", labelsize=8)
    ax5.set_xlim(1e-2, 1e3)
    ax5.xaxis.set_major_locator(LogLocator(base=10, numticks=6))
    ax5.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:g}"))

    # ========================================================================
    # Axis Formatting (All Tracks)
    # ========================================================================
    for i, ax in enumerate(axes):
        ax.invert_yaxis()
        ax.grid(True, which="both", ls=":", lw=0.4, color="grey", alpha=0.6)
        ax.xaxis.set_label_position("top")
        ax.xaxis.tick_top()
        ax.tick_params(axis="x", labelsize=8)
        if i == 0:
            ax.set_ylabel("Depth (m)", fontsize=11)

    axes[0].set_ylim(depth.max(), depth.min())
    plt.subplots_adjust(top=0.88, bottom=0.04, left=0.06, right=0.985)

    try:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        logger.info(f"Saved plot: {output_path}")
    except Exception as e:
        logger.error(f"Failed to save plot: {e}")
        raise
    finally:
        plt.close(fig)


# ============================================================================
# Main Pipeline
# ============================================================================


def process_well(
    las_path: str,
    output_dir: str = ".",
    well_number: str = "17"
) -> pd.DataFrame:
    """
    Main processing pipeline: read LAS → calculate properties → export results.

    Args:
        las_path: Path to input LAS file
        output_dir: Directory for CSV and PNG output (created if missing)
        well_number: Well identifier for filenames and titles (default: "17")

    Returns:
        DataFrame with all computed results (Vsh, Kn, Kпр)

    Raises:
        FileNotFoundError: If LAS file not found
        ValueError: If LAS cannot be parsed or lacks required curves
    """
    logger.info(f"Processing well #{well_number}")
    logger.info(f"Input: {las_path}")

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # ========================================================================
    # Step 1: Read LAS file
    # ========================================================================
    logger.info("Reading LAS file...")
    df = read_las(las_path)
    logger.info(
        f"Loaded: {df.shape[0]} measurements, {df.shape[1]} curves | "
        f"Depth range: {df['DEPT'].min():.1f} - {df['DEPT'].max():.1f} m"
    )

    # Validate required curves
    validate_curves(df)

    # ========================================================================
    # Step 2: Calculate shale volume (Larionov)
    # ========================================================================
    logger.info("Calculating shale volume (Larionov formula)...")
    vsh, gr_clean, gr_shale = calc_vsh_larionov(df["GR"].values)
    df["Vsh"] = vsh
    logger.info(f"  GR calibration: clean={gr_clean:.1f}, shale={gr_shale:.1f} API")

    # ========================================================================
    # Step 3: Calculate effective porosity (neutron + shale correction)
    # ========================================================================
    logger.info("Calculating effective porosity (neutron-derived)...")
    kn, n_min, n_max = calc_porosity_from_neutron(df["neutron"].values, vsh)
    df["Kn"] = kn
    logger.info(f"  Neutron calibration: min={n_min:.1f}, max={n_max:.1f}")

    # ========================================================================
    # Step 4: Calculate permeability (Timur equation)
    # ========================================================================
    logger.info("Calculating permeability (Timur 1968 equation)...")
    df["Kпр"] = calc_permeability_timur(kn, swir=SWIR_DEFAULT)

    # ========================================================================
    # Step 5: Export results to CSV
    # ========================================================================
    csv_path = os.path.join(output_dir, f"well_{well_number}_results.csv")
    logger.info(f"Exporting results to CSV: {csv_path}")
    try:
        df.to_csv(csv_path, index=False, sep=";", float_format="%.4f")
        logger.info(f"  CSV exported: {df.shape[0]} rows, {df.shape[1]} columns")
    except Exception as e:
        logger.error(f"Failed to export CSV: {e}")
        raise

    # ========================================================================
    # Step 6: Generate well log plot
    # ========================================================================
    png_path = os.path.join(output_dir, f"well_{well_number}_logplot.png")
    logger.info(f"Generating well log plot: {png_path}")
    plot_well(df, png_path, well_number=well_number)

    # ========================================================================
    # Summary Statistics
    # ========================================================================
    logger.info("\n" + "=" * 70)
    logger.info("RESULTS SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Shale Volume (Vsh):        {vsh.min():.2%} - {vsh.max():.2%} "
                f"(mean: {np.nanmean(vsh):.2%})")
    logger.info(f"Effective Porosity (Kn):   {kn.min():.2%} - {kn.max():.2%} "
                f"(mean: {np.nanmean(kn):.2%})")

    kpr_valid = df["Kпр"][df["Kпр"] > 0]
    if len(kpr_valid) > 0:
        logger.info(f"Permeability (Kпр):        {kpr_valid.min():.2f} - "
                    f"{kpr_valid.max():.2f} mD (mean: {kpr_valid.mean():.2f} mD)")
    else:
        logger.warning("Permeability: No valid values computed")

    logger.info("=" * 70 + "\n")

    return df


def main():
    """
    Command-line entry point.

    Usage:
        python well_analysis.py [LAS_FILE] [OUTPUT_DIR] [WELL_NUMBER]

    Examples:
        python well_analysis.py 17.las results 17
        python well_analysis.py data/well_42.las . 42
    """
    # Parse command-line arguments
    las_path = sys.argv[1] if len(sys.argv) > 1 else "17.las"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "."
    well_number = sys.argv[3] if len(sys.argv) > 3 else "17"

    logger.info(f"Petrophysical Well Analysis v1.0")
    logger.info(f"Python {sys.version}")

    try:
        df = process_well(las_path, output_dir, well_number)
        logger.info("✓ Processing completed successfully")
        return 0
    except FileNotFoundError as e:
        logger.error(f"✗ File error: {e}")
        return 1
    except ValueError as e:
        logger.error(f"✗ Data error: {e}")
        return 1
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
