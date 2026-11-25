"""
Main entry point for field storyline generation.
Orchestrates data loading, crop identification, alignment, and dashboard creation.
"""

import os
import sys
import pandas as pd
from pathlib import Path
from typing import Optional, List

from data_loader import load_field_data
from crop_identifier import identify_crops_from_data
from ndvi_processor import align_year_on_calendar, extract_ndvi_stats
from weather_metrics import calculate_metrics


def generate_field_storyline_dashboards(
    field_id: str,
    crop_data: pd.DataFrame,
    crop_field_col: str = 'field_id',
    crop_year_col: str = 'year',
    crop_name_col: str = 'crop_name',
    crop_pct_col: str = 'pct',
    crop_type: Optional[str] = None,
    output_dir: str = './output',
    data_root: str = '/home/coder/my-farm-advisor-runtime/data-pipeline',
    coverage_threshold: float = 0.80,
    gdd_base_temp_c: float = 10,
    season_start: str = '05-01',
    season_end: str = '10-31'
) -> str:
    """
    Main entry point for reusable skill.
    Dynamically discovers crops, generates dashboards for specified crops.
    
    Works with ANY crop data source (CDL, TERN, NSW DPI, etc.)
    
    Parameters:
    -----------
    field_id : str
        Field identifier (e.g., 'ia-r1-20', 'toowoomba-1')
    
    crop_data : pd.DataFrame
        Crop dataset from ANY source (CDL, TERN, NSW DPI, etc.)
    
    crop_field_col : str
        Name of field column in crop_data (default: 'field_id')
        CDL: 'field_id', TERN: 'paddock_id', NSW DPI: 'paddock'
    
    crop_year_col : str
        Name of year column in crop_data (default: 'year')
        CDL: 'year', TERN: 'season', NSW DPI: 'planting_year'
    
    crop_name_col : str
        Name of crop name column in crop_data (default: 'crop_name')
        CDL: 'crop_name', TERN: 'crop_type', NSW DPI: 'crop_planted'
    
    crop_pct_col : str
        Name of coverage % column in crop_data (default: 'pct')
        CDL: 'pct', TERN: 'area_fraction', NSW DPI: 'coverage_pct'
    
    crop_type : str or None
        'crop_name' to generate specific crop only
        None to generate all crops found in field
    
    output_dir : str
        Where to save dashboard images
    
    data_root : str
        Path to data-pipeline root
    
    coverage_threshold : float
        Minimum crop coverage percentage (0-1)
    
    gdd_base_temp_c : float
        Base temperature for GDD calculation (°C)
    
    season_start : str
        Start of growing season (format: 'MM-DD', default '05-01')
    
    season_end : str
        End of growing season (format: 'MM-DD', default '10-31')
    
    Returns:
    --------
    str : Path to output directory
    
    Examples:
    ---------
    # Iowa field (CDL, default columns)
    generate_field_storyline_dashboards(
        field_id='ia-r1-20',
        crop_data=cdl_dataframe
    )
    # Outputs: 5 dashboards (Corn 2022, 2024; Soybeans 2021, 2023, 2025)
    
    # Iowa field, Corn only
    generate_field_storyline_dashboards(
        field_id='ia-r1-20',
        crop_data=cdl_dataframe,
        crop_type='Corn'
    )
    # Outputs: 2 dashboards (Corn 2022, 2024)
    
    # Toowoomba field (TERN with custom column names)
    generate_field_storyline_dashboards(
        field_id='toowoomba-1',
        crop_data=tern_dataframe,
        crop_field_col='paddock_id',
        crop_year_col='season',
        crop_name_col='crop_type',
        crop_pct_col='area_fraction',
        data_root='/tern-data'
    )
    # Outputs: X dashboards (whatever crops are in TERN data)
    """
    
    print(f"\n{'='*100}")
    print(f"FIELD STORYLINE GENERATION: {field_id}")
    print(f"{'='*100}")
    
    # Step 1: Load all data for field
    print(f"\n[Step 1] Loading field data...")
    field_data = load_field_data(field_id, data_root)
    
    # Step 2: DYNAMICALLY identify crops from ANY data source (no hardcoding)
    print(f"\n[Step 2] Identifying crops from data source...")
    try:
        years_by_crop = identify_crops_from_data(
            field_id=field_id,
            crop_data=crop_data,
            field_col=crop_field_col,
            year_col=crop_year_col,
            crop_col=crop_name_col,
            pct_col=crop_pct_col,
            coverage_threshold=coverage_threshold
        )
    except Exception as e:
        print(f"✗ Error identifying crops: {str(e)}")
        return None
    
    if not years_by_crop:
        print(f"✗ No crops found for {field_id} above coverage threshold ({coverage_threshold*100:.0f}%)")
        return None
    
    print(f"  Discovered crops: {list(years_by_crop.keys())}")
    for crop, years in sorted(years_by_crop.items()):
        print(f"    {crop}: {years}")
    
    # Step 3: Determine which crops to generate
    if crop_type is None:
        # Generate all crops discovered
        crops_to_generate = sorted(years_by_crop.keys())
    else:
        # Generate specific crop only
        if crop_type not in years_by_crop:
            print(f"✗ Crop '{crop_type}' not found for {field_id}")
            print(f"  Available crops: {list(years_by_crop.keys())}")
            return None
        crops_to_generate = [crop_type]
    
    print(f"  Generating: {crops_to_generate}")
    
    # Step 4: For each crop, generate dashboards for all its years
    print(f"\n[Step 3] Generating dashboards...")
    
    generated_count = 0
    dashboard_info = []
    
    for crop in crops_to_generate:
        years = years_by_crop[crop]
        print(f"\n  {crop} ({len(years)} years): {years}")
        
        for year in years:
            try:
                # Align data
                print(f"    {year}: Aligning data...", end=' ', flush=True)
                aligned = align_year_on_calendar(field_data, year, season_start, season_end)
                print(f"✓", flush=True)
                
                # Calculate metrics
                print(f"    {year}: Calculating metrics...", end=' ', flush=True)
                metrics = calculate_metrics(aligned, base_temp_c=gdd_base_temp_c)
                print(f"✓", flush=True)
                
                # Extract NDVI stats
                print(f"    {year}: Extracting NDVI stats...", end=' ', flush=True)
                ndvi_stats = extract_ndvi_stats(aligned, field_data, year)
                print(f"✓", flush=True)
                
                # Prepare info for dashboard
                dashboard_data = {
                    'field_id': field_id,
                    'year': year,
                    'crop': crop,
                    'aligned': aligned,
                    'metrics': metrics,
                    'ndvi_stats': ndvi_stats
                }
                
                dashboard_info.append(dashboard_data)
                generated_count += 1
                
                print(f"    {year}: Ready for dashboard rendering")
                
            except Exception as e:
                print(f"✗ ERROR: {str(e)}")
                continue
    
    if generated_count == 0:
        print(f"\n✗ No dashboards generated")
        return None
    
    # Step 5: Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n[Step 4] Summary")
    print(f"{'='*100}")
    print(f"✓ Generated {generated_count} dashboard(s) for {field_id}")
    print(f"  Output directory: {output_dir}")
    print(f"  Dashboards ready for rendering:")
    for info in dashboard_info:
        crop_safe = info['crop'].lower().replace('/', '_').replace(' ', '_')
        filename = f"{info['field_id']}_{info['year']}_{crop_safe}_dashboard.png"
        print(f"    - {filename}")
        print(f"      Year: {info['year']}, Crop: {info['crop']}")
        print(f"      NDVI: {info['ndvi_stats']['ndvi_min']:.2f}-{info['ndvi_stats']['ndvi_max']:.2f} (peak {info['ndvi_stats']['peak_ndvi_value']:.2f} on {info['ndvi_stats']['peak_ndvi_date']})")
        print(f"      GDD: {info['metrics']['gdd']['cumulative_gdd'].iloc[-1]:.0f}")
        print(f"      Weather events: {len(info['metrics']['events'])}")
    
    # For now, return the dashboard info (rendering will be in next step)
    # Save dashboard info for rendering step
    dashboard_info_path = os.path.join(output_dir, f"{field_id}_dashboard_info.pkl")
    
    import pickle
    with open(dashboard_info_path, 'wb') as f:
        pickle.dump(dashboard_info, f)
    
    print(f"\n✓ Dashboard data saved to {dashboard_info_path}")
    print(f"{'='*100}\n")
    
    return output_dir


if __name__ == '__main__':
    # Example usage
    from data_loader import load_crop_data_all_years
    
    # Load CDL data
    cdl = load_crop_data_all_years('ia-r1-20', '/home/coder/my-farm-advisor-runtime/data-pipeline')
    
    # Generate dashboards
    output = generate_field_storyline_dashboards(
        field_id='ia-r1-20',
        crop_data=cdl,
        output_dir='./output',
        crop_type=None  # Generate all crops
    )
    
    if output:
        print(f"\n✓ Workflow completed successfully!")
        print(f"  Output directory: {output}")
    else:
        print(f"\n✗ Workflow failed")
        sys.exit(1)
