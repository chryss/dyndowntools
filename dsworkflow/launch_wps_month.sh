#!/bin/bash

# echo an error message before exiting and stop on error
set -e
trap 'echo "\"${last_command}\" command filed with exit code $?."' EXIT

# environment 
BASEDIR=/center1/DYNDOWN/cwaigl/ERA5_WRF
MONTHLABEL=$1
SCRIPTDIR=`pwd`
umask 002

module purge
module load data/netCDF-Fortran/4.4.4-pic-intel-2016b
source /home/cwaigl/.bashrc
conda activate dyndown

WPSDIR=${BASEDIR}/WPS${MONTHLABEL}
# clone the WPS prototype directory
cp -r ${BASEDIR}/WPS_dyndown_archivedir ${WPSDIR}

python generate_namelists.py -t wps ${MONTHLABEL}

cd ${WPSDIR}
./link_grib.csh ${LINKDIR}/*.grb
./ungrib.exe > /dev/null
./metgrid.exe > /dev/null

rm FILE*
