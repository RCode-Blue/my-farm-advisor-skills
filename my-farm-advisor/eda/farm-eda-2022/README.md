# Farm EDA (2022-focused)

Static exploratory outputs for the three Assignment 2 farms (Iowa, Illinois, Nebraska).
Document-routed under `my-farm-advisor/eda/`. Not a separate runtime skill.

## Story

2022 was the driest year for all three farms. Year-to-year weather changed far more than
field-to-field differences within a farm. Crop share responses are shown as correlations,
not causes.

## Caveats

- **One weather record per farm.** Every field in a farm shares the same weather series,
  so weather figures describe a single site, not a field spread.
- **Small samples.** Five years and three farms. Correlations use n = 3 to 30 and are
  exploratory only.
- **CDL 2025** is after the course's 2026-02-01 data cutoff (exception, recorded here).
- **Illinois crop switch.** Five fields switched to soybeans in 2024 and most returned to corn
  in 2025. Planting-window rainfall does not explain it: 2024 had 177 mm, 2021 had 155 mm
  (corn), and 2023 had 77 mm.
- **Soil** is out of scope. The Iowa farm is soil-uniform in the final set, so it is not
  part of the story.

## EDA skill

The EDA skill (located in `my-farm-advisor/eda/farm-eda-2022/`) generates exploratory outputs for the three farms in the assignment (Iowa, Illinois, and Nebraska).

It reads farm data from runtime tables and creates visualizations and CSV summaries, combined in a single HTML report for viewing.

### Structure

- Script is located in `scripts/build_eda.py`
- It loads field boundaries, weather, and CDL from the farms' runtime tables and generates charts and summaries related to weather, field boundaries, and crop types
- Outputs are written to `${DATA_PIPELINE_DATA_ROOT}/data-pipeline/eda/` (untracked runtime path)
- A committed `README.md` documents what the skill generates and where to find the outputs


## Outputs

Written to `${DATA_PIPELINE_DATA_ROOT}/data-pipeline/eda/` (untracked runtime path).

| File | Category | Shows |
|---|---|---|
| `boundary_size_by_farm.png` | Boundaries | Field size per farm, median marked |
| `boundary_spacing_by_farm.png` | Boundaries | Nearest-neighbour distance between field centres |
| `boundary_size_vs_changes.png` / `.csv` | Boundaries (comparison) | Field size vs dominant-crop changes, r = 0.18 |
| `map_fields_by_farm.png` | Boundaries (map) | Real field boundaries per farm |
| `weather_annual_precip_by_farm.png` / `.csv` | Weather | Annual precipitation by farm, 2022 highlighted |
| `weather_cumulative_precip_by_doy.png` | Weather | Cumulative precipitation by day of year, 2022 highlighted |
| `weather_2022_vs_other_years.png` / `.csv` | Weather (comparison) | 2022 vs mean of other years: Iowa -26%, Illinois -14%, Nebraska -36% |
| `map_weather_2022_by_farm.png` | Weather (map) | Farm locations with 2022 precipitation |
| `cdl_farm_share_by_year.png` / `.csv` | CDL | Area-weighted corn and soybean share per farm, per year |
| `cdl_field_heatmap.png` | CDL | Per-field corn and soybean share, per year |
| `cdl_illinois_planting_rain_vs_soy.png` | CDL (comparison) | Illinois planting-window rain vs soybean share, r = -0.49, n = 5 |
| `map_cdl_dominant_2022.png` | CDL (map) | Dominant crop per field, 2022 |

`NOTES.txt` lists the headline numbers.

## Running

```bash
export DATA_PIPELINE_DATA_ROOT=/home/coder/my-farm-advisor-runtime
cd "${DATA_PIPELINE_DATA_ROOT}/data-pipeline"
./.venv/bin/python /home/coder/workspace/assignment-1/my-farm-advisor/eda/farm-eda-2022/scripts/build_eda.py
```

Set `EDA_OUT_DIR` to write elsewhere. Report generation is not part of this subskill.

## Sources

- Runtime farm tables: CDL composition, weather, and field boundaries, from `growers/<grower>/farms/<farm>/`.
- Nearest-neighbour spacing is centre-to-centre in metres (EPSG:6933). It differs from the
  earlier pairwise-median figures, so do not compare them directly.
