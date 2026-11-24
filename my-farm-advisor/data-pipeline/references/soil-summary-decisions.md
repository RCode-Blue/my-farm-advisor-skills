# Soil summary decisions (per-field SSURGO values)

These are the rules the farm soil summary uses. They are implemented in
`src/scripts/ingest/download_soil.py` (`_surface_om_ph_dominant`,
`_profile_water_cm`). Reports and posters read the summary columns below.

## Organic matter and pH (`avg_om_pct`, `avg_ph`)

- **Depth:** 0 to 30 cm only. A horizon that crosses 30 cm contributes only
  the part above 30 cm.
- **Weighting:** each horizon is weighted by its thickness inside 0 to 30 cm
  multiplied by its component's share of the map unit (`comppct_r`).
- **Why:** organic matter and pH are concentrated in the topsoil, and the
  agronomic thresholds used in the strategy text (1.5% and 3.0% OM) are read
  from topsoil samples.
- **Rationale for 30 cm:** a conventional plough-layer depth, chosen over the
  top 15 to 20 cm that some labs use.
- **Replaces:** a plain mean over all horizons, which gave deep horizons the
  same weight as the topsoil.

## Dominant soil (`dominant_soil`)

- **Rule:** the component name with the highest `comppct_r` for the field.
- **Replaces:** the first row in the field's soil table, which depended on
  query order rather than extent.
- **Matches:** the rule in `soil/ssurgo-soil/src/ssurgo_soil.py`.

## Water storage (`total_aws_cm`) - unchanged for now

- **Method:** depth-weighted plant-available water, summed over horizons and
  normalised to a 200 cm profile, in centimetres.
- **Open item:** the 200 cm basis is the same for every crop. Crop-specific
  effective rooting depth (corn about 90 to 120 cm, soybean about 60 to 90 cm,
  from UNL Extension G2245) is the planned change and is not yet applied.
- **Thresholds (10.2 cm and 15.2 cm)** are converted from 4 and 6 inches and
  have no cited agronomic source yet.

## Soil type shown in reports

- **Dominant soil** is the highest-share component, as above.
- **Drainage class** still uses the first row for each field. It is not yet
  tied to the dominant component.

## Not yet sourced

- The OM thresholds (1.5% and 3.0%) and the water storage thresholds have no
  cited source. The 0 to 30 cm choice is a method decision, not an agronomic
  standard.
