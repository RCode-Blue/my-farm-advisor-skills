"""
Weather metrics calculation module.
Calculates precipitation, temperature, GDD, and detects weather events.
"""

import pandas as pd
from typing import Dict, List, Tuple


def calculate_metrics(
    aligned_data: pd.DataFrame,
    base_temp_c: float = 10,
    cap_temp_c: float = 30
) -> Dict:
    """
    For one year's aligned data, calculate all weather metrics.
    
    Parameters:
    -----------
    aligned_data : pd.DataFrame
        Aligned dataset from align_year_on_calendar()
        Must have columns: T2M_MAX, T2M_MIN, T2M, PRECTOTCORR
    
    base_temp_c : float
        GDD base temperature in Celsius
        (default 10°C, standard for corn/soybeans; equivalent to 50°F)
    
    cap_temp_c : float
        GDD cap temperature in Celsius
        (default 30°C, standard for corn/soybeans; equivalent to 86°F)
    
    Returns:
    --------
    dict : {
        'precip': DataFrame with daily_precip_mm,
        'temp': DataFrame with T2M_MAX, T2M_MIN, T2M, tavg_7d,
        'gdd': DataFrame with daily_gdd, cumulative_gdd,
        'events': [dict, ...]
    }
    """
    
    metrics = {}
    
    # 1. Precipitation (already daily in PRECTOTCORR)
    metrics['precip'] = aligned_data[['PRECTOTCORR']].rename(
        columns={'PRECTOTCORR': 'daily_precip_mm'}
    ).copy()
    
    # 2. Temperature
    metrics['temp'] = aligned_data[['T2M_MAX', 'T2M_MIN', 'T2M']].copy()
    metrics['temp']['tavg_7d'] = aligned_data['T2M'].rolling(7, center=True).mean()
    
    # 3. GDD (Growing Degree Days)
    # Formula: GDD = (Tmax + Tmin)/2 - base_temp
    # Cap Tmax at cap_temp_c to avoid overestimation
    tmax_capped = aligned_data['T2M_MAX'].clip(upper=cap_temp_c)
    tavg = (tmax_capped + aligned_data['T2M_MIN']) / 2
    daily_gdd = (tavg - base_temp_c).clip(lower=0)
    
    metrics['gdd'] = pd.DataFrame({
        'daily_gdd': daily_gdd,
        'cumulative_gdd': daily_gdd.cumsum()
    })
    
    # 4. Event detection
    events = detect_weather_events(aligned_data)
    metrics['events'] = events
    
    return metrics


def detect_weather_events(aligned_data: pd.DataFrame) -> List[Dict]:
    """
    Detect weather events within growing season.
    
    Events detected:
    - Heavy rain (>25mm single day)
    - Frost/freeze (Tmin ≤ 0°C)
    - Heat stress (Tmax >35°C for 3+ consecutive days)
    - Dry spell (5+ consecutive days with precip <2.5mm)
    
    Parameters:
    -----------
    aligned_data : pd.DataFrame
        Aligned dataset with weather columns
    
    Returns:
    --------
    list : [
        {'date': '2022-06-10', 'type': 'heavy_rain', 'value': 28.5, 'description': '...'},
        ...
    ]
    """
    
    events = []
    
    # Heavy rain (>25mm)
    for date, row in aligned_data.iterrows():
        if pd.notna(row['PRECTOTCORR']) and row['PRECTOTCORR'] > 25:
            events.append({
                'date': date.strftime('%Y-%m-%d'),
                'type': 'heavy_rain',
                'value': float(row['PRECTOTCORR']),
                'description': f"Heavy rain {row['PRECTOTCORR']:.1f}mm"
            })
    
    # Frost events (Tmin ≤ 0°C)
    for date, row in aligned_data.iterrows():
        if pd.notna(row['T2M_MIN']) and row['T2M_MIN'] <= 0:
            events.append({
                'date': date.strftime('%Y-%m-%d'),
                'type': 'frost',
                'value': float(row['T2M_MIN']),
                'description': f"Frost risk (Tmin {row['T2M_MIN']:.1f}°C)"
            })
    
    # Heat stress (3+ consecutive days Tmax >35°C)
    heat_stress_runs = _identify_consecutive_events(aligned_data, 'T2M_MAX', 35, min_duration=3)
    for run in heat_stress_runs:
        start_date = run['start_date'].strftime('%Y-%m-%d')
        end_date = run['end_date'].strftime('%Y-%m-%d')
        max_temp = run['max_value']
        duration = run['duration']
        
        events.append({
            'date': start_date,
            'type': 'heat_stress',
            'value': float(max_temp),
            'description': f"Heat stress {duration}d ({max_temp:.1f}°C max, {start_date} to {end_date})"
        })
    
    # Dry spells (5+ consecutive days with precip <2.5mm)
    dry_spell_runs = _identify_consecutive_low_precip(aligned_data, threshold=2.5, min_duration=5)
    for run in dry_spell_runs:
        start_date = run['start_date'].strftime('%Y-%m-%d')
        end_date = run['end_date'].strftime('%Y-%m-%d')
        duration = run['duration']
        total_precip = run['total_precip']
        
        events.append({
            'date': start_date,
            'type': 'dry_spell',
            'value': float(total_precip),
            'description': f"Dry spell {duration}d ({total_precip:.1f}mm total, {start_date} to {end_date})"
        })
    
    # Sort events by date
    events.sort(key=lambda x: x['date'])
    
    return events


