#!/bin/bash -e

# echo an error message before exiting and stop on error
trap 'echo "\"${last_command}\" command filed with exit code $?."' EXIT

# environment 
BASEDIR=/center1/DYNDOWN/cwaigl/ERA5_WRF
MONTHLABEL=$1
SCRIPTDIR=$(pwd)
umask 002

module purge
module load data/netCDF-Fortran/4.4.4-pic-intel-2016b
source /home/cwaigl/.bashrc
conda activate dyndown

LINKDIR=${BASEDIR}/era5_grib/${MONTHLABEL}_C
printf '%s %s\n' "$(date)" "Making links in ${LINKDIR}"
mkdir -p $LINKDIR

if [[ ! $(ls -1 $LINKDIR | wc -l) -ge 85 ]]; then
    cd $LINKDIR
    ln -sf ${BASEDIR}/era5_grib/${MONTHLABEL}/e5.oper.an.pl*${MONTHLABEL}1[0-9]*.grb .
    ln -sf ${BASEDIR}/era5_grib/${MONTHLABEL}/e5.oper.an.pl*${MONTHLABEL}2[0-7]*.grb .
    ln -sf ${BASEDIR}/era5_grib/${MONTHLABEL}/*e5.oper.an.sfc*.grb .
    ln -sf ${BASEDIR}/era5_grib/invar/*.grb .
    cd ${SCRIPTDIR}
else 
    printf '%s %s\n' "$(date)" "${LINKDIR} already contains necessary links to GRIB files"
fi

# clone the WPS prototype directory
WPSDIR=${BASEDIR}/WPS${MONTHLABEL}_C
printf '%s %s\n' "$(date)" "Cloning WPS directory to ${WPSDIR}"
cp -r ${BASEDIR}/WPS_dyndown_archivedir ${WPSDIR}

python generate_namelists.py -t wps ${MONTHLABEL}_C

cd ${WPSDIR}
./link_grib.csh ${LINKDIR}/*.grb
./ungrib.exe > /dev/null
./metgrid.exe > /dev/null

rm FILE*
