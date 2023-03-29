# launch a wrf run

import shutil
from functools import partial 
import argparse
from pathlib import Path

BASEDIR = "/center1/DYNDOWN/cwaigl/ERA5_WRF/"

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
    parser.add_argument('datelabel',  
        help='run label for 2-day run format YYMMDD 180301 means March 1, 2018',
        type=str)
    return parser.parse_args()

if __name__ == '__main__':
    pass
