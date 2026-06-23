 #! /usr/bin/env python
#
# python script to download selected files from rda.ucar.edu
# after you save the file, don't forget to make it executable
#   i.e. - "chmod 755 <name_of_script>"
# 
# Refactored and ported to Python 3 cwaigl@alaska.edu 2023/02

import sys
import ssl
import datetime as dt
import calendar as cal
import time
import argparse
from pathlib import Path
from functools import partial
import urllib.request, urllib.parse
from http.client import IncompleteRead
from multiprocessing import Pool

NUMPROC = 10
NUMTRIES = 4    # try up to 4 times to download a file
GETNETCDF = True
CHUNK = 16 * 1024
OUTDIR = "/center1/DYNDOWN/cwaigl/ERA5_WRF/era5_grib/"
PRODUCTURL = "https://data.rda.ucar.edu/d633006/"   # since summer 2024
VERBOSE = True
OVERWRITE = False

YEAR = 2022
MONTH = 10
varsets_folders = {
    "e5.oper.an.ml" : {
        "regn320sc": [
            '128_134_sp'
        ],

    },
}

if GETNETCDF:
    EXT = "nc"
else:
    EXT = "grb"

def parse_arguments():
    """Parse arguments"""
    parser = argparse.ArgumentParser(description='Download one month worth of ERA5 input data for WRF')
    parser.add_argument('yrmonth',  
        help='run label for monthlabel 201803 means March 2018',
        type=str)
    parser.add_argument('-d', '--directory', 
        type=str,
        default=OUTDIR,
        help='directory to which to save the data')
    return parser.parse_args()

def get_localpth(mthstr, firsthr, lasthr, folder, varclass, varname):
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
                for day in days:
                    firsthr = day.strftime("%Y%m%d00")
                    lasthr = day.strftime("%Y%m%d23")
                    for var in varsets_folders[folder][varclass]:
                        fnpth = get_localpth(mthstr, firsthr, lasthr, folder, varclass, var)
                        filelist.append(fnpth)
            elif folder == "e5.oper.an.ml":
                for day in days:
                    for starth in [0, 6, 12, 18]:
                        firsthr = day.strftime(f"%Y%m%d{str(starth).zfill(2)}")
                        lasthr = day.strftime(f"%Y%m%d{str(starth+5).zfill(2)}")
                        for var in varsets_folders[folder][varclass]:
                            fnpth = get_localpth(mthstr, firsthr, lasthr, folder, varclass, var)
                            filelist.append(fnpth)
            elif folder == "e5.oper.an.sfc":
                firsthr = days[0].strftime("%Y%m%d00")
                lasthr = days[-1].strftime("%Y%m%d23")
                for var in varsets_folders[folder][varclass]:
                    fnpth = get_localpth(mthstr, firsthr, lasthr, folder, varclass, var)
                    filelist.append(fnpth)
    return filelist

def read_write_chunked(url, outfile, context=None):
    """Retrieve and write file, chunked download"""

    with urllib.request.urlopen(url, context=context) as infile:
        for chunk in iter(lambda: infile.read(CHUNK), ''):
            if not chunk:
                break
            outfile.write(chunk)   

def read_write_SSLorNot(url, outfile):
    try: 
        read_write_chunked(url, outfile)
    except ssl.SSLError as error:
        # if we get a certificate error, we don't check the cert
        print(f"An error occurred: {error}")
        print(f"Trying without cert checking.")
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        read_write_chunked(url, outfile, context=ctx)

def process_file(outpath, fileID):
    outpath.mkdir(parents=True, exist_ok=True)
    url = f"{PRODUCTURL}{fileID}"
    print(url)
    idx = fileID.rfind("/")
    if (idx > 0):
        ofile = fileID[idx+1:]
    else:
        ofile = fileID
    outfp = outpath / ofile
    
    if (not outfp.exists() or OVERWRITE):
        if (VERBOSE):
            sys.stdout.write(f"... downloading {ofile} to {outpath}.\n")
        for ii in range(NUMTRIES):
            try: 
                with open(outfp, "wb") as outfile:
                    read_write_SSLorNot(url, outfile)
                break
            except IncompleteRead:
                if ii == NUMTRIES-1:
                    print(f"Attempt {ii+1} to download {url} failed. This failutre is fatal.")
                    raise       # give up after NUMTRIES attempts
                print(f"Attempt {ii+1} to download {url} failed. Retrying.")
                with open(outfp, "wb") as outfile:
                    read_write_SSLorNot(url, outfile)
        if (VERBOSE):
            sys.stdout.write(f"Done with {ofile}.\n")
    else:
        if (VERBOSE):
            sys.stdout.write(f"{ofile} exists, and overwite not enabled. skipping.\n")

if __name__ == "__main__":

    args = parse_arguments()
    year = int(args.yrmonth[:4])
    month = int(args.yrmonth[4:])
    mthstr = args.yrmonth
    outpath = Path(args.directory) / mthstr

    start_time = time.perf_counter()
    listoffiles = get_filelist(year, month)
    print(f"Downloading {len(listoffiles)} files.")
    print(listoffiles)

    mapfunc = partial(process_file, outpath)
    with Pool(NUMPROC) as p:
        p.map(mapfunc, listoffiles)

    run_time = time.perf_counter() - start_time
    print(f"Elapsed time: {int(run_time // 60)} minutes, {run_time % 60:0.2f} seconds")
