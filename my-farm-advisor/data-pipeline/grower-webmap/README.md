# Grower Web Map Subskill

The **Grower Web Map** subskill provides lightweight, interactive HTML web mapping
for agricultural grower field portfolios within the My Farm Advisor data pipeline.

## Overview

Agricultural growers, agronomists, and farm managers need an intuitive way to explore
their full field portfolio geographically without installing specialized GIS software or
running heavy web mapping servers.

This subskill generates a fully self-contained, lightweight single-page HTML map for any
grower. It directly consumes real field boundary polygons produced during the data-pipeline
run and renders them over an online satellite-style basemap (Esri World Imagery) with
interactive popup inspections and field navigation controls.

| Feature | Description |
|---|---|
| **Field Boundaries** | Actual field polygons from data pipeline outputs (USDA CSB / OSM) |
| **Basemap** | High-resolution Esri World Imagery online satellite tiles |
| **Offline Resilience** | Vendored Leaflet 1.9.4 CSS/JS embedded inline; UI functions offline |
| **Interactive Popups** | Click any field to inspect grower, farm, field name, state, county, crop, acreage, and source |
| **Field List Sidebar** | Collapsible sidebar listing all fields with search/filter, crop badges, and click-to-zoom |
| **Lightweight Footprint** | Complete HTML bundle is under 200 KB — no heavy rasters or binary bundles embedded |

## Output Artifacts

For a given grower (e.g., `il-grower`), artifacts are staged under the grower's canonical
runtime directory:

```text
${DATA_PIPELINE_DATA_ROOT}/data-pipeline/growers/<grower_slug>/
├── derived/
│   └── reports/
│       └── <grower_slug>_field_webmap.html      # Self-contained interactive map
└── manifests/
    └── grower_webmap_manifest.json              # Provenance & checksum record
```

## CLI Usage

Run directly from the runtime scripts directory:

```bash
# Generate for a single grower
python scripts/reporting/generate_grower_webmap.py --grower-slug il-grower

# Generate for all existing growers in runtime
python scripts/reporting/generate_grower_webmap.py --all-growers

# Force rebuild
python scripts/reporting/generate_grower_webmap.py --grower-slug ia-grower --force
```

Or run as part of the default pipeline via `scripts/run_farm_pipeline.py`.

## Documentation

- [Local Instructions](AGENTS.md)
- [Workflow Guide](GUIDE.md)
- [Provenance & Attribution](PROVENANCE.md)
