"""Extract daily WRF 4km fields, clipped to the PCH summer study area.

For each day in May-Aug of the requested years, opens that day's 24-hourly
source file, clips it to the Porcupine Caribou Herd (PCH) summer study area
shapefile, and reduces to the day's requested statistic per variable. Writes
one NetCDF per year under output/.

The clip (shapefile reprojection, bounding-box index range, polygon mask) is
computed once from a reference file and reused across every day, since the
WRF grid is static across the whole record -- see dyndowntools.wrf_clip.
"""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import xarray as xr

from dyndowntools import paths
from dyndowntools.climatology_metadata import CONVENTIONS, CREATOR_EMAIL, CREATOR_NAME, INSTITUTION
from dyndowntools.wrf_clip import ClipInfo, apply_clip, build_clip_info

PRODUCT_ROOT = Path(__file__).resolve().parents[1]
SHAPEFILE_PATH = (
    PRODUCT_ROOT / "input_external" / "PCH_StudyArea" / "PCH_summer_SA_extent_WGS84.shp"
)
RESOLUTION = 4
DEFAULT_START_YEAR = 2021
DEFAULT_END_YEAR = 2024
DEFAULT_MONTHS = [5, 6, 7, 8]

# Noah LSM 4-layer soil scheme (soil_layers_stag), per user confirmation 2026-07-28:
# layer 1: 0-10 cm, layer 2: 10-40 cm, layer 3: 40-100 cm, layer 4: 100-200 cm.
SOIL_LAYER_DEPTH_BOUNDS_CM = [(0, 10), (10, 40), (40, 100), (100, 200)]
SOIL_LAYER_DEPTH_CM = [(top + bottom) / 2 for top, bottom in SOIL_LAYER_DEPTH_BOUNDS_CM]

# output_name -> (source variable, aggregation over the day's 24 hourly steps)
DAILY_STATS = {
    "t2_mean": ("T2", "mean"),
    "t2_min": ("T2", "min"),
    "t2_max": ("T2", "max"),
    "snow_00z": ("SNOW", "snapshot"),
    "snowc_00z": ("SNOWC", "snapshot"),
    "snowh_00z": ("SNOWH", "snapshot"),
    "smois_mean": ("SMOIS", "mean"),
    "tslb_min": ("TSLB", "min"),
    "tslb_max": ("TSLB", "max"),
}
SOURCE_VARS = sorted({v for v, _ in DAILY_STATS.values()} | {"rainc", "rainnc", "XLAT", "XLONG"})

