"""
Dashboard rendering module.
Creates aligned 4-panel matplotlib figures with NDVI, precipitation, temperature, and GDD.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.dates import DateFormatter, MonthLocator
import numpy as np
from typing import Dict, Tuple
from datetime import datetime


def create_dashboard_figure(
    aligned_data: pd.DataFrame,
    metrics: Dict,
    ndvi_stats: Dict,
    field_id: str,
    year: int,
    crop_name: str,
    county: str = 'Kossuth',
    state: str = 'Iowa',
    output_path: str = None,
    dpi: int = 300
) -> Tuple[plt.Figure, str]:
    """
    Create aligned 4-panel dashboard figure.
    
    Parameters:
    -----------
    aligned_data : pd.DataFrame
        Aligned NDVI and weather data with shared date index
    
    metrics : dict
        Weather metrics: {'precip': DF, 'temp': DF, 'gdd': DF, 'events': []}
    
    ndvi_stats : dict
        NDVI statistics: {'ndvi_min', 'ndvi_max', 'peak_ndvi_date', 'peak_ndvi_value', ...}
    
    field_id, year, crop_name : str
        Field and year identifiers
    
    county, state : str
        Location info for header
    
    output_path : str or None
        Where to save PNG. If None, generates default name.
    
    dpi : int
        Resolution for output (default 300 DPI)
    
    Returns:
    --------
    tuple : (figure, output_path_saved)
    """
    
    # Extract data
    dates = aligned_data.index
    ndvi = aligned_data['ndvi']
    precip = metrics['precip']['daily_precip_mm']
    tmax = metrics['temp']['T2M_MAX']
    tmin = metrics['temp']['T2M_MIN']
    tavg_7d = metrics['temp']['tavg_7d']
    cumulative_gdd = metrics['gdd']['cumulative_gdd']
    events = metrics['events']
    
    # Calculate summary statistics
    total_precip = precip.sum()
    max_precip = precip.max()
    final_gdd = cumulative_gdd.iloc[-1]
    peak_ndvi = ndvi_stats['peak_ndvi_value']
    peak_ndvi_date = ndvi_stats['peak_ndvi_date']
    
    # Create figure with 4 subplots (shared x-axis)
    fig, axes = plt.subplots(4, 1, figsize=(16, 12), sharex=True)
    
    # =========================================================================
    # PANEL 1: SENTINEL NDVI
    # =========================================================================
    ax1 = axes[0]
    ax1.plot(dates, ndvi, color='forestgreen', linewidth=2.5, label='NDVI (interpolated)', zorder=3)
    
    # Mark actual Sentinel observations
    ndvi_obs = ndvi_stats['observations']
    if ndvi_obs:
        obs_dates = pd.to_datetime([obs['date'] for obs in ndvi_obs])
        obs_values = [obs['ndvi'] for obs in ndvi_obs]
        ax1.scatter(obs_dates, obs_values, color='darkgreen', s=80, 
                   marker='o', edgecolors='black', linewidth=1.5,
                   label='Sentinel observations', zorder=4)
    
    ax1.set_ylabel('NDVI', fontsize=12, fontweight='bold')
    ax1.set_ylim(-0.05, 1.05)
    ax1.grid(True, alpha=0.3, linestyle=':')
    ax1.legend(loc='upper left', fontsize=9)
    ax1.set_title('Panel 1: Sentinel NDVI (May 1 - Oct 31)', fontsize=11, fontweight='bold', pad=8)
    
    # Annotation: peak NDVI
    ax1.annotate(f'Peak: {peak_ndvi:.2f} on {peak_ndvi_date}',
                xy=(pd.Timestamp(peak_ndvi_date), peak_ndvi),
                xytext=(10, 20), textcoords='offset points',
                fontsize=9, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.8),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', color='black'))
    
    # =========================================================================
    # PANEL 2: DAILY PRECIPITATION
    # =========================================================================
    ax2 = axes[1]
    
    # Color bars: light blue for normal, dark blue for heavy rain
    colors = ['darkblue' if p >= 25 else 'lightblue' if p > 0 else 'lightgray' for p in precip]
    ax2.bar(dates, precip, color=colors, width=0.8, edgecolor='none')
    
    ax2.set_ylabel('Precipitation (mm)', fontsize=12, fontweight='bold')
    ax2.set_ylim(0, max(max_precip * 1.15, 30))
    ax2.grid(True, alpha=0.3, axis='y', linestyle=':')
    ax2.set_title('Panel 2: Daily Precipitation (May 1 - Oct 31)', fontsize=11, fontweight='bold', pad=8)
    
    # Annotation: total seasonal precip
    ax2.text(0.02, 0.98, f'Total: {total_precip:.1f}mm',
            transform=ax2.transAxes, fontsize=10, fontweight='bold',
            verticalalignment='top',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', alpha=0.8))
    
    # Mark heavy rain events
    heavy_rain_events = [e for e in events if e['type'] == 'heavy_rain']
    for event in heavy_rain_events[:3]:  # Show top 3 to avoid clutter
        event_date = pd.Timestamp(event['date'])
        if event_date in precip.index:
            value = precip[event_date]
            ax2.text(event_date, value + 2, '↑', fontsize=12, ha='center', color='darkblue', fontweight='bold')
    
    # =========================================================================
    # PANEL 3: TEMPERATURE & EXTREMES
    # =========================================================================
    ax3 = axes[2]
    
    # Plot temperature lines
    ax3.plot(dates, tmax, color='red', linewidth=2.5, label='Tmax', zorder=3)
    ax3.plot(dates, tmin, color='blue', linewidth=2.5, label='Tmin', zorder=3)
    ax3.plot(dates, tavg_7d, color='black', linewidth=1.5, linestyle='--', 
            label='7-day avg', zorder=2)
    
    # Fill between Tmax and Tmin
    ax3.fill_between(dates, tmin, tmax, alpha=0.15, color='gray', zorder=1)
    
    # Shade frost zone (Tmin ≤ 0°C)
    ax3.axhspan(-15, 0, alpha=0.08, color='blue', zorder=0)
    
    # Shade heat stress zone (Tmax >35°C)
    ax3.axhspan(35, 42, alpha=0.08, color='red', zorder=0)
    
    ax3.set_ylabel('Temperature (°C)', fontsize=12, fontweight='bold')
    ax3.set_ylim(-15, 42)
    ax3.grid(True, alpha=0.3, linestyle=':')
    ax3.set_title('Panel 3: Temperature & Extremes (May 1 - Oct 31)', fontsize=11, fontweight='bold', pad=8)
    ax3.legend(loc='upper right', fontsize=9)
    
    # Add zone labels
    ax3.text(0.5, -12, 'Frost Risk Zone', fontsize=8, style='italic', 
            color='blue', alpha=0.6, transform=ax3.get_yaxis_transform())
    ax3.text(0.5, 38.5, 'Heat Stress Zone', fontsize=8, style='italic',
            color='red', alpha=0.6, transform=ax3.get_yaxis_transform())
    
    # Mark frost and heat events
    frost_events = [e for e in events if e['type'] == 'frost']
    heat_events = [e for e in events if e['type'] == 'heat_stress']
    
    if frost_events:
        event_date = pd.Timestamp(frost_events[0]['date'])
        if event_date in tmin.index:
            ax3.plot(event_date, tmin[event_date], marker='v', color='blue', 
                    markersize=8, markeredgecolor='darkblue', markeredgewidth=1)
    
    if heat_events:
        event_date = pd.Timestamp(heat_events[0]['date'])
        if event_date in tmax.index:
            ax3.plot(event_date, tmax[event_date], marker='^', color='red',
                    markersize=8, markeredgecolor='darkred', markeredgewidth=1)
    
    # =========================================================================
    # PANEL 4: CUMULATIVE GDD
    # =========================================================================
    ax4 = axes[3]
    
    # Plot cumulative GDD
    ax4.plot(dates, cumulative_gdd, color='saddlebrown', linewidth=3, zorder=3)
    ax4.fill_between(dates, 0, cumulative_gdd, alpha=0.2, color='tan', zorder=1)
    
    ax4.set_ylabel('Cumulative GDD', fontsize=12, fontweight='bold')
    ax4.set_xlabel('Date', fontsize=12, fontweight='bold')
    ax4.set_ylim(0, final_gdd * 1.1)
    ax4.grid(True, alpha=0.3, linestyle=':')
    ax4.set_title('Panel 4: Cumulative Growing Degree Days (Base 10°C)', fontsize=11, fontweight='bold', pad=8)
    
    # Annotation: final GDD with crop maturity reference
    crop_gdd_ref = {
        'Corn': (2700, 2900),
        'Soybeans': (2500, 2700),
    }
    
    gdd_range = crop_gdd_ref.get(crop_name, (2000, 3000))
    
    ax4.text(0.98, 0.95, f'Final GDD: {final_gdd:.0f}',
            transform=ax4.transAxes, fontsize=11, fontweight='bold',
            horizontalalignment='right', verticalalignment='top',
            bbox=dict(boxstyle='round,pad=0.6', facecolor='lightyellow', alpha=0.9))
    
    ax4.text(0.98, 0.78, f'{crop_name} maturity:\n{gdd_range[0]}-{gdd_range[1]} GDD',
            transform=ax4.transAxes, fontsize=8, style='italic',
            horizontalalignment='right', verticalalignment='top',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='lightcyan', alpha=0.8))
    
    # =========================================================================
    # CONFIGURE SHARED X-AXIS
    # =========================================================================
    for ax in axes:
        ax.xaxis.set_major_locator(MonthLocator())
        ax.xaxis.set_major_formatter(DateFormatter('%b'))
        ax.set_xlim(dates[0], dates[-1])
    
    axes[-1].set_xticks(pd.date_range(start=dates[0], end=dates[-1], freq='2W'))
    
    # =========================================================================
    # FIGURE HEADER (Two lines)
    # =========================================================================
    # Line 1: Field and year info
    fig.text(0.5, 0.993, f'{field_id}, {year}: {crop_name} | {county} County, {state}',
            ha='center', fontsize=15, fontweight='bold')
    
    # Line 2: Metrics
    fig.text(0.5, 0.987, f'GDD: {final_gdd:.0f} | Precip: {total_precip:.1f}mm | '
                         f'NDVI Range: {ndvi_stats["ndvi_min"]:.2f}-{ndvi_stats["ndvi_max"]:.2f} '
                         f'(peak {peak_ndvi:.2f} on {peak_ndvi_date}) | '
                         f'{len(ndvi_obs)} Sentinel observations',
            ha='center', fontsize=9, style='italic')
    
    # Adjust layout (leave more space at top for two-line header)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    # Save figure
    if output_path is None:
        crop_safe = crop_name.lower().replace('/', '_').replace(' ', '_')
        output_path = f'{field_id}_{year}_{crop_safe}_dashboard.png'
    
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight', facecolor='white')
    
    return fig, output_path


def render_all_dashboards(
    dashboard_info_list: list,
    output_dir: str = './examples'
) -> list:
    """
    Render all dashboard figures from prepared data.
    
    Parameters:
    -----------
    dashboard_info_list : list
        List of dashboard data dicts from field_storyline_generator
    
    output_dir : str
        Directory to save PNG files
    
    Returns:
    --------
    list : [output_path1, output_path2, ...]
    """
    
    output_paths = []
    
    for i, dashboard_data in enumerate(dashboard_info_list, 1):
        field_id = dashboard_data['field_id']
        year = dashboard_data['year']
        crop = dashboard_data['crop']
        
        print(f"Rendering dashboard {i}/{len(dashboard_info_list)}: {field_id} {year} ({crop})...", 
              end=' ', flush=True)
        
        try:
            fig, output_path = create_dashboard_figure(
                aligned_data=dashboard_data['aligned'],
                metrics=dashboard_data['metrics'],
                ndvi_stats=dashboard_data['ndvi_stats'],
                field_id=field_id,
                year=year,
                crop_name=crop,
                output_path=f"{output_dir}/{field_id}_{year}_{crop.lower().replace(' ', '_')}_dashboard.png"
            )
            
            output_paths.append(output_path)
            print(f"✓ {output_path}")
            
            plt.close(fig)
            
        except Exception as e:
            print(f"✗ ERROR: {str(e)}")
            continue
    
    return output_paths
