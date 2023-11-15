#!/usr/local/env python
import argparse

YEAR = 1976

def parse_arguments():
    parser = argparse.ArgumentParser(description='Print out one year worth of WRF and WPS tasks for given year')
    parser.add_argument('-y', '--year',
        help='year',
        default=YEAR,
        type=int)
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_arguments()
    for ii in range(12, 0, -1):
        if (ii + 3) > 12:
            wrfmth = str(ii + 3 - 12).zfill(2)
            wrfyr = str(args.year+1)
        else:
            wrfmth = str(ii + 3).zfill(2)
            wrfyr = str(args.year)
        wpsmth = str(ii).zfill(2)
        wpsyr = str(args.year)
        print(f"bash launch_wps_monthS.sh {wpsyr}{wpsmth}")
        print(f"bash launch_wps_bridgeS.sh {wpsyr}{wpsmth}")
        print(f"python launch_wrf.py -bb -ba {wrfyr}{wrfmth}")
