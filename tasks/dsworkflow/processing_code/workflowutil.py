##############################################
# utilities 
# cwaigl@alaska.edu July 2023
##############################################

import datetime as dt
from pathlib import Path
from dotenv import dotenv_values

STATUSFILE = Path('status/status.feather')

# shared with bash, read from the single source of truth
_SHELL_CONFIG = dotenv_values(Path(__file__).resolve().parent / "config.sh")
BASEDIR = Path(_SHELL_CONFIG["BASEDIR"])
SCRIPTDIR = Path(_SHELL_CONFIG["SCRIPTDIR"])
WRF_ARCHIVE_DIR = Path(_SHELL_CONFIG["WRF_ARCHIVE_DIR"])
SNOW_ARCHIVE_DIR = Path(_SHELL_CONFIG["SNOW_ARCHIVE_DIR"])

# Python-only — never read by a bash script
# (named *_INPUT_DIR rather than *_GRIB_DIR: RDA has been moving ERA5 away from
# GRIB toward NetCDF, so baking "grib" into the name would already be misleading.
# Folder names on disk are untouched in this pass.)
ERA_INPUT_DIR = BASEDIR / "era5_grib"
ERA_NC_INPUT_DIR = BASEDIR / "era5_nc"    # AWS-mirror NetCDF input, 2024-01-02 forward -- see aws_era5_month.py
JRA55_INPUT_DIR = BASEDIR / "jra55_grib"
JRA3Q_INPUT_DIR = BASEDIR / "jra3q_nc"
WRF_DIR = BASEDIR / "WRF"
JRA55_PRODUCTURL = "https://osdf-director.osg-htc.org/ncar/gdex/d628000/"
JRA3Q_PRODUCTURL = "https://osdf-director.osg-htc.org/ncar/gdex/d640000/"
ERA5_PRODUCTURL = "https://osdf-director.osg-htc.org/ncar/gdex/d633000/"
# NCAR's public AWS Open Data mirror -- era5_to_int requires input laid out
# exactly like this bucket's own structure (verified 2026-07-10: NetCDF-only,
# folder-per-product/folder-per-YYYYMM, covers through end of 2025).
ERA5_AWS_PRODUCTURL = "https://nsf-ncar-era5.s3.amazonaws.com/"
ERA5_AWS_BUCKET = "nsf-ncar-era5"    # same bucket, for boto3 (bucket, key) calls
DYNDOWN_USER = "cwaigl"

def get_bridge(date: dt.datetime) -> bool:
    if (
        date.month != (date + dt.timedelta(days=2)).month
        ) or (
        date.month != (date - dt.timedelta(days=1)).month):
        return 1
    else:
        return 0