"""Export each daily-extraction variable to per-day GeoTIFFs, one subfolder per variable.

Reads the yearly NetCDF outputs of extract_daily_vars.py and writes one
GeoTIFF per variable per day via dyndowntools.wrf_geotiff.to_geotiff().
Variables with a soil_layers_stag dimension (smois_mean, tslb_min, tslb_max)
are written as 4-band GeoTIFFs (one band per layer, labeled with each layer's
depth range), since to_geotiff allows one non-spatial "band" dimension.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import rasterio
import xarray as xr

from dyndowntools.wrf_geotiff import to_geotiff
from extract_daily_vars import PRODUCT_ROOT, SOIL_LAYER_DEPTH_BOUNDS_CM, VAR_METADATA

DEFAULT_YEARS = [2021, 2022, 2023, 2024]
VARIABLES = list(VAR_METADATA)
SOIL_LAYER_VARS = ("smois_mean", "tslb_min", "tslb_max")
SOIL_LAYER_LABELS = [f"{top}-{bottom} cm" for top, bottom in SOIL_LAYER_DEPTH_BOUNDS_CM]


def _set_band_descriptions(tif_path: Path, labels: list[str]) -> None:
    """Label each band of an existing GeoTIFF in place (e.g. by soil layer depth)."""
    with rasterio.open(tif_path, "r+") as dst:
        for band, label in enumerate(labels, start=1):
            dst.set_band_description(band, label)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for daily GeoTIFF export."""
    parser = argparse.ArgumentParser(
        description=(
            "Export akcasc_caribou_daily_<year>.nc variables to per-day GeoTIFFs, "
            "one subfolder per variable."
        )
    )
    parser.add_argument("--years", type=int, nargs="+", default=DEFAULT_YEARS)
    parser.add_argument("--indir", type=Path, default=PRODUCT_ROOT / "output")
    parser.add_argument("--outdir", type=Path, default=PRODUCT_ROOT / "output" / "geotiff")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing GeoTIFFs.")
    return parser.parse_args()


def export_year(nc_path: Path, variables: list[str], outdir: Path, overwrite: bool) -> int:
    """Write one GeoTIFF per variable per day for one year's NetCDF file."""
    ds = xr.open_dataset(nc_path)
    n_written = 0
    for var in variables:
        var_dir = outdir / var
        var_dir.mkdir(parents=True, exist_ok=True)
        da = ds[var]
        for i in range(da.sizes["time"]):
            day = da.isel(time=i)
            date_str = str(day["time"].values)[:10]
            out_path = var_dir / f"{var}_{date_str}.tif"
            if out_path.exists() and not overwrite:
                continue
            to_geotiff(day, out_path)
            if var in SOIL_LAYER_VARS:
                _set_band_descriptions(out_path, SOIL_LAYER_LABELS)
            n_written += 1
    ds.close()
    return n_written


def main() -> None:
    """Export all requested years' variables to per-day GeoTIFFs."""
    args = parse_args()
    total = 0
    for year in args.years:
        nc_path = args.indir / f"akcasc_caribou_daily_{year}.nc"
        if not nc_path.exists():
            print(f"[{year}] {nc_path.name} not found, skipping.")
            continue
        n = export_year(nc_path, VARIABLES, args.outdir, args.overwrite)
        print(f"[{year}] wrote {n} GeoTIFFs from {nc_path.name}")
        total += n
    print(f"Total GeoTIFFs written: {total}")


if __name__ == "__main__":
    main()
