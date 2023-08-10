import argparse
import datetime as dt
from pathlib import Path
import pandas as pd
import workflowutil as wu

STATUSFILE = Path('conf/status.feather')
FINALDIR = Path('/import/SNAP/cwaigl/wrf_era5')
SUBDIRS = ['04km', '12km']

def parse_arguments():
    parser = argparse.ArgumentParser(description='Check and update the status file')
    parser.add_argument('datelabel',)
    parser.add_argument('datelabel',
        help='find out status for one datestamp',
        action='store_true')
    parser.add_argument('-d', '--diagnostic',
        help='find out status for one datestamp',
        action='store_true')
    parser.add_argument('-d', '--delete',
        help='delete listed directories',
        action='store_true')
    return parser.parse_args()

if __name__ == '__main__'

    statusdf = pd.read_feather(STATUSFILE)
    print(statusdf)