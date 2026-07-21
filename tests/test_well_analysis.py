"""Unit tests for well_analysis module."""

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from well_analysis import (
    calc_permeability_timur,
    calc_porosity_from_neutron,
    calc_vsh_larionov,
    read_las,
    validate_curves,
)


class TestLASParser:
    """Test LAS file parsing functionality."""

    def test_read_las_basic(self, sample_las_file: str) -> None:
        """Test reading valid LAS file."""
        df = read_las(sample_las_file)

        # Check structure
        assert isinstance(df, pd.DataFrame)
        assert df.shape[0] == 10  # 10 data rows
        assert df.shape[1] == 5  # 5 curves

        # Check columns
        expected_cols = {"DEPT", "GR", "neutron", "PZ", "LLD"}
        assert set(df.columns) == expected_cols

        # Check data types
        assert df["DEPT"].dtype in [np.float64, np.float32]
        assert df["GR"].dtype in [np.float64, np.float32]

    def test_read_las_nonexistent_file(self) -> None:
        """Test error handling for missing file."""
        with pytest.raises(FileNotFoundError, match="LAS file not found"):
            read_las("/nonexistent/path/file.las")

    def test_read_las_null_values(self, sample_las_file: str) -> None:
        """Test that null values are replaced with NaN."""
        df = read_las(sample_las_file)
        # Check no -999.25 values remain
        assert not (df == -999.25).any().any()

    def test_read_las_malformed(self, malformed_las_content: str) -> None:
        """Test error handling for malformed LAS."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".las", delete=False, encoding="utf-8"
        ) as f:
            f.write(malformed_las_content)
            temp_path = f.name

        try:
            with pytest.raises(ValueError):
                read_las(temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestCurveValidation:
    """Test curve validation functionality."""

    def test_validate_curves_valid(self, sample_dataframe: pd.DataFrame) -> None:
        """Test validation of valid curves."""
        # Should not raise
        validate_curves(sample_dataframe)

    def test_validate_curves_missing_required(self) -> None:
        """Test error when required curves are missing."""
        df = pd.DataFrame({"DEPT": [1, 2, 3], "GR": [40, 50, 60]})

        with pytest.raises(ValueError, match="Missing required curves"):
            validate_curves(df)

    def test_validate_curves_custom_required(self, sample_dataframe: pd.DataFrame) -> None:
        """Test validation with custom required curves."""
        required = {"DEPT", "GR"}
        # Should not raise
        validate_curves(sample_dataframe, required=required)


class TestShaleVolumeCalculation:
    """Test Larionov shale volume calculation."""

    def test_calc_vsh_larionov_basic(self) -> None:
        """Test basic Larionov calculation."""
        gr = np.array([40, 50, 60, 70, 80])
        vsh, gr_clean, gr_shale = calc_vsh_larionov(gr)

        # Check output types
        assert isinstance(vsh, np.ndarray)
        assert isinstance(gr_clean, (float, np.floating))
        assert isinstance(gr_shale, (float, np.floating))

        # Check value ranges
        assert np.all((vsh >= 0) & (vsh <= 1))
        assert gr_clean < gr_shale

    def test_calc_vsh_larionov_range(self) -> None:
        """Test Larionov output is in valid range [0, 1]."""
        gr = np.random.uniform(20, 100, 1000)
        vsh, _, _ = calc_vsh_larionov(gr)

        assert np.all(vsh >= 0)
        assert np.all(vsh <= 1)

    def test_calc_vsh_larionov_custom_calibration(self) -> None:
        """Test Larionov with custom calibration points."""
        gr = np.array([40, 50, 60, 70, 80])
        vsh1, _, _ = calc_vsh_larionov(gr, gr_clean=35, gr_shale=85)
        vsh2, _, _ = calc_vsh_larionov(gr)

        # Results should differ with different calibration
        assert not np.allclose(vsh1, vsh2)

    def test_calc_vsh_larionov_with_nans(self) -> None:
        """Test Larionov handles NaN values gracefully."""
        gr = np.array([40, 50, np.nan, 70, 80])
        vsh, _, _ = calc_vsh_larionov(gr)

        # Should return array with NaN at same position
        assert len(vsh) == len(gr)
        assert np.isnan(vsh[2])


class TestPorosityCalculation:
    """Test neutron-derived porosity calculation."""

    def test_calc_porosity_from_neutron_basic(self) -> None:
        """Test basic porosity calculation."""
        nlog = np.array([0.20, 0.22, 0.25, 0.28, 0.30])
        vsh = np.array([0.1, 0.15, 0.2, 0.25, 0.3])

        phi_eff, n_min, n_max = calc_porosity_from_neutron(nlog, vsh)

        # Check output types
        assert isinstance(phi_eff, np.ndarray)
        assert isinstance(n_min, (float, np.floating))
        assert isinstance(n_max, (float, np.floating))

        # Check value ranges
        assert np.all((phi_eff >= 0) & (phi_eff <= 0.30))  # Within PHI_MAX

    def test_calc_porosity_range(self) -> None:
        """Test porosity output range."""
        nlog = np.random.uniform(0.15, 0.35, 1000)
        vsh = np.random.uniform(0, 1, 1000)

        phi_eff, _, _ = calc_porosity_from_neutron(nlog, vsh)

        # Should be within physical bounds
        assert np.all(phi_eff >= 0)
        assert np.all(phi_eff <= 0.30)  # PHI_MAX

    def test_calc_porosity_shale_correction(self) -> None:
        """Test that shale correction is applied."""
        nlog = np.array([0.25, 0.25, 0.25])
        vsh_zero = np.array([0, 0, 0])
        vsh_high = np.array([1, 1, 1])

        phi1, _, _ = calc_porosity_from_neutron(nlog, vsh_zero)
        phi2, _, _ = calc_porosity_from_neutron(nlog, vsh_high)

        # Higher shale should give lower porosity (correction applied)
        assert np.all(phi1 > phi2)


class TestPermeabilityCalculation:
    """Test Timur permeability calculation."""

    def test_calc_permeability_timur_basic(self) -> None:
        """Test basic Timur calculation."""
        phi = np.array([0.05, 0.10, 0.15, 0.20, 0.25])
        k_md = calc_permeability_timur(phi)

        # Check output
        assert isinstance(k_md, np.ndarray)
        assert len(k_md) == len(phi)

        # Check physical validity (clipped range)
        valid_k = k_md[~np.isnan(k_md)]
        assert np.all(valid_k >= 0.01)  # MIN_PERMEABILITY
        assert np.all(valid_k <= 1000.0)  # MAX_PERMEABILITY

    def test_calc_permeability_increases_with_porosity(self) -> None:
        """Test that permeability increases with porosity (Timur relation)."""
        phi_low = np.array([0.05, 0.05, 0.05])
        phi_high = np.array([0.20, 0.20, 0.20])

        k_low = calc_permeability_timur(phi_low)
        k_high = calc_permeability_timur(phi_high)

        # Higher porosity should give higher permeability
        assert np.mean(k_high) > np.mean(k_low)

    def test_calc_permeability_zero_porosity(self) -> None:
        """Test handling of zero/negative porosity."""
        phi = np.array([0, -0.1, 0.15, -0.05])
        k_md = calc_permeability_timur(phi)

        # Zero and negative should give NaN
        assert np.isnan(k_md[0])
        assert np.isnan(k_md[1])
        assert np.isnan(k_md[3])

    def test_calc_permeability_custom_swir(self) -> None:
        """Test Timur with custom water saturation."""
        phi = np.array([0.15, 0.15, 0.15])

        k1 = calc_permeability_timur(phi, swir=0.25)
        k2 = calc_permeability_timur(phi, swir=0.50)

        # Different water saturation should give different results
        assert not np.allclose(k1, k2)


class TestIntegration:
    """Integration tests for full pipeline."""

    def test_full_pipeline(self, sample_las_file: str, tmp_path) -> None:
        """Test complete processing pipeline."""
        from well_analysis import process_well

        output_dir = str(tmp_path)
        df = process_well(sample_las_file, output_dir, well_number="TEST")

        # Check results
        assert "Vsh" in df.columns
        assert "Kn" in df.columns
        assert "Kпр" in df.columns

        # Check files were created
        csv_path = Path(output_dir) / "well_TEST_results.csv"
        png_path = Path(output_dir) / "well_TEST_logplot.png"

        assert csv_path.exists()
        assert png_path.exists()

        # Check CSV content
        df_csv = pd.read_csv(csv_path, sep=";")
        assert len(df_csv) > 0
        assert "Vsh" in df_csv.columns

    def test_pipeline_with_invalid_las(self) -> None:
        """Test pipeline error handling."""
        from well_analysis import process_well

        with pytest.raises((FileNotFoundError, ValueError)):
            process_well("/nonexistent/file.las", ".", "TEST")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=well_analysis"])
