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
JRA55_INPUT_DIR = BASEDIR / "jra55_grib"
WRF_DIR = BASEDIR / "WRF"
JRA55_PRODUCTURL = "https://data.rda.ucar.edu/d628000/"
ERA5_PRODUCTURL = "https://osdf-director.osg-htc.org/ncar/gdex/d633000/"
DYNDOWN_USER = "cwaigl"

def get_bridge(date: dt.datetime) -> bool:
    if (
        date.month != (date + dt.timedelta(days=2)).month
        ) or (
        date.month != (date - dt.timedelta(days=1)).month):
        return 1
    else:
        return 0