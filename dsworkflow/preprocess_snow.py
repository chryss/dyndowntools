#!/usr/bin/env python

import argparse
from pathlib import Path
import xarray as xr
from cfgrib.xarray_to_grib import to_grib

ERADIR = "/center1/DYNDOWN/cwaigl/ERA5_WRF/era5_grib"
JRADIR = "/center1/DYNDOWN/cwaigl/ERA5_WRF/jra55_grib"
MASKDIR = "masks"
MASKFN = "glaciermask_thresh_1m_dilate2.nc"
ERAPREFIX = "e5.oper.an.sfc.128_141_sd.ll025sc."
# JRAPREFIX = "anl_land125.065_snwe."
JRAPREFIX = "anl_land.065_snwe.reg_tl319."

def parse_arguments():
    """Parse arguments"""
    parser = argparse.ArgumentParser(description='Generate synthetic snow from ERA5 and JRA55')
    parser.add_argument('--eradir',  
        default=ERADIR,
        type=str,
        help='directory where ERA5 files are located')
    parser.add_argument('--jradir',  
        default=JRADIR,
        type=str,
        help='directory where JRA55 files are located')
    parser.add_argument('yrmonth',  
        help='for which download month to run; format YYYYMM: 201810 = Oct 2018',
        type=str)
    return parser.parse_args()

if __name__ == "__main__":

    args = parse_arguments()
    erapth = Path(args.eradir)
    jrapth = Path(args.jradir)
    maskpth = Path(MASKDIR)
    
    mask = maskpth / MASKFN
    with xr.open_dataset(mask) as src:
        glaciermask = src.glaciermask

    for fpth in (erapth / args.yrmonth).glob(f"{ERAPREFIX}*"):
        monthstr_jra55 = fpth.stem[-21:-2] + "18"
        jra55path = jrapth / f"{JRAPREFIX}{monthstr_jra55}"
        with xr.open_dataset(jra55path, engine="cfgrib") as src:
            snow_jra = src.sd
        ds_era = xr.open_dataset(fpth, engine="cfgrib")
        combined_DS = ds_era.sd.where(
                glaciermask==0).combine_first(
                snow_jra.fillna(0).interp_like(
                ds_era, method='nearest') / 1000)
        ds_era['sd'] = combined_DS
        to_grib(ds_era, erapth / args.yrmonth / ("synth_" + fpth.name))
        ds_era.close()
