#!/usr/bin/env python3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportGeneralTypeIssues=false
"""Generate lightweight interactive HTML web maps for grower field portfolios.

Builds a self-contained single-file HTML map embedding actual field polygon
boundaries, interactive zoom/pan controls, field navigation sidebar,
satellite-style online basemap (Esri World Imagery), and field metadata popups.
Vendored Leaflet is embedded inline to eliminate external CDN dependencies.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
_LIB_DIR = _SCRIPTS_DIR / "lib"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from paths import (  # noqa: E402
    DATA_ROOT,
    GROWERS_ROOT,
    farm_boundary_path,
    farm_dir,
    grower_dir,
    grower_manifest_dir,
    validate_path_slug,
)

_VENDOR_DIR = Path(__file__).resolve().parent / "vendor" / "leaflet"
_ESRI_IMAGERY_URL = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
)
_ESRI_ATTRIBUTION = (
    "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, "
    "Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community"
)

# Semantic crop color palette for field visualization
_CROP_COLORS: dict[str, str] = {
    "corn": "#eab308",  # amber / corn yellow
    "soybeans": "#22c55e",  # lush green
    "soybean": "#22c55e",
    "wheat": "#f97316",  # orange
    "cotton": "#06b6d4",  # cyan
    "unknown": "#3b82f6",  # blue
}


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _read_vendored_leaflet() -> tuple[str, str]:
    """Read local vendored Leaflet CSS and JS for inlining."""
    css_path = _VENDOR_DIR / "leaflet.css"
    js_path = _VENDOR_DIR / "leaflet.js"

    if not css_path.exists() or not js_path.exists():
        raise FileNotFoundError(
            f"Vendored Leaflet assets missing at {_VENDOR_DIR}. "
            "Ensure leaflet.css and leaflet.js are present."
        )

    css = css_path.read_text(encoding="utf-8")
    js = js_path.read_text(encoding="utf-8")
    return css, js


def _crop_color(crop_name: str | None) -> str:
    key = (crop_name or "").strip().lower()
    return _CROP_COLORS.get(key, _CROP_COLORS["unknown"])


def _collect_grower_fields(grower_slug: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Collect field GeoJSON features and metadata across all farms for a grower."""
    g_dir = grower_dir(grower_slug)
    farms_dir = g_dir / "farms"
    if not farms_dir.exists():
        return [], [], []

    all_features: list[dict[str, Any]] = []
    farms_meta: list[dict[str, Any]] = []
    source_provenance: list[dict[str, Any]] = []

    farm_dirs = sorted([d for d in farms_dir.iterdir() if d.is_dir()])
    for f_dir in farm_dirs:
        farm_slug = f_dir.name
        farm_json_path = f_dir / "farm.json"
        farm_name = farm_slug.replace("-", " ").title()
        if farm_json_path.exists():
            try:
                fdata = json.loads(farm_json_path.read_text(encoding="utf-8"))
                farm_name = fdata.get("display_name") or farm_name
            except Exception:
                pass

        boundary_file = farm_boundary_path(grower_slug, farm_slug)
        if not boundary_file.exists():
            continue

        try:
            bdata = json.loads(boundary_file.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"Warning: could not read {boundary_file}: {exc}", file=sys.stderr)
            continue

        file_hash = _sha256(boundary_file)
        source_provenance.append({
            "farm_slug": farm_slug,
            "boundary_path": str(boundary_file),
            "sha256": file_hash,
            "feature_count": len(bdata.get("features", [])),
        })

        features = bdata.get("features", [])
        for feat in features:
            props = dict(feat.get("properties") or {})
            # Ensure grower and farm context are attached to each field
            props.setdefault("grower_slug", grower_slug)
            props.setdefault("farm_slug", farm_slug)
            props.setdefault("farm_name", farm_name)
            # The field identifier is the field name per requirements
            field_name = props.get("field_id") or props.get("field_slug") or "Field"
            props["field_name"] = str(field_name)
            props["color"] = _crop_color(props.get("crop"))
            feat["properties"] = props
            all_features.append(feat)

        farms_meta.append({
            "farm_slug": farm_slug,
            "farm_name": farm_name,
            "field_count": len(features),
        })

    return all_features, farms_meta, source_provenance


