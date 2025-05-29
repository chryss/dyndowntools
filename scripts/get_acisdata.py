#!/usr/bin/env python
# 
# 2023-02-28 cwaigl@alaska.edu

import csv
from pathlib import Path
import requests
import pandas as pd
import geopandas as gp
import numpy as np

PROJPATH = Path(__file__).resolve().parent.parent
ACISDIR = PROJPATH / "evaluation/auxdata"
OUTDIR = PROJPATH / "evaluation/working"
ACISSTATIONS = "ACIS_stations.csv"
STARTDATE = '1951-01-01'
ENDDATE = '2020-12-31'

def safelyget(alist, idx, default='N/A'):
    """Returns alist[idx] if exists, else default"""
    try:
        return alist[idx]
    except (KeyError, IndexError):
        return default

def get_acis_stationdata(uid):

    baseurl = 'http://data.rcc-acis.org/StnData'
    params = {
        'uid': uid,
        'sdate': f"{STARTDATE}",
        'edate': f"{ENDDATE}",
        'elems': "maxt,mint,avgt,pcpn,snwd,13",
        'output': 'csv'
    }
    resp = requests.get(url=baseurl, params=params)
    return resp.text

def postproc_acisdata(textblock):
    pass

if __name__=='__main__':
    # get station file
    stations = pd.read_csv(ACISDIR / ACISSTATIONS)

    for idx, record in stations.iterrows():
        outfn = f"{record['name'].replace(' ', '_')}_T_max_min_avg_pcpn_sd_swe.csv"
        print(f"getting {outfn}")
        out = get_acis_stationdata(record['acisID'])
        with open(OUTDIR / outfn, 'w') as dst:
            dst.write(out)