# HPC Notebook Notes: Downscaled Reanalysis Workflows

This file is a working note for running large-data analyses on the 420×450 downscaled climate reanalysis dataset in Jupyter on HPC.

## Dataset Facts
- Grid: 450 × 420 spatial points.
- Time axis: hourly, 1959–2022.
- File count: 23,000+ NetCDF files.
- Typical analysis target: one data variable such as `wspd10`.
- HPC node used for the benchmark: 28 cores, 125 GB RAM.

## Core Chunking Strategy
- Use the actual dimension names from the files: `Time`, `south_north`, `west_east`.
- For file opening, chunk by time only or keep time chunks moderate for I/O efficiency.
- For compute, rechunk so the final analysis chunks are small in space and complete in time.
- A good working pattern for exact quantiles was:
```python
chunks={'Time': 8760}
ds_for_calc = ds.chunk({"Time": -1, "south_north": 20, "west_east": 20})
```
- Avoid chunk names that do not exist in the dataset, such as `latitude` and `longitude` if the files use `south_north` and `west_east`.

## Quantile Workflow
- Open the multi-file dataset lazily with xarray.
- Rechunk explicitly before exact quantile computations.
- Compute the quantile on the rechunked array.
- Save the reduced result immediately so the Dask graph does not stay alive longer than needed.

Example pattern:
```python
full_percentiles = ds_for_calc["wspd10"].quantile([0.90, 0.95], dim='Time')
full_percentiles.to_netcdf('final_hourly_percentiles_90_95.nc')
```

## What Worked in Practice
- 10% random-file benchmark completed successfully.
- Loading took about 3 minutes.
- Rechunking took about 20 seconds.
- Quantile computation plus saving to NetCDF took about 13.5 minutes.
- This suggests the full run is feasible on the 28-core, 125 GB node with a 48h allocation.

## Dask and Runtime Settings
- Create the Dask client with an explicit worker and memory cap.
- A practical starting point was:
```python
client = Client(n_workers=14, threads_per_worker=2, memory_limit='8GB')
```
- Restart the notebook kernel before a clean production run.
- Restart the Jupyter server only when the server itself is broken, such as repeated 403/auth issues.

## Output Format
- Use `to_netcdf()` for small reduced outputs such as quantiles, climatologies, or trend summaries.
- Use `to_zarr()` mainly for large intermediate arrays or chunked checkpoints.

## Reuse Across Similar Tasks
- Use Kerchunk when the main bottleneck is repeatedly opening many NetCDF files.
- Kerchunk creates a virtual Zarr-style view of the source files without copying the data.
- Kerchunk does not physically rechunk the data.
- Use Rechunker when the main bottleneck is repeated computation on the same access pattern.
- Rechunker writes a new physical Zarr store with chunking chosen for the analysis workload.
- For repeated quantiles, climatologies, or trends on the same variable, a rechunked Zarr cache is usually the better long-term option.

Suggested decision rule:
```text
Many repeated opens only -> Kerchunk
Many repeated analyses -> Rechunker + Zarr cache
One-off analysis -> current xarray + Dask approach is fine
```

Example workflow:
```python
# 1. Open the source data lazily or through a virtual reference.
# 2. Rechunk once into a reusable Zarr store if the analysis will be repeated.
# 3. Reuse that Zarr store for quantiles, climatologies, trends, and similar reductions.
```

Example target chunking for this dataset:
```python
target_chunks = {"Time": 8760, "south_north": 20, "west_east": 20}
```

## Suggested Chunk Layouts By Task

For the 420×450 downscaled reanalysis grid, these are practical starting points:

### 1. Exact quantiles over the full time axis
- Purpose: percentiles such as 90th and 95th over all hours.
- Suggested chunks:
```python
{"Time": -1, "south_north": 20, "west_east": 20}
```
- Why: exact quantiles need the full time axis available per spatial block.

### 2. Climatologies on the full gridded field
- Purpose: monthly or seasonal means, means by month-of-year, day-of-year, or similar summaries.
- Suggested chunks: 
```python
{"Time": 8760, "south_north": 20, "west_east": 20}
```
- Why: time chunks stay large enough for efficient I/O, while spatial chunks remain manageable.
- If the climatology is computed repeatedly, cache the rechunked Zarr result and reuse it.

### 3. Trends on the full gridded field
- Purpose: linear trends, decadal change, or other grid-cell trend fits.
- Suggested chunks:
```python
{"Time": -1, "south_north": 20, "west_east": 20}
```
- Why: many trend calculations need the full time series for each grid cell or each masked region.
- If the trend method can be streamed or reduced in stages, a moderate time chunk may also work, but `Time: -1` is the safest exact layout.

### 4. Aggregated climatologies or trends over a raster mask
- Purpose: the mask is already on the correct grid and the analysis reduces the raster to a regional time series or masked aggregate.
- Suggested chunks before aggregation:
```python
{"Time": 8760, "south_north": 20, "west_east": 20}
```
- Suggested chunks after aggregation to a regional series:
```python
{"Time": 8760}
```
- Why: once the mask has reduced the field, spatial chunking matters less; the remaining bottleneck is usually time.
- If the masked result will be reused often, save the aggregated series to Zarr or NetCDF and analyze that derived product directly.

### 5. Aggregated quantiles over a raster mask
- Purpose: compute quantiles after masking or regional averaging.
- Suggested chunks before the mask:
```python
{"Time": -1, "south_north": 20, "west_east": 20}
```
- Suggested chunks after the field has been reduced to a single time series:
```python
{"Time": -1}
```
- Why: exact masked quantiles still need the full time axis, but the spatial workload disappears once the raster has been collapsed.

## Seasonal and Multi-Step Analyses
- For seasonal percentiles, filter by season, compute the seasonal statistic, and save the result immediately.
- For exceedance counts or other follow-on calculations, reload the saved summary first so the heavy graph does not keep growing.
- This graph-breaking pattern is especially useful when chaining percentile thresholds into later calculations.

## Jupyter Server Notes
- If reconnecting to a new SLURM job causes 403 errors, the issue is usually stale client/session state against a fresh server token.
- A server config such as the following can avoid that class of problem when port forwarding already provides security:
```python
c.ServerApp.token = ''
c.ServerApp.password = ''
c.ServerApp.allow_remote_access = True
c.ServerApp.allow_origin = '*'
```

## Future Additions
- Climatology calculations.
- Trend estimation.
- Seasonal anomalies.
- Other variable-specific workflows.

## Notes to Keep Updating
- Record new benchmark timings here when a full run completes.
- Add any variable-specific chunking guidance if a different field behaves differently.
- Keep the notebook-specific workflow notes in this file so future runs stay consistent.