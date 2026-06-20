# testing out whether xr.open_dataset() or xr.open_mfdataset() 
# is the way to go for extracting / aggregating data 
 
import itertools
import time
from pathlib import Path
import numpy as np
import xarray as xr
import dask

datadir = Path("/import/SNAP/cwaigl/wrf_era5/04km/")
filepattern = "era5_wrf_dscale_4km_*.nc"
testyears_1 = ['2010', '2011']
testyears_2 = ['2012', '2013']
testyears_3 = [str(yr) for yr in range(1970, 2024)]
months = [str(item).zfill(2) for item in range (1, 13)]

if __name__ == '__main__':

    filelist_3 = sorted(list(itertools.chain(*[
        list((datadir / f"{yr}").glob("era5_wrf_dscale_4km_*.nc")) for yr in testyears_3])))
    filelist_2 = sorted(list(itertools.chain(*[
        list((datadir / f"{yr}").glob("era5_wrf_dscale_4km_*.nc")) for yr in testyears_2])))

    start_time = time.perf_counter ()

    with xr.open_mfdataset(filelist_3, chunks='auto', parallel=True) as ds:
        snowacc = ds.acsnow
        monthly_snowacc_1 = snowacc.resample(Time='ME').sum()
        monthly_snowacc_1.to_netcdf("snowacc_test3.nc")

    end_time = time.perf_counter ()
    print("Execution with mfdataset, 1970-")
    print(f"{end_time - start_time:.2f}", "seconds")