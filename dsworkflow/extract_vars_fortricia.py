import logging
import argparse
from pathlib import Path
from netCDF4 import Dataset
import wrf
import xarray as xr
import datetime as dt

# experimental - we should enable multicore support differently ultimately
maxprocs = wrf.omp_get_num_procs()
wrf.omp_set_num_threads(min(16, maxprocs))

LOGLEVEL = logging.DEBUG
TESTFOLDER = 'out-s1978'
WRFDATA = Path("/glade/campaign/uwyo/wyom0200/alaska/miroc6/ssp370") / TESTFOLDER
OUTDATA = Path().resolve() / "testout_daily"  # output directory right under current directory
# create output directory if it doesn't exist
Path(OUTDATA).mkdir(parents=True, exist_ok=True) 
SUBSETS = {
    'd01': '12km',
    'd02': '4km',
    'd03': '1.33km'
}
PLEVELS = [200., 300., 500., 700., 850., 900., 925., 950., 1000.]
COMPRESSIONLEVEL = 5
NDAYS = 7       # how many days should be processed starting from yrmd argumnt

VARS = ['RAINNC', 'RAINC', 'ACSNOW', 'slp',
        'wspd_wdir10', 'uvmet10', 'ctt',
        'rh2', 'T2', 'Q2', 'PSFC',
        'SNOW', 'SNOWH', 'SNOWC',
        'twb', 'ALBEDO', 'SMOIS', 'SH2O',
        'TSK', 'TSLB', 'SEAICE',
        'HFX', 'LH',
        'SWDNB', 'SWDNBC', 'SWUPB', 'SWUPBC',
        'LWDNB', 'LWDNBC', 'LWUPB', 'LWUPBC',
        'rh', 'temp', 'z', 'uvmet', 'wa',
        'CLDFRA']
ACCVARS = ['rainnc', 'rainc', 'acsnow']
PRESSUREVARS = ['temp', 'z', 'u', 'v', 'w',
                'rh', 'CLDFRA']

def parse_arguments():
    """Parse arguments"""
    parser = argparse.ArgumentParser(description='Extract variables from wrfout to daily NetCDF')
    parser.add_argument('-w', '--wrfdir',
                        default=WRFDATA,
                        type=str,
                        help='directory where wrfout files are located')
    parser.add_argument('-o', '--outdir',
                        default=OUTDATA,
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
                        help="experimental run - mark outputs with an X",
                        action="store_true")
    parser.add_argument('-n', '--ndays',                    ## Tricia: new option! 
                        help="how many days to output",
                        default=NDAYS,
                        type=int)
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

def postproc_pressurelevel(varname, fn, fieldtypelabel=None):
    return wrf.vinterp(fn,
                       field=varname,
                       vert_coord="p",
                       interp_levels=PLEVELS,
                       timeidx=wrf.ALL_TIMES,
                       extrapolate=True,
                       field_type=fieldtypelabel,
                       log_p=True)

def get_files(testset, startdate, ii, wrfdir):
    currentdatestr = (startdate + dt.timedelta(days=ii)).strftime("%Y-%m-%d")
    filelist = sorted(list((wrfdir).glob(f"wrfout_{testset}_{currentdatestr}*")))
    # add one more file for accumulating variables 
    nextdatestr = (startdate + dt.timedelta(days=ii+1)).strftime("%Y-%m-%d")
    additional = Path(wrfdir) / f"wrfout_{testset}_{nextdatestr}_00:00:00"
    if not additional.exists():
        raise Exception(f"File {additional} is required to extract accumulating variables")
    filelist.append(additional)
    logging.debug(filelist)
    return currentdatestr, filelist

