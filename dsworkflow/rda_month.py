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
SKIPSNOW = True
CHUNK = 16 * 1024
OUTDIR = "/center1/DYNDOWN/cwaigl/ERA5_WRF/era5_grib/"
PRODUCTURL = "https://data.rda.ucar.edu/d633000/"   # since summer 2024
VERBOSE = True
OVERWRITE = False

YEAR = 2022
MONTH = 10
folder = "e5.oper.an.pl"

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
            '128_168_2d', '128_170_stl2', '128_183_stl3', '128_235_skt', '128_236_stl4' ,
        ],
    },
}
if not SKIPSNOW:
    varsets_folders["e5.oper.an.sfc"]["ll025sc"].append('128_141_sd')
listoffiles = []
# listoffiles=["e5.oper.an.sfc/202112/e5.oper.an.sfc.128_141_sd.ll025sc.2021120100_2021123123.grb",
            #  "e5.oper.an.sfc/202112/e5.oper.an.sfc.128_151_msl.ll025sc.2021120100_2021123123.grb"]
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
    # print(url)
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
    if not listoffiles:
        listoffiles = get_filelist(year, month)
    print(f"Downloading {len(listoffiles)} files.")
    # print(listoffiles)

    mapfunc = partial(process_file, outpath)
    with Pool(NUMPROC) as p:
        p.map(mapfunc, listoffiles)

    run_time = time.perf_counter() - start_time
    print(f"Elapsed time: {int(run_time // 60)} minutes, {run_time % 60:0.2f} seconds")
