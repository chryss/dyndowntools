#!/usr/local/env python
import argparse

YEAR = 1976
DELTA = 4

def parse_arguments():
    parser = argparse.ArgumentParser(description='Print out one year worth of WRF and WPS tasks for given year')
    parser.add_argument('-y', '--year',
        help='year',
        default=YEAR,
        type=int)
    parser.add_argument('-r', '--reverse',
        help='reverse order',
        action='store_false')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_arguments()
    if args.reverse:
        start = 12
        stop = 0
        step = -1
        mult = 1
    else:
        start = 1
        stop = 13
        step = 1
        mult = -1
    for ii in range(start, stop, step):
        if (ii + mult * DELTA) > 12:
            wrfmth = str(ii + mult * DELTA - 12).zfill(2)
            wrfyr = str(args.year+1)
        elif (ii + mult * DELTA) < 1:
            wrfmth = str(ii + mult * DELTA + 12).zfill(2)
            wrfyr = str(args.year-1)
        else:
            wrfmth = str(ii + mult * DELTA).zfill(2)
            wrfyr = str(args.year)
        wpsmth = str(ii).zfill(2)
        wpsyr = str(args.year)
        print(f"bash launch_wps_monthS.sh {wpsyr}{wpsmth}")
        print(f"bash launch_wps_bridgeS.sh {wpsyr}{wpsmth}")
        print(f"python launch_wrf.py -bb -ba {wrfyr}{wrfmth}")
