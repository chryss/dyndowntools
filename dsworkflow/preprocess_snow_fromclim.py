#!/usr/bin/env python

import argparse
from pathlib import Path
import xarray as xr
import pandas as pd
from cfgrib.xarray_to_grib import to_grib

ERADIR = "/center1/DYNDOWN/cwaigl/ERA5_WRF/era5_grib"
JRADIR = "/center1/DYNDOWN/cwaigl/ERA5_WRF/jra55_grib"
MASKDIR = "masks"
MASKFN = "glaciermask_thresh_1.0m_dilate1.nc"
ERAPREFIX = "e5.oper.an.sfc.128_141_sd.ll025sc."
JRAFN = "jra55_snwe_clim_1966_1985"
THRESH = 1.0

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
    parser.add_argument('-m', '--mask',  
        action='store_true',
        help='whether we should use the predefined mask')
    parser.add_argument('-s', '--single',  
        action='store_true',
        help='whether we should only one method')
    parser.add_argument('yrmonth',  
        help='for which download month to run; format YYYYMM: 201810 = Oct 2018',
        type=str)
    return parser.parse_args()

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
            glaciermask = src.glaciermask
    else:
        infix='automask_'

    for fpth in (erapth / args.yrmonth).glob(f"{ERAPREFIX}*.grb"):
        # open both ERA5 and JRA55 datasets
        calendarstr = fpth.stem[-21:-2] + "18"
        jra55path = jrapth / JRAFN
        with xr.open_dataset(jra55path, engine="cfgrib") as src:
            snow_jra = src.sd
        ds_era = xr.open_dataset(fpth, engine="cfgrib")
        sd = ds_era.sd
        # masking of ERA5 snow
        if args.mask or not args.single:
            print("using supplied mask")
            sd = sd.where(glaciermask==0)
        if not args.single:
            print("adding intrinsic mask")
            sd = sd.where(sd < THRESH)
        # prepare JRA climatology slice with appropriate time coordinate
        numdays = len(ds_era.time) // 24
        theyear = ds_era.isel(time=0).time.dt.year.item()
        themonth = ds_era.isel(time=0).time.dt.month.item()
        startdatestr = f'{theyear}-{themonth}-01T00:00:00.000000000'
        startdatestr_JRA = f'1985-{themonth}-01T18:00:00.000000000'
        JRAclim_slice = snow_jra.sel(time=pd.date_range(startdatestr_JRA, freq='D', periods=numdays+1))
        JRAclim_slice.coords['time'] = pd.date_range(startdatestr, freq='D', periods=numdays+1)
        # combining
        combined_DS = sd.combine_first(
            JRAclim_slice.fillna(0).interp_like(
            ds_era, method='linear') / 1000)
        ds_era['sd'] = combined_DS
        to_grib(ds_era, erapth / args.yrmonth / (f"synth_{infix}" + fpth.name))
        ds_era.close()
