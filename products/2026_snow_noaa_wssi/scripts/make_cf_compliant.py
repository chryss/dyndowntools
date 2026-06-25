"""Rewrite the snow climatology NetCDF outputs in place with CF-compliant metadata."""

from pathlib import Path

import xarray as xr

from dyndowntools.climatology_metadata import add_monthly_climatology_metadata

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
CLIMATOLOGY_START = 1981
CLIMATOLOGY_END = 2010
REFERENCE_YEAR = 1995  # midpoint of the climatology period, non-leap

# within-year statistic computed before the across-years mean, by output filename prefix
WITHIN_YEAR_STATISTIC = {
    "acsnow_monthly_accum_clim": "sum",
    "snow_monthly_max_clim": "maximum",
    "snow_monthly_avg_clim": "mean",
}


def main() -> None:
    for fpath in sorted(OUTPUT_DIR.glob("*.nc")):
        prefix = next(p for p in WITHIN_YEAR_STATISTIC if fpath.name.startswith(p))
        print(f"Updating {fpath.name}")
        with xr.open_dataset(fpath) as ds:
            ds_cf = add_monthly_climatology_metadata(
                ds.load(),
                CLIMATOLOGY_START,
                CLIMATOLOGY_END,
                REFERENCE_YEAR,
                WITHIN_YEAR_STATISTIC[prefix],
            )
        tmp_path = fpath.with_suffix(".tmp.nc")
        ds_cf.to_netcdf(tmp_path)
        ds_cf.close()
        tmp_path.replace(fpath)


if __name__ == "__main__":
    main()
