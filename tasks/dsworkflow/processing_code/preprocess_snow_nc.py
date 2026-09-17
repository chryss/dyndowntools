#!/usr/bin/env python
#
# Snow synthesis for NetCDF ERA5 (AWS mirror, see aws_era5_month.py), for
# any month regardless of pipeline generation. Same algorithm as
# preprocess_snow.py (ERA5 snow depth is primary, replaced by interpolated
# JRA snow water equivalent only inside the glacier/implausible-value mask)
# -- only the snow-source-specific I/O differs, selected by --jra-source:
#   - JRA-3Q ships as native NetCDF (no cfgrib), always one file per
#     calendar month (no yearly-file case like JRA-55 pre-2014). Its dims
#     are named lat/lon, not latitude/longitude -- renamed before
#     interp_like, otherwise it silently fails to align and broadcasts
#     instead of interpolating.
#   - JRA-55 ships as GRIB (opened via cfgrib, which already names dims
#     latitude/longitude), monthly files pre-2014 replaced by one yearly
#     file. Used for the pre-cutover / crossover case: ERA5 re-fetched as
#     NetCDF from the AWS mirror (e.g. to replace a corrupted RDA/GDEX GRIB
#     download) but snow still sourced from the already-downloaded JRA-55.
# preprocess_snow.py (GRIB ERA5 + JRA-55) is left untouched for the
# unmixed legacy pipeline.
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
JRA3QDIR = str(wu.JRA3Q_INPUT_DIR)
JRA55DIR = str(wu.JRA55_INPUT_DIR)
MASKDIR = "masks"
MASKFN = "glaciermask_thresh_1.0m_dilate1.nc"
ERAPREFIX = "e5.oper.an.sfc.128_141_sd.ll025sc."
JRA3QPREFIX = "jra3q.anl_surf.0_1_13.weasd-sfc-an-gauss."
JRA3QVAR = "weasd-sfc-an-gauss"
JRA55PREFIX = "anl_land.065_snwe.reg_tl319."
THRESH = 1.0


def parse_arguments():
    """Parse arguments"""
    parser = argparse.ArgumentParser(description='Generate synthetic snow from ERA5 (NetCDF) and JRA-55/JRA-3Q')
    parser.add_argument('--eradir',
        default=ERADIR,
        type=str,
        help='directory where ERA5 NetCDF files are located')
    parser.add_argument('--jradir',
        default=None,
        type=str,
        help='directory where JRA files are located (defaults to the standard JRA-55/JRA-3Q dir for --jra-source)')
    parser.add_argument('--jra-source',
        choices=['auto', 'jra55', 'jra3q'],
        default='auto',
        help="which JRA generation to source snow from; 'auto' picks by "
             f"date ({wu.JRA_CUTOVER_YRMONTH} onward -> JRA-3Q, earlier -> "
             "JRA-55), and errors on the transitional month 202401, which "
             "the pipeline splits mid-month (see README.md)")
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


def resolve_jra_source(yrmonth: str, requested: str) -> str:
    """Resolve 'auto' to jra55/jra3q by date; pass explicit choices through."""
    if requested != 'auto':
        return requested
    if yrmonth == "202401":
        raise ValueError(
            "202401 straddles the pipeline cutover mid-month -- pass "
            "--jra-source jra55 or jra3q explicitly for this month."
        )
    return 'jra3q' if yrmonth >= wu.JRA_CUTOVER_YRMONTH else 'jra55'


def jra3q_calendarstr(yrmonth: str) -> str:
    """JRA-3Q files are always monthly: YYYYMM0100_YYYYMM<lastday>18."""
    year, month = int(yrmonth[:4]), int(yrmonth[4:6])
    lastday = cal.monthrange(year, month)[1]
    return f"{yrmonth}0100_{yrmonth}{lastday:02d}18"


def jra55_calendarstr(erafpth: Path) -> str:
    """JRA-55 files are monthly (YYYYMMDDHH_YYYYMMDDHH18) from 2014 on,
    yearly (YYYY010100_YYYY123118) before that -- derived from the ERA5
    filename's own firsthr_lasthr tail, replacing its last-hour ...23 with
    JRA-55's ...18 synoptic hour."""
    calendarstr = erafpth.stem[-21:-2] + "18"
    yrstr = calendarstr[:4]
    if int(yrstr) < 2014:
        calendarstr = f"{yrstr}010100_{yrstr}123118"
    return calendarstr