def generate_html(
    *,
    grower_slug: str,
    features: list[dict[str, Any]],
    farms_meta: list[dict[str, Any]],
    css_content: str,
    js_content: str,
) -> str:
    """Render self-contained HTML page embedding Leaflet, GeoJSON, and UI controls."""
    geojson_payload = json.dumps({"type": "FeatureCollection", "features": features})
    total_fields = len(features)
    total_acres = sum(float(f.get("properties", {}).get("area_acres") or 0.0) for f in features)
    total_ha = sum(float(f.get("properties", {}).get("area_ha_est") or 0.0) for f in features)

    # Unique crops represented
    crops = sorted({str(f.get("properties", {}).get("crop") or "Unknown") for f in features})

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{grower_slug} &mdash; Field Portfolio Web Map</title>
  <style>
/* ==========================================================================
   Vendored Leaflet CSS
   ========================================================================== */
{css_content}

/* ==========================================================================
   Grower Web Map Custom Styling
   ========================================================================== */
:root {{
  --bg-primary: #0f172a;
  --bg-secondary: #1e293b;
  --bg-card: rgba(30, 41, 59, 0.92);
  --text-primary: #f8fafc;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;
  --border-color: #334155;
  --accent-blue: #3b82f6;
  --accent-hover: #60a5fa;
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}}

* {{
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}}

html, body {{
  height: 100%;
  width: 100%;
  font-family: var(--font-sans);
  background: var(--bg-primary);
  color: var(--text-primary);
  overflow: hidden;
}}

#app-container {{
  display: flex;
  height: 100%;
  width: 100%;
  position: relative;
}}

/* Sidebar */
#sidebar {{
  width: 380px;
  max-width: 100%;
  height: 100%;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  z-index: 1000;
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.4);
  transition: transform 0.25s ease-in-out;
}}

#sidebar.collapsed {{
  transform: translateX(-100%);
  position: absolute;
}}

.sidebar-header {{
  padding: 1.25rem 1.25rem 1rem 1.25rem;
  background: linear-gradient(180deg, #1e293b 0%, #152238 100%);
  border-bottom: 1px solid var(--border-color);
}}

.sidebar-header .brand {{
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--accent-hover);
  margin-bottom: 0.25rem;
}}

.sidebar-header h1 {{
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
  margin-bottom: 0.5rem;
}}

.stats-grid {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
  margin-top: 0.75rem;
}}

.stat-box {{
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 0.5rem;
  text-align: center;
}}

.stat-box .num {{
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--text-primary);
}}

.stat-box .lbl {{
  font-size: 0.7rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}}

.filter-bar {{
  padding: 0.75rem 1.25rem;
  border-bottom: 1px solid var(--border-color);
  background: rgba(15, 23, 42, 0.3);
  display: flex;
  gap: 0.5rem;
}}

.filter-bar input {{
  flex: 1;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 0.45rem 0.75rem;
  color: var(--text-primary);
  font-size: 0.85rem;
  outline: none;
}}

.filter-bar input:focus {{
  border-color: var(--accent-blue);
}}

.filter-bar button {{
  background: var(--accent-blue);
  color: white;
  border: none;
  border-radius: 6px;
  padding: 0.45rem 0.85rem;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}}

.filter-bar button:hover {{
  background: var(--accent-hover);
}}

.field-list {{
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}}

.field-card {{
  background: rgba(15, 23, 42, 0.5);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 0.75rem 0.9rem;
  cursor: pointer;
  transition: all 0.15s ease-in-out;
  position: relative;
}}

.field-card:hover {{
  background: rgba(59, 130, 246, 0.15);
  border-color: var(--accent-blue);
  transform: translateY(-1px);
}}

.field-card.active {{
  background: rgba(59, 130, 246, 0.25);
  border-color: var(--accent-hover);
  box-shadow: 0 0 0 1px var(--accent-hover);
}}

.field-card-header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.35rem;
}}

.field-name {{
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 0.4rem;
}}

.field-name .color-pip {{
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}}

.crop-badge {{
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.15rem 0.5rem;
  border-radius: 9999px;
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
  border: 1px solid rgba(255, 255, 255, 0.15);
}}

.field-meta-row {{
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
  color: var(--text-secondary);
  line-height: 1.4;
}}

.field-meta-sub {{
  font-size: 0.72rem;
  color: var(--text-muted);
  margin-top: 0.25rem;
}}

.sidebar-footer {{
  padding: 0.75rem 1.25rem;
  border-top: 1px solid var(--border-color);
  background: var(--bg-primary);
  font-size: 0.72rem;
  color: var(--text-muted);
  display: flex;
  justify-content: space-between;
  align-items: center;
}}