def retrieve_vars(ncfile, mergedic):
    """Get the variables out of one NetCDF file and append to daily merge dictionary"""
    concatdic = {}
    for varname in VARS:
        concatdic[varname] = get_var_all(ncfile, varname)

    logging.debug(f"splitting up wind vars")
    concatdic['u10'] = concatdic['uvmet10'].sel(u_v='u', drop=True)
    concatdic['v10'] = concatdic['uvmet10'].sel(u_v='v', drop=True)
    concatdic['u'] = concatdic['uvmet'].sel(u_v='u', drop=True)
    concatdic['v'] = concatdic['uvmet'].sel(u_v='v', drop=True)
    concatdic['w'] = concatdic['wa']
    concatdic.pop('wspd_wdir10', None)
    concatdic.pop('uvmet10', None)
    concatdic.pop('uvmet', None)
    concatdic.pop('wa', None)
    for varname in ['u10', 'v10', 'u', 'v', 'w']:
        concatdic[varname].name = varname

    logging.debug(f"post-processing pressure level vars")
    for varname in PRESSUREVARS:
        if varname == 'temp':
            concatdic[varname] = postproc_pressurelevel(concatdic[varname], ncfile, fieldtypelabel='tk')
        else:
            concatdic[varname] = postproc_pressurelevel(concatdic[varname], ncfile)

    logging.debug("Appending to variable merge dictionary")
    for var in concatdic:
        try:
            mergedic[var].append(concatdic[var])
        except KeyError:
            mergedic[var] = [concatdic[var]]
    return mergedic

def postprocess_acc_all(concatdic):
    """Concatenate along Time axis and postprocess accumulating variables"""
    logging.info(f"postprocessing accumulating variables")
    for varname in ACCVARS:
        concatdic[varname] = postproc_acc(concatdic[varname.upper()])
        concatdic[varname].name = varname
        concatdic[varname].attrs = concatdic[varname.upper()].attrs
        concatdic[varname].attrs['description'] = 'HOURLY ' + concatdic[varname].attrs['description']
        concatdic.pop(varname.upper())
    logging.debug(concatdic.keys())
    logging.debug([item.name for item in concatdic.values()])
    return concatdic

if __name__ == '__main__':
    args = get_args()
    loglevel = LOGLEVEL
    if args.debug:
        loglevel = logging.DEBUG
    logging.basicConfig(level=loglevel)

    begin_script = dt.datetime.now()
    startdate = dt.datetime.strptime(args.yrmd, '%Y%m%d')
    logging.info(f"Script started at: {begin_script}")
    logging.info(f"Processing {args.ndays} days starting at {startdate}")

    # We'll process files by domain (subset) and day 
    for testset in SUBSETS:
        for ii in range(args.ndays):
            currentdatestr, filelist  = get_files(testset, startdate, ii, args.wrfdir)
            # Now process the files for this day: 1/ retrieve into giant merge dictionary
            mergedic = {}
            for fn in filelist:
                logging.info(f"getting vars from {fn.stem}")
                with Dataset(fn) as ncfile:
                    mergedic = retrieve_vars(ncfile, mergedic)
            # 2/ concatenate along Time axis
            concatdic = {
                item: xr.concat(mergedic[item], dim='Time')
                for item in mergedic}
            # 3/ postprocess  accumulating variables 
            concatdict = postprocess_acc_all(concatdic)

            # Merging everything into one dataset
            logging.debug("merging vars")
            merged_datasets = [item.to_dataset() for item in concatdic.values()]
            merged = xr.merge(merged_datasets)
            merged.attrs['date'] = dt.datetime.now().isoformat()
            merged.attrs['data'] = 'Downscaled CMIP6 using WRF'
            merged.attrs['info'] = 'Alaska Climate Adaptation Science Center, University of Alaska Fairbanks'
            merged.attrs['contact'] = 'phutton5@alaska.edu'
            merged.attrs['version'] = 'WRF V4.5.1 - project v. 1.1'
            merged.interp_level.attrs['units'] = "hPa"
            for var in merged.data_vars:
                merged[var].attrs['projection'] = str(merged[var].attrs['projection'])

            # Save the output for this set of files
            encoding = {
                var: {"zlib": True, "complevel": COMPRESSIONLEVEL}
                for var in merged.data_vars
            }
            infix = ''
            if args.experimental:
                infix = '_X'
            res = SUBSETS[testset]
            logging.info(f'Writing wrf_dscale_{res}_{currentdatestr}{infix}.nc')
            merged.sel(Time=slice(currentdatestr, currentdatestr)).to_netcdf(
                args.outdir / f"wrf_dscale_{res}_{currentdatestr}{infix}.nc", engine="netcdf4", 
                encoding=encoding, mode='a')

    end_script = dt.datetime.now()
    logging.info(f"Script ended at: {end_script}")
    logging.info(f"Total duration: {end_script - begin_script}")