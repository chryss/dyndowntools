# Extract variables from wrfout file
# Presumes 54h 

import logging
import argparse
from pathlib import Path
from netCDF4 import Dataset
import wrf
import xarray as xr
import datetime as dt

logging.basicConfig(level=logging.DEBUG)

WRFDATA = Path.home() / "Projects/dyndowndata/Icestorm2021/" 
OUTDATA = Path.home() / "Projects/dyndowndata/proctest02/" 
TESTFOLDER = '211229'
SUBSETS = {'d01': '12km', 
           'd02': '4km'}
PLEVELS = [200., 300., 500., 700., 850., 925., 1000.]
COMPRESSIONLEVEL = 5

VARS = ['RAINNC', 'RAINC', 'ACSNOW', 'slp', 
        'wspd_wdir10', 'uvmet10', 'ctt', 'dbz', 
        'rh2', 'T2', 'Q2', 'PSFC', 
        'SNOW', 'SNOWH', 'SNOWC',
        'twb', 'ALBEDO', 'SMOIS', 'SH2O',
        'TSK', 'TSLB', 'SEAICE', 'SST',
        'HFX', 'LH',
        'SWDNB', 'SWDNBC', 'SWUPB', 'SWUPBC',
        'LWDNB', 'LWDNBC', 'LWUPB', 'LWUPBC',
        'rh', 'temp', 'z', 'uvmet', 'wa',
        'CLDFRA', 'QVAPOR']
ACCVARS = ['rainnc', 'rainc', 'acsnow']
PRESSUREVARS = ['temp', 'z', 'u', 'v', 'w',
        'dbz', 'twb', 'rh', 'CLDFRA', 'QVAPOR']

def parse_arguments():
    """Parse arguments"""
    parser = argparse.ArgumentParser(description='Extract variables from wrfout to daily NetCDF')
    parser.add_argument('-w', '--wrfdir',  
        default=WRFDATA,
        type=str,
        help='directory where wrfout files are located')
    parser.add_argument('-o','--outdir',  
        default=None,
        type=str,
        help='directory to write output to')
    return parser.parse_args()

def get_var_all(fn, varname):
    return wrf.getvar(fn, varname, timeidx=wrf.ALL_TIMES, method="cat")

def postproc_acc(accarray):
    accarray = accarray.diff("Time")
    return accarray.where(accarray >= 0, other=0)
    
def postproc_snow(snowarr):
    return snowarr.where(snowarr <= 330, other=330)

def postproc_snowh(snowarr):
    return snowarr.where(snowarr <= 2.2, other=2.2)

def postproc_pressurelevel(varname, fn, fieldtypelabel=None):
    return wrf.vinterp(fn,
               field=varname,
               vert_coord="p",
               interp_levels=PLEVELS,
               timeidx=wrf.ALL_TIMES,
               extrapolate=True,
               field_type=fieldtypelabel,
               log_p=True)

if __name__ == '__main__':
    for testset in SUBSETS:
        res = SUBSETS[testset]
        filelist = sorted(list((WRFDATA / f"{TESTFOLDER}").glob(f"wrfout_{testset}*")))
        startdate = dt.datetime.strptime(TESTFOLDER, '%y%m%d')

        concatdic = {}
        mergedic = {}
        for fn in filelist:
            logging.info(f"getting vars from {fn.stem}")
            with Dataset(fn) as ncfile:
                for varname in VARS:
                    concatdic[varname] = get_var_all(ncfile, varname)

                logging.debug(f"splitting up wind vars")
                concatdic['wspd10'] = concatdic['wspd_wdir10'].sel(wspd_wdir='wspd', drop=True)
                concatdic['wdir10'] = concatdic['wspd_wdir10'].sel(wspd_wdir='wdir', drop=True)
                concatdic['u10'] = concatdic['uvmet10'].sel(u_v='u', drop=True)
                concatdic['v10'] = concatdic['uvmet10'].sel(u_v='v', drop=True)
                concatdic['u'] = concatdic['uvmet'].sel(u_v='u', drop=True)
                concatdic['v'] = concatdic['uvmet'].sel(u_v='v', drop=True)
                concatdic['w'] = concatdic['wa']
                concatdic.pop('wspd_wdir10', None)
                concatdic.pop('uvmet10', None)
                concatdic.pop('uvmet', None)
                concatdic.pop('wa', None)
                for varname in ['wspd10', 'wdir10', 'u10', 'v10', 'u', 'v', 'w']:
                    concatdic[varname].name = varname

                logging.debug(f"post-processing pressure level vars")
                for varname in PRESSUREVARS:
                    if varname == 'temp':
                        concatdic[varname] = postproc_pressurelevel(concatdic[varname], ncfile, fieldtypelabel='tk')
                    else:
                        concatdic[varname] = postproc_pressurelevel(concatdic[varname], ncfile)

                logging.debug(f"post-processing snow")
                concatdic['SNOW'] = postproc_snow(concatdic['SNOW'])
                concatdic['SNOWH'] = postproc_snowh(concatdic['SNOWH'])

                logging.info("Append to variable merge dictionary")
                for var in concatdic:
                    try:
                        mergedic[var].append(concatdic[var])
                    except KeyError:
                        mergedic[var] = [concatdic[var]]
        
        concatdic = {
            item: xr.concat(mergedic[item], dim='Time') 
            for item in concatdic}
        
        print(f"postprocessing accumulating variables")
        for varname in ACCVARS:
            concatdic[varname] = postproc_acc(concatdic[varname.upper()])
            concatdic[varname].name = varname
            concatdic[varname].attrs = concatdic[varname.upper()].attrs
            concatdic[varname].attrs['description'] = 'HOURLY ' + concatdic[varname].attrs['description']
            concatdic.pop(varname.upper())

        logging.debug(concatdic.keys())
        logging.debug([item.name for item in concatdic.values()])

        logging.debug("merging vars")
        merged_datasets = [item.to_dataset() for item in concatdic.values()]
        merged = xr.merge(merged_datasets)

        merged.attrs['date'] = dt.datetime.now().isoformat()
        merged.attrs['data'] = 'Downscaled ERA5 using WRF'
        merged.attrs['info'] = 'Alaska Climate Adaptation Science Center, University of Alaska Fairbanks'
        merged.attrs['contact'] = 'cwaigl@alaska.edu'
        merged.attrs['version'] = 'WRF V4.3.3'
        merged.interp_level.attrs['units'] = "hPa"
        for var in merged.data_vars:
            merged[var].attrs['projection'] = str(merged[var].attrs['projection'])

        encoding = {
            var: {"zlib": True, "complevel": COMPRESSIONLEVEL}
            for var in merged.data_vars
        }

        for delta in [0, 1]:
            daystamp = (startdate + dt.timedelta(days=delta)).strftime('%Y-%m-%d')
            logging.info(f'Writing era5_wrf_dscale_{daystamp}_{res}.nc')
            logging.debug(f"{daystamp}")
            merged.sel(Time=slice(daystamp, daystamp)).to_netcdf(
                OUTDATA / f"era5_wrf_dscale_{daystamp}_{res}.nc", engine="netcdf4", encoding=encoding)
