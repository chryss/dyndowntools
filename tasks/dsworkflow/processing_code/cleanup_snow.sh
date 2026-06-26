#!/bin/bash 

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"
DATADIR="${BASEDIR}/era5_grib"
TARGETDIR="${SNOW_ARCHIVE_DIR}/"
SNOWPATTERN="??????/synth_e5.oper.an.sfc.128_141_sd.*.grb"

cd $DATADIR
rsync -avz  --progress ${SNOWPATTERN}  $TARGETDIR