VAR_METADATA = {
    "t2_mean": dict(units="K", long_name="daily mean 2m air temperature", standard_name="air_temperature"),
    "t2_min": dict(units="K", long_name="daily minimum 2m air temperature", standard_name="air_temperature"),
    "t2_max": dict(units="K", long_name="daily maximum 2m air temperature", standard_name="air_temperature"),
    "precip_total": dict(units="mm", long_name="daily total precipitation (convective + grid-scale)"),
    "snow_00z": dict(units="kg m-2", long_name="snow water equivalent at 00Z"),
    "snowc_00z": dict(units="1", long_name="snow cover flag at 00Z"),
    "snowh_00z": dict(units="m", long_name="physical snow depth at 00Z"),
    "smois_mean": dict(
        units="m3 m-3", long_name="daily mean soil moisture", standard_name="moisture_content_of_soil_layer"
    ),
    "tslb_min": dict(units="K", long_name="daily minimum soil temperature", standard_name="soil_temperature"),
    "tslb_max": dict(units="K", long_name="daily maximum soil temperature", standard_name="soil_temperature"),
}


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for daily caribou-product extraction."""
    parser = argparse.ArgumentParser(
        description="Extract daily WRF 4km fields clipped to the PCH summer study area."
    )
    parser.add_argument("--start-year", type=int, default=DEFAULT_START_YEAR)
    parser.add_argument("--end-year", type=int, default=DEFAULT_END_YEAR)
    parser.add_argument("--months", type=int, nargs="+", default=DEFAULT_MONTHS)
    parser.add_argument("--outdir", type=Path, default=PRODUCT_ROOT / "output")
    parser.add_argument(
        "--overwrite", action="store_true", help="Recompute years whose output file already exists."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="List the days that would be processed, without reading data."
    )
    return parser.parse_args()


def files_for_year_months(datadir: Path, year: int, months: list[int]) -> list[Path]:
    """Return sorted daily source file paths for one year, filtered to the given months."""
    year_dir = datadir / str(year)
    files = []
    for month in months:
        files.extend(year_dir.glob(f"era5_wrf_dscale_{RESOLUTION}km_{year}-{month:02d}-*.nc"))
    return sorted(files)


def file_date(path: Path) -> dt.date:
    """Parse the calendar date encoded in a daily source filename."""
    return dt.datetime.strptime(path.stem.rsplit("_", 1)[-1], "%Y-%m-%d").date()


def compute_daily_stats(ds: xr.Dataset) -> xr.Dataset:
    """Reduce one day's 24-hourly clipped Dataset to its daily statistics.

    Parameters
    ----------
    ds : xr.Dataset
        One day's source variables (24 Time steps), already clipped.

    Returns
    -------
    xr.Dataset
        One value per DAILY_STATS entry, plus precip_total (rainc+rainnc,
        summed over the day -- both are already hourly deltas in this
        dataset, confirmed against a rainy day: hourly values fluctuate up
        and down rather than monotonically accumulating).
    """
    out = {}
    for out_name, (source_var, agg) in DAILY_STATS.items():
        da = ds[source_var]
        if agg == "mean":
            out[out_name] = da.mean(dim="Time")
        elif agg == "min":
            out[out_name] = da.min(dim="Time")
        elif agg == "max":
            out[out_name] = da.max(dim="Time")
        elif agg == "snapshot":
            out[out_name] = da.isel(Time=0, drop=True)
    out["precip_total"] = (ds["rainc"] + ds["rainnc"]).sum(dim="Time")
    for da in out.values():
        da.attrs = {}  # drop the stale source variable's attrs (own metadata set by the caller)
    return xr.Dataset(out)


def process_year(
    year: int, datadir: Path, months: list[int], clip: ClipInfo, outdir: Path, overwrite: bool
) -> None:
    """Build and write the clipped daily-statistics NetCDF for one year."""
    out_path = outdir / f"akcasc_caribou_daily_{year}.nc"
    if out_path.exists() and not overwrite:
        print(f"[{year}] {out_path.name} already exists, skipping (use --overwrite to redo).")
        return

    paths_for_year = files_for_year_months(datadir, year, months)
    if not paths_for_year:
        print(f"[{year}] No source files found for months {months}, skipping.")
        return

    daily = []
    dates = []
    for fpath in paths_for_year:
        ds = xr.open_dataset(fpath)[SOURCE_VARS]
        ds = apply_clip(ds, clip)
        daily.append(compute_daily_stats(ds))
        dates.append(file_date(fpath))
        ds.close()

    time_index = [dt.datetime(d.year, d.month, d.day) for d in dates]
    out_ds = xr.concat(daily, dim=xr.DataArray(time_index, dims="time", name="time"))

    ref_ds = xr.open_dataset(paths_for_year[0])[["XLAT", "XLONG"]]
    ref_ds = apply_clip(ref_ds, clip)
    out_ds = out_ds.assign_coords(XLAT=ref_ds["XLAT"], XLONG=ref_ds["XLONG"])
    ref_ds.close()

    out_ds = out_ds.assign_coords(soil_layers_stag=("soil_layers_stag", SOIL_LAYER_DEPTH_CM))
    out_ds["soil_layer_depth_bounds"] = (("soil_layers_stag", "nv"), SOIL_LAYER_DEPTH_BOUNDS_CM)
    out_ds["soil_layers_stag"].attrs.update(
        standard_name="depth",
        long_name="soil layer center depth",
        units="cm",
        positive="down",
        axis="Z",
        bounds="soil_layer_depth_bounds",
    )

    for var, meta in VAR_METADATA.items():
        out_ds[var].attrs.update(meta)
    out_ds["XLAT"].attrs.update(standard_name="latitude", long_name="latitude", units="degrees_north")
    out_ds["XLONG"].attrs.update(standard_name="longitude", long_name="longitude", units="degrees_east")
    out_ds.attrs.update(
        Conventions=CONVENTIONS,
        institution=INSTITUTION,
        creator_name=CREATOR_NAME,
        creator_email=CREATOR_EMAIL,
        source=f"Clipped to PCH summer study area from daily {RESOLUTION}km downscaled ERA5/WRF output",
        year=year,
        generated=dt.datetime.now(dt.timezone.utc).isoformat(),
    )

    outdir.mkdir(parents=True, exist_ok=True)
    encoding = {var: {"zlib": True, "complevel": 5} for var in VAR_METADATA}
    tmp_path = out_path.with_suffix(".nc.tmp")
    out_ds.to_netcdf(tmp_path, encoding=encoding)
    tmp_path.rename(out_path)
    print(f"[{year}] wrote {out_path.name} ({len(paths_for_year)} days)")


def main() -> None:
    """Run daily extraction for the requested year range and months."""
    args = parse_args()
    datadir = paths.resolve("wrf_era5_root") / f"{RESOLUTION:02d}km"
    years = range(args.start_year, args.end_year + 1)

    if args.dry_run:
        for year in years:
            n = len(files_for_year_months(datadir, year, args.months))
            print(f"[{year}] {n} source files for months {args.months}")
        return

    reference_path = files_for_year_months(datadir, args.start_year, args.months)[0]
    reference_ds = xr.open_dataset(reference_path)[["XLAT", "XLONG"]]
    clip = build_clip_info(reference_ds, str(SHAPEFILE_PATH))
    reference_ds.close()
    print(
        f"Clip: south_north {clip.south_north}, west_east {clip.west_east}, "
        f"{int(clip.mask.sum())}/{clip.mask.size} cells inside polygon"
    )

    for year in years:
        process_year(year, datadir, args.months, clip, args.outdir, args.overwrite)


if __name__ == "__main__":
    main()
