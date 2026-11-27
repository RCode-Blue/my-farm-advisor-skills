# HTML Generator Guide - Field-Season Storylines

## Overview

The `html_generator.py` module provides two ways to create interactive HTML dashboards from field-season storylines:

1. **Standalone utility** - Generate HTML independently from existing graphics
2. **Skill integration** - Optional parameter in the main skill workflow

Both create professional, responsive HTML viewers that showcase dashboards and event data.

---

## Standalone Utility Function

### `create_field_dashboard_summary()`

Generate HTML summary for field-level dashboards independently, without running the full skill.

**Use case:** Perfect for assignment submissions - take existing PNG dashboards and create a polished HTML viewer.

**Function signature:**
```python
def create_field_dashboard_summary(
    field_id: str,
    output_dir: str,
    graphics_dir: Optional[str] = None,
    title: Optional[str] = None
) -> str
```

**Parameters:**
- `field_id` (str): Field identifier (e.g., "ia-r1-20")
- `output_dir` (str): Directory where HTML file will be saved
- `graphics_dir` (str, optional): Directory containing PNG images and pickle files. If None, uses `output_dir`
- `title` (str, optional): Custom title for dashboard. If None, auto-generated from field_id

**Returns:** Path to generated HTML file

**Example:**
```python
from html_generator import create_field_dashboard_summary

html_file = create_field_dashboard_summary(
    field_id="ia-r1-20",
    output_dir="/path/to/outputs",
    graphics_dir="/path/to/outputs",
    title="Iowa Field ia-r1-20 - Seasonal Analysis (2021-2025)"
)

print(f"HTML created: {html_file}")
```

**What it does:**
1. Finds all dashboard PNG images for the field
2. Loads event summary pickle file (if available)
3. Parses filenames to extract year and crop information
4. Generates responsive HTML with:
   - Year selection buttons
   - Full-sized dashboard images
   - Metadata (crop, NDVI stats, precipitation, GDD)
   - Detected event cards (color-coded)
   - Professional styling and responsive design

---

## Skill Integration Function

### `generate_html_for_skill()`

Generate HTML within the field-season-storylines skill workflow using an optional parameter.

**Use case:** Automated HTML generation during normal skill execution.

**Function signature:**
```python
def generate_html_for_skill(
    field_id: str,
    dashboards: List[str],
    event_data: Optional[Dict[int, Any]] = None,
    output_dir: str = None,
    title: Optional[str] = None
) -> str
```

**Parameters:**
- `field_id` (str): Field identifier
- `dashboards` (List[str]): List of paths to dashboard PNG files
- `event_data` (Dict[int, Any], optional): Dictionary of event summaries, keyed by year
- `output_dir` (str, optional): Directory where HTML will be saved
- `title` (str, optional): Custom title for dashboard

**Returns:** Path to generated HTML file

**How to integrate into skill:**

In `field_storyline_generator.py`, add an optional parameter:

```python
def generate_field_storylines(
    field_id: str,
    year: int,
    output_dir: str,
    generate_html: bool = False  # ← Add this
):
    # ... existing code generates dashboards ...
    dashboard_png = create_dashboard(...)
    event_summary = save_pickle(...)
    
    # NEW: Optional HTML generation
    if generate_html:
        from html_generator import generate_html_for_skill
        
        html_file = generate_html_for_skill(
            field_id=field_id,
            dashboards=all_dashboard_files,
            event_data=event_summary_data,
            output_dir=output_dir
        )
        print(f"HTML viewer created: {html_file}")
```

---

## HTML Features

### Interactive Controls
- Year selection buttons (click to switch between years)
- Smooth animations between years
- Active state highlighting
- Mobile-responsive buttons

### Dashboard Display
- Full-width responsive images
- Professional styling with shadows
- Automatic image scaling
- Clean layout

### Metadata Display
- Crop type for each year
- Peak NDVI with date
- Total seasonal precipitation (mm)
- Cumulative growing degree days (°C)
- Number of detected events

### Event Cards
- Color-coded by event type:
  - **Orange**: Dry spells
  - **Blue**: Heavy rain
  - **Red**: Heat stress
  - **Dark**: Frost risk
- Event date, type, description, and value
- Grid layout that adapts to screen size

### Responsive Design
- Works on desktop, tablet, and mobile
- Touch-friendly buttons
- Readable font sizes
- Adapts to screen width

### Professional Styling
- Gradient header (purple/blue)
- Clean spacing and typography
- Hover effects on buttons
- Smooth fade-in animations
- Box shadows for depth
- Color scheme optimized for readability

