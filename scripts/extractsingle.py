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

logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')
logger.addHandler(logging.StreamHandler(sys.stderr))
NUMBER_OF_CORES = 4
projdir = Path().resolve().parents[0]
outdir = projdir / "evaluation/working"

# settings for years and location 
teststation = 'FAIRBANKS INTL AP'
startyear = 1990
endyear = 1990
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

def getdates(station, stationDFs):
    dates = stationDFs[station].index.strftime('%Y-%m-%d').to_list()
    return [item for item in dates if int(item[:4]) in range(startyear, endyear+1)] + [f'{endyear+1}-01-01']

def process_file_at_loc(filepath, x=100, y=100):
    with xr.open_dataset(filepath) as src:
        return (src.rainnc + src.rainc).isel(south_north=y, west_east=x).load().drop_vars(['XLAT', 'XLONG', 'XTIME'])

def main():
    logger.info(f"Working on precip data for {teststation}")
    start_time = time.perf_counter()
    stations = getweatherstationlist()
    weatherstationDFs = getweatherstationdata(stations)
    dates = getdates(teststation, weatherstationDFs)

    # precipdata from ACIS
    logger.info("Getting weather station data")
    precipDF = pd.DataFrame(weatherstationDFs[teststation]['precip_in'] * 2.54)
    precipDF.replace(-9999* 2.54, np.nan, inplace=True)
    precipDF.columns = [teststation]

    test_lat, test_lon = getlatlon(teststation, stations, lon360=False)
    for res in resolutions:
        curr_time_start = time.perf_counter() 
        logger.info(f"getting ERA5 data for {res} km at {teststation}")
        logger.info(f"Starting at {time.ctime()}")
        xloc, yloc = None, None
        filepattern = f"era5_wrf_dscale_{res}km"
        datadir = Path(f"/import/beegfs/CMIP6/wrf_era5/{str(res).zfill(2)}km/")
        filepaths = [datadir / f"{datestr[:4]}/{filepattern}_{datestr}.nc" for datestr in dates]
        logger.debug(f"{filepaths[0]}, {filepaths[-1]}")

        # we first need to find the i, j coordinates of our location
        if filepaths:
            with xr.open_dataset(filepaths[0]) as src:
                xloc, yloc = getXY(test_lat, test_lon, src)
        logger.debug(f"{test_lat}, {test_lon}, {xloc}, {yloc}")
        # data from downscaled ERA5 
        process_file = partial(process_file_at_loc, x=xloc, y=yloc)
        with get_context('spawn').Pool(NUMBER_OF_CORES) as pool:
            parallel_results = pool.map(process_file, filepaths, 5)
            # pool.close()
            # pool.join()
        all_rain = xr.concat(parallel_results, dim='Time').to_dataframe(name=f'rain_ERA5_{res}km')
        all_rain.index = all_rain.index + dt.timedelta(hours=-9)
        all_rain = all_rain.resample('D').mean()

        # put it together
        compDF = all_rain[1:-1].merge(precipDF[f'{startyear}-01-01':f'{endyear}-12-31'], left_index=True, right_index=True )
        compDF['month'] = list(map(lambda x: calendar.month_abbr[x], compDF.index.month))

        outfn = f"{outfilepatt}_{res}km.csv"
        logger.info(f"Writing {outfn}")
        compDF.to_csv(outdir / outfn, float_format='%.3f')

        curr_time_end = time.perf_counter()
        elapsed_time = curr_time_end - curr_time_start 
        logger.info(f"Extraction for precip {res} km, {startyear}-{endyear}: {elapsed_time:.4f} seconds")
    
    curr_time_end = time.perf_counter()
    elapsed_time = curr_time_end - start_time
    logger.info(f"Ended at {time.ctime()}")
    logger.info(f"Total run time: {elapsed_time:.4f} seconds")

if __name__ == '__main__':
    main()
