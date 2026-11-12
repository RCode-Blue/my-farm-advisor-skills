# Local Instructions: Grower Web Map

## Purpose

This folder owns the grower-level interactive web map subskill for the My Farm Advisor
data pipeline. It generates lightweight, self-contained single-page HTML maps for grower
field portfolios using real pipeline boundary outputs, embedded Leaflet assets, and online
satellite imagery.

## Safe edit scope

Edits should stay in this folder, its children, and the associated generator script under
`../src/scripts/reporting/generate_grower_webmap.py`. Do not change parent `SKILL.md`,
sibling workflows, or root policy unless explicitly requested.

## Read nearby docs first

Read `README.md` first for the subskill overview, then `GUIDE.md` for workflow details and
`PROVENANCE.md` for attribution. For data pipeline runtime conventions, review `../AGENTS.md`
and `../README.md`.

## Command runbook

Generate map for a specific grower:

```bash
export DATA_PIPELINE_DATA_ROOT=/home/coder/my-farm-advisor-runtime
cd "${DATA_PIPELINE_DATA_ROOT}/data-pipeline/src"
"${DATA_PIPELINE_DATA_ROOT}/data-pipeline/.venv/bin/python" \
  scripts/reporting/generate_grower_webmap.py --grower-slug il-grower
```

Generate maps for all active growers:

```bash
export DATA_PIPELINE_DATA_ROOT=/home/coder/my-farm-advisor-runtime
cd "${DATA_PIPELINE_DATA_ROOT}/data-pipeline/src"
"${DATA_PIPELINE_DATA_ROOT}/data-pipeline/.venv/bin/python" \
  scripts/reporting/generate_grower_webmap.py --all-growers
```

Force-rebuild an existing map:

```bash
export DATA_PIPELINE_DATA_ROOT=/home/coder/my-farm-advisor-runtime
cd "${DATA_PIPELINE_DATA_ROOT}/data-pipeline/src"
"${DATA_PIPELINE_DATA_ROOT}/data-pipeline/.venv/bin/python" \
  scripts/reporting/generate_grower_webmap.py --grower-slug ia-grower --force
```

## Local validation

Run `./scripts/validate.sh` from the repository root after documentation or structure changes.
Verify output HTML files are under 250 KB and validate that polygon counts match the
underlying `field_boundaries.geojson` features.

## Local-delta-only reminder

This nested AGENTS.md only records instructions that differ from the parent or root files.
Do not duplicate root-wide asset, vendor, or validation policy here except this pointer to
`../../../AGENTS.md`.
