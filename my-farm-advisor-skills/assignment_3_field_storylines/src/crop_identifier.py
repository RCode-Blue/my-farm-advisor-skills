"""
Crop identification module.
Dynamically identifies crops from any data source (CDL, TERN, NSW DPI, etc.)
"""

import pandas as pd
from typing import Dict, List


def identify_crops_from_data(
    field_id: str,
    crop_data: pd.DataFrame,
    field_col: str = 'field_id',
    year_col: str = 'year',
    crop_col: str = 'crop_name',
    pct_col: str = 'pct',
    coverage_threshold: float = 0.80
) -> Dict[str, List[int]]:
    """
    Dynamically identify all crops grown for a field from ANY data source.
    
    Works with:
    - USDA CDL (Iowa, USA): columns [field_id, year, crop_code, crop_name, pct]
    - TERN crop maps (Australia): columns [paddock_id, season, crop_type, area_fraction]
    - NSW DPI crop data (NSW): columns [paddock, planting_year, crop_planted, coverage_pct]
    - AAFC Annual Crop Inventory (Canada): columns [field, year, crop, percentage]
    - Any crop dataset with same structure
    
    Parameters:
    -----------
    field_id : str
        Field identifier (e.g., 'ia-r1-20', 'toowoomba-1', 'wagga-1')
    
    crop_data : pd.DataFrame
        Any crop dataset with columns specified below
    
    field_col : str
        Name of field identifier column in crop_data
        (default: 'field_id', TERN: 'paddock_id', NSW DPI: 'paddock')
    
    year_col : str
        Name of year column in crop_data
        (default: 'year', TERN: 'season', NSW DPI: 'planting_year')
    
    crop_col : str
        Name of crop name column in crop_data
        (default: 'crop_name', TERN: 'crop_type', NSW DPI: 'crop_planted')
    
    pct_col : str
        Name of crop percentage/coverage column in crop_data
        (default: 'pct', TERN: 'area_fraction', NSW DPI: 'coverage_pct')
    
    coverage_threshold : float
        Minimum crop coverage (0-1, default 0.80 = 80%)
        Automatically handles both 0-1 and 0-100 scales
    
    Returns:
    --------
    dict : {crop_name: [year1, year2, ...], ...}
        Crops discovered, with years where each crop is dominant
        Years are sorted ascending within each crop
    
    Raises:
    -------
    ValueError : If field not found in crop_data
    KeyError : If required columns not found in crop_data
    
    Examples:
    ---------
    # USDA CDL (Iowa) - uses default column names
    identify_crops_from_data(
        field_id='ia-r1-20',
        crop_data=cdl_dataframe
    )
    # Returns: {'Corn': [2022, 2024], 'Soybeans': [2021, 2023, 2025]}
    
    # TERN crop maps (Australia, different column names)
    identify_crops_from_data(
        field_id='toowoomba-1',
        crop_data=tern_dataframe,
        field_col='paddock_id',
        year_col='season',
        crop_col='crop_type',
        pct_col='area_fraction'
    )
    # Returns: {'Barley': [2021, 2023], 'Wheat': [2022, 2024], 'Maize': [2020]}
    
    # NSW DPI crop data (different column names again)
    identify_crops_from_data(
        field_id='wagga-1',
        crop_data=nsw_dpi_dataframe,
        field_col='paddock',
        year_col='planting_year',
        crop_col='crop_planted',
        pct_col='coverage_pct'
    )
    # Returns: {'Barley': [...], 'Wheat': [...], 'Canola': [...], 'Pulses': [...]}
    """
    
    # Validate that required columns exist
    required_cols = {field_col, year_col, crop_col, pct_col}
    missing_cols = required_cols - set(crop_data.columns)
    
    if missing_cols:
        raise KeyError(
            f"Missing columns in crop_data: {missing_cols}. "
            f"Available columns: {list(crop_data.columns)}"
        )
    
    # Get all records for this field
    field_data = crop_data[crop_data[field_col] == field_id].sort_values(year_col)
    
    if field_data.empty:
        raise ValueError(f"Field '{field_id}' not found in crop_data")
    
    # Build year → dominant_crop mapping
    crops_by_year = {}
    
    for year in sorted(field_data[year_col].unique()):
        year_data = field_data[field_data[year_col] == year].sort_values(pct_col, ascending=False)
        
        if len(year_data) > 0:
            # Get dominant crop (highest percentage)
            dominant_crop = year_data.iloc[0][crop_col]
            pct = year_data.iloc[0][pct_col]
            
            # Apply coverage threshold
            # Automatically handle both 0-1 scale (decimals) and 0-100 scale (percentages)
            threshold = coverage_threshold if pct <= 1 else coverage_threshold * 100
            
            if pct > threshold:
                crops_by_year[year] = dominant_crop
    
    # Invert to get crop → years mapping
    years_by_crop = {}
    for year, crop in crops_by_year.items():
        if crop not in years_by_crop:
            years_by_crop[crop] = []
        years_by_crop[crop].append(year)
    
    # Sort years within each crop
    for crop in years_by_crop:
        years_by_crop[crop] = sorted(years_by_crop[crop])
    
    return years_by_crop
