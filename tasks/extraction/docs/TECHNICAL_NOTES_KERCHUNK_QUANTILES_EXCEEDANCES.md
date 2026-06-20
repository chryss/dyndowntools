# Technical Notes: Kerchunk Catalog Workflow for Quantiles and Exceedances

## Purpose
This document describes a practical HPC workflow for:
1. Building Kerchunk catalogs from many NetCDF files.
2. Loading data from Kerchunk with xarray + Dask.
3. Rechunking for quantile calculations.
4. Computing 90th/95th percentile thresholds.
5. Computing annual exceedance counts from those thresholds.

The notes are tuned for the downscaled ERA5 workflow in this repository.

## Data and Dimension Conventions
Use these dimension names exactly as stored in files:
- `Time`
- `south_north`
- `west_east`

For this dataset family:
- Time: hourly, multi-decade.
- Grid: roughly 450 x 420.

## Geospatial Coordinate Preservation
All derived outputs should keep static geospatial coordinates:
- `XLAT`
- `XLONG`

Recommended pattern:
1. Keep `XLAT`/`XLONG` in the loaded working dataset when available.
2. Before writing each derived DataArray, attach static lat/lon coordinates from the source dataset.
3. If `XLAT`/`XLONG` contain `Time`, drop it with `isel(Time=0, drop=True)` before attaching.

Helper function:

```python
def attach_static_latlon(da, ds_ref):
    out = da
    for name in ("XLAT", "XLONG"):
        if name in ds_ref.variables:
            coord = ds_ref[name]
            if "Time" in coord.dims:
                coord = coord.isel(Time=0, drop=True)
            out = out.assign_coords({name: coord})
    return out
```

## Why Kerchunk
Kerchunk creates a JSON reference map that presents many NetCDF files as a single virtual Zarr-like dataset.

Benefits:
- Faster opens across many files.
- No full data copy required.
- Works with xarray `engine="zarr"` via `reference://`.

Important:
- Kerchunk does not physically rechunk data.
- Rechunking behavior still depends on Dask/xarray chunk operations after load.

## Catalog Layout Used in This Project
Common locations:
- Combined catalogs: `kerchunk_refs/`
- Seasonal catalogs: `extraction/kerchunk_refs/`

Examples:
- `kerchunk_refs/block_1957_2023.json`
- `extraction/kerchunk_refs/era5_wrf_dscale_4km_djf_1959_2022_kerchunk.json`
- `extraction/kerchunk_refs/era5_wrf_dscale_4km_mam_1959_2022_kerchunk.json`
- `extraction/kerchunk_refs/era5_wrf_dscale_4km_jja_1959_2022_kerchunk.json`
- `extraction/kerchunk_refs/era5_wrf_dscale_4km_son_1959_2022_kerchunk.json`

## Catalog Integrity Checks
Before large runs, verify each catalog:
1. File exists.
2. JSON parses.
3. Top-level `version` and `refs` fields exist.
4. Referenced source files exist.

Example shell check:

```bash
cd /import/SNAP/cwaigl/dyndowntools
jq -e . kerchunk_refs/block_1957_2023.json >/dev/null
jq -r '.version, (.refs|type), (.refs|length)' kerchunk_refs/block_1957_2023.json
```

Referenced-source check pattern:

```bash
jq -r '.refs | to_entries[] | .value | if type=="array" then .[0] else empty end | select(type=="string")' \
  kerchunk_refs/block_1957_2023.json | sed 's#^file://##' | sort -u
```

## Opening a Kerchunk Dataset

```python
import xarray as xr
from pathlib import Path

kerchunk_catalog = Path("./kerchunk_refs/block_1957_2023.json")

if not kerchunk_catalog.exists():
    raise FileNotFoundError(f"Missing catalog: {kerchunk_catalog}")

ds_full = xr.open_dataset(
    "reference://",
    engine="zarr",
    backend_kwargs={
        "consolidated": False,
        "storage_options": {
            "fo": str(kerchunk_catalog),
            "remote_protocol": "file",
        },
    },
)

keep_vars = ["wspd10"] + [v for v in ("XLAT", "XLONG") if v in ds_full.variables]
ds = ds_full[keep_vars].chunk({"Time": 8760})
```

Notes:
- Keep initial time chunks moderate (for example `8760`) for stable I/O.
- Rechunk later only where needed for a specific operation.

If multiple catalogs, for example opening seasonal catalogs as one:

```
seasonal_catalogs = [
    Path("./extraction/kerchunk_refs/era5_wrf_dscale_4km_djf_1959_2022_kerchunk.json"),
    Path("./extraction/kerchunk_refs/era5_wrf_dscale_4km_mam_1959_2022_kerchunk.json"),
    Path("./extraction/kerchunk_refs/era5_wrf_dscale_4km_jja_1959_2022_kerchunk.json"),
    Path("./extraction/kerchunk_refs/era5_wrf_dscale_4km_son_1959_2022_kerchunk.json"),
]

for p in seasonal_catalogs:
    if not p.exists():
        raise FileNotFoundError(f"Missing seasonal catalog: {p}")

dss = []
for p in seasonal_catalogs:
    ds_i = xr.open_dataset(
        "reference://",
        engine="zarr",
        backend_kwargs={
            "consolidated": False,
            "storage_options": {"fo": str(p), "remote_protocol": "file"},
        },
    )
    keep_vars = ["wspd10"] + [v for v in ("XLAT", "XLONG") if v in ds_i.variables]
    dss.append(ds_i[keep_vars])

# Merge seasons into one time series
ds_full = xr.concat(
    dss,
    dim="Time",
    data_vars="minimal",
    coords="minimal",
    compat="override",
    combine_attrs="drop_conflicts",
).sortby("Time").chunk({"Time": 8760})

# Optional: drop duplicate timestamps if any
_, idx = np.unique(ds_full["Time"].values, return_index=True)
ds_full = ds_full.isel(Time=np.sort(idx))

# sorting by Time is ootional as well
```

