# Provenance & Attribution: Grower Web Map Subskill

## Component Attribution

### 1. Leaflet (Mapping Engine)
- **Version:** 1.9.4
- **License:** BSD-2-Clause (Copyright &copy; 2010-2023, Vladimir Agafonkin; Copyright &copy; 2010-2011, CloudMade)
- **Usage:** Vendored under `src/scripts/reporting/vendor/leaflet/` (`leaflet.js`, `leaflet.css`, `LICENSE`)
  and inlined at generation time into `<style>` and `<script>` tags to ensure offline operation.
- **Source:** https://github.com/Leaflet/Leaflet / https://unpkg.com/leaflet@1.9.4/

### 2. Basemap Tiles (Esri World Imagery)
- **Provider:** Esri ArcGIS Online
- **Tile Endpoint:** `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}`
- **Attribution:** Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community.
- **Access:** Keyless, online HTTP GET tile requests.

### 3. Field Polygon Boundaries
- **Source:** Data pipeline runtime boundary files:
  `${DATA_PIPELINE_DATA_ROOT}/data-pipeline/growers/<grower>/farms/<farm>/boundary/field_boundaries.geojson`
- **Lineage:** Ingested via USDA NASS Crop Sequence Boundaries (CSB) through FIBOA GeoParquet
  (`https://data.source.coop/fiboa/us-usda-cropland/`), CC-BY-4.0 / USDA public domain.
- **Checksumming:** SHA-256 checksums of source boundaries are recorded in each grower's
  `manifests/grower_webmap_manifest.json`.
