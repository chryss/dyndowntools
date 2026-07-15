#!/usr/bin/env python
#
# Snow synthesis for the 2024-01-02-forward era: NetCDF ERA5 (AWS mirror,
# see aws_era5_month.py) + JRA-3Q (see rda_JRA_yr.py) instead of GRIB
# ERA5 + JRA-55. Same algorithm as preprocess_snow.py (ERA5 snow depth is
# primary, replaced by interpolated JRA snow water equivalent only inside
# the glacier/implausible-value mask) -- only the source-specific I/O
# differs:
#   - JRA-3Q ships as native NetCDF (no cfgrib), always one file per
#     calendar month (no yearly-file case like JRA-55 pre-2014).
#   - JRA-3Q's dims are named lat/lon, not latitude/longitude -- renamed
#     before interp_like, otherwise it silently fails to align and
#     broadcasts instead of interpolating.
# preprocess_snow.py is left untouched; call this script instead for any
# month at/after 2024-01-02.
#
# cwaigl@alaska.edu 2026/07

import argparse
import calendar as cal
from pathlib import Path
import xarray as xr
import workflowutil as wu

ENGINE = 'netcdf4'
EXT = 'nc'

ERADIR = str(wu.ERA_NC_INPUT_DIR / "e5.oper.an.sfc")
JRADIR = str(wu.JRA3Q_INPUT_DIR)
MASKDIR = "masks"
MASKFN = "glaciermask_thresh_1.0m_dilate1.nc"
ERAPREFIX = "e5.oper.an.sfc.128_141_sd.ll025sc."
JRAPREFIX = "jra3q.anl_surf.0_1_13.weasd-sfc-an-gauss."
JRAVAR = "weasd-sfc-an-gauss"
THRESH = 1.0


def parse_arguments():
    """Parse arguments"""
    parser = argparse.ArgumentParser(description='Generate synthetic snow from ERA5 (NetCDF) and JRA-3Q')
    parser.add_argument('--eradir',
        default=ERADIR,
        type=str,
        help='directory where ERA5 NetCDF files are located')
    parser.add_argument('--jradir',
        default=JRADIR,
        type=str,
        help='directory where JRA-3Q files are located')
    parser.add_argument('-m', '--mask',
        action='store_true',
        help='whether we should use the predefined mask')
    parser.add_argument('-s', '--single',
        action='store_true',
        help='whether we should only use one method')
    parser.add_argument('yrmonth',
        help='for which month to run; format YYYYMM: 202401 = Jan 2024',
        type=str)
    return parser.parse_args()


def jra3q_calendarstr(yrmonth: str) -> str:
    """JRA-3Q files are always monthly: YYYYMM0100_YYYYMM<lastday>18."""
    year, month = int(yrmonth[:4]), int(yrmonth[4:6])
    lastday = cal.monthrange(year, month)[1]
    return f"{yrmonth}0100_{yrmonth}{lastday:02d}18"


if __name__ == "__main__":

    args = parse_arguments()
    erapth = Path(args.eradir)
    jrapth = Path(args.jradir)

    if args.mask or not args.single:
        print("loading glaciers")
        infix = ''
        maskpth = Path(MASKDIR)
        mask = maskpth / MASKFN
        with xr.open_dataset(mask) as src:
            glaciermask = src.glaciermask.load()
    else:
        infix = 'automask_'

    jra3qpath = jrapth / f"{JRAPREFIX}{jra3q_calendarstr(args.yrmonth)}.{EXT}"
    with xr.open_dataset(jra3qpath, engine="netcdf4") as src:
        snow_jra = src[JRAVAR].rename({'lat': 'latitude', 'lon': 'longitude'}).load()

    for fpth in (erapth / args.yrmonth).glob(f"{ERAPREFIX}*.{EXT}"):
        ds_era = xr.open_dataset(fpth, engine=ENGINE)
        sd = ds_era.SD
        if args.mask or not args.single:
            print("using supplied mask")
            sd = sd.where(glaciermask == 0)
        if not args.single:
            print("adding intrinsic mask")
            sd = sd.where(sd < THRESH)
        combined_DS = sd.combine_first(
            snow_jra.fillna(0).interp_like(
            ds_era, method='linear') / 1000)
        # JRA-3Q's grid falls just short of ERA5's at the poles/date line;
        # interp_like doesn't extrapolate, so a thin edge sliver can stay
        # NaN where ERA5 was also masked there. Physically reasonable to
        # zero-fill (no valid snow estimate from either source) rather than
        # leave holes in the output.
        combined_DS = combined_DS.fillna(0)
        ds_era['SD'] = combined_DS
        ds_era.to_netcdf(erapth / args.yrmonth / (f"synth_{infix}" + fpth.name), engine=ENGINE)
        ds_era.close()
