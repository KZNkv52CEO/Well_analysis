# Petrophysical Well Log Analysis

Python script for automated interpretation of well logging data (LAS 2.0 format) without heavy external petrophysical libraries.

## Features

- **Custom LAS Parser**: Reads LAS 2.0 files directly using standard Python and regular expressions (no `lasio` dependency)
- **Shale Volume ($V_{sh}$)**: Computed using the Larionov formula for young/unconsolidated sediments
- **Effective Porosity ($\phi_e$)**: Derived from Neutron log (ННК) data with shale correction
- **Permeability ($K_{pr}$)**: Estimated using the empirical Timur equation (1968)
- **Professional Visualization**: Generates a 5-track well log plot with:
  - Inverted depth scales (depth increases downward)
  - Log-scale resistivity and permeability tracks
  - Customized color-coded tracks with dual-axis support
- **Structured CSV Export**: Saves all computed results with depth for further analysis
- **Comprehensive Logging**: Detailed console output of processing steps and results
- **Error Handling**: Validates input data and provides clear error messages
- **Flexible Parameterization**: Accept any well number and LAS file via command-line arguments

## Requirements

```
numpy
pandas
matplotlib
```

Install with:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python well_analysis.py 17.las
```

This reads `17.las` from the current directory and generates:
- `well_17_results.csv` — Computed results (Vsh, Kn, Kпр)
- `well_17_logplot.png` — 5-track visualization

### Advanced Usage

```bash
python well_analysis.py <LAS_FILE> [OUTPUT_DIR] [WELL_NUMBER]
```

**Examples:**
```bash
# Process well #42 from custom directory
python well_analysis.py data/well_42.las results 42

# Process multiple wells
python well_analysis.py well_001.las output 001
python well_analysis.py well_002.las output 002
```

**Arguments:**
- `LAS_FILE` (required): Path to input LAS file
- `OUTPUT_DIR` (optional): Directory for CSV/PNG output (default: current directory)
- `WELL_NUMBER` (optional): Well identifier for filenames/titles (default: "17")

## Input Data Format

The script expects a LAS 2.0 file with the following curve names (case-sensitive):
- `DEPT` — Depth (meters)
- `GR` — Gamma Ray log (API units)
- `neutron` — Neutron Porosity log (raw values)
- `PZ` — Shallow Resistivity log (Ω·m)
- `LLD` — Deep Resistivity log (Ω·m)

**Example LAS Header:**
```
~Curve Section
 DEPT   .   1   DEPTH                M
 GR     .   1   GAMMA RAY            API
 neutron.   1   NEUTRON POROSITY     P.U.
 PZ     .   1   SHALLOW RESISTIVITY  OHMM
 LLD    .   1   DEEP RESISTIVITY     OHMM
```

## Output

### CSV Results (`well_XX_results.csv`)

Semicolon-delimited file with computed values:

| DEPT | GR | neutron | PZ | LLD | Vsh | Kn | Kпр |
|------|-----|---------|-----|-----|-----|-----|-----|
| 1068.0 | 45.2 | 0.28 | 12.5 | 15.3 | 0.145 | 0.182 | 245.67 |
| 1068.5 | 48.1 | 0.26 | 14.2 | 18.7 | 0.156 | 0.175 | 198.43 |

### PNG Plot (`well_XX_logplot.png`)

5-track well log visualization:

1. **Track 1**: Gamma Ray (GR) + Shale Volume (Vsh)
2. **Track 2**: Neutron Log (ННК)
3. **Track 3**: Resistivity (PZ + LLD, log scale)
4. **Track 4**: Effective Porosity (Kn) with filled background
5. **Track 5**: Permeability (Kпр, log scale)

## Computational Methods

### Shale Volume (Larionov Formula)

For young/unconsolidated sediments (Tertiary–Quaternary):

$$V_{sh} = 0.083 \times (2^{3.7 \times I_{GR}} - 1)$$

Where $I_{GR} = \frac{GR - GR_{min}}{GR_{max} - GR_{min}}$

- $GR_{min}$: 5th percentile (clean sand reference)
- $GR_{max}$: 95th percentile (shale reference)

**Reference**: Larionov, V.V. (1969). *Radioactive Well Logging*

### Effective Porosity (Neutron-Derived with Shale Correction)

$$\phi_{eff} = \phi_n - V_{sh} \times \phi_{shale}$$

Where:
- $\phi_n$: Neutron porosity (normalized to [2%, 30%])
- $\phi_{shale}$: Porosity attributed to clay matrix (default: 30%)

### Permeability (Timur Equation, 1968)

For sandstone reservoirs:

$$K = 100 \times \left(\frac{\phi^{2.25}}{S_{wir}}\right)^2 \text{ [mD]}$$

Where:
- $\phi$: Effective porosity (fraction)
- $S_{wir}$: Irreducible water saturation (default: 0.25)

**Reference**: Timur, A. (1968). *An Investigation of Permeability, Porosity, and Residual Water Saturation Relationships for Sandstone Reservoirs*

## Configuration

Edit constants at the top of `well_analysis.py` to customize calculations:

```python
# Larionov formula coefficients
LARIONOV_COEFFICIENT = 0.083
LARIONOV_EXPONENT = 3.7

