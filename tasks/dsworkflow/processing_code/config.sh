#!/bin/bash
# Instance-specific paths for this HPC deployment, read directly by bash scripts
# (via `source`) and by Python scripts (via python-dotenv, see workflowutil.py).
# Edit this file to adapt the pipeline to a different system/account.

export BASEDIR="/beegfs/DYNDOWN/cwaigl/ERA5_WRF"             # downscaling is run from this directory
export SCRIPTDIR="${BASEDIR}/scripts"                       # scripts in this directory are deployed to here
export WRF_ARCHIVE_DIR="/import/SNAP/cwaigl/wrf_era5"       # archived output files after postprocessing
export SNOW_ARCHIVE_DIR="/import/SNAP/cwaigl/synthsnow"     # archived synthetic snow files after postprocessing

# First YYYYMM sourced from JRA-3Q rather than JRA-55 (see README.md); the
# true cutover is 2024-01-26, mid-month, so 202401 itself can't be resolved
# at month granularity by auto-selection logic keyed on this value.
export JRA_CUTOVER_YRMONTH="202402"
