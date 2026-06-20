"""Extract one gridded variable from the daily downscaled ERA5/WRF NetCDF files
into one well-chunked NetCDF file per year.

Storage chunks span the full year along Time with small spatial blocks
(default 8x8), matching the layout validated in
TECHNICAL_NOTES_KERCHUNK_QUANTILES_EXCEEDANCES.md for exact per-pixel
quantile/trend calculations on this dataset.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import time
from functools import partial
from pathlib import Path

import xarray as xr
from dask.distributed import Client

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATADIR = Path("/beegfs/CMIP6/wrf_era5")
DEFAULT_START_YEAR = 1959
DEFAULT_END_YEAR = 2022


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for annual variable extraction."""
    parser = argparse.ArgumentParser(
        description=(
            "Extract one variable from the daily downscaled ERA5/WRF NetCDF files "
            "into one well-chunked NetCDF file per year."
        )
    )
    parser.add_argument("--variable", default="wspd10", help="Variable to extract.")
    parser.add_argument(
        "--datadir",
        type=Path,
        default=DEFAULT_DATADIR,
        help="Base directory containing per-resolution/per-year folders.",
    )
    parser.add_argument("--resolution", type=int, default=4, help="Resolution in km.")
    parser.add_argument("--start-year", type=int, default=DEFAULT_START_YEAR)
    parser.add_argument("--end-year", type=int, default=DEFAULT_END_YEAR)
    parser.add_argument(
        "--outdir",
        type=Path,
        default=None,
        help="Output directory (default: extraction/annual/<variable> under the repo root).",
    )
    parser.add_argument(
        "--spatial-chunksize",
        type=int,
        default=8,
        help=(
            "south_north/west_east chunk size, used both for the Dask array and the "
            "on-disk NetCDF chunk layout. 8 matches the validated quantile/trend chunking."
        ),
    )
    parser.add_argument("--complevel", type=int, default=5, help="NetCDF zlib compression level.")
    parser.add_argument("--n-workers", type=int, default=4)
    parser.add_argument("--threads-per-worker", type=int, default=4)
    parser.add_argument("--memory-limit", default="16GB", help="Memory limit per worker.")
    parser.add_argument(
        "--pack-int16",
        action="store_true",
        help=(
            "Store the variable as scaled int16 (CF scale_factor/add_offset) instead of "
            "float32, rounded to --scale-factor precision. Cuts file size substantially."
        ),
    )
    parser.add_argument(
        "--scale-factor",
        type=float,
        default=0.01,
        help="Quantization step (m/s) used when --pack-int16 is set.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Recompute and overwrite years whose annual output file already exists.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List the years and file counts that would be processed, without reading or writing data.",
    )
    args = parser.parse_args()
    if args.outdir is None:
        args.outdir = PROJECT_ROOT / "extraction" / "annual" / args.variable
    return args


def is_leap_year(year: int) -> bool:
    """Return True if `year` is a leap year (Gregorian calendar)."""
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def files_for_year(datadir: Path, resolution: int, year: int) -> list[Path]:
    """Return sorted daily NetCDF paths for one resolution/year."""
    year_dir = datadir / f"{resolution:02d}km" / str(year)
    return sorted(year_dir.glob(f"era5_wrf_dscale_{resolution}km_{year}-*.nc"))


def select_vars(ds: xr.Dataset, variable: str) -> xr.Dataset:
    """Keep only the target variable plus static lat/lon, before combining files."""
    keep = [variable] + [v for v in ("XLAT", "XLONG") if v in ds.variables]
    return ds[keep]


def attach_static_latlon(da: xr.DataArray, ds_ref: xr.Dataset) -> xr.DataArray:
    """Attach static XLAT/XLONG coords (Time-independent) if available."""
    out = da
    for name in ("XLAT", "XLONG"):
        if name in ds_ref.variables:
            coord = ds_ref[name]
            if "Time" in coord.dims:
                coord = coord.isel(Time=0, drop=True)
            out = out.assign_coords({name: coord})
    return out


