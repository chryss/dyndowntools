#!/bin/bash

# environment 
BASEDIR=/center1/DYNDOWN/cwaigl/ERA5_WRF
MONTHLABEL=$1
SCRIPTDIR=$(pwd)

source /home/cwaigl/.bashrc
conda activate dyndown

# First of all generate a link directory for month and previous month
PREVMONTH=$(date -d "${MONTHLABEL}01 - 1 month" +%Y%m)
LINKDIR=${BASEDIR}/era5_grib/${MONTHLABEL}_B
mkdir $LINKDIR
ln -s  ${BASEDIR}/era5_grib/${MONTHLABEL}/*.grb ${LINKDIR}
ln -s  ${BASEDIR}/era5_grib/${PREVMONTH}/*.grb ${LINKDIR}
# ln -s ${BASEDIR}/era5_grib/invar/*.grb ${LINKDIR}

# clone the WPS prototype directory
WPSDIR=${BASEDIR}/WPS${MONTHLABEL}_B
cp -r ${BASEDIR}/WPS_dyndown_archivedir ${WPSDIR}

python generate_namelists.py -t wps ${MONTHLABEL}_B

cd ${WPSDIR}
./link_grib.csh ${LINKDIR}/*.grb
./ungrib.exe
./metgrid.exe

rm FILE*