def _identify_consecutive_events(
    data: pd.DataFrame,
    column: str,
    threshold: float,
    min_duration: int = 3
) -> List[Dict]:
    """
    Identify runs of consecutive days where column > threshold.
    
    Parameters:
    -----------
    data : pd.DataFrame
        Data with DatetimeIndex
    
    column : str
        Column name to check
    
    threshold : float
        Value threshold
    
    min_duration : int
        Minimum number of consecutive days to count as event
    
    Returns:
    --------
    list : [{'start_date': ..., 'end_date': ..., 'duration': ..., 'max_value': ...}, ...]
    """
    
    runs = []
    
    # Create boolean mask
    mask = data[column] > threshold
    
    # Identify runs (transitions from False to True, and True to False)
    transitions = mask.astype(int).diff()
    
    # Find starts (False -> True)
    starts = data.index[transitions == 1]
    # Find ends (True -> False)
    ends = data.index[transitions == -1]
    
    # Handle edge case: if data starts with True
    if mask.iloc[0]:
        starts = data.index[0:1].tolist() + starts.tolist()
    
    # Handle edge case: if data ends with True
    if mask.iloc[-1]:
        ends = ends.tolist() + data.index[-1:].tolist()
    
    # Pair starts and ends
    for start, end in zip(starts, ends):
        duration = (end - start).days + 1
        
        if duration >= min_duration:
            run_data = data.loc[start:end, column]
            runs.append({
                'start_date': start,
                'end_date': end,
                'duration': duration,
                'max_value': float(run_data.max()),
                'mean_value': float(run_data.mean())
            })
    
    return runs


def _identify_consecutive_low_precip(
    data: pd.DataFrame,
    threshold: float = 2.5,
    min_duration: int = 5
) -> List[Dict]:
    """
    Identify runs of consecutive days with low precipitation.
    
    Parameters:
    -----------
    data : pd.DataFrame
        Data with DatetimeIndex and 'PRECTOTCORR' column
    
    threshold : float
        Precipitation threshold (days with <threshold mm count as "dry")
    
    min_duration : int
        Minimum number of consecutive days to count as event
    
    Returns:
    --------
    list : [{'start_date': ..., 'end_date': ..., 'duration': ..., 'total_precip': ...}, ...]
    """
    
    runs = []
    
    # Create boolean mask (dry = precip < threshold)
    mask = data['PRECTOTCORR'] < threshold
    
    # Identify runs
    transitions = mask.astype(int).diff()
    
    # Find starts
    starts = data.index[transitions == 1]
    # Find ends
    ends = data.index[transitions == -1]
    
    # Handle edge cases
    if mask.iloc[0]:
        starts = data.index[0:1].tolist() + starts.tolist()
    
    if mask.iloc[-1]:
        ends = ends.tolist() + data.index[-1:].tolist()
    
    # Pair starts and ends
    for start, end in zip(starts, ends):
        duration = (end - start).days + 1
        
        if duration >= min_duration:
            run_data = data.loc[start:end, 'PRECTOTCORR']
            runs.append({
                'start_date': start,
                'end_date': end,
                'duration': duration,
                'total_precip': float(run_data.sum()),
                'mean_daily_precip': float(run_data.mean())
            })
    
    return runs
