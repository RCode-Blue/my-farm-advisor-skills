"""
HTML generation utilities for field-season storylines dashboards.

Provides two functions:
1. Optional HTML generation within the skill workflow
2. Standalone HTML summary generation from existing graphics
"""

import os
import json
import pickle
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any


def create_field_dashboard_summary(
    field_id: str,
    output_dir: str,
    graphics_dir: Optional[str] = None,
    title: Optional[str] = None
) -> str:
    """
    Generate HTML summary for field-level dashboards (independent utility).
    
    Takes existing PNG dashboards and pickle event summaries and creates
    a polished HTML viewer. Can be run independently after graphics are generated.
    
    Args:
        field_id: Field identifier (e.g., "ia-r1-20")
        output_dir: Directory where HTML file will be saved
        graphics_dir: Directory containing PNG images and pickle files.
                     If None, uses output_dir
        title: Custom title for the dashboard. If None, auto-generated from field_id
    
    Returns:
        Path to generated HTML file
    
    Example:
        create_field_dashboard_summary(
            field_id="ia-r1-20",
            output_dir="/path/to/outputs",
            graphics_dir="/path/to/outputs",
            title="Iowa Field ia-r1-20 - Seasonal Analysis"
        )
    """
    if graphics_dir is None:
        graphics_dir = output_dir
    
    graphics_dir = Path(graphics_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all dashboards for this field
    dashboards = sorted(graphics_dir.glob(f"{field_id}_*_dashboard.png"))
    
    if not dashboards:
        raise FileNotFoundError(f"No dashboards found for field {field_id} in {graphics_dir}")
    
    # Load event summary if available
    pickle_file = graphics_dir / f"{field_id}_dashboard_info.pkl"
    event_data = {}
    
    if pickle_file.exists():
        try:
            with open(pickle_file, 'rb') as f:
                event_list = pickle.load(f)
                # Convert to dict keyed by year for easier lookup
                for event in event_list:
                    year = event['year']
                    event_data[year] = event
        except Exception as e:
            print(f"Warning: Could not load pickle file: {e}")
    
    # Parse dashboard filenames to get years and crops
    dashboard_info = {}
    for dashboard in dashboards:
        filename = dashboard.stem  # e.g., "ia-r1-20_2021_soybeans_dashboard"
        parts = filename.split('_')
        if len(parts) >= 3:
            year = parts[-3]
            crop = parts[-2]
            try:
                year = int(year)
                dashboard_info[year] = {
                    'file': dashboard.name,
                    'crop': crop,
                    'relative_path': os.path.relpath(dashboard, output_dir)
                }
            except ValueError:
                pass
    
    if not dashboard_info:
        raise ValueError(f"Could not parse dashboard filenames for field {field_id}")
    
    # Sort by year
    sorted_years = sorted(dashboard_info.keys())
    
    # Generate title
    if title is None:
        title = f"Field {field_id} - Seasonal Analysis"
    
    # Create HTML
    html_content = _generate_html(
        field_id=field_id,
        title=title,
        dashboard_info=dashboard_info,
        sorted_years=sorted_years,
        event_data=event_data
    )
    
    # Save HTML file
    html_file = output_dir / f"{field_id}_dashboard_summary.html"
    with open(html_file, 'w') as f:
        f.write(html_content)
    
    return str(html_file)


def generate_html_for_skill(
    field_id: str,
    dashboards: List[str],
    event_data: Optional[Dict[int, Any]] = None,
    output_dir: str = None,
    title: Optional[str] = None
) -> str:
    """
    Generate HTML within the skill workflow (optional parameter in skill).
    
    This function is called by the field-season-storylines skill when
    generate_html=True parameter is set.
    
    Args:
        field_id: Field identifier
        dashboards: List of paths to dashboard PNG files
        event_data: Dictionary of event summaries (from pickle files), keyed by year
        output_dir: Directory where HTML will be saved
        title: Custom title for dashboard
    
    Returns:
        Path to generated HTML file
    """
    if output_dir is None:
        output_dir = Path(dashboards[0]).parent
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Parse dashboards to get years and crops
    dashboard_info = {}
    for dashboard_path in dashboards:
        dashboard_path = Path(dashboard_path)
        filename = dashboard_path.stem
        
        parts = filename.split('_')
        if len(parts) >= 3:
            year = parts[-3]
            crop = parts[-2]
            try:
                year = int(year)
                dashboard_info[year] = {
                    'file': dashboard_path.name,
                    'crop': crop,
                    'relative_path': os.path.relpath(dashboard_path, output_dir)
                }
            except ValueError:
                pass
    
    sorted_years = sorted(dashboard_info.keys())
    
    if title is None:
        title = f"Field {field_id} - Seasonal Analysis"
    
    if event_data is None:
        event_data = {}
    
    html_content = _generate_html(
        field_id=field_id,
        title=title,
        dashboard_info=dashboard_info,
        sorted_years=sorted_years,
        event_data=event_data
    )
    
    html_file = output_dir / f"{field_id}_dashboard_summary.html"
    with open(html_file, 'w') as f:
        f.write(html_content)
    
    return str(html_file)


def _generate_html(
    field_id: str,
    title: str,
    dashboard_info: Dict[int, Dict],
    sorted_years: List[int],
    event_data: Dict[int, Any]
) -> str:
    """
    Generate HTML content (internal utility).
    
    Creates the actual HTML markup for the dashboard viewer.
    """
    
    # Build year buttons
    year_buttons_html = ""
    for year in sorted_years:
        year_buttons_html += f'<button class="year-btn" onclick="showYear({year})">{year}</button>'
    
    # Build dashboard galleries
    galleries_html = ""
    for year in sorted_years:
        info = dashboard_info[year]
        events_html = _get_events_html(year, event_data)
        metadata_html = _get_metadata_html(year, event_data, info)
        
        style = "display: none;" if year != sorted_years[0] else "display: block;"
        
        galleries_html += f"""
    <div id="year-{year}" class="year-gallery" style="{style}">
        <div class="gallery-header">
            <h2>{field_id} - {year} ({info['crop']})</h2>
            {metadata_html}
        </div>
        
        <div class="dashboard-container">
            <img src="{info['relative_path']}" alt="Dashboard for {year}" class="dashboard-image">
        </div>
        
        {events_html}
    </div>
"""
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        
        .controls {{
            background: #f8f9fa;
            padding: 20px;
            border-bottom: 1px solid #dee2e6;
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            align-items: center;
            justify-content: center;
        }}
        
        .year-btn {{
            padding: 10px 20px;
            border: 2px solid #667eea;
            background: white;
            color: #667eea;
            border-radius: 6px;
            cursor: pointer;
            font-size: 1em;
            font-weight: 600;
            transition: all 0.3s ease;
        }}
        
        .year-btn:hover {{
            background: #667eea;
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }}
        
        .year-btn.active {{
            background: #667eea;
            color: white;
        }}
        
        .content {{
            padding: 30px;
        }}
        
        .year-gallery {{
            animation: fadeIn 0.3s ease-in-out;
        }}
        
        @keyframes fadeIn {{
            from {{
                opacity: 0;
            }}
            to {{
                opacity: 1;
            }}
        }}
        
        .gallery-header {{
            margin-bottom: 30px;
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 20px;
        }}
        
        .gallery-header h2 {{
            color: #333;
            margin-bottom: 15px;
            font-size: 1.8em;
        }}
        
        .metadata {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 10px;
        }}
        
        .metadata-item {{
            background: #f0f7ff;
            padding: 12px;
            border-left: 4px solid #667eea;
            border-radius: 4px;
        }}
        
        .metadata-label {{
            font-weight: 600;
            color: #667eea;
            font-size: 0.9em;
            text-transform: uppercase;
        }}
        
        .metadata-value {{
            color: #333;
            font-size: 1.1em;
            margin-top: 4px;
        }}
        
        .dashboard-container {{
            margin: 30px 0;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }}
        
        .dashboard-image {{
            width: 100%;
            height: auto;
            display: block;
            background: #f8f9fa;
        }}
        
        .events-section {{
            margin-top: 30px;
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
        }}
        
        .events-section h3 {{
            color: #333;
            margin-bottom: 15px;
            font-size: 1.3em;
        }}
        
        .events-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 15px;
        }}
        
        .event-card {{
            background: white;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #667eea;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }}
        
        .event-type {{
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: 600;
            text-transform: uppercase;
            margin-bottom: 8px;
        }}
        
        .event-type.dry_spell {{
            background: #e67e22;
        }}
        
        .event-type.heavy_rain {{
            background: #3498db;
        }}
        
        .event-type.heat_stress {{
            background: #e74c3c;
        }}
        
        .event-type.frost {{
            background: #2c3e50;
        }}
        
        .event-date {{
            font-weight: 600;
            color: #667eea;
            font-size: 0.9em;
        }}
        
        .event-description {{
            color: #555;
            margin-top: 8px;
            font-size: 0.95em;
        }}
        
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            border-top: 1px solid #dee2e6;
            font-size: 0.9em;
        }}
        
        .footer p {{
            margin: 5px 0;
        }}
        
        @media (max-width: 768px) {{
            .header {{
                padding: 30px 20px;
            }}
            
            .header h1 {{
                font-size: 1.8em;
            }}
            
            .controls {{
                padding: 15px;
                gap: 8px;
            }}
            
            .year-btn {{
                padding: 8px 15px;
                font-size: 0.9em;
            }}
            
            .content {{
                padding: 15px;
            }}
            
            .metadata {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <p>Field-Season Weather & Vegetation Analysis</p>
        </div>
        
        <div class="controls">
            <span style="color: #667; font-weight: 600;">Select Year:</span>
            {year_buttons_html}
        </div>
        
        <div class="content">
            {galleries_html}
        </div>
        
        <div class="footer">
            <p><strong>Field-Season Storylines</strong> - Aligned NDVI, Weather & GDD Analysis</p>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
    
    <script>
        function showYear(year) {{
            // Hide all galleries
            document.querySelectorAll('.year-gallery').forEach(el => {{
                el.style.display = 'none';
            }});
            
            // Remove active class from all buttons
            document.querySelectorAll('.year-btn').forEach(btn => {{
                btn.classList.remove('active');
            }});
            
            // Show selected gallery
            document.getElementById('year-' + year).style.display = 'block';
            
            // Add active class to clicked button
            event.target.classList.add('active');
        }}
        
        // Initialize first year as active
        document.querySelectorAll('.year-btn')[0].classList.add('active');
    </script>
</body>
</html>
"""
    
    return html


def _get_events_html(year: int, event_data: Dict[int, Any]) -> str:
    """Generate HTML for detected events."""
    
    if year not in event_data:
        return ""
    
    events = event_data[year].get('events', [])
    
    if not events:
        return ""
    
    events_html = '<div class="events-section">\n<h3>Detected Events</h3>\n<div class="events-grid">\n'
    
    for event in events:
        event_type = event.get('type', 'unknown')
        event_date = event.get('date', 'Unknown')
        event_desc = event.get('description', '')
        
        events_html += f"""        <div class="event-card">
            <div class="event-type {event_type}">{event_type.replace('_', ' ')}</div>
            <div class="event-date">{event_date}</div>
            <div class="event-description">{event_desc}</div>
        </div>
"""
    
    events_html += '    </div>\n</div>'
    
    return events_html


def _get_metadata_html(year: int, event_data: Dict[int, Any], dashboard_info: Dict) -> str:
    """Generate HTML for dashboard metadata."""
    
    metadata_html = '<div class="metadata">\n'
    
    # Crop info (from filename parsing)
    crop = dashboard_info.get('crop', 'Unknown')
    metadata_html += f"""        <div class="metadata-item">
            <div class="metadata-label">Crop</div>
            <div class="metadata-value">{crop}</div>
        </div>
"""
    
    if year in event_data:
        event = event_data[year]
        
        # NDVI stats
        ndvi_stats = event.get('ndvi_stats', {})
        if ndvi_stats:
            peak_ndvi = ndvi_stats.get('peak_ndvi_value', 0)
            peak_date = ndvi_stats.get('peak_ndvi_date', 'Unknown')
            metadata_html += f"""        <div class="metadata-item">
            <div class="metadata-label">Peak NDVI</div>
            <div class="metadata-value">{peak_ndvi:.4f} on {peak_date}</div>
        </div>
"""
        
        # Metrics
        metrics = event.get('metrics', {})
        
        # Total precipitation
        precip_data = metrics.get('precip', None)
        if precip_data is not None:
            try:
                total_precip = precip_data['daily_precip_mm'].sum()
                metadata_html += f"""        <div class="metadata-item">
            <div class="metadata-label">Total Precipitation</div>
            <div class="metadata-value">{total_precip:.1f} mm</div>
        </div>
"""
            except:
                pass
        
        # GDD
        gdd_data = metrics.get('gdd', None)
        if gdd_data is not None:
            try:
                total_gdd = gdd_data['cumulative_gdd'].iloc[-1]
                metadata_html += f"""        <div class="metadata-item">
            <div class="metadata-label">Cumulative GDD</div>
            <div class="metadata-value">{total_gdd:.1f}°C</div>
        </div>
"""
            except:
                pass
        
        # Event count
        events = event.get('events', [])
        event_count = len(events)
        metadata_html += f"""        <div class="metadata-item">
            <div class="metadata-label">Detected Events</div>
            <div class="metadata-value">{event_count} events</div>
        </div>
"""
    
    metadata_html += '    </div>'
    
    return metadata_html
