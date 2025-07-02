from pathlib import Path
from functools import partial
from multiprocessing import get_context
import time
import sys
import datetime as dt
import calendar
import xarray as xr
import numpy as np
import pandas as pd
import logging

READAPPROACHES = {
    1: "multiprocessing w/ span",
    2: "xarray open_mfdataset",
    3: "loop"
}
READAPPROACH = 3

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
datadir = Path(f"/import/beegfs/CMIP6/wrf_era5/")

# settings for years and location 
teststation = 'FAIRBANKS INTL AP'
startyear = 1981
endyear = 1984
timezoneoffset = -9  # h for Alaska Standard Time vs UTC 
var = 'precip'
outfilepatt = f"{var}_{teststation.replace(' ','_')}_{startyear}_{endyear}"

# settings for downscaled ERA5 files
resolutions = [4, 12]         # 4 or 12 km

# settings for weather station data 
COLNAMES = ["Tmax_f", "Tmin_F", "Tavg_F", "precip_in", "sd_m", "swe"]
weatherstationlist = projdir / "evaluation/auxdata/ACIS_stations.csv"
weatherstationdir = projdir / "evaluation/weatherstationdata/ACIS"
weatherstationfnpatt = "_T_max_min_avg_pcpn_sd_swe.csv"

def getweatherstationlist():
    return pd.read_csv(weatherstationlist)

def station2df(stationpth):
    df = pd.read_csv(stationpth, header=1, 
        names=COLNAMES, parse_dates=True)
    df = df.replace("M", "-9999",)
    df = df.replace("T", 0.01,)
    df['Tavg_F'] = df['Tavg_F'].astype(float)
    df['precip_in'] = df['precip_in'].astype(float)
    df['year'] = df.index.year
    return df

def getweatherstationdata(stations):
    weatherstationframes = {}
    for idx, record in stations.iterrows():
        stationdatapth = weatherstationdir / f"{record['name'].replace(' ', '_')}{weatherstationfnpatt}"
        try:
            weatherstationframes[record['name']] = station2df(stationdatapth)
        except FileNotFoundError:
            continue
    return weatherstationframes

def getlatlon(station, stationDF, lon360=True):
    lat = stationDF[stationDF.name == station].latitude.item()
    if lon360:
        lon = stationDF[stationDF.name == station].longitude.item() % 360
    else:
        lon = stationDF[stationDF.name == station].longitude.item()
    return lat, lon

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
        return (src.rainnc + src.rainc).isel(south_north=y, west_east=x).load().drop_vars(['XLAT', 'XLONG', 'XTIME'])

def main():
    logger.info(f"Working on precip data for {teststation}")
    start_time = time.perf_counter()
    stations = getweatherstationlist()
    weatherstationDFs = getweatherstationdata(stations)

    # precipdata from ACIS
    logger.info("Getting weather station data")
    precipDF = pd.DataFrame(weatherstationDFs[teststation]['precip_in'] * 25.4)
    precipDF.replace(-9999*25.4, np.nan, inplace=True)
    precipDF.columns = [teststation]
    test_lat, test_lon = getlatlon(teststation, stations, lon360=False)

    years = range(startyear, endyear+1)
    for res in resolutions:
        outfn = f"{outfilepatt}_{res}km.csv"
        curr_time_start = time.perf_counter() 
        logger.info(f"getting ERA5 data for {res} km at {teststation}")
        xloc, yloc = None, None
        filepattern = f"era5_wrf_dscale_{res}km"
        thisdatadir = datadir / f"{str(res).zfill(2)}km/"
        for yr in years: 
            logger.info(f"Working on {yr}")
            dates = getdates(teststation, weatherstationDFs, yr, yr)
            filepaths = [thisdatadir / f"{datestr[:4]}/{filepattern}_{datestr}.nc" for datestr in dates]
            logger.debug(f"{filepaths[0]}, {filepaths[-1]}")
            # we first need to find the i, j coordinates of our location
            if (yr == startyear) and filepaths:
                with xr.open_dataset(filepaths[0], engine='netcdf4') as src:
                    xloc, yloc = getXY(test_lat, test_lon, src)
            logger.debug(f"{test_lat}, {test_lon}, {xloc}, {yloc}")
            # data from downscaled ERA5 
            process_file = partial(process_file_at_loc, x=xloc, y=yloc)
            with get_context('spawn').Pool(NUMBER_OF_CORES) as pool:
                parallel_results = pool.map(process_file, filepaths, 3)
                # pool.close()
                # pool.join()
            all_rain = xr.concat(parallel_results, dim='Time').to_dataframe(name=f'precip_mm_ERA5_{res}km')
            all_rain.index = all_rain.index + dt.timedelta(hours=-9)
            all_rain = all_rain.resample('D').sum()

            # put it together
            compDF = all_rain[1:-1].merge(precipDF[f'{yr}-01-01':f'{yr}-12-31'], left_index=True, right_index=True )
            compDF['month'] = list(map(lambda x: calendar.month_abbr[x], compDF.index.month))

            logger.info(f"Writing/appending to {outfn}")
            with open(outdir / outfn, 'a', newline='') as dst:
                compDF.to_csv(dst, float_format='%.3f')

            curr_time_end = time.perf_counter()
            elapsed_time = curr_time_end - curr_time_start 
        logger.info(f"Extraction for precip {res} km, {startyear}-{endyear}: {elapsed_time:.4f} seconds")
    
    curr_time_end = time.perf_counter()
    elapsed_time = curr_time_end - start_time
    logger.info(f"Total run time: {elapsed_time:.4f} seconds")

if __name__ == '__main__':
    main()
