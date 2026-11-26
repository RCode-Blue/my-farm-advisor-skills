"""
NDVI processing module.
Aligns NDVI observations with weather data on a fixed calendar window.
"""

import pandas as pd
from typing import Dict, List, Tuple


def align_year_on_calendar(
    field_data: Dict,
    year: int,
    season_start: str = '05-01',
    season_end: str = '10-31'
) -> pd.DataFrame:
    """
    For a single year, align NDVI and weather on fixed calendar window.
    
    Parameters:
    -----------
    field_data : dict
        Field data dictionary with keys:
        - 'weather': DataFrame with daily weather
        - 'ndvi': Dict {year: [observations]}
    
    year : int
        Year to align (e.g., 2022)
    
    season_start : str
        Start of growing season (format: 'MM-DD', default '05-01' = May 1)
    
    season_end : str
        End of growing season (format: 'MM-DD', default '10-31' = October 31)
    
    Returns:
    --------
    pd.DataFrame
        Aligned dataset with daily index (season_start to season_end)
        Columns: T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, ... (weather), ndvi
        Index: DatetimeIndex (May 1 - Oct 31 of given year)
    
    Notes:
    ------
    - NDVI observations are sparse (Sentinel 10-day revisit)
    - Missing NDVI values are interpolated linearly
    - Weather data is typically continuous (no gaps)
    """
    
    # 1. Create unified daily index for season
    full_start = f"{year}-{season_start}"
    full_end = f"{year}-{season_end}"
    daily_index = pd.date_range(full_start, full_end, freq='D')
    
    # 2. Extract weather for this year & season
    weather_year = field_data['weather'][
        (field_data['weather']['date'].dt.year == year) &
        (field_data['weather']['date'] >= full_start) &
        (field_data['weather']['date'] <= full_end)
    ].copy()
    
    if weather_year.empty:
        raise ValueError(f"No weather data found for {year} between {full_start} and {full_end}")
    
    weather_year = weather_year.set_index('date')
    
    # 3. Extract NDVI for this year & season
    ndvi_year_obs = field_data['ndvi'].get(year, [])
    
    if not ndvi_year_obs:
        raise ValueError(f"No NDVI observations found for year {year}")
    
    # Filter NDVI to observations within season window
    ndvi_in_window = [
        obs for obs in ndvi_year_obs
        if full_start <= obs['date'] <= full_end
    ]
    
    if not ndvi_in_window:
        raise ValueError(f"No NDVI observations found for {year} between {full_start} and {full_end}")
    
    # Create NDVI series from observations
    ndvi_series = pd.Series(
        [obs['ndvi'] for obs in ndvi_in_window],
        index=pd.to_datetime([obs['date'] for obs in ndvi_in_window])
    )
    
    # 4. Reindex both to daily index
    weather_reindexed = weather_year.reindex(daily_index)
    ndvi_reindexed = ndvi_series.reindex(daily_index)
    
    # 5. Interpolate NDVI gaps (handle sparse Sentinel observations)
    ndvi_interpolated = ndvi_reindexed.interpolate(method='linear')
    
    # Fill any remaining NaNs (before first observation or after last)
    ndvi_interpolated = ndvi_interpolated.bfill().ffill()
    
    # 6. Merge on date index
    aligned = pd.concat(
        [weather_reindexed, ndvi_interpolated.rename('ndvi')],
        axis=1
    )
    
    return aligned


def extract_ndvi_stats(
    aligned_data: pd.DataFrame,
    field_data: Dict,
    year: int
) -> Dict:
    """
    Extract NDVI statistics and phenological events for a year.
    
    Parameters:
    -----------
    aligned_data : pd.DataFrame
        Aligned dataset from align_year_on_calendar()
    
    field_data : dict
        Field data dictionary with NDVI observations
    
    year : int
        Year being analyzed
    
    Returns:
    --------
    dict : {
        'ndvi_min': float,
        'ndvi_max': float,
        'ndvi_mean': float,
        'peak_ndvi_date': str (YYYY-MM-DD),
        'peak_ndvi_value': float,
        'observation_count': int,
        'observations': [{date, ndvi}, ...]
    }
    """
    
    ndvi_obs = field_data['ndvi'].get(year, [])
    ndvi_obs_filtered = [obs for obs in ndvi_obs if 'T' not in obs['date']]  # Remove time component if present
    
    ndvi_values = aligned_data['ndvi'].dropna()
    
    # Find peak NDVI
    peak_idx = ndvi_values.idxmax()
    peak_date = peak_idx.strftime('%Y-%m-%d')
    peak_value = ndvi_values[peak_idx]
    
    return {
        'ndvi_min': float(ndvi_values.min()),
        'ndvi_max': float(ndvi_values.max()),
        'ndvi_mean': float(ndvi_values.mean()),
        'peak_ndvi_date': peak_date,
        'peak_ndvi_value': float(peak_value),
        'observation_count': len(ndvi_obs_filtered),
        'observations': ndvi_obs_filtered
    }
