# AKCASC caribou data delivery

**Status:** draft
**Branch:** akcasc-caribou
**Requested by:** AKCASC caribou project
**Created:** 2026-07-24

## What this produces

Quick data delivery for the AKCASC caribou project: WRF 4km output clipped to the PCH
(Porcupine Caribou Herd) summer study area (`input_external/`), May–Aug 2021–2024, per
variable:

| Variable | Meaning | Temporal aggregation |
|---|---|---|
| `T2` | air temp | daily (mean, min, max) |
| `RAINC`/`RAINNC` | convective/non-convective precip | monthly mean; weekly total (May–Aug) |
| `SNOW` | snow water equivalent | 1 May snapshot only |
| `SNOWC`/`SNOWH` | snow cover / snow depth | daily (May–Aug) |
| `SMOIS` | soil moisture | weekly mean (May–Aug) |
| `TSLB` | soil temp | weekly (mean, max) |

Delivery format: NetCDF confirmed. GeoTIFF also wanted but needs further planning (e.g.
per-variable/per-timestep band structure) before committing to an approach.

## Inputs

- `input_external/` (gitignored repo-wide via `products/*/input_external/` — externally
  supplied source data doesn't belong in git history): the PCH (Porcupine Caribou Herd)
  summer study-area shapefile (`PCH_StudyArea/PCH_summer_SA_extent_WGS84.*`, plus the source
  `.zip`), used to spatially subset the extraction below.

## Outputs

- `output/` (tracked in git): the delivered data/figures themselves.
- `output_norepo/` (gitignored, see this folder's own `.gitignore` entry): large
  intermediates that support generating the delivery but aren't the delivery itself.

Note (2026-07-28): `.gitignore` now excludes `output/*` but explicitly un-ignores
`output/README.md`, so the generated NetCDF/GeoTIFF files stay untracked while
`output/README.md` (describing them) lands in git history.
`climatecollection_publication`'s product_note.md still flags the original
discrepancy — same fix would apply there if it grows an output/README.md.

## How to generate

<Entry point: which script/notebook to run, in what order, with what inputs.>
