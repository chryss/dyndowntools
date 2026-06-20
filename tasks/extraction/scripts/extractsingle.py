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
READAPPROACH = 4

logger = logging.getLogger(__name__)
logger.setLevel('INFO')
formatter = logging.Formatter(
    '%(asctime)s::%(levelname)s::%(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(formatter)
logger.addHandler(handler)

NUMBER_OF_CORES = 4
projdir = Path().resolve().parents[0]
outdir = projdir / "evaluation/working"
# datadir = Path(f"/import/beegfs/CMIP6/wrf_era5/")
datadir = Path(f"/import/SNAP/cwaigl/wrf_era5")

# settings for getting station related parameters
lat, lon = 64.80309, -147.87605     # Fairbanks, PAFA station as per ACIS
locname = 'FAI_PAFA'
startyear = 1980
endyear = 2020
timezoneoffset = -9  # h for Alaska Standard Time vs UTC 
var = 'precip'
outfilepatt = f"{var}_{locname.replace(' ','_')}_{startyear}_{endyear}"

# settings for downscaled ERA5 files
resolutions = [4, 12]         # 4 or 12 km or both

def getXY(lat, lon, dataarray):
    abslat = np.abs(dataarray.XLAT-lat)
    abslon = np.abs(dataarray.XLONG-lon)
    # c = np.maximum(abslon, abslat)
    d = abslon**2 + abslat**2
    ([yloc], [xloc]) = np.where(d == np.min(d))
    return xloc, yloc

def getdates(station, stationDFs, startyr, endyr):
    dates = stationDFs[station].index.strftime('%Y-%m-%d').to_list()
    return [item for item in dates if int(item[:4]) in range(startyr, endyr+1)] + [f'{endyr+1}-01-01']

def process_file_at_loc(filepath, x=100, y=100):
    with xr.open_dataset(filepath, engine='netcdf4') as src:
        rain = (src.rainnc + src.rainc).isel(
            south_north=y, west_east=x).load().drop_vars(['XLAT', 'XLONG', 'XTIME'])
        src.close()
        del src
    return rain
    
def preprocess_ds_at_loc(ds, x=100, y=100):
    return (ds.rainnc + ds.rainc).isel(south_north=y, west_east=x).drop_vars(['XLAT', 'XLONG', 'XTIME'])

def getdates(yr):
    return [dateitem.date() for dateitem in pd.date_range(f'{yr}-01-01', f'{yr}-12-31')]

def main():
    start_time = time.perf_counter()

    years = range(startyear, endyear+1)
    for res in resolutions:
        outfn = f"{outfilepatt}_{res}km.csv"
        (outdir / outfn).unlink(missing_ok=True)
        curr_time_start = time.perf_counter() 
        logger.info(f"getting ERA5 data for {res} km at {locname}: {lat}, {lon}")
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
                        # pool.close()
                        # pool.join()
                    all_rain = xr.concat(parallel_results, dim='Time').to_dataframe(name=f'precip_mm_ERA5_{res}km')
                case 2:
                    from dask.distributed import Client
                    client = Client(n_workers=NUMBER_OF_CORES, memory_limit='10GB')
                    all_rain = xr.open_mfdataset(filepaths, parallel=True, engine='netcdf4',
                            preprocess=partial(preprocess_ds_at_loc, x=xloc, y=yloc))
                    all_rain = all_rain.to_dataframe(name=f'precip_mm_ERA5_{res}km')
                    client.shutdown()
                case 3:
                    results = []
                    for ii, pth in enumerate(filepaths):
                        logger.debug(ii)
                        rain = process_file_at_loc(pth, xloc, yloc)
                        results.append(rain) 
                    all_rain = xr.concat(results, dim='Time').to_dataframe(name=f'precip_mm_ERA5_{res}km')
                case 4:
                    from joblib import Parallel, delayed
                    results = Parallel(n_jobs=NUMBER_OF_CORES)(
                        delayed(partial(process_file_at_loc, x=xloc, y=yloc))(pth) for pth in filepaths)
                    all_rain = xr.concat(results, dim='Time').to_dataframe(name=f'precip_mm_ERA5_{res}km')
            all_rain = all_rain.resample('D').sum()

            logger.info(f"Writing/appending to {outfn}")
            with open(outdir / outfn, 'a', newline='') as dst:
                all_rain.to_csv(dst, float_format='%.3f', header=dst.tell()==0)

            curr_time_end = time.perf_counter()
            elapsed_time = curr_time_end - curr_time_start 
        logger.info(f"Extraction for precip {res} km, {startyear}-{endyear}: {elapsed_time:.4f} seconds")
    
    curr_time_end = time.perf_counter()
    elapsed_time = curr_time_end - start_time
    logger.info(f"Total run time: {elapsed_time:.4f} seconds")

if __name__ == '__main__':
    main()
