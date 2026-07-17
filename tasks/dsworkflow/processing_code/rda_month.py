#! /usr/bin/env python
#
# Rewrite mirroring aws_era5_month.py's design and output layout, but
# downloading from NCAR's RDA/GDEX (OSDF-fronted) archive instead of the
# AWS ERA5 mirror. RDA/GDEX has a given month's data ~2 months before it
# reaches the AWS mirror -- this is the tool for that narrow window, not a
# general substitute for aws_era5_month.py (see its header and README.md).
# RDA/GDEX has also stopped serving GRIB, so like the AWS mirror this
# always downloads NetCDF; the previous GETNETCDF/SKIPSNOW toggles (the
# latter silently dropping snow depth by default) are gone.
#
# URL/dataset ID/layout verified live 2026-07-17 against
# osdf-director.osg-htc.org, dataset d633000: HEAD requests resolve
# Content-Length correctly through the redirect chain, and the
# root/{folder}/{YYYYMM}/{filename} key structure matches what's assumed
# below. Per workflowutil.py's own warning, NCAR has rebranded/restructured
# this access path multiple times and will likely do so again -- re-verify
# before trusting this if downloads start failing (see the
# rda-gdex-url-check skill).
#
# cwaigl@alaska.edu 2026/07 (originally 2023/02; rewritten for
# aws_era5_month.py parity)

import sys
import ssl
import time
import argparse
import calendar as cal
import datetime as dt
from pathlib import Path
from functools import partial
from multiprocessing import Pool
import urllib.request
from urllib.error import URLError, HTTPError
from http.client import IncompleteRead
import workflowutil as wu

NUMPROC = 10
NUMTRIES = 4    # try up to 4 times to download a file, on a size mismatch or a transfer error
CHUNK = 16 * 1024
OUTDIR = str(wu.ERA_NC_INPUT_DIR)
PRODUCTURL = wu.ERA5_PRODUCTURL
VERBOSE = True
OVERWRITE = False
EXT = "nc"    # RDA/GDEX, like the AWS mirror, is NetCDF-only now

# Same variable set as aws_era5_month.py, snow depth (128_141_sd) included
# unconditionally -- only the source (RDA/GDEX vs AWS) and therefore the
# URL differ; local layout is identical.
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
        description='Download one month worth of ERA5 input data for WRF from RDA/GDEX')
    parser.add_argument('yrmonth',
        help='run label for monthlabel 202403 means March 2024',
        type=str)
    parser.add_argument('-d', '--directory',
        type=str,
        default=OUTDIR,
        help='directory under which to save the data (folder-per-product, then month -- matches aws_era5_month.py/era5_to_int)')
    return parser.parse_args()


def get_localpth(mthstr, firsthr, lasthr, folder, varclass, varname):
    # Matches the remote key structure and aws_era5_month.py's local layout:
    # {folder}/{mthstr}/{folder}.{varname}.{varclass}.{firsthr}_{lasthr}.nc
    return f"{folder}/{mthstr}/{folder}.{varname}.{varclass}.{firsthr}_{lasthr}.{EXT}"


def get_monthstr(yr, mth):
    return f"{str(yr)}{str(mth).zfill(2)}"


def get_filelist(yr, mth):
    filelist = []
    mthstr = get_monthstr(yr, mth)
    num_days = cal.monthrange(yr, mth)[1]
    days = [dt.date(yr, mth, day) for day in range(1, num_days + 1)]
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


def _urlopen(url_or_request):
    # RDA/GDEX has occasionally hit certificate verification errors that a
    # same-context retry doesn't clear; falling back to an unverified
    # context on SSLError is the same workaround the original script used.
    try:
        return urllib.request.urlopen(url_or_request, timeout=60)
    except ssl.SSLError as error:
        print(f"SSL error ({error}), retrying without cert verification.")
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return urllib.request.urlopen(url_or_request, context=ctx, timeout=60)


def get_content_length(url):
    # HEAD, followed through the OSDF director's redirect to the actual
    # cache node -- verified live to return an accurate Content-Length.
    req = urllib.request.Request(url, method="HEAD")
    with _urlopen(req) as resp:
        length = resp.headers.get("Content-Length")
        return int(length) if length is not None else None


def download(url, outfp):
    with _urlopen(url) as infile, open(outfp, "wb") as outfile:
        while True:
            chunk = infile.read(CHUNK)
            if not chunk:
                break
            outfile.write(chunk)


def process_file(rootpath, fileID):
    # fileID is "{folder}/{mthstr}/{filename}" -- preserved verbatim under
    # rootpath, matching aws_era5_month.py's layout (era5_to_int/
    # preprocess_era_nc.sh expect root/{folder}/{YYYYMM}/... with no year
    # level).
    outfp = rootpath / fileID
    outfp.parent.mkdir(parents=True, exist_ok=True)
    ofile = outfp.name

    if outfp.exists() and not OVERWRITE:
        if VERBOSE:
            sys.stdout.write(f"{ofile} exists, and overwrite not enabled. skipping.\n")
        return

    url = f"{PRODUCTURL}{fileID}"
    expected_size = get_content_length(url)

    for attempt in range(1, NUMTRIES + 1):
        if VERBOSE:
            sys.stdout.write(f"... downloading {ofile} to {outfp.parent} (attempt {attempt}).\n")
        try:
            download(url, outfp)
        except (URLError, HTTPError, IncompleteRead) as error:
            print(f"Attempt {attempt} to download {fileID} failed: {error}.")
        else:
            actual_size = outfp.stat().st_size
            if expected_size is None or actual_size == expected_size:
                if VERBOSE:
                    verified = ", size-verified" if expected_size is not None else ""
                    sys.stdout.write(f"Done with {ofile} ({actual_size} bytes{verified}).\n")
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
    with Pool(NUMPROC) as p:
        p.map(mapfunc, listoffiles)

    run_time = time.perf_counter() - start_time
    print(f"Elapsed time: {int(run_time // 60)} minutes, {run_time % 60:0.2f} seconds")
