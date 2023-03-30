#! /usr/bin/env python
#
# python script to download selected files from rda.ucar.edu
# after you save the file, don't forget to make it executable
#   i.e. - "chmod 755 <name_of_script>"
# 
# Refactored and ported to Python 3 cwaigl@alaska.edu 2023/02

import sys, os
import datetime as dt
import calendar as cal
import time
from pathlib import Path
import urllib.request, urllib.parse
import http.cookiejar
from dotenv import load_dotenv
from multiprocessing import Pool

NUMPROC = 20
CHUNK = 16 * 1024
OUTPATH_test = Path("../../working/")
OUTPATH = Path("/center1/DYNDOWN/cwaigl/ERA5_WRF/era5_grib/")
LOGINURL = "https://rda.ucar.edu/cgi-bin/login"
PRODUCTURL = "http://rda.ucar.edu/data/ds633.0/"
VERBOSE = True
OVERWRITE = False


load_dotenv()
rdauser = os.getenv("RDAUSER")
rdapass = os.getenv("RDAPASS")

year = 2022
month = 7
folder = "e5.oper.an.pl"
varsets_folders = {
    "e5.oper.an.pl" : {
        "ll025sc": [
            '128_129_z', '128_130_t',  '128_157_r', 
        ],
        "ll025uv": [
            '128_131_u', '128_132_v',
        ],
    },
    "e5.oper.an.sfc" : {
        "ll025sc": [
            '128_031_ci', '128_032_asn', '128_033_rsn', '128_034_sstk', '128_039_swvl1',
            '128_040_swvl2', '128_041_swvl3', '128_042_swvl4', '128_134_sp', '128_139_stl1',
            '128_141_sd', '128_151_msl', '128_165_10u', '128_166_10v', '128_167_2t', 
            '128_168_2d', '128_170_stl2', '128_183_stl3', '128_235_skt', '128_236_stl4' ,
        ],
    },
}
listoffiles = []
# listoffiles=["e5.oper.an.sfc/202112/e5.oper.an.sfc.128_141_sd.ll025sc.2021120100_2021123123.grb",
            #  "e5.oper.an.sfc/202112/e5.oper.an.sfc.128_151_msl.ll025sc.2021120100_2021123123.grb"]

def get_localpth(mthstr, firsthr, lasthr, folder, varclass, varname):
    return f"{folder}/{mthstr}/{folder}.{varname}.{varclass}.{firsthr}_{lasthr}.grb"

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


def get_urlopener(rdauser, rdapass):

    cj = http.cookiejar.MozillaCookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    # check for existing cookies file and authenticate if necessary
    do_authentication = False
    if (os.path.isfile("auth.rda.ucar.edu")):
        cj.load("auth.rda.ucar.edu", False, True)
        for cookie in cj:
            if (cookie.name == "sess" and cookie.is_expired()):
                do_authentication = True
    else:
        do_authentication = True
    if (do_authentication):
        params = {
            "email": rdauser,
            "password": rdapass,
            "action": "login"
        }
        data = urllib.parse.urlencode(params).encode("utf-8")
        login = opener.open(
            LOGINURL, data)
    # save the authentication cookies for future downloads
        cj.clear_session_cookies()
        cj.save("auth.rda.ucar.edu", True, True)
    return opener

def process_file(fileID):
    mthstr = get_monthstr(year, month)
    outpath = OUTPATH / mthstr
    outpath.mkdir(parents=True, exist_ok=True)
    opener = get_urlopener(rdauser, rdapass)
    idx = fileID.rfind("/")
    if (idx > 0):
        ofile = fileID[idx+1:]
    else:
        ofile = fileID
    outfp = outpath / ofile
    
    if (not outfp.exists() or OVERWRITE):
        if (VERBOSE):
            sys.stdout.write(f"... downloading {ofile} to {outpath}.\n")
        with open(outfp, "wb") as outfile:
            with opener.open(f"{PRODUCTURL}{fileID}") as infile:
                while True:
                    chunk = infile.read(CHUNK)
                    if not chunk:
                        break
                    outfile.write(chunk)
        if (VERBOSE):
            sys.stdout.write(f"Done with {ofile}.\n")
    else:
        if (VERBOSE):
            sys.stdout.write(f"{ofile} exists, and overwite not enabled. skipping.\n")


if __name__ == "__main__":

    start_time = time.perf_counter()
    if not listoffiles:
        listoffiles = get_filelist(year, month)
    print(f"Downloading {len(listoffiles)} files.")
    # print(listoffiles)

    with Pool(NUMPROC) as p:
        p.map(process_file, listoffiles)

    run_time = time.perf_counter() - start_time
    print(f"Elapsed time: {int(run_time // 60)} minutes, {run_time % 60:0.2f} seconds")