/* Map Container */
#map-container {{
  flex: 1;
  height: 100%;
  position: relative;
}}

#map {{
  width: 100%;
  height: 100%;
  background: #0b1120;
}}

/* Toggle Sidebar Button */
.toggle-sidebar-btn {{
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 1001;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  display: none;
}}

@media (max-width: 768px) {{
  .toggle-sidebar-btn {{
    display: block;
  }}
  #sidebar {{
    position: absolute;
    top: 0;
    left: 0;
    bottom: 0;
  }}
}}

/* Custom Leaflet Controls */
.leaflet-bar {{
  border: 1px solid var(--border-color) !important;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4) !important;
  border-radius: 6px !important;
  overflow: hidden;
}}

.leaflet-bar a {{
  background-color: var(--bg-secondary) !important;
  color: var(--text-primary) !important;
  border-bottom: 1px solid var(--border-color) !important;
  transition: background 0.15s;
}}

.leaflet-bar a:hover {{
  background-color: var(--border-color) !important;
  color: var(--accent-hover) !important;
}}

/* Custom Popup */
.leaflet-popup-content-wrapper {{
  background: var(--bg-secondary) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border-color);
  border-radius: 8px !important;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5) !important;
  padding: 0 !important;
}}

.leaflet-popup-tip {{
  background: var(--bg-secondary) !important;
}}

.leaflet-popup-content {{
  margin: 0 !important;
  line-height: 1.4 !important;
}}

.popup-card {{
  padding: 1rem 1.1rem;
  min-width: 260px;
}}

.popup-title {{
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 0.4rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 0.5rem;
}}

.popup-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
  margin-top: 0.4rem;
}}

.popup-table td {{
  padding: 0.25rem 0;
}}

.popup-table td.label {{
  color: var(--text-secondary);
  font-weight: 500;
  width: 40%;
}}

.popup-table td.value {{
  color: var(--text-primary);
  font-weight: 600;
}}

/* Map Legend */
.map-legend {{
  background: var(--bg-card);
  backdrop-filter: blur(8px);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 0.6rem 0.85rem;
  color: var(--text-primary);
  font-size: 0.75rem;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
}}

.map-legend h4 {{
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
  margin-bottom: 0.4rem;
}}

.legend-item {{
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}}

.legend-color {{
  width: 12px;
  height: 12px;
  border-radius: 3px;
  border: 1px solid rgba(255, 255, 255, 0.3);
}}
  </style>
</head>
<body>
  <div id="app-container">
    <aside id="sidebar">
      <div class="sidebar-header">
        <div class="brand">🌾 My Farm Advisor &bull; Web Map</div>
        <h1>{grower_slug}</h1>
        <div class="stats-grid">
          <div class="stat-box">
            <div class="num">{total_fields}</div>
            <div class="lbl">Fields</div>
          </div>
          <div class="stat-box">
            <div class="num">{total_acres:.0f}</div>
            <div class="lbl">Acres</div>
          </div>
          <div class="stat-box">
            <div class="num">{total_ha:.0f}</div>
            <div class="lbl">Hectares</div>
          </div>
        </div>
      </div>

      <div class="filter-bar">
        <input type="text" id="field-search" placeholder="Search fields or crops..." aria-label="Search fields">
        <button type="button" id="fit-all-btn" title="Zoom to fit all grower fields">Fit All</button>
      </div>

      <div class="field-list" id="field-list-container">
        <!-- Rendered via JavaScript -->
      </div>

      <div class="sidebar-footer">
        <span>Farms: {len(farms_meta)}</span>
        <span>Self-contained UI &bull; Esri Basemap</span>
      </div>
    </aside>

    <main id="map-container">
      <button class="toggle-sidebar-btn" id="toggle-sidebar-btn" type="button">☰ Fields</button>
      <div id="map"></div>
    </main>
  </div>

  <script>
/* ==========================================================================
   Vendored Leaflet JS
   ========================================================================== */
{js_content}

/* ==========================================================================
   Grower Map Interactive Application Logic
   ========================================================================== */
