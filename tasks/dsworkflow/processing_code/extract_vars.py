# Extract variables from wrfout file
# Presumes 54h 

import logging
import argparse
import os
from pathlib import Path
from multiprocessing import Pool
from netCDF4 import Dataset
import wrf
import xarray as xr
import datetime as dt

LOGLEVEL=logging.INFO
TESTFOLDER = '211229'
WRFDATA = Path.home() / "Projects/dyndowndata/Icestorm2021/" / TESTFOLDER
OUTDATA = Path.home() / "Projects/dyndowndata/proctest02/"
SUBSETS = {'d01': '12km',
           'd02': '4km'}
PLEVELS = [200., 300., 500., 700., 850., 900., 925., 950., 1000.]
COMPRESSIONLEVEL = 5
NPROC = 10    # one wrfout file's extraction+vinterp per worker; ~10 files/subset in a 54h run

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
    parser.add_argument('--yrmd',  
        help='year-month-day to start; format YYYYMMDD: 20201210 = Dec 10, 2020',
        default=None,
        type=str)
    parser.add_argument('-d', '--debug', 
        help="switch on debugging output",
        action="store_true")
    parser.add_argument('-e', '--experimental', 
        help="experimental run - mark outputs",
        action="store_true")
    return parser.parse_args()

def get_args():
    """Get arguments with pre-processing"""
    args = parse_arguments()
    args.wrfdir = Path(args.wrfdir)
    if args.outdir is None:
        args.outdir = args.wrfdir
    else:
        args.outdir = Path(args.outdir)
    if args.yrmd is None:
        yrstr = args.wrfdir.stem
        if int(yrstr[:2]) > 39:
            args.yrmd = '19' + yrstr
        else: 
            args.yrmd = '20' + yrstr
    return args

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

def _init_worker():
    # wrf.getvar's diagnostic calculations (dbz, rh, etc.) can use OpenMP
    # internally; without this, NPROC worker processes could each try to
    # fan out across all cores and oversubscribe the node.
    os.environ["OMP_NUM_THREADS"] = "1"

def process_file(fn):
    """Extract and postprocess all variables for one wrfout file."""
    logging.info(f"getting vars from {fn.stem}")
    with Dataset(fn) as ncfile:
        concatdic = {varname: get_var_all(ncfile, varname) for varname in VARS}

        logging.debug("splitting up wind vars")
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

        logging.debug("post-processing pressure level vars")
        for varname in PRESSUREVARS:
            if varname == 'temp':
                concatdic[varname] = postproc_pressurelevel(concatdic[varname], ncfile, fieldtypelabel='tk')
            else:
                concatdic[varname] = postproc_pressurelevel(concatdic[varname], ncfile)

    return concatdic

def build_chunksizes(dataarray):
    """Chunk by single Time step, full extent on every other dimension."""
    return tuple(1 if dim == 'Time' else dataarray.sizes[dim] for dim in dataarray.dims)

if __name__ == '__main__':
    args = get_args()

    loglevel = LOGLEVEL
    if args.debug:
        loglevel = logging.DEBUG
    logging.basicConfig(level=loglevel)

    for testset in SUBSETS:
        res = SUBSETS[testset]
        filelist = sorted(list((args.wrfdir).glob(f"wrfout_{testset}*")))
        startdate = dt.datetime.strptime(args.yrmd, '%Y%m%d')

        logging.info(f"extracting {len(filelist)} files for {testset} using {min(NPROC, len(filelist))} processes")
        with Pool(min(NPROC, len(filelist)), initializer=_init_worker) as pool:
            results = pool.map(process_file, filelist)

        mergedic = {}
        for concatdic in results:
            for var in concatdic:
                mergedic.setdefault(var, []).append(concatdic[var])

        # logging.debug(f"post-processing snow")
        # concatdic['SNOW'] = postproc_snow(concatdic['SNOW'])
        # concatdic['SNOWH'] = postproc_snowh(concatdic['SNOWH'])

        concatdic = {
            item: xr.concat(mergedic[item], dim='Time')
            for item in mergedic}

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
        merged.attrs['version'] = 'WRF V4.5.1 - project v. 1.1'
        merged.interp_level.attrs['units'] = "hPa"
        merged.wdir10.attrs['units'] = "degree"
        merged.XLONG.attrs['units'] = 'degrees_east'
        merged.XLONG.attrs['standard_name'] = 'longitude'
        merged.XLONG.attrs['long_name'] = 'longitude'
        merged.XLAT.attrs['units'] = 'degrees_north'
        merged.XLAT.attrs['standard_name'] = 'latitude'
        merged.XLAT.attrs['long_name'] = 'latitude'
        for var in merged.data_vars:
            merged[var].attrs['projection'] = str(merged[var].attrs['projection'])

        # wrf.getvar returns some diagnostics (slp, ctt, z/height, uvmet, wa)
        # as float64 even though WRF's own output -- and every other
        # extracted variable -- is float32; force float32 uniformly here
        # rather than special-casing which diagnostics happen to promote.
        encoding = {
            var: {
                "zlib": True,
                "complevel": COMPRESSIONLEVEL,
                "chunksizes": build_chunksizes(merged[var]),
                "dtype": "float32",
            }
            for var in merged.data_vars
        }
        infix = ''
        if args.experimental: infix = '_X'
        for delta in [0, 1]:
            daystamp = (startdate + dt.timedelta(days=delta)).strftime('%Y-%m-%d')
            logging.info(f'Writing era5_wrf_dscale_{res}_{daystamp}{infix}.nc')
            logging.debug(f"{daystamp}")
            merged.sel(Time=slice(daystamp, daystamp)).to_netcdf(
                args.outdir / f"era5_wrf_dscale_{res}_{daystamp}{infix}.nc", engine="netcdf4", encoding=encoding)
