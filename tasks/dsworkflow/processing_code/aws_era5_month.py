#! /usr/bin/env python
#
# Replacement for rda_month.py, for the 2024-01-02-forward era: downloads
# ERA5 input data for WRF from NCAR's public AWS Open Data mirror
# (nsf-ncar-era5) instead of RDA/GDEX. RDA has stopped serving GRIB, and
# era5_to_int (used for the WPS branch from the cutover forward) requires
# input laid out exactly like this bucket's own directory structure -- so
# locally we mirror that structure verbatim, flat under one root (no
# year-level folder), matching era5_to_int's own path builder
# (root/{folder}/{YYYYMM}/...), which has no year level either -- a
# per-year root would break for any date range spanning a year boundary.
# rda_month.py is left untouched as the tool for re-fetching any
# pre-cutover (RDA/GDEX, GRIB-era) month, e.g. to replace a corrupted file.
#
# cwaigl@alaska.edu 2026/07

import sys
import datetime as dt
import calendar as cal
import time
import argparse
from pathlib import Path
from functools import partial
from multiprocessing import Pool
import boto3
from botocore import UNSIGNED
from botocore.config import Config
from botocore.exceptions import ClientError, EndpointConnectionError
import workflowutil as wu

NUMPROC = 3
NUMTRIES = 4    # try up to 4 times to download a file, on a size mismatch or a transfer error
OUTDIR = str(wu.ERA_NC_INPUT_DIR)
BUCKET = wu.ERA5_AWS_BUCKET
VERBOSE = True
OVERWRITE = False
EXT = "nc"    # the AWS mirror is NetCDF-only

_s3 = None    # per-worker-process boto3 client, set by _init_worker

def _init_worker():
    # A boto3 client isn't safe to share across forked processes, so each
    # Pool worker gets its own. Public bucket -- no credentials needed.
    global _s3
    _s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))

# Same variable set as rda_month.py, snow depth included (preprocess_snow.py
# uses ERA5 sd as its primary field, replaced by JRA snow only inside the
# glacier/implausible-value mask) 
varsets_folders = {
    "e5.oper.an.pl" : {
        "ll025sc": [
            '128_129_z', '128_130_t',  '128_157_r', '128_133_q',
        ],
        "ll025uv": [
            '128_131_u', '128_132_v',
        ],
    },
    "e5.oper.an.sfc" : {
        "ll025sc": [
            '128_031_ci', '128_032_asn', '128_033_rsn', '128_034_sstk', '128_039_swvl1',
            '128_040_swvl2', '128_041_swvl3', '128_042_swvl4', '128_134_sp', '128_139_stl1',
            '128_151_msl', '128_165_10u', '128_166_10v', '128_167_2t',
            '128_168_2d', '128_170_stl2', '128_183_stl3', '128_235_skt', '128_236_stl4',
            '128_141_sd',
        ],
    },
}
listoffiles = []

def parse_arguments():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
        description='Download one month worth of ERA5 input data for WRF from the AWS ERA5 mirror')
    parser.add_argument('yrmonth',
        help='run label for monthlabel 202403 means March 2024',
        type=str)
    parser.add_argument('-d', '--directory',
        type=str,
        default=OUTDIR,
        help='directory under which to save the data (flat, no YYYY subfolder -- matches the AWS bucket layout)')
    return parser.parse_args()

def get_localpth(mthstr, firsthr, lasthr, folder, varclass, varname):
    # Matches the AWS bucket's own key structure exactly
    return f"{folder}/{mthstr}/{folder}.{varname}.{varclass}.{firsthr}_{lasthr}.{EXT}"

def get_monthstr(yr, mth):
    return f"{str(yr)}{str(mth).zfill(2)}"

def get_filelist(yr, mth):
    filelist = []
    mthstr = get_monthstr(yr, mth)
    num_days = cal.monthrange(yr, mth)[1]
    days = [dt.date(yr, mth, day) for day in range(1,num_days+1)]
    for folder in varsets_folders:
        for varclass in varsets_folders[folder]:
            if folder == "e5.oper.an.pl":
                # pressure-level fields: one file per day
                for day in days:
                    firsthr = day.strftime("%Y%m%d00")
                    lasthr = day.strftime("%Y%m%d23")
                    for var in varsets_folders[folder][varclass]:
                        fnpth = get_localpth(mthstr, firsthr, lasthr, folder, varclass, var)
                        filelist.append(fnpth)
            elif folder == "e5.oper.an.sfc":
                # surface fields: one file per month
                firsthr = days[0].strftime("%Y%m%d00")
                lasthr = days[-1].strftime("%Y%m%d23")
                for var in varsets_folders[folder][varclass]:
                    fnpth = get_localpth(mthstr, firsthr, lasthr, folder, varclass, var)
                    filelist.append(fnpth)
    return filelist

def process_file(rootpath, fileID):
    # fileID is "{folder}/{mthstr}/{filename}" 
    if _s3 is None:    # allows direct calls outside a Pool, e.g. manual testing
        _init_worker()
    outfp = rootpath / fileID
    outfp.parent.mkdir(parents=True, exist_ok=True)
    ofile = outfp.name

    if outfp.exists() and not OVERWRITE:
        if VERBOSE:
            sys.stdout.write(f"{ofile} exists, and overwrite not enabled. skipping.\n")
        return

    expected_size = _s3.head_object(Bucket=BUCKET, Key=fileID)["ContentLength"]

    for attempt in range(1, NUMTRIES + 1):
        if VERBOSE:
            sys.stdout.write(f"... downloading {ofile} to {outfp.parent} (attempt {attempt}).\n")
        try:
            _s3.download_file(BUCKET, fileID, str(outfp))
        except (ClientError, EndpointConnectionError) as error:
            print(f"Attempt {attempt} to download {fileID} failed: {error}.")
        else:
            actual_size = outfp.stat().st_size
            if actual_size == expected_size:
                if VERBOSE:
                    sys.stdout.write(f"Done with {ofile} ({actual_size} bytes, size-verified).\n")
                return
            print(
                f"Attempt {attempt}: size mismatch for {ofile} "
                f"(expected {expected_size}, got {actual_size}) -- likely a truncated transfer."
            )
            outfp.unlink()
        if attempt < NUMTRIES:
            print("Retrying.")

    raise RuntimeError(f"Failed to download {fileID} with a correct size after {NUMTRIES} attempts.")

if __name__ == "__main__":

    args = parse_arguments()
    year = int(args.yrmonth[:4])
    month = int(args.yrmonth[4:])
    rootpath = Path(args.directory)

    start_time = time.perf_counter()
    if not listoffiles:
        listoffiles = get_filelist(year, month)
    print(f"Downloading {len(listoffiles)} files.")

    mapfunc = partial(process_file, rootpath)
    with Pool(NUMPROC, initializer=_init_worker) as p:
        p.map(mapfunc, listoffiles)

    run_time = time.perf_counter() - start_time
    print(f"Elapsed time: {int(run_time // 60)} minutes, {run_time % 60:0.2f} seconds")