---

## Example Output

### Generated Files

After running either function, you get:

**File:** `{field_id}_dashboard_summary.html` (typically 10-20 KB)

**Directory structure:**
```
examples/
├── ia-r1-20_2021_soybeans_dashboard.png
├── ia-r1-20_2022_corn_dashboard.png
├── ia-r1-20_2023_soybeans_dashboard.png
├── ia-r1-20_2024_corn_dashboard.png
├── ia-r1-20_2025_soybeans_dashboard.png
├── ia-r1-20_dashboard_info.pkl
└── ia-r1-20_dashboard_summary.html  ← NEW
```

### Opening in Browser

Simply open the HTML file in any modern web browser:
```bash
open ia-r1-20_dashboard_summary.html  # macOS
# or
firefox ia-r1-20_dashboard_summary.html  # Linux
# or double-click file on Windows
```

No server required - pure HTML/CSS/JavaScript that works standalone.

---

## Implementation Workflow

### For Assignment 3 Submission

**Step 1:** Generate dashboards and pickle files
```bash
python run_skill.py --field ia-r1-20 --year 2022
```

**Step 2:** Create HTML summary
```python
from html_generator import create_field_dashboard_summary

html = create_field_dashboard_summary(
    field_id="ia-r1-20",
    output_dir="./examples"
)
```

**Step 3:** Submit
- Include HTML file in GitHub repo
- Share link to HTML or upload to assignment platform
- HTML displays all years, metadata, and events in one view

### For Skill Integration

**Step 1:** Modify field_storyline_generator.py to add `generate_html` parameter

**Step 2:** When running skill with `generate_html=True`, HTML is auto-generated

**Step 3:** HTML is saved alongside other outputs

---

## Technical Details

### Dependencies
- Python standard library only (no external packages required)
- Uses `pickle` to load event data
- Generates pure HTML/CSS/JavaScript

### File Size
- HTML file: ~10-20 KB (very small, shareable)
- Independent of image sizes
- Lightweight for email/web sharing

### Browser Compatibility
- Works in all modern browsers (Chrome, Firefox, Safari, Edge)
- Mobile-friendly
- No JavaScript frameworks required
- Pure vanilla JavaScript

### Image Handling
- Uses relative paths for image references
- Images stay in same directory as HTML
- If you move HTML, keep images nearby
- Or update image paths in HTML

---

## Troubleshooting

### "No dashboards found for field"
- Check field_id matches filename exactly
- Verify PNG files exist in graphics_dir
- Filenames should follow pattern: `{field_id}_{year}_{crop}_dashboard.png`

### "Could not load pickle file"
- Event data is optional - HTML still works without it
- Check pickle file exists and is readable
- Warning will be printed if file has issues

### Images not showing in HTML
- Verify images are in same directory as HTML
- Check image file paths in generated HTML
- Adjust image paths if you move files

### Styling looks weird
- Clear browser cache (Ctrl+Shift+Delete or Cmd+Shift+Delete)
- Try different browser
- Check if CSS loaded (right-click → Inspect → Network tab)

---

## Future Enhancements

Potential additions to html_generator.py:

- [ ] Multi-field comparison view
- [ ] Export to PDF
- [ ] Interactive NDVI trend chart
- [ ] Weather pattern visualization
- [ ] Custom color themes
- [ ] Data table export
- [ ] Mobile app version

---

## Example: Iowa Field ia-r1-20

**Generated file:** `ia-r1-20_dashboard_summary.html`

**Features:**
- 5 years of dashboards (2021-2025)
- Crop rotation: Corn/Soybeans
- Interactive year selection
- Event detection (25-26 events per year)
- Metadata for each year
- Professional styling

**Open in browser to see:**
- Select different years with buttons
- View full dashboard for each year
- See metadata and event cards
- Responsive on mobile devices

---

## Usage Summary

| Use Case | Function | Method |
|----------|----------|--------|
| Assignment submission | `create_field_dashboard_summary()` | Standalone |
| Skill integration | `generate_html_for_skill()` | Add to skill |
| Batch processing | `create_field_dashboard_summary()` | Loop over fields |
| One-time generation | `create_field_dashboard_summary()` | Direct call |

---

## See Also

- `field_storyline_generator.py` - Main skill that generates dashboards
- `ndvi_processor.py` - NDVI data processing
- `weather_metrics.py` - Weather calculations
- `dashboard_renderer.py` - Dashboard PNG generation