(function() {{
  const geojsonData = {geojson_payload};
  const growerSlug = {json.dumps(grower_slug)};

  // Initialize Leaflet map
  const map = L.map("map", {{
    zoomControl: false,
    minZoom: 3,
    maxZoom: 19,
  }});

  // Place zoom control in top-right
  L.control.zoom({{ position: "topright" }}).addTo(map);

  // Satellite-style online basemap (Esri World Imagery)
  const esriSatellite = L.tileLayer({json.dumps(_ESRI_IMAGERY_URL)}, {{
    attribution: {json.dumps(_ESRI_ATTRIBUTION)},
    maxZoom: 19,
    maxNativeZoom: 18,
  }}).addTo(map);

  // Layer dictionary to track map layers by field_name/field_id
  const fieldLayers = {{}};
  let activeFieldCard = null;

  // Build popup card HTML for a field
  function buildPopupContent(props) {{
    const fieldName = props.field_name || props.field_id || "Field";
    const farmName = props.farm_name || props.farm_slug || "Farm";
    const crop = props.crop || "Unknown";
    const county = props.county || "Unknown";
    const state = props.state || "Unknown";
    const acres = props.area_acres != null ? Number(props.area_acres).toFixed(1) + " ac" : "N/A";
    const ha = props.area_ha_est != null ? Number(props.area_ha_est).toFixed(1) + " ha" : "N/A";
    const csbId = props.csb_id || "N/A";
    const source = props.source || "usda_csb_fiboa";

    return `
      <div class="popup-card">
        <div class="popup-title">
          <span>${{fieldName}}</span>
          <span class="crop-badge" style="background:${{props.color}}33; border-color:${{props.color}}">${{crop}}</span>
        </div>
        <table class="popup-table">
          <tr><td class="label">Grower</td><td class="value">${{props.grower_slug || growerSlug}}</td></tr>
          <tr><td class="label">Farm</td><td class="value">${{farmName}}</td></tr>
          <tr><td class="label">State</td><td class="value">${{state}}</td></tr>
          <tr><td class="label">County</td><td class="value">${{county}}</td></tr>
          <tr><td class="label">Area</td><td class="value">${{acres}} (${{ha}})</td></tr>
          <tr><td class="label">Crop</td><td class="value">${{crop}}</td></tr>
          <tr><td class="label">CSB ID</td><td class="value">${{csbId}}</td></tr>
          <tr><td class="label">Source</td><td class="value">${{source}}</td></tr>
        </table>
      </div>
    `;
  }}

  // GeoJSON Layer styling & event bindings
  const geojsonLayer = L.geoJSON(geojsonData, {{
    style: function(feature) {{
      const color = feature.properties.color || "#3b82f6";
      return {{
        color: color,
        weight: 2.5,
        opacity: 0.95,
        fillColor: color,
        fillOpacity: 0.35,
      }};
    }},
    onEachFeature: function(feature, layer) {{
      const props = feature.properties || {{}};
      const fieldId = props.field_name || props.field_id;
      if (fieldId) {{
        fieldLayers[fieldId] = layer;
      }}

      // Bind tooltip for quick hover identification
      layer.bindTooltip(fieldId + " (" + (props.crop || "") + ")", {{
        sticky: true,
        direction: "top",
        offset: [0, -8],
      }});

      // Bind popup with full metadata
      layer.bindPopup(buildPopupContent(props), {{
        maxWidth: 320,
      }});

      // Interactive hover & selection effects
      layer.on({{
        mouseover: function(e) {{
          const target = e.target;
          target.setStyle({{
            weight: 4,
            fillOpacity: 0.6,
          }});
          target.bringToFront();
        }},
        mouseout: function(e) {{
          geojsonLayer.resetStyle(e.target);
        }},
        click: function(e) {{
          highlightFieldInList(fieldId);
        }}
      }});
    }}
  }}).addTo(map);

  // Fit bounds to all fields
  function fitAllFields() {{
    const bounds = geojsonLayer.getBounds();
    if (bounds.isValid()) {{
      map.fitBounds(bounds, {{ padding: [40, 40], maxZoom: 15 }});
    }}
  }}
  fitAllFields();

  // Populate Sidebar Field List
  const listContainer = document.getElementById("field-list-container");
  const features = geojsonData.features || [];

  function renderFieldList(items) {{
    listContainer.innerHTML = "";
    if (items.length === 0) {{
      listContainer.innerHTML = '<div style="color:var(--text-muted);padding:1rem;text-align:center;">No matching fields found.</div>';
      return;
    }}

    items.forEach(function(feat) {{
      const p = feat.properties || {{}};
      const fieldId = p.field_name || p.field_id;
      const color = p.color || "#3b82f6";

      const card = document.createElement("div");
      card.className = "field-card";
      card.id = "card-" + fieldId;

      card.innerHTML = `
        <div class="field-card-header">
          <span class="field-name">
            <span class="color-pip" style="background:${{color}}"></span>
            ${{fieldId}}
          </span>
          <span class="crop-badge" style="border-color:${{color}}88">${{p.crop || "Unknown"}}</span>
        </div>
        <div class="field-meta-row">
          <span>${{p.county || ""}}, ${{p.state || ""}}</span>
          <span>${{p.area_acres != null ? Number(p.area_acres).toFixed(1) + " ac" : ""}}</span>
        </div>
        <div class="field-meta-sub">
          Farm: ${{p.farm_name || p.farm_slug || "Default"}} &bull; ${{p.area_ha_est != null ? Number(p.area_ha_est).toFixed(1) + " ha" : ""}}
        </div>
      `;

      card.addEventListener("click", function() {{
        selectField(fieldId);
      }});

      listContainer.appendChild(card);
    }});
  }}

  renderFieldList(features);

  // Select field: zoom map, open popup, highlight sidebar card
  function selectField(fieldId) {{
    const layer = fieldLayers[fieldId];
    if (!layer) return;

    // Highlight card
    if (activeFieldCard) {{
      activeFieldCard.classList.remove("active");
    }}
    const card = document.getElementById("card-" + fieldId);
    if (card) {{
      card.classList.add("active");
      card.scrollIntoView({{ behavior: "smooth", block: "nearest" }});
      activeFieldCard = card;
    }}

    // Zoom and open popup
    const bounds = layer.getBounds();
    map.flyToBounds(bounds, {{
      padding: [60, 60],
      maxZoom: 16,
      duration: 1.0,
    }});

    setTimeout(function() {{
      layer.openPopup();
    }}, 400);
  }}

  function highlightFieldInList(fieldId) {{
    if (activeFieldCard) {{
      activeFieldCard.classList.remove("active");
    }}
    const card = document.getElementById("card-" + fieldId);
    if (card) {{
      card.classList.add("active");
      card.scrollIntoView({{ behavior: "smooth", block: "nearest" }});
      activeFieldCard = card;
    }}
  }}

  // Fit All button
  document.getElementById("fit-all-btn").addEventListener("click", function() {{
    fitAllFields();
    if (activeFieldCard) {{
      activeFieldCard.classList.remove("active");
      activeFieldCard = null;
    }}
    map.closePopup();
  }});

  // Filter input
  document.getElementById("field-search").addEventListener("input", function(e) {{
    const q = e.target.value.trim().toLowerCase();
    const filtered = features.filter(function(feat) {{
      const p = feat.properties || {{}};
      const name = (p.field_name || p.field_id || "").toLowerCase();
      const crop = (p.crop || "").toLowerCase();
      const county = (p.county || "").toLowerCase();
      const farm = (p.farm_name || p.farm_slug || "").toLowerCase();
      return name.includes(q) || crop.includes(q) || county.includes(q) || farm.includes(q);
    }});
    renderFieldList(filtered);
  }});

  // Mobile sidebar toggle
  const toggleBtn = document.getElementById("toggle-sidebar-btn");
  const sidebar = document.getElementById("sidebar");
  if (toggleBtn && sidebar) {{
    toggleBtn.addEventListener("click", function() {{
      sidebar.classList.toggle("collapsed");
    }});
  }}

  // Crop legend control on the map
  const legend = L.control({{ position: "bottomright" }});
  legend.onAdd = function() {{
    const div = L.DomUtil.create("div", "map-legend");
    const cropColors = {json.dumps(_CROP_COLORS)};
    let html = "<h4>Crop Legend</h4>";
    const activeCrops = {json.dumps(crops)};
    activeCrops.forEach(function(crop) {{
      const color = cropColors[crop.toLowerCase()] || "#3b82f6";
      html += '<div class="legend-item"><span class="legend-color" style="background:' + color + '"></span><span>' + crop + '</span></div>';
    }});
    div.innerHTML = html;
    return div;
  }};
  legend.addTo(map);
}})();
  </script>
