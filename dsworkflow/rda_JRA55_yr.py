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

# https://rda.ucar.edu/data/ds628.0/anl_land125/1958/anl_land125.065_snwe.1958010100_1958123118

NUMPROC = 20
CHUNK = 16 * 1024
OUTPATH_test = Path("../../working/")
OUTPATH = Path("/center1/DYNDOWN/cwaigl/ERA5_WRF/jra55_grib/")
LOGINURL = "https://rda.ucar.edu/cgi-bin/login"
PRODUCTURL = "http://rda.ucar.edu/data/ds628.0/"
VERBOSE = True
OVERWRITE = False


load_dotenv()
rdauser = os.getenv("RDAUSER")
rdapass = os.getenv("RDAPASS")

startyear = 1958
endyear = 2022
folder = "anl_land"
var = "065_snwe"
listoffiles = []

# https://rda.ucar.edu/data/ds628.0/anl_land/2014/anl_land.065_snwe.reg_tl319.2014020100_2014022818

def get_localpth(firsthr, lasthr, folder, varname):
    yr = firsthr[:4]
    return f"{folder}/{yr}/{folder}.{varname}.reg_tl319.{firsthr}_{lasthr}"

def get_monthstr(yr, mth):
    return f"{str(yr)}{str(mth).zfill(2)}"

def get_filelist(startyear, endyear):
    filelist = []
    for yr in range(startyear, endyear+1):
        if yr < 2014:
            firsthr = f"{yr}010100"
            lasthr = f"{yr}123118"
            filelist.append(get_localpth(firsthr, lasthr, folder, var))
        else:
            for mth in range(1, 13):
                num_days = cal.monthrange(yr, mth)[1]
                days = [dt.date(yr, mth, day) for day in range(1,num_days+1)]
                firsthr = days[0].strftime("%Y%m%d00")
                lasthr = days[-1].strftime("%Y%m%d18")
                filelist.append(get_localpth(firsthr, lasthr, folder, var))
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
    outpath = OUTPATH 
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
        listoffiles = get_filelist(startyear, endyear)
    print(f"Downloading {len(listoffiles)} files.")
    # print(listoffiles)

    with Pool(NUMPROC) as p:
        p.map(process_file, listoffiles)

    run_time = time.perf_counter() - start_time
    print(f"Elapsed time: {int(run_time // 60)} minutes, {run_time % 60:0.2f} seconds")