## Dask Client Profiles by Subtask
Different steps behave differently. Reconfigure client between subtasks.

### Quantiles/Rechunk-heavy profile
Use a single large worker to avoid cross-worker shuffle/rechunk failures.

```python
client = Client(
    n_workers=1,
    threads_per_worker=14,
    memory_limit="110GB",
    local_directory="/import/SNAP/$USER/dask_spill",
    dashboard_address=":8787",
)
```

### Exceedance counting profile
Exceedance counting is often less memory-intensive and can benefit from more workers.

```python
client = Client(
    n_workers=4,
    threads_per_worker=2,
    memory_limit="24GB",
    local_directory="/import/SNAP/$USER/dask_spill",
    dashboard_address=":8787",
)
```

Operational rule:
- Close existing clients before starting a new profile.

## Quantile Strategy
Target: full-period p90/p95 at each grid cell.

### Recommended steps
1. Load with moderate time chunking (`Time: 8760`).
2. Rechunk for quantile math:
   - `Time: -1`
   - small spatial chunks (for example `8 x 8`)
3. Compute p90 and p95 sequentially.
4. Concatenate and write to NetCDF.

```python
task1_spatial_chunksize = 8

ds_for_calc = ds.chunk(
    {
        "Time": -1,
        "south_north": task1_spatial_chunksize,
        "west_east": task1_spatial_chunksize,
    }
)

p90 = ds_for_calc["wspd10"].quantile(0.90, dim="Time").compute()
p95 = ds_for_calc["wspd10"].quantile(0.95, dim="Time").compute()

full_percentiles = xr.concat([p90, p95], dim="percentile").assign_coords(percentile=[0.90, 0.95])
full_percentiles.name = "wspd10"
full_percentiles = attach_static_latlon(full_percentiles, ds)
full_percentiles.to_netcdf("final_hourly_percentiles_90_95.nc")
```

## Annual Exceedance Strategy (Whole Year)
Given threshold file from p90/p95 quantiles, count hours per year above threshold.

### Key chunking choice
For counts, keep time chunked by year-like blocks (for example `8760`) instead of `Time: -1`.

```python
thresh = xr.open_dataset(
    "final_hourly_percentiles_90_95.nc",
    chunks={"percentile": 1, "south_north": 8, "west_east": 8},
)

ds_for_counts = ds["wspd10"].chunk({"Time": 8760, "south_north": 8, "west_east": 8})

q_values = thresh["percentile"].values
years = ds_for_counts.Time.dt.year.values

aannual = []
for q in q_values:
    tq = thresh["wspd10"].sel(percentile=q)
    yearly = []
    for y in sorted(set(years)):
        ds_year = ds_for_counts.sel(Time=str(int(y)))
        exceedance_hours = (ds_year > tq).sum(dim="Time")
        yearly.append(exceedance_hours.expand_dims(year=[int(y)]))

    q_all_years = xr.concat(yearly, dim="year").expand_dims(percentile=[q])
    aannual.append(q_all_years)

annual_exceedances = xr.concat(aannual, dim="percentile")
annual_exceedances = attach_static_latlon(annual_exceedances, ds)
annual_exceedances.to_netcdf("annual_exceedance_counts_90_95.nc")
```

## Seasonal Workflow Pattern
For seasonal thresholds:
1. Loop over seasonal Kerchunk catalogs (`djf`, `mam`, `jja`, `son`).
2. Open only one season at a time.
3. Compute seasonal p90/p95.
4. Append to list and free objects between seasons.
5. Concatenate seasons and write output.

This avoids large combined graphs and reduces memory pressure.

## Common Failure Mode and Fixes
### Symptom
`KilledWorker` during tasks like `xarray-rechunk-transfer-...`.

### Typical root cause
Distributed shuffle/rechunk memory blow-up across multiple workers.

### Mitigations
1. Use one large worker for quantile/rechunk-heavy steps.
2. Keep spatial chunks small (`8 x 8` worked in prior successful runs).
3. Compute quantiles sequentially (p90 then p95).
4. Persist outputs to disk between major stages.
5. Switch to multi-worker only for lighter throughput stages (for example exceedance counting).

## Suggested Run Order
1. Start quantile profile client.
2. Open dataset from Kerchunk (or direct files for small debug subsets).
3. Run full-period quantiles and save threshold file.
4. Switch to exceedance profile client.
5. Run annual exceedance counting and save output.
6. Switch profile as needed for seasonal sections.
7. Close all clients at the end.

## Reproducibility Notes
Record for each production run:
- Catalog path used.
- Time range represented by the catalog.
- Dask profile used per subtask.
- Chunk settings per stage.
- Output filenames.
- Runtime and any warnings/errors.

Keeping these settings explicit is essential, because behavior can change due to catalog scope, chunking, and scheduler profile even when analysis code looks similar.