def load_snow_jra(jra_source: str, jrapth: Path, yrmonth: str, erafpth: Path = None) -> xr.DataArray:
    """Load the JRA snow field for one month, in ERA5's latitude/longitude naming."""
    if jra_source == 'jra3q':
        jra3qpath = jrapth / f"{JRA3QPREFIX}{jra3q_calendarstr(yrmonth)}.{EXT}"
        with xr.open_dataset(jra3qpath, engine="netcdf4") as src:
            return src[JRA3QVAR].rename({'lat': 'latitude', 'lon': 'longitude'}).load()
    jra55path = jrapth / f"{JRA55PREFIX}{jra55_calendarstr(erafpth)}"
    with xr.open_dataset(jra55path, engine="cfgrib") as src:
        # cfgrib attaches step/surface/valid_time alongside the real `time`
        # dim coordinate; unlike time, these don't survive interp_like onto
        # ERA5's own time axis intact (valid_time in particular has come
        # back holding the raw int64 NaT sentinel, -2**63, which then
        # overflows any later decode_times=True read) -- drop them here so
        # they never enter the interpolation/combine chain at all.
        return src.sd.reset_coords(['step', 'surface', 'valid_time'], drop=True).load()


if __name__ == "__main__":

    args = parse_arguments()
    erapth = Path(args.eradir)
    jra_source = resolve_jra_source(args.yrmonth, args.jra_source)
    jrapth = Path(args.jradir) if args.jradir else Path(JRA3QDIR if jra_source == 'jra3q' else JRA55DIR)

    if args.mask or not args.single:
        print("loading glaciers")
        infix = ''
        maskpth = Path(MASKDIR)
        mask = maskpth / MASKFN
        with xr.open_dataset(mask) as src:
            glaciermask = src.glaciermask.load()
    else:
        infix = 'automask_'

    erafiles = list((erapth / args.yrmonth).glob(f"{ERAPREFIX}*.{EXT}"))
    # JRA-3Q is one file per month, loaded once outside the loop; JRA-55's
    # calendar string is derived per ERA5 file (yearly file pre-2014 is the
    # same file reused across each month's single ERA5 file in that year).
    if jra_source == 'jra3q':
        snow_jra = load_snow_jra(jra_source, jrapth, args.yrmonth)

    for fpth in erafiles:
        if jra_source == 'jra55':
            snow_jra = load_snow_jra(jra_source, jrapth, args.yrmonth, erafpth=fpth)
        ds_era = xr.open_dataset(fpth, engine=ENGINE)
        # ERA5's own SD ships as float64 on disk (unlike every other ERA5
        # variable here, which is float32) -- snow depth in meters doesn't
        # need double precision, and combine_first upcasts its whole result
        # to match whichever operand is wider, so leaving this as float64
        # doubles the memory footprint of every step below.
        sd = ds_era.SD.astype('float32')
        if args.mask or not args.single:
            print("using supplied mask")
            sd = sd.where(glaciermask == 0)
        if not args.single:
            print("adding intrinsic mask")
            sd = sd.where(sd < THRESH)
        # interp_like's scipy-based interpolation promotes float32 input to
        # float64 internally regardless of source dtype -- cast back down
        # before combine_first, or the same doubling happens from this side.
        snow_interp = snow_jra.fillna(0).interp_like(
            ds_era, method='linear').astype('float32') / 1000
        combined_DS = sd.combine_first(snow_interp)
        # JRA's grid falls just short of ERA5's at the poles/date line;
        # interp_like doesn't extrapolate, so a thin edge sliver can stay
        # NaN where ERA5 was also masked there. Physically reasonable to
        # zero-fill (no valid snow estimate from either source) rather than
        # leave holes in the output.
        combined_DS = combined_DS.fillna(0)
        ds_era['SD'] = combined_DS
        ds_era.to_netcdf(erapth / args.yrmonth / (f"synth_{infix}" + fpth.name), engine=ENGINE)
        ds_era.close()
