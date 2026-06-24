# NOAA Winter Storm Severity Index (WSSI) snow climatologies

**Status:** in progress
**Branch:** snow-noaa-wssi-2026
**Requested by:** NOAA-WSSI — note: the pre-existing prototype notebooks under
`Jupyter_Notebooks/` are misnamed `forRickTte`; that's a naming slip, not a different requester.
**Created:** 2026-06-23

## What this produces

Three 1981-2010 climatologies derived from downscaled WRF/ERA5 output, at both the 4km and
12km domains:

1. **Climatology of monthly accumulated (summed) ACSNOW** — hourly snow accumulation
   (mm / kg m⁻² liquid water equivalent), summed within each calendar month, then averaged
   across 1981-2010.
2. **Climatology of the monthly maximum SNOW** (snow water equivalent, mm / kg m⁻²) —
   within-month maximum for each calendar month/year, then averaged across 1981-2010.
3. **Climatology of the monthly average SNOW** (mm / kg m⁻²) — within-month mean for each
   calendar month/year, then averaged across 1981-2010.

Source variables `ACSNOW` and `SNOW` come from the downscaled WRF output (see
`tasks/dsworkflow/processing_code/extract_vars.py`).

**Source data:** `/import/beegfs/CMIP6/wrf_era5/{04,12}km/<year>/era5_wrf_dscale_{04,12}km_<year>-<mm>-<dd>.nc`
(hourly files; this is the `rltorgerson:cmip6`-owned copy, not the `/import/SNAP/cwaigl/wrf_era5/`
working copy used by the unrelated `tasks/extraction/scripts/accsnow_testing_*.py` prototypes).

## Outputs

`products/2026_snow_noaa_wssi/output/` (gitignored, not tracked in git) — six files
(3 climatologies x 2 domains), naming TBD as scripts are written, e.g.:
- `acsnow_monthly_accum_clim_1981-2010_04km.nc` / `_12km.nc`
- `snow_monthly_max_clim_1981-2010_04km.nc` / `_12km.nc`
- `snow_monthly_avg_clim_1981-2010_04km.nc` / `_12km.nc`

No external delivery path confirmed yet — local `output/` is sufficient for now.

## How to generate

Not yet written. Related prior prototyping exists but lives elsewhere and was deliberately
*not* moved into this folder:
- `Jupyter_Notebooks/analyisis_snowacc_forRickT_prototype.ipynb` and `_regress.ipynb` —
  open_dataset vs. open_mfdataset benchmarking for ACSNOW monthly summation, against the
  `/import/beegfs/CMIP6/wrf_era5/` path used here.
- `tasks/extraction/scripts/accsnow_testing_loop.py` / `accsnow_testing_mf.py` — same
  benchmarking question, against the `/import/SNAP/cwaigl/wrf_era5/` path (different source).
- `tasks/extraction/scripts/monthavg_wspd_loop.py` — closest existing pattern for a
  monthly-climatology loop (Dask client setup, year/month looping).
