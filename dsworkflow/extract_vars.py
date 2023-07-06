# Extract variables from wrfout file
# Presumes 54h 

from pathlib import Path
from netCDF4 import Dataset
import wrf
import xarray as xr

WRFDATA = Path.home() / "Projects/dyndowndata/Icestorm2021/" 
TESTFOLDER = '211227'
SUBSETS = ['d01', 'd02']
PLEVELS = [200, 300, 500, 700, 850, 925, 1000]

if __name__ == '__main__':
    testset = SUBSETS[0]
    wrflist = [
        Dataset(item) for item in sorted(list((WRFDATA / f"{TESTFOLDER}").glob(f"wrfout_{testset}*")))
    ]
    rainnc = wrf.getvar(wrflist, 'RAINNC', timeidx=wrf.ALL_TIMES, method="cat")
    rainc = wrf.getvar(wrflist, 'RAINC', timeidx=wrf.ALL_TIMES, method="cat")
    slp = wrf.getvar(wrflist, "slp", timeidx=wrf.ALL_TIMES, method="cat")
    wind = wrf.getvar(wrflist, "wspd_wdir10", timeidx=wrf.ALL_TIMES, method="cat") 