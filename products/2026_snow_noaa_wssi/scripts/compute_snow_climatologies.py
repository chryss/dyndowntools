"""Compute 1981-2010 climatologies of monthly ACSNOW accumulation and SNOW
water-equivalent statistics from downscaled WRF/ERA5 output.

Produces three climatologies for one domain resolution per run: monthly
accumulated acsnow, monthly maximum SNOW, and monthly average SNOW, each
averaged across 1981-2010. Edit RESOLUTION and rerun for the other domain.
"""

import os
import time
from pathlib import Path

import dask
import pandas as pd
import xarray as xr
from dask.distributed import Client

RESOLUTION = 12  # 4 or 12 km
YEAR_START = 1981
YEAR_END = 2010
SOURCE_DIR = Path(f"/import/beegfs/CMIP6/wrf_era5/{RESOLUTION:02d}km/")
FILEPATTERN = f"era5_wrf_dscale_{RESOLUTION}km"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
MONTHS = [str(m).zfill(2) for m in range(1, 13)]

# Per-file reductions are independent (no rechunk/shuffle), so this is a
# throughput task: many small workers beat one big one. Sized for a 28-core /
# 150GB compute node allocation, per TECHNICAL_NOTES_KERCHUNK_QUANTILES_EXCEEDANCES.md's
# "exceedance counting" profile, scaled up.
N_WORKERS = 7
THREADS_PER_WORKER = 4
MEMORY_LIMIT = "20GB"  # 7 x 20 = 140GB, headroom on a 150GB node
DASK_SPILL_DIR = Path(f"/import/SNAP/{os.environ['USER']}/dask_spill")


def monthly_aggregates(
    filepaths: list[Path],
) -> tuple[xr.DataArray, xr.DataArray, xr.DataArray]:
    """Compute one month's acsnow sum, SNOW max, and SNOW mean from daily files.

    Each daily file is opened as a single dask chunk so the Client can
    parallelize across files within the month; results are computed
    (not left lazy) before returning, keeping memory bounded to one month
    of files rather than deferring the full 1981-2010 graph to the end.

    Parameters
    ----------
    filepaths : list of Path
        Daily source files covering one calendar month.

    Returns
    -------
    tuple of xr.DataArray
        (acsnow monthly sum, SNOW monthly max, SNOW monthly mean).
    """
    chunks = {"Time": -1, "south_north": -1, "west_east": -1}
    daily = [xr.open_dataset(pth, chunks=chunks) for pth in filepaths]
    # acsnow (lowercase) is already an hourly delta, post-processed from the
    # raw monotonic accumulator during extraction (see extract_vars.py
    # postproc_acc) -- summing it directly gives the monthly total.
    # SNOW (uppercase) is the raw instantaneous field straight off wrfout,
    # untouched by that post-processing.
    acsnow_sum = sum(ds.acsnow.sum(dim="Time") for ds in daily)
    snow_max = xr.concat(
        [ds.SNOW.max(dim="Time") for ds in daily], dim="day"
    ).max(dim="day")
    snow_mean = sum(ds.SNOW.mean(dim="Time") for ds in daily) / len(daily)
    return dask.compute(acsnow_sum, snow_max, snow_mean)


if __name__ == "__main__":
    client = Client(
        n_workers=N_WORKERS,
        threads_per_worker=THREADS_PER_WORKER,
        memory_limit=MEMORY_LIMIT,
        local_directory=str(DASK_SPILL_DIR),
        dashboard_address=":8787",
    )
    print(client.dashboard_link)
    start_time = time.perf_counter()

    years = [str(y) for y in range(YEAR_START, YEAR_END + 1)]
    acsnow_monthly, snowmax_monthly, snowmean_monthly = [], [], []

    for yr in years:
        print(f"Working on year {yr}")
        for mth in MONTHS:
            fpths = sorted((SOURCE_DIR / yr).glob(f"{FILEPATTERN}_{yr}-{mth}*.nc"))
            print(f"  month {mth}: {len(fpths)} files")
            acsnow_sum, snow_max, snow_mean = monthly_aggregates(fpths)
            acsnow_monthly.append(acsnow_sum)
            snowmax_monthly.append(snow_max)
            snowmean_monthly.append(snow_mean)
        print(f"  elapsed: {time.perf_counter() - start_time:.1f} s")

    time_index = pd.date_range(
        years[0], freq="ME", periods=len(years) * len(MONTHS), name="time"
    )
    acsnow_ts = xr.concat(acsnow_monthly, dim=time_index)
    snowmax_ts = xr.concat(snowmax_monthly, dim=time_index)
    snowmean_ts = xr.concat(snowmean_monthly, dim=time_index)

    print("Computing climatologies")
    acsnow_clim = acsnow_ts.groupby("time.month").mean()
    snowmax_clim = snowmax_ts.groupby("time.month").mean()
    snowmean_clim = snowmean_ts.groupby("time.month").mean()

    acsnow_clim.attrs.update(
        units="kg m-2",
        description=(
            f"Climatology ({YEAR_START}-{YEAR_END}) of monthly accumulated "
            "ACSNOW (hourly accumulated snow, summed within month, "
            "averaged across years)"
        ),
    )
    snowmax_clim.attrs.update(
        units="kg m-2",
        description=(
            f"Climatology ({YEAR_START}-{YEAR_END}) of monthly maximum SNOW "
            "(snow water equivalent, averaged across years)"
        ),
    )
    snowmean_clim.attrs.update(
        units="kg m-2",
        description=(
            f"Climatology ({YEAR_START}-{YEAR_END}) of monthly average SNOW "
            "(snow water equivalent, averaged across years)"
        ),
    )

    suffix = f"{YEAR_START}-{YEAR_END}_{RESOLUTION:02d}km.nc"
    print("Saving files")
    acsnow_clim.to_netcdf(
        OUTPUT_DIR / f"acsnow_monthly_accum_clim_{suffix}",
        encoding={"acsnow": {"zlib": True, "complevel": 5}},
    )
    snowmax_clim.to_netcdf(
        OUTPUT_DIR / f"snow_monthly_max_clim_{suffix}",
        encoding={"SNOW": {"zlib": True, "complevel": 5}},
    )
    snowmean_clim.to_netcdf(
        OUTPUT_DIR / f"snow_monthly_avg_clim_{suffix}",
        encoding={"SNOW": {"zlib": True, "complevel": 5}},
    )

    print(f"Total execution time: {time.perf_counter() - start_time:.1f} s")
