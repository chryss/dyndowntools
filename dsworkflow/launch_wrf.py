# launch a wrf run

import argparse
import subprocess
import datetime as dt
import pandas as pd
import workflowutil as wu

BASEDIR = "/center1/DYNDOWN/cwaigl/ERA5_WRF/"
TESTING = False   

def parse_arguments():
    """Parse arguments"""
    parser = argparse.ArgumentParser(description='Generate synthetic snow from ERA5 and JRA55')
    parser.add_argument('yrmonth',
        type=str,
        help='which year YYYY or year + month YYYYMM to launch')
    parser.add_argument('-bb', '--bridgebefore', 
        action='store_true',
        help='whether to include the bridge day(s) preceding the selected period')
    parser.add_argument('-ba', '--bridgeafter', 
        action='store_true',
        help='whether to include the bridge day(s) following the selected period')
    parser.add_argument('-t', '--test',  
        action='store_true',
        help='just display which ones will be launched',)
    return parser.parse_args()

def get_command(row):
    datestamp = pd.to_datetime(row.datelabel, format='%y%m%d')
    util = "launch_wrf.sh"
    if row.bridgemonth == 1:
        wpssuffix = '_B'
        if datestamp.day < 15:
            year = row.year
            month = row.month
        else:
            if row.year < 1969: 
                year = (datestamp + dt.timedelta(days=20)).year - 100
            else: 
                year = (datestamp + dt.timedelta(days=20)).year
            month = (datestamp + dt.timedelta(days=20)).month
    else:
        wpssuffix = "_C"
        year = row.year
        month = row.month
    return f"bash {util} {row.datelabel} WPS{str(year)}{str(month).zfill(2)}{wpssuffix}"

if __name__ == '__main__':
    args = parse_arguments()
    print(args)
    statusdf = pd.read_feather(wu.STATUSFILE)

    if len(args.yrmonth) == 6:
        year = int(args.yrmonth[:4])
        months = [int(args.yrmonth[4:])]
    else:
        raise Exception("Not implemented: options other than YYYYMM")
    
    selected = statusdf[(statusdf.year == year) & (statusdf.month.isin(months))]
    # print(selected[( selected.datelabel.str.slice(start=4).astype(int) < 10 )])
    if not args.bridgebefore:
        selected = selected[( selected.datelabel.str.slice(start=4).astype(int) > 15 ) | ( selected.bridgemonth == 0)]
    if not args.bridgeafter:
        selected = selected[( selected.datelabel.str.slice(start=4).astype(int) < 15 ) | ( selected.bridgemonth == 0) ]

    for _, row in selected.iterrows():
        commandelms = get_command(row).split()
        if args.test:
            print(f"subprocess.run({commandelms}")
        else:
            subprocess.run(commandelms)


