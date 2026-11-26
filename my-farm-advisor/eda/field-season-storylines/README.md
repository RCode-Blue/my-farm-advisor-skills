# Field-Season Weather & NDVI Storylines

## Overview

This skill generates aligned 4-panel mini-dashboards combining Sentinel NDVI, daily precipitation, temperature extremes, and cumulative Growing Degree Days (GDD) across a growing season (May 1 - October 31). Each dashboard tells the weather-phenology story for one field-year, with automated annotations highlighting key seasonal events (frost, heat stress, heavy rain, drought).

## Example: ia-r1-20 (Kossuth County, Iowa, 2021-2025)

**Field:** 55 hectares in Kossuth County, Iowa  
**Crop Rotation:** Corn (2022, 2024), Soybeans (2021, 2023, 2025)  
**Data Coverage:** Complete (5 years, 1,826 daily weather records, 33 Sentinel NDVI observations)

### Generated Dashboards

| Year | Crop | NDVI Peak | GDD | Precip |
|------|------|-----------|-----|--------|
| 2021 | Soybeans | 0.85 (Aug 22) | 1,765 | 510.8 mm |
| 2022 | Corn | 0.60 (Aug 4) | 1,693 | 383.0 mm |
| 2023 | Soybeans | 0.66 (Aug 12) | 1,796 | 473.5 mm |
| 2024 | Corn | 0.52 (Aug 31) | 1,642 | 697.9 mm |
| 2025 | Soybeans | 0.57 (Jul 14) | 1,669 | 641.8 mm |

**Key Finding:** Within-crop comparisons reveal weather-phenology relationships. 2024 corn (82% wetter) showed lower NDVI peak (0.52 vs 0.60) and later phenology than 2022, suggesting water stress increases canopy vigor. Soybean series shows declining NDVI (0.85→0.57) with earlier peak dates in wetter years.

## Data Inputs (Approved Areas)

- **CDL Crop Classification:** `growers/ia-grower/farms/ia-grower-iowa/derived/tables/ia_grower_iowa_*_cdl.csv`
- **Daily Weather:** `growers/ia-grower/farms/ia-grower-iowa/fields/ia-r1-20/weather/daily_weather.csv` (1,826 records, 2021-2025)
- **Sentinel NDVI:** `growers/ia-grower/farms/ia-grower-iowa/fields/ia-r1-20/satellite/sentinel/` (33 observations, 5-8 per year)
- **Field Boundary:** `growers/ia-grower/farms/ia-grower-iowa/fields/ia-r1-20/boundary/field_boundary.geojson`

## Workflow

1. **Load field data** — CDL, weather, NDVI, boundary from approved inputs
2. **Identify crops** — Dynamically discover crop types from CDL (no hardcoding)
3. **Align data** — Interpolate sparse Sentinel observations to daily values on fixed calendar (May 1 - Oct 31)
4. **Calculate metrics:**
   - Precipitation: daily totals + seasonal sum + heavy rain events (>25mm)
   - Temperature: max/min daily + 7-day rolling average + frost/heat detection
   - GDD: cumulative (base 10°C, capped 30°C) May 1 - Oct 31
5. **Detect events** — Frost (Tmin ≤0°C), heat stress (Tmax >35°C × 3+ days), heavy rain, drought
6. **Render dashboard** — 4 aligned panels with annotations + captions

## Reusable Design

The workflow accepts flexible column parameters and works with any crop dataset (CDL, TERN, NSW DPI, AAFC). No hardcoding of crop names or years — crops are discovered from data.

```python
from src.field_storyline_generator import generate_field_storyline_dashboards

# Generate dashboards for all crops in a field
generate_field_storyline_dashboards(
    field_id='ia-r1-20',
    crop_data=cdl_dataframe,
    crop_field_col='field_id',          # Flexible column names
    crop_year_col='year',
    crop_name_col='crop_name',
    crop_pct_col='pct',
    output_dir='./examples',
    data_root='/path/to/data-pipeline'
)
```

## Rerun the Workflow

```bash
cd my-farm-advisor/eda/field-season-storylines
pip install -r requirements.txt

python3 << 'EOF'
import sys
sys.path.insert(0, './src')
from data_loader import load_crop_data_all_years
from field_storyline_generator import generate_field_storyline_dashboards

# Load CDL data
cdl = load_crop_data_all_years('ia-r1-20', '/home/coder/my-farm-advisor-runtime/data-pipeline')

# Generate all dashboards
generate_field_storyline_dashboards(
    field_id='ia-r1-20',
    crop_data=cdl,
    output_dir='./examples',
    crop_type=None  # None = all crops
)
EOF
```

**Output:** 5 PNG dashboards saved to `examples/` (300 DPI, 16×12 inches)

## Known Limitations

- **Sentinel Revisit:** ~10-day gaps filled by linear interpolation (may mask true phenology)
- **Weather Source:** Satellite-derived (no ground truth validation)
- **Fixed Calendar:** May 1 - Oct 31 for all years; actual planting/harvest may vary
- **GDD Base:** 10°C standard for corn/soybeans; adjust `gdd_base_temp_c` parameter for other crops

## Technical Details

See:
- `STEP_5_SUMMARY.md` — Workflow implementation and test results
- `STEP_6_SUMMARY.md` — Dashboard generation and analysis insights
- `src/` — Six production-ready Python modules (1,107 lines total)

## References

- USDA NASS CDL: https://www.nass.usda.gov/Research_and_Science/Cropland/SARS1a.php
- NASA POWER: https://power.larc.nasa.gov/
- Sentinel-2: https://sentinel.esa.int/web/sentinel/missions/sentinel-2
- GDD Calculation: https://www.extension.purdue.edu/extmedia/GDD_Calculator.xlsx
