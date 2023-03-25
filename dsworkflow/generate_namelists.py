#!/usr/bin/env python

import argparse
from pathlib import Path
import datetime as dt

BASEDIR = "/center1/DYNDOWN/cwaigl/ERA5_WRF/"

def parse_date(date_str):
    """Parse YYMMDD"""
    parsed = dt.datetime.strptime(date_str,'%y%m%d')
    current_date = dt.datetime.now()
    if parsed > current_date:
        parsed = parsed.replace(year=parsed.year - 100)
    return parsed

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
        help='run label for 2-day run format YYMMDD: 181004 = run that produces data for Oct 4-6, 2018',
        type=str)
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_arguments()

    nominalstart = parse_date(args.date)
    startdt = nominalstart - dt.timedelta(hours=6)
    enddt = nominalstart + dt.timedelta(days=2)

    params = {}
    params['startyear'] = str(startdt.year)
    params['startmonth'] = str(startdt.month).zfill(2)
    params['startday'] = str(startdt.day).zfill(2)
    params['starthours'] = str(startdt.hour).zfill(2)
    params['endyear'] = str(enddt.year)
    params['endmonth'] = str(enddt.month).zfill(2)
    params['endday'] = str(enddt.day).zfill(2)
    params['endhours'] = str(enddt.hour).zfill(2)

    if args.type == 'wrf':
        outdir = Path(BASEDIR) / 'WRF' / args.date
        templatedir = Path('templates')
        fn = 'namelist.input'
        with open(templatedir / 'namelist.input.TEMPLATE', 'r') as src:
            with open(outdir / fn, 'w') as target:
                target.write(src.read().format(**params))