</body>
</html>
"""
    return html


def generate_for_grower(
    grower_slug: str,
    *,
    farm_slug_filter: str | None = None,
    force: bool = False,
) -> Path | None:
    """Generate the self-contained HTML field web map for a single grower."""
    grower_slug = validate_path_slug(grower_slug, "grower_slug")
    features, farms_meta, source_provenance = _collect_grower_fields(grower_slug)

    if farm_slug_filter:
        features = [
            f for f in features if f.get("properties", {}).get("farm_slug") == farm_slug_filter
        ]
        farms_meta = [fm for fm in farms_meta if fm.get("farm_slug") == farm_slug_filter]

    if not features:
        print(f"[{grower_slug}] No field boundaries found; skipping map generation.")
        return None

    g_dir = grower_dir(grower_slug)
    reports_dir = g_dir / "derived" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    output_path = reports_dir / f"{grower_slug}_field_webmap.html"

    if output_path.exists() and not force:
        # Check if source boundaries are unchanged
        manifest_file = grower_manifest_dir(grower_slug) / "grower_webmap_manifest.json"
        if manifest_file.exists():
            try:
                mdata = json.loads(manifest_file.read_text(encoding="utf-8"))
                cached_sources = {s["boundary_path"]: s["sha256"] for s in mdata.get("sources", [])}
                current_sources = {s["boundary_path"]: s["sha256"] for s in source_provenance}
                if cached_sources == current_sources:
                    print(f"[{grower_slug}] Web map up to date: {output_path}")
                    return output_path
            except Exception:
                pass

    css_content, js_content = _read_vendored_leaflet()

    html = generate_html(
        grower_slug=grower_slug,
        features=features,
        farms_meta=farms_meta,
        css_content=css_content,
        js_content=js_content,
    )

    output_path.write_text(html, encoding="utf-8")
    html_size = output_path.stat().st_size

    # Write provenance manifest
    manifest_data = {
        "grower_slug": grower_slug,
        "output_path": str(output_path),
        "html_size_bytes": html_size,
        "html_size_kb": round(html_size / 1024, 1),
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "field_count": len(features),
        "farms": farms_meta,
        "sources": source_provenance,
        "basemap": {
            "name": "Esri World Imagery",
            "tile_url": _ESRI_IMAGERY_URL,
            "attribution": _ESRI_ATTRIBUTION,
        },
        "leaflet_version": "1.9.4",
        "vendored_assets": {
            "css": str(_VENDOR_DIR / "leaflet.css"),
            "js": str(_VENDOR_DIR / "leaflet.js"),
            "license": "BSD-2-Clause",
        },
    }

    m_dir = grower_manifest_dir(grower_slug)
    m_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = m_dir / "grower_webmap_manifest.json"
    manifest_path.write_text(json.dumps(manifest_data, indent=2) + "\n", encoding="utf-8")

    print(f"✓ [{grower_slug}] Web map generated → {output_path}")
    print(f"  Fields: {len(features)} across {len(farms_meta)} farm(s)")
    print(f"  Size: {html_size / 1024:.1f} KB (self-contained with vendored Leaflet)")
    print(f"  Manifest: {manifest_path}")

    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate lightweight interactive HTML web maps for grower field portfolios"
    )
    parser.add_argument(
        "--grower-slug",
        default=os.environ.get("AG_GROWER_SLUG"),
        help="Target grower slug (defaults to AG_GROWER_SLUG env)",
    )
    parser.add_argument(
        "--farm-slug",
        default=os.environ.get("AG_FARM_SLUG"),
        help="Optional farm slug filter within grower",
    )
    parser.add_argument(
        "--all-growers",
        action="store_true",
        help="Scan and generate web maps for all existing growers in runtime",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=os.environ.get("AG_FORCE") == "1",
        help="Force regeneration even if output and sources are unchanged",
    )
    args = parser.parse_args(argv)

    if args.all_growers:
        if not GROWERS_ROOT.exists():
            print(f"Growers root does not exist: {GROWERS_ROOT}", file=sys.stderr)
            return 1
        growers = sorted([
            d.name for d in GROWERS_ROOT.iterdir()
            if d.is_dir() and not d.name.startswith(".") and d.name != "shared"
        ])
        if not growers:
            print("No growers found to process.")
            return 0
        success = True
        for g in growers:
            res = generate_for_grower(g, farm_slug_filter=args.farm_slug, force=args.force)
            if res is None:
                success = False
        return 0 if success else 1

    grower_slug = args.grower_slug
    if not grower_slug:
        parser.error("Specify --grower-slug or --all-growers")

    out = generate_for_grower(grower_slug, farm_slug_filter=args.farm_slug, force=args.force)
    return 0 if out is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
