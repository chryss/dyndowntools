#!/usr/bin/env python

import argparse
from pathlib import Path
import datetime as dt
import calendar

BASEDIR = "/center1/DYNDOWN/cwaigl/ERA5_WRF/"

def parse_date(date_str):
    """Parse YYMMDD"""
    parsed = dt.datetime.strptime(date_str,'%y%m%d')
    current_date = dt.datetime.now()
    if parsed > current_date:
        parsed = parsed.replace(year=parsed.year - 100)
    return parsed

def parse_wpslabel(date_str):
    """Parse YYMM or YYMM_B"""
    date_str = date_str[:5]
    parsed = dt.datetime.strptime(date_str+'01','%y%m%d')
    current_date = dt.datetime.now()
    if parsed > current_date:
        parsed = parsed.replace(year=parsed.year - 100)
    return parsed

def get_params(startdt, enddt):
    params = {}
    params['startyear'] = str(startdt.year)
    params['startmonth'] = str(startdt.month).zfill(2)
    params['startday'] = str(startdt.day).zfill(2)
    params['starthours'] = str(startdt.hour).zfill(2)
    params['endyear'] = str(enddt.year)
    params['endmonth'] = str(enddt.month).zfill(2)
    params['endday'] = str(enddt.day).zfill(2)
    params['endhours'] = str(enddt.hour).zfill(2)
    return params

def parse_arguments():
    """Parse arguments"""
    parser = argparse.ArgumentParser(description='Generate synthetic snow from ERA5 and JRA55')

    parser.add_argument('-t',  '--type',
        default='wrf',
        type=str,
        help='type of namelist to generate; choices are wrf, wps or both')
    parser.add_argument('-d', '--directory', 
        type=str,
        default=None,
        help='directory to which to deploy the namelist')
    parser.add_argument('date',  
        help='run label for 2-day run format YYMMDD or - wps only - monthlabel with optional B for bridge: 1803_B means 2018, bridge between Feb and March',
        type=str)
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_arguments()
    templatedir = Path('templates')

    jobs = []
    if args.type == 'both':
        jobs.extend(['wps', 'wrf'])
    else: 
        jobs.append( args.type)

    for job in jobs:
        if job == 'wrf':
            outdir = Path(BASEDIR) / 'WRF' / args.date
            fn = 'namelist.input'
            nominalstart = parse_date(args.date)
            startdt = nominalstart - dt.timedelta(hours=6)
            enddt = nominalstart + dt.timedelta(days=2)
            params = get_params(startdt, enddt)
            with open(templatedir / 'namelist.input.TEMPLATE', 'r') as src:
                with open(outdir / fn, 'w') as target:
                    target.write(src.read().format(**params))
        elif job == 'wps':
            fn = 'namelist.wps'
            nominalstart = parse_wpslabel(args.date[:5])
            outdir = Path(BASEDIR) / f'WPS{nominalstart.year}{args.date[2:]}' 
            if args.date[-1] == 'B':
                startdt = nominalstart - dt.timedelta(days=3)
                enddt = nominalstart + dt.timedelta(days=2)
            else: 
                days_in_month = calendar.monthrange(nominalstart.year, nominalstart.month)[1]
                startdt = nominalstart
                enddt = nominalstart + dt.timedelta(days=days_in_month-1)
            params = get_params(startdt, enddt)
            with open(templatedir / 'namelist.wps.TEMPLATE', 'r') as src:
                with open(outdir / fn, 'w') as target:
                    target.write(src.read().format(**params))