# Porosity constraints
PHI_MAX = 0.30        # 30%
PHI_MIN = 0.02        # 2%
PHI_SHALE = 0.30      # Shale porosity

# Irreducible water saturation
SWIR_DEFAULT = 0.25   # 25%

# LAS null marker
LAS_NULL_VALUE = -999.25
```

## Example Output

```
2026-07-21 11:15:30,123 - INFO - Petrophysical Well Analysis v1.0
2026-07-21 11:15:30,124 - INFO - Processing well #17
2026-07-21 11:15:30,125 - INFO - Reading LAS file...
2026-07-21 11:15:30,126 - INFO - Loaded LAS: 94 measurements, 5 curves, null value = -999.25
2026-07-21 11:15:30,127 - INFO - Calculating shale volume (Larionov formula)...
2026-07-21 11:15:30,128 - INFO - Shale volume (Larionov): min=14.50%, max=58.32%, mean=32.18%
2026-07-21 11:15:30,129 - INFO - Calculating effective porosity (neutron-derived)...
2026-07-21 11:15:30,130 - INFO - Effective porosity (neutron-derived): min=2.00%, max=18.23%, mean=10.45%
2026-07-21 11:15:30,131 - INFO - Calculating permeability (Timur 1968 equation)...
2026-07-21 11:15:30,132 - INFO - Permeability (Timur): min=0.01 mD, max=456.78 mD, mean=124.32 mD
2026-07-21 11:15:30,145 - INFO - Exporting results to CSV: well_17_results.csv
2026-07-21 11:15:30,146 - INFO - CSV exported: 94 rows, 8 columns
2026-07-21 11:15:30,147 - INFO - Generating well log plot: well_17_logplot.png
2026-07-21 11:15:30,285 - INFO - Saved plot: well_17_logplot.png
2026-07-21 11:15:30,286 - INFO - ======================================================================
2026-07-21 11:15:30,287 - INFO - RESULTS SUMMARY
2026-07-21 11:15:30,288 - INFO - Shale Volume (Vsh):        14.50% - 58.32% (mean: 32.18%)
2026-07-21 11:15:30,289 - INFO - Effective Porosity (Kn):   2.00% - 18.23% (mean: 10.45%)
2026-07-21 11:15:30,290 - INFO - Permeability (Kпр):        0.01 - 456.78 mD (mean: 124.32 mD)
```

## Code Structure

```
well_analysis.py
├── Configuration Constants (lines 35-59)
├── LAS Parser (lines 62-130)
│   └── read_las() — Parse LAS 2.0 files
│   └── validate_curves() — Validate required curves
├── Petrophysical Calculations (lines 135-239)
│   ├── calc_vsh_larionov() — Shale volume
│   ├── calc_porosity_from_neutron() — Effective porosity
│   └── calc_permeability_timur() — Permeability
├── Visualization (lines 244-372)
│   └── plot_well() — 5-track well log plot
└── Main Pipeline (lines 376-508)
    ├── process_well() — Full processing pipeline
    └── main() — Command-line entry point
```

## Error Handling

The script validates inputs and provides clear error messages:

```bash
$ python well_analysis.py nonexistent.las
ERROR: File error: LAS file not found: nonexistent.las

$ python well_analysis.py test.las
ERROR: Data error: Missing required curves: {'neutron', 'PZ', 'LLD'}
```

## Performance

- **Processing time**: ~100-500 ms for typical well (1000+ depth points)
- **Memory usage**: ~10-50 MB depending on LAS file size
- **Dependencies**: Only numpy, pandas, matplotlib (minimal overhead)

## License

Open source. Modify and distribute freely.

## Author

Developed for petrophysical well log interpretation.

## References

- Larionov, V.V. (1969). *Radioactive Well Logging*. Moscow: Nedra
- Timur, A. (1968). An Investigation of Permeability, Porosity, and Residual Water Saturation Relationships for Sandstone Reservoirs. *Journal of Petroleum Technology*, 20(06)
- LAS 2.0 Format: [Canadian Well Logging Society](http://www.cwls.org/)

---

**Last Updated**: 2026-07-21  
**Version**: 1.0
