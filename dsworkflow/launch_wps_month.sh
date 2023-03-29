#!/bin/bash

# environment 
BASEDIR=/center1/DYNDOWN/cwaigl/ERA5_WRF
MONTHLABEL=$1
SCRIPTDIR=`pwd`

source /home/cwaigl/.bashrc
conda activate dyndown

WPSDIR=${BASEDIR}/WPS${MONTHLABEL}
# clone the WPS prototype directory
cp -r ${BASEDIR}/WPS_dyndown_archivedir ${WPSDIR}

python generate_namelists.py -t wps ${MONTHLABEL}

cd ${WPSDIR}
./link_grib.csh ${BASEDIR}/era5_grib/${MONTHLABEL}/*.grb
./ungrib.exe
./metgrid.exe

rm FILE*
