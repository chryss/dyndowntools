#! /usr/bin/env python
#
# python script to download selected files from rda.ucar.edu
# after you save the file, don't forget to make it executable
#   i.e. - "chmod 755 <name_of_script>"
# 
# Refactored and ported to Python 3 cwaigl@alaska.edu 2023/02

import sys, os
import datetime as dt
from pathlib import Path
import urllib.request, urllib.parse
import http.cookiejar
from dotenv import load_dotenv
from multiprocessing import Pool

NUMPROC = 20
OUTPATH = Path("../../working/")
LOGINURL = "https://rda.ucar.edu/cgi-bin/login"
PRODUCTURL = "http://rda.ucar.edu/data/ds633.0/"
verbose = True

load_dotenv()
rdauser = os.getenv("RDAUSER")
rdapass = os.getenv("RDAPASS")

year = 2022
month = 12
vars3d = ['128_129_z', '128_130_t', '128_131_u', '128_132_v', 'q', '128_157_r', '128_133_q']
vars2d = []

listoffiles=["e5.oper.an.pl/202104/e5.oper.an.pl.128_129_z.ll025sc.2021040100_2021040123.grb","e5.oper.an.pl/202104/e5.oper.an.pl.128_130_t.ll025sc.2021040100_2021040123.grb","e5.oper.an.pl/202104/e5.oper.an.pl.128_131_u.ll025uv.2021040100_2021040123.grb","e5.oper.an.pl/202104/e5.oper.an.pl.128_132_v.ll025uv.2021040100_2021040123.grb","e5.oper.an.pl/202104/e5.oper.an.pl.128_133_q.ll025sc.2021040100_2021040123.grb","e5.oper.an.pl/202104/e5.oper.an.pl.128_157_r.ll025sc.2021040100_2021040123.grb","e5.oper.an.pl/202104/e5.oper.an.pl.128_129_z.ll025sc.2021040200_2021040223.grb","e5.oper.an.pl/202104/e5.oper.an.pl.128_130_t.ll025sc.2021040200_2021040223.grb","e5.oper.an.pl/202104/e5.oper.an.pl.128_131_u.ll025uv.2021040200_2021040223.grb","e5.oper.an.pl/202104/e5.oper.an.pl.128_132_v.ll025uv.2021040200_2021040223.grb","e5.oper.an.pl/202104/e5.oper.an.pl.128_133_q.ll025sc.2021040200_2021040223.grb","e5.oper.an.pl/202104/e5.oper.an.pl.128_157_r.ll025sc.2021040200_2021040223.grb"]

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
    opener = get_urlopener(rdauser, rdapass)
    idx = fileID.rfind("/")
    if (idx > 0):
        ofile = fileID[idx+1:]
    else:
        ofile = fileID
    if (verbose):
        sys.stdout.write(f"downloading {ofile}...\n")
        sys.stdout.flush()
    infile=opener.open(f"{PRODUCTURL}{fileID}")
    outfile=open(OUTPATH / ofile, "wb")
    outfile.write(infile.read())
    outfile.close()
    if (verbose):
        sys.stdout.write(f"done with {ofile}.\n")


if __name__ == "__main__":
    with Pool(NUMPROC) as p:
        p.map(process_file, listoffiles)
