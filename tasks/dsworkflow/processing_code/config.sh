#!/bin/bash
# Instance-specific paths for this HPC deployment, read directly by bash scripts
# (via `source`) and by Python scripts (via python-dotenv, see workflowutil.py).
# Edit this file to adapt the pipeline to a different system/account.

export BASEDIR="/center1/DYNDOWN/cwaigl/ERA5_WRF"           # downscaling is run from this directory
export SCRIPTDIR="${BASEDIR}/scripts"                       # scripts in this directory are deployed to here
export WRF_ARCHIVE_DIR="/import/SNAP/cwaigl/wrf_era5"       # archived output files after postprocessing
export SNOW_ARCHIVE_DIR="/import/SNAP/cwaigl/synthsnow"     # archived synthetic snow files after postprocessing
