from pathlib import Path
from functools import partial
from multiprocessing import get_context
import time
import sys
import datetime as dt
import xarray as xr
import numpy as np
import pandas as pd
import logging

READAPPROACHES = {
    1: "multiprocessing w/ spawn",
    2: "xarray open_mfdataset",
    3: "loop",
    4: "joblib"
}
READAPPROACH = 4        # after testing, this seems to be working the smoothest

logger = logging.getLogger(__name__)
logger.setLevel('INFO')
formatter = logging.Formatter(
    '%(asctime)s::%(levelname)s::%(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(formatter)
logger.addHandler(handler)

NUMBER_OF_CORES = 8
projdir = Path().resolve().parents[0]
outdir = projdir / "evaluation/working"
# datadir = Path(f"/import/beegfs/CMIP6/wrf_era5/")
datadir = Path(f"/import/SNAP/cwaigl/wrf_era5")

# settings for station related parameters
weatherstationlist = projdir / "evaluation/auxdata/ACIS_stations.csv"
locnames = {
    'PAFA': 'FAI',
    'PANC': 'ANC',
    'PABR': 'UTQ',
    # 'PABE': 'BTH'
}
DAILY = True
startyear = 1981
endyear = 2020
timezoneoffset = -9
vars = ['T2']
aggs = ['max', 'mean']
varname = 't2m'

# settings for downscaled ERA5 files
resolutions = [4, 12]         # 4 or 12 km or both

class stationNotFoundException(Exception):
    """Custom exception for skipping over unavailable stations"""
    pass

def remove_outfiles(station, res, daily=DAILY):
    if daily:
        for aggscheme in aggs:
            outfilepatt = f"{varname}_{aggscheme}_{locnames[station]}_{station}_{startyear}_{endyear}"
        else:
            outfilepatt = f"{varname}_{locnames[station]}_{station}_{startyear}_{endyear}"
        outfn = f"{outfilepatt}_{res}km.csv"
        (outdir / outfn).unlink(missing_ok=True)

def getXY(lat, lon, dataarray):
    abslat = np.abs(dataarray.XLAT-lat)
    abslon = np.abs(dataarray.XLONG-lon)
    # c = np.maximum(abslon, abslat)
    d = abslon**2 + abslat**2
    ([yloc], [xloc]) = np.where(d == np.min(d))
    return xloc, yloc

def getweatherstationlist():
    return pd.read_csv(weatherstationlist)

def getlatlon(station, stationDF, lon360=True):
    lat = stationDF[stationDF.icao == station].latitude.item()
    if lon360:
        lon = stationDF[stationDF.icao == station].longitude.item() % 360
    else:
        lon = stationDF[stationDF.icao == station].longitude.item()
    return lat, lon

def process_file_at_loc(filepath, x=100, y=100):
    with xr.open_dataset(filepath, engine='netcdf4') as src:
        var = src[vars].isel(
            south_north=y, west_east=x).load().drop_vars(['XLAT', 'XLONG', 'XTIME'])
        src.close()
        del src
    return var
    
def preprocess_ds_at_loc(ds, x=100, y=100):
    return ds[vars].isel(south_north=y, west_east=x).drop_vars(['XLAT', 'XLONG', 'XTIME'])

def getdates(yr):
    return [dateitem.date() for dateitem in pd.date_range(f'{yr}-01-01', f'{yr}-12-31')] + [dt.date(yr+1, 1, 1)]

def writetofile(dataDF, outfn):
    logger.info(f"Writing/appending to {outfn}")
    with open(outdir / outfn, 'a', newline='') as dst:
        dataDF.to_csv(dst, float_format='%.3f', header=dst.tell()==0)

def process_station(station):
    stationname = locnames[station]
    logger.info(f"Working on {varname} data for {station}")

    allstations = getweatherstationlist()
    try:
        lat, lon = getlatlon(station, allstations, lon360=False)
    except ValueError:
        print(f"Cannot get location of {station}. Check whether it is present in station list.")
        raise stationNotFoundException("Station not found, continuing to next")

    years = range(startyear, endyear+1)
    for res in resolutions:
        curr_time_start = time.perf_counter() 
        logger.info(f"getting {varname} ERA5 data for {res} km at {station}: {lat}, {lon}")
        remove_outfiles(station, res, daily=DAILY)
        xloc, yloc = None, None
        filepattern = f"era5_wrf_dscale_{res}km"
        thisdatadir = datadir / f"{str(res).zfill(2)}km/"
        for yr in years: 
            logger.info(f"Working on {yr}")
            dates = getdates(yr)
            filepaths = [thisdatadir / f"{dateitem.year}/{filepattern}_{dateitem}.nc" for dateitem in dates]
            logger.debug(f"{filepaths[0]}, {filepaths[-1]}")
            # we first need to find the i, j coordinates of our location
            if (yr == startyear) and filepaths:
                with xr.open_dataset(filepaths[0], engine='netcdf4') as src:
                    xloc, yloc = getXY(lat, lon, src)
            logger.debug(f"{lat}, {lon}, {xloc}, {yloc}")

            # select method of extraction depending on setting 
            logger.info(f"Extracting data using {READAPPROACHES[READAPPROACH]} - method {READAPPROACH}")
            match READAPPROACH:
                case 1:
                    # data from downscaled ERA5 with multiprocessing
                    process_file = partial(process_file_at_loc, x=xloc, y=yloc)
                    with get_context('spawn').Pool(NUMBER_OF_CORES) as pool:
                        parallel_results = pool.map(process_file, filepaths, 3)
                    all_var = xr.concat(parallel_results, dim='Time').to_dataframe(name=f'{varlabel}_ERA5_{res}km')
                case 2:
                    from dask.distributed import Client
                    client = Client(n_workers=NUMBER_OF_CORES, memory_limit='10GB')
                    all_var = xr.open_mfdataset(filepaths, parallel=True, engine='netcdf4',
                            preprocess=partial(preprocess_ds_at_loc, x=xloc, y=yloc))
                    all_var = all_var.to_dataframe(name=f'{varlabel}_ERA5_{res}km')
                    client.shutdown()
                case 3:
                    results = []
                    for ii, pth in enumerate(filepaths):
                        logger.debug(ii)
                        varout = process_file_at_loc(pth, xloc, yloc)
                        results.append(varout) 
                    all_var = xr.concat(results, dim='Time').to_dataframe(name=f'{varlabel}_ERA5_{res}km')
                case 4:
                    from joblib import Parallel, delayed
                    results = Parallel(n_jobs=NUMBER_OF_CORES)(
                        delayed(partial(process_file_at_loc, x=xloc, y=yloc))(pth) for pth in filepaths)
                    all_var = xr.concat(results, dim='Time').to_dataframe()
            all_var.index = all_var.index + dt.timedelta(hours=timezoneoffset)
            if DAILY:
                for aggscheme in aggs:
                    outfilepatt = f"{varname}_{aggscheme}_{stationname}_{station}_{startyear}_{endyear}"
                    outfn = f"{outfilepatt}_{res}km.csv"
                    # (outdir / outfn).unlink(missing_ok=True)
                    match aggscheme:
                        case 'max': 
                            data_out = all_var.resample('D').max()
                        case 'min': 
                            data_out = all_var.resample('D').min()
                        case 'mean': 
                            data_out = all_var.resample('D').mean()
                        case 'sum': 
                            data_out = all_var.resample('D').sum()
                    data_out.columns = [col + f'_{aggscheme}' for col in all_var.columns]
                    if timezoneoffset < 0:
                        writetofile(data_out[1:-1], outfn)
                    else:
                        writetofile(data_out, outfn)
            else:
                outfilepatt = f"{varname}_{stationname}_{station}_{startyear}_{endyear}"
                outfn = f"{outfilepatt}_{res}km.csv"
                (outdir / outfn).unlink(missing_ok=True)
                writetofile(all_var, outfn)
            curr_time_end = time.perf_counter()
            elapsed_time = curr_time_end - curr_time_start 
        logger.info(f"Extraction for {varname} {res} km, {startyear}-{endyear}: {elapsed_time:.4f} seconds")

def main():
    start_time = time.perf_counter()

    for station in locnames:
        try:
            process_station(station)
        except stationNotFoundException as e:
            print(e)
            continue

    curr_time_end = time.perf_counter()
    elapsed_time = curr_time_end - start_time
    logger.info(f"Total run time: {elapsed_time:.4f} seconds")

if __name__ == '__main__':
    main()
