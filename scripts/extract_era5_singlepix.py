#!/usr/bin/env python
# coding=utf-8
"""
Single-pixel extraction tool for ERA5 data by location

Chris Waigl, cwaigl@alaska.edu, created 2021-10-20
"""

from argparse import ArgumentParser
from pathlib import Path
import xarray as xr
import pandas as pd

startyr = 1981
endyr = 2020
projdir = Path().resolve().parents[0]
outdir = projdir / "evaluation/working"
datadir = Path(f"/import/AKCASC/data/cds/reanalysis-era5-single-levels")
weatherstationlist = projdir / "evaluation/auxdata/ACIS_stations.csv"
fileprefix = "reanalysis-era5-single-levels"
locnames = {
    'PAFA': 'FAI',
    'PANC': 'ANC',
    'PABR': 'UTQ',
    'PABE': 'BTH'
}
vars = [
    't2m',
    'tp',
    'u10',
    'v10',
    ]

def _is_valid_lonlat(argstring):
    """
    Validate longlat argument as lon,lat
    """
    pass


def get_parser(desc="Parse command line arguments"):
    """
    Parse command line arguments
    """
    parser = ArgumentParser(description=desc)
    parser.add_argument('-f', '--file',
        help='Input file name', default=None, dest='fpath', required=True)
    parser.add_argument('-l', '--ll', '--lonlat',
        help='Specify longitude and latitude separated by space',
        default=[fai_lon, fai_lat], nargs=2, metavar=('longitude', 'latitude'), type=float)
    parser.add_argument('-v', '--var',
        help="Name of the NetCDF variable in the file",
        default=None, type=str, required=True)
    return parser

def getweatherstationlist():
    return pd.read_csv(weatherstationlist)

def getlatlon(station, stationDF, lon360=True):
    lat = stationDF[stationDF.icao == station].latitude.item()
    if lon360:
        lon = stationDF[stationDF.icao == station].longitude.item() % 360
    else:
        lon = stationDF[stationDF.icao == station].longitude.item()
    return lat, lon

if __name__ == '__main__':
    # argparser = get_parser()
    # args = argparser.parse_args()
    # print(args)
    years = range(startyr, endyr+1)
    allstations = getweatherstationlist()

    print(allstations)
    for var in vars:
        files = sorted(list((datadir / f'{var}').glob(f'{fileprefix}_{var}*.nc')))
        files = filter(lambda fpth: int(fpth.stem[-7:-3]) >= startyr, files)
        files = filter(lambda fpth: int(fpth.stem[-7:-3]) <= endyr, files)
        # print(list(files))
        results = {}
        coords = {}

        for station in locnames:
            results[station] = []
            print(station)
            coords[station] = getlatlon(station, allstations, lon360=True)
        for fp in files:
            with xr.open_dataset(fp, chunks={"time": 30, "longitude": 120, "latitude": 120}) as src:
                try:
                    src = src.rename({'valid_time':'time'})     # if the time variable is named valid_time, rename it to time
                except ValueError:
                    pass
                for station in locnames:
                    stationname = locnames[station]
                    data = src[var].sel(
                        latitude=coords[station][0], 
                        longitude=coords[station][1], 
                        method='nearest').to_dataframe()
                    results[station].append(data)
                    print(data)
            # if args.ll[0] < 0:
            #     data['longitude'] = 360.0 - data['longitude']
        for station in locnames:
            outdata = pd.concat(results[station], axis=0)
            outdata.to_csv(f"era5_{station}_{var}_{startyr}_{endyr}.csv")