def extract_year(
    year: int,
    variable: str,
    datadir: Path,
    resolution: int,
    outdir: Path,
    spatial_chunksize: int,
    complevel: int,
    pack_int16: bool,
    scale_factor: float,
    overwrite: bool,
) -> None:
    """Build and write the annual NetCDF extract for one year, if not already done."""
    out_path = outdir / f"{variable}_{resolution}km_{year}.nc"
    if out_path.exists() and not overwrite:
        print(f"[{year}] {out_path.name} already exists, skipping (use --overwrite to redo).")
        return

    paths = files_for_year(datadir, resolution, year)
    if not paths:
        print(f"[{year}] No source files found under {datadir}, skipping.")
        return

    expected = 366 if is_leap_year(year) else 365
    if len(paths) != expected:
        print(f"[{year}] WARNING: found {len(paths)} daily files, expected {expected}.")

    start = time.perf_counter()
    ds_full = xr.open_mfdataset(
        paths,
        parallel=True,
        chunks={"Time": 24},
        data_vars="minimal",
        coords="minimal",
        compat="override",
        preprocess=partial(select_vars, variable=variable),
    )

    if variable not in ds_full.variables:
        raise KeyError(f"Variable '{variable}' not found in source files for {year}.")

    n_time = ds_full.sizes["Time"]
    expected_hours = 8784 if is_leap_year(year) else 8760
    if n_time != expected_hours:
        diff = expected_hours - n_time
        direction = "missing" if diff > 0 else "extra"
        print(
            f"[{year}] WARNING: {n_time} hours found, expected {expected_hours} "
            f"({abs(diff)} {direction})."
        )

    da = ds_full[variable].chunk(
        {"Time": -1, "south_north": spatial_chunksize, "west_east": spatial_chunksize}
    )
    da = attach_static_latlon(da, ds_full)
    da.name = variable

    out_ds = da.to_dataset()
    out_ds.attrs.update(
        {
            "source": f"Extracted from daily {resolution}km downscaled ERA5/WRF output",
            "variable": variable,
            "year": year,
            "contact": "cwaigl@alaska.edu",
            "generated": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
    )

    encoding = {
        variable: {
            "zlib": True,
            "complevel": complevel,
            "shuffle": True,
            "chunksizes": (n_time, spatial_chunksize, spatial_chunksize),
        }
    }
    if pack_int16:
        encoding[variable].update(
            {
                "dtype": "int16",
                "scale_factor": scale_factor,
                "add_offset": 0.0,
                "_FillValue": -32767,
            }
        )

    outdir.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(".nc.tmp")
    out_ds.to_netcdf(tmp_path, encoding=encoding)
    tmp_path.rename(out_path)
    ds_full.close()

    elapsed = time.perf_counter() - start
    print(
        f"[{year}] wrote {out_path.name} ({n_time} hours from {len(paths)} files) "
        f"in {elapsed:.1f}s"
    )


def main() -> None:
    """Run annual extraction for the requested year range."""
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    years = range(args.start_year, args.end_year + 1)

    if args.dry_run:
        for year in years:
            paths = files_for_year(args.datadir, args.resolution, year)
            out_path = args.outdir / f"{args.variable}_{args.resolution}km_{year}.nc"
            status = "exists" if out_path.exists() else "to do"
            print(f"[{year}] {len(paths)} source files, output {status}: {out_path.name}")
        return

    user = os.environ.get("USER", "cwaigl")
    spill_dir = Path(f"/import/SNAP/{user}/dask_spill")
    spill_dir.mkdir(parents=True, exist_ok=True)

    client = Client(
        n_workers=args.n_workers,
        threads_per_worker=args.threads_per_worker,
        memory_limit=args.memory_limit,
        local_directory=str(spill_dir),
        dashboard_address=":8787",
    )
    print(f"Dashboard: {client.dashboard_link}")

    start = time.perf_counter()
    failed_years = []
    for year in years:
        try:
            extract_year(
                year=year,
                variable=args.variable,
                datadir=args.datadir,
                resolution=args.resolution,
                outdir=args.outdir,
                spatial_chunksize=args.spatial_chunksize,
                complevel=args.complevel,
                pack_int16=args.pack_int16,
                scale_factor=args.scale_factor,
                overwrite=args.overwrite,
            )
        except Exception as exc:
            failed_years.append(year)
            print(f"[{year}] ERROR: {exc!r}, skipping to next year.")

    client.close()
    print(f"Total run time: {time.perf_counter() - start:.1f}s")
    if failed_years:
        print(f"Years that failed and need attention: {failed_years}")


if __name__ == "__main__":
    main()
