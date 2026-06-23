import argparse
import pandas as pd
import workflowutil as wu

STATUSFILE = wu.STATUSFILE

# This was originally meant to update status.feather with per-run progress
# columns (erapreproc, wpsready, wrfstarted, wrfcomplete, wrfsuccessful,
# dataarchived, wrfcleanup, wpscleanup, era5cleanp -- see taskcontrol.ipynb).
# That was never implemented. In practice status.feather is only used to
# look up date labels and the bridge/center WPS classification
# (workflowutil.get_bridge) -- this script does that lookup for one date.

def parse_arguments():
    parser = argparse.ArgumentParser(description='Look up the status file entry for one date')
    parser.add_argument('datelabel', help='date label to look up, format YYMMDD')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_arguments()
    statusdf = pd.read_feather(STATUSFILE)
    print(statusdf[statusdf.datelabel == args.datelabel])