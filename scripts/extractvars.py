o#!/usr/bin/env python
# 
# Extract variables from wrfout file

import xarray as xr
import netCDF4 as nc
from pathlib import Path
import wrf 

WRFDIR = "/center1/DYNDOWN/cwaigl/ERA5_WRF/WRF/run_active/"
WRFPTH = Path(WRFDIR)

d01wrf = [nc.Dataset(item) 
    for item in sorted(list(WRFPTH.glob("wrfout_d01_*")))]

rh_cat = wrf.getvar(d01wrf, "RH", timeidx=wrf.ALL_TIMES, method="cat")

print(rh_cat)