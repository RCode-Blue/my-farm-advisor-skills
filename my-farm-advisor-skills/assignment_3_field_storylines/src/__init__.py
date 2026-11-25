"""
Assignment 3: Field-Season Weather & NDVI Storylines

This package provides tools for generating aligned mini-dashboards showing
NDVI, precipitation, temperature, and cumulative GDD for field-year combinations.

Modules:
- data_loader: Load crop data, weather, NDVI, field boundaries from any source
- crop_identifier: Dynamically identify crops from CDL, TERN, NSW DPI, etc.
- ndvi_processor: Align NDVI observations with weather on fixed calendar window
- weather_metrics: Calculate GDD, temperature metrics, detect weather events
- field_storyline_generator: Main orchestration engine
- dashboard_renderer: (placeholder for Step 5) Create matplotlib figures

Usage:
    from field_storyline_generator import generate_field_storyline_dashboards
    
    # Generate dashboards for a field
    generate_field_storyline_dashboards(
        field_id='ia-r1-20',
        crop_data=cdl_dataframe,
        output_dir='./output'
    )
"""

__version__ = '0.1.0'
__author__ = 'my-farm-advisor team'

from .data_loader import load_field_data, load_crop_data_all_years
from .crop_identifier import identify_crops_from_data
from .ndvi_processor import align_year_on_calendar
from .weather_metrics import calculate_metrics
from .field_storyline_generator import generate_field_storyline_dashboards

__all__ = [
    'load_field_data',
    'load_crop_data_all_years',
    'identify_crops_from_data',
    'align_year_on_calendar',
    'calculate_metrics',
    'generate_field_storyline_dashboards',
]
