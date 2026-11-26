"""
Data loading module for field storyline generation.
Loads crop data, weather data, NDVI observations, and field boundaries.
"""

import pandas as pd
import geopandas as gpd
import rasterio
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional


def load_crop_data_all_years(field_id: str, data_root: str) -> pd.DataFrame:
    """
    Load crop data (CDL, TERN, NSW DPI, etc.) for all available years.
    
    Parameters:
    -----------
    field_id : str
        Field identifier (e.g., 'ia-r1-20')
    
    data_root : str
        Path to data-pipeline root
    
    Returns:
    --------
    pd.DataFrame
        Crop data with columns: field_id, year, crop_code, crop_name, pct
        (Exact columns may vary by data source, but must include field, year, crop, percentage)
    """
    
    # Try to find CDL files in standard location
    cdl_dir = os.path.join(data_root, 'growers/ia-grower/farms/ia-grower-iowa/derived/tables')
    
    if not os.path.exists(cdl_dir):
        raise FileNotFoundError(f"CDL directory not found: {cdl_dir}")
    
    # Load full composition file (has all years)
    full_composition_file = os.path.join(cdl_dir, 'ia_grower_iowa_cdl_2021_2025_full_composition.csv')
    
    if os.path.exists(full_composition_file):
        crop_data = pd.read_csv(full_composition_file)
    else:
        # Fallback: load individual year files and concatenate
        crop_dataframes = []
        for year in range(2021, 2026):
            year_file = os.path.join(cdl_dir, f'ia_grower_iowa_{year}_cdl.csv')
            if os.path.exists(year_file):
                df = pd.read_csv(year_file)
                crop_dataframes.append(df)
        
        if not crop_dataframes:
            raise FileNotFoundError(f"No CDL files found in {cdl_dir}")
        
        crop_data = pd.concat(crop_dataframes, ignore_index=True)
    
    return crop_data


def load_weather_all_years(field_id: str, data_root: str) -> pd.DataFrame:
    """
    Load daily weather data for all available years.
    
    Parameters:
    -----------
    field_id : str
        Field identifier (e.g., 'ia-r1-20')
    
    data_root : str
        Path to data-pipeline root
    
    Returns:
    --------
    pd.DataFrame
        Weather data with columns: date, T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, ...
        Date range: typically 2021-01-01 to 2025-12-31
    """
    
    weather_file = os.path.join(
        data_root,
        f'growers/ia-grower/farms/ia-grower-iowa/fields/{field_id}/weather/daily_weather.csv'
    )
    
    if not os.path.exists(weather_file):
        raise FileNotFoundError(f"Weather file not found: {weather_file}")
    
    weather_data = pd.read_csv(weather_file)
    
    # Convert date column to datetime
    if 'date' in weather_data.columns:
        weather_data['date'] = pd.to_datetime(weather_data['date'])
    
    return weather_data


