"""Pytest fixtures and configuration."""

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def sample_las_content() -> str:
    """
    Generate sample LAS 2.0 file content for testing.

    Returns:
        Complete LAS file as string
    """
    return """~Version Information Section
 VERS.                  2.0    : LAS Version
 FILM.                  NONE   : Film size
~Well Information
 STRT.M        1068.00:START DEPTH
 STOP.M        1161.90:STOP DEPTH
 STEP.M           0.50:STEP
 NULL.        -999.25:NULL VALUE
 COMP.      TEST WELL:COMPANY
 WELL.         WELL#17:WELL NAME
 FLD .      TEST FIELD:FIELD
 CTRY.         RUSSIA:COUNTRY
 PROV.      TEST PROV:PROVINCE
~Curve Information
 DEPT   .M               :DEPTH
 GR     .API             :GAMMA RAY
 neutron.P.U.            :NEUTRON POROSITY
 PZ     .OHMM            :SHALLOW RESISTIVITY
 LLD    .OHMM            :DEEP RESISTIVITY
~Ascii Data
 1068.00  45.2  0.280  12.5  15.3
 1068.50  48.1  0.260  14.2  18.7
 1069.00  42.5  0.290  10.8  12.1
 1069.50  50.3  0.240  18.5  22.3
 1070.00  38.7  0.310  8.5   9.2
 1070.50  55.2  0.220  25.3  30.1
 1071.00  35.4  0.325  6.2   6.8
 1071.50  58.1  0.200  32.1  40.5
 1072.00  32.1  0.340  4.8   5.1
 1072.50  60.5  0.180  40.2  52.3
"""


@pytest.fixture
def sample_las_file(sample_las_content: str) -> str:
    """
    Create temporary LAS file for testing.

    Args:
        sample_las_content: LAS file content

    Yields:
        Path to temporary LAS file
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".las", delete=False, encoding="utf-8"
    ) as f:
        f.write(sample_las_content)
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    """
    Create sample petrophysical data for testing.

    Returns:
        DataFrame with well log data
    """
    np.random.seed(42)
    n = 100

    return pd.DataFrame(
        {
            "DEPT": np.linspace(1000, 1500, n),
            "GR": np.random.uniform(30, 80, n),
            "neutron": np.random.uniform(0.15, 0.35, n),
            "PZ": np.random.uniform(5, 50, n),
            "LLD": np.random.uniform(8, 60, n),
        }
    )


@pytest.fixture
def malformed_las_content() -> str:
    """
    Generate malformed LAS content for error testing.

    Returns:
        Malformed LAS file content
    """
    return """~Version
 VERS.  2.0
~Curve
 DEPT.M
 GR.API
~Ascii
 NOT NUMERIC DATA
"""
