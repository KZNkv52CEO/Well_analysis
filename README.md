# Petrophysical Well Log Analysis (Well #17)

Python script for automated interpretation of well logging data (LAS 2.0 format) without heavy external petrophysical libraries.

## Features
- Custom LAS Parser: Reads LAS 2.0 files directly using standard Python and regular expressions.
- Shale Volume ($V_{sh}$): Computed using the non-linear Larionov formula for young/unconsolidated sediments.
- Effective Porosity ($\phi_e$): Derived from Neutron log (ННК) data with shale correction.
- Permeability ($K_{pr}$): Estimated using the empirical Timur equation (1968).
- Visualization: Generates a professional 5-track well log plot with inverted depth scales, log-scale resistivity/permeability tracks, and customized styling.
- Export: Saves processed results into a structured CSV file.

## Requirements
- numpy
- pandas
- matplotlib

## Usage
1. Place your LAS file named 17.las in the project directory.
2. Run the script:
```bash
python well_analysis.py