def load_ndvi_all_years(field_id: str, data_root: str) -> Dict[int, List[Dict]]:
    """
    Load Sentinel NDVI observations for all available years.
    
    Parameters:
    -----------
    field_id : str
        Field identifier (e.g., 'ia-r1-20')
    
    data_root : str
        Path to data-pipeline root
    
    Returns:
    --------
    dict : {year: [{'date': '2022-06-23', 'ndvi': 0.42}, ...], ...}
        NDVI observations grouped by year
        Each observation has 'date' (str) and 'ndvi' (float)
    """
    
    ndvi_base = os.path.join(
        data_root,
        f'growers/ia-grower/farms/ia-grower-iowa/fields/{field_id}/satellite/sentinel'
    )
    
    if not os.path.exists(ndvi_base):
        raise FileNotFoundError(f"NDVI directory not found: {ndvi_base}")
    
    ndvi_all_years = {}
    
    # Iterate through year directories
    for year_dir in sorted(os.listdir(ndvi_base)):
        year_path = os.path.join(ndvi_base, year_dir)
        
        # Skip if not a directory or not a year
        if not os.path.isdir(year_path):
            continue
        
        try:
            year = int(year_dir)
        except ValueError:
            continue  # Skip non-year directories (e.g., manifest.json)
        
        # Collect NDVI observations for this year
        ndvi_obs = []
        
        # Iterate through observation directories (e.g., sentinel_20220623)
        for obs_dir in sorted(os.listdir(year_path)):
            obs_path = os.path.join(year_path, obs_dir)
            
            if not os.path.isdir(obs_path):
                continue
            
            # Look for NDVI GeoTIFF file
            ndvi_file = os.path.join(obs_path, f'{obs_dir}_ndvi.tif')
            
            if os.path.exists(ndvi_file):
                # Extract date from directory name (format: sentinel_YYYYMMDD)
                try:
                    date_str = obs_dir.split('_')[1]  # 'sentinel_20220623' -> '20220623'
                    date_formatted = f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"
                    
                    # Read NDVI value from GeoTIFF
                    with rasterio.open(ndvi_file) as src:
                        data = src.read(1)
                        # Calculate mean NDVI for field (ignore NaN)
                        ndvi_value = float(data[~pd.isna(data)].mean())
                    
                    ndvi_obs.append({
                        'date': date_formatted,
                        'ndvi': ndvi_value
                    })
                
                except (IndexError, ValueError, Exception) as e:
                    print(f"Warning: Could not read NDVI from {ndvi_file}: {str(e)}")
                    continue
        
        if ndvi_obs:
            ndvi_all_years[year] = ndvi_obs
    
    return ndvi_all_years


def load_boundary(field_id: str, data_root: str) -> gpd.GeoDataFrame:
    """
    Load field boundary geometry.
    
    Parameters:
    -----------
    field_id : str
        Field identifier (e.g., 'ia-r1-20')
    
    data_root : str
        Path to data-pipeline root
    
    Returns:
    --------
    gpd.GeoDataFrame
        Field boundary with geometry column
    """
    
    boundary_file = os.path.join(
        data_root,
        f'growers/ia-grower/farms/ia-grower-iowa/fields/{field_id}/boundary/field_boundary.geojson'
    )
    
    if not os.path.exists(boundary_file):
        raise FileNotFoundError(f"Boundary file not found: {boundary_file}")
    
    boundary = gpd.read_file(boundary_file)
    
    return boundary


def load_field_data(field_id: str, data_root: str = '/home/coder/my-farm-advisor-runtime/data-pipeline') -> Dict:
    """
    Load all data for a single field (all available years).
    
    Parameters:
    -----------
    field_id : str
        Field identifier (e.g., 'ia-r1-20')
    
    data_root : str
        Path to data-pipeline root
    
    Returns:
    --------
    dict : {
        'crop_data': DataFrame with crop information,
        'weather': DataFrame with daily weather,
        'ndvi': Dict {year: [observations]},
        'boundary': GeoDataFrame with field polygon
    }
    """
    
    print(f"Loading data for field {field_id}...")
    
    # Load crop data
    print("  Loading crop data...")
    crop_data = load_crop_data_all_years(field_id, data_root)
    
    # Load weather
    print("  Loading weather data...")
    weather = load_weather_all_years(field_id, data_root)
    
    # Load NDVI
    print("  Loading NDVI observations...")
    ndvi = load_ndvi_all_years(field_id, data_root)
    
    # Load boundary
    print("  Loading field boundary...")
    boundary = load_boundary(field_id, data_root)
    
    print(f"✓ Data loaded for {field_id}")
    print(f"  Crop data: {len(crop_data)} records, years {crop_data['year'].min()}-{crop_data['year'].max()}")
    print(f"  Weather: {len(weather)} daily records, {weather['date'].min()} to {weather['date'].max()}")
    print(f"  NDVI: {len(ndvi)} years with observations")
    print(f"  Boundary: {len(boundary)} feature(s)")
    
    return {
        'crop_data': crop_data,
        'weather': weather,
        'ndvi': ndvi,
        'boundary': boundary
    }
