# Workflow Guide: Grower Interactive Web Map

This guide describes how to configure, generate, and verify grower-level interactive
web maps within the My Farm Advisor data pipeline.

## Architectural Design

The grower web map is designed around three principles:

1. **Self-Contained Portability:** The entire map application, including the Leaflet
   mapping library, styling, GeoJSON boundaries, and application logic, is serialized
   into a single static HTML file. No web server, database, or external asset folder
   is required to inspect the map.
2. **Offline-Resilient Architecture:** By inlining vendored Leaflet JS and CSS, the map
   UI, field polygons, tooltips, sidebar, search filter, and popups function even without
   an active internet connection. When connected to the internet, online satellite tiles
   (Esri World Imagery) automatically load underneath.
3. **Zero Heavy Bloat:** Raw GeoTIFFs, satellite bands, and multi-gigabyte raster files
   are intentionally kept out of the HTML document. Only vector boundary geometries and
   descriptive metadata are included, keeping output size below 200 KB.

## Step-by-Step Workflow

### Step 1: Ensure Field Boundaries are Available
Before running the web map generator, ensure the grower has at least one farm with
`boundary/field_boundaries.geojson` present in the data pipeline runtime.

For example:
```text
${DATA_PIPELINE_DATA_ROOT}/data-pipeline/growers/il-grower/farms/il-grower-illinois/boundary/field_boundaries.geojson
```

### Step 2: Run the Generator Script
Invoke `generate_grower_webmap.py` using the data pipeline virtualenv:

```bash
export DATA_PIPELINE_DATA_ROOT=/home/coder/my-farm-advisor-runtime
cd "${DATA_PIPELINE_DATA_ROOT}/data-pipeline/src"
"${DATA_PIPELINE_DATA_ROOT}/data-pipeline/.venv/bin/python" \
  scripts/reporting/generate_grower_webmap.py --grower-slug il-grower
```

### Step 3: Verify the Output
Inspect the generated HTML report:

```bash
ls -lh "${DATA_PIPELINE_DATA_ROOT}/data-pipeline/growers/il-grower/derived/reports/il-grower_field_webmap.html"
cat "${DATA_PIPELINE_DATA_ROOT}/data-pipeline/growers/il-grower/manifests/grower_webmap_manifest.json"
```

Verify that:
- File size is between 150 KB and 250 KB.
- Polygon count matches the number of features in the source GeoJSON.
- The manifest records correct SHA-256 hashes of input boundaries.

## Interactive Features

- **Field Polygons:** Styled with distinct borders and crop-based semantic colors.
- **Hover Inspection:** Displays quick tooltip with Field ID and crop type.
- **Click Inspection:** Opens a detailed card showing grower slug, farm name, state, county,
  calculated acreage / hectares, crop, CSB sequence ID, and boundary source.
- **Sidebar Field List:** Interactive card list showing all fields across the grower portfolio.
  Clicking any card smoothly flies the camera to that field, opens its popup, and highlights the card.
- **Search & Filter:** Real-time search box filters fields by name, crop, or county.
- **Fit All Button:** Resets viewport to envelope all grower fields.
