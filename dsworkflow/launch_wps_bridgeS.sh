#!/bin/bash -e

# environment 
BASEDIR=/center1/DYNDOWN/cwaigl/ERA5_WRF
MONTHLABEL=$1
SCRIPTDIR=$(pwd)
umask 002

module purge
module load slurm
module load data/netCDF-Fortran/4.4.4-pic-intel-2016b
source /home/cwaigl/.bashrc
conda activate dyndown

# First of all generate a link directory for month and previous month
PREVMONTH=$(date -d "${MONTHLABEL}01 - 1 month" +%Y%m)
LINKDIR=${BASEDIR}/era5_grib/${MONTHLABEL}_B
printf '%s %s\n' "$(date)" "Making links in ${LINKDIR}"
mkdir -p $LINKDIR

if [[ ! $(ls -1 $LINKDIR | wc -l) -ge 85 ]]; then
    cd $LINKDIR
    ln -s ${BASEDIR}/era5_grib/${MONTHLABEL}/e5.oper.an.pl*${MONTHLABEL}01*.grb .
    ln -s ${BASEDIR}/era5_grib/${MONTHLABEL}/e5.oper.an.pl*${MONTHLABEL}02*.grb .
    ln -s ${BASEDIR}/era5_grib/${MONTHLABEL}/e5.oper.an.pl*${MONTHLABEL}03*.grb .
    ln -s ${BASEDIR}/era5_grib/${MONTHLABEL}/*e5.oper.an.sfc*.grb .
    ln -s ${BASEDIR}/era5_grib/${PREVMONTH}/e5.oper.an.pl*${PREVMONTH}3*.grb .
    ln -s ${BASEDIR}/era5_grib/${PREVMONTH}/e5.oper.an.pl*${PREVMONTH}29*.grb .
    ln -s ${BASEDIR}/era5_grib/${PREVMONTH}/e5.oper.an.pl*${PREVMONTH}28*.grb .
    ln -s ${BASEDIR}/era5_grib/${PREVMONTH}/e5.oper.an.pl*${PREVMONTH}27*.grb .
    ln -s ${BASEDIR}/era5_grib/${PREVMONTH}/*e5.oper.an.sfc*.grb .
    ln -s ${BASEDIR}/era5_grib/invar/*.grb .
    cd $SCRIPTDIR
else 
    printf '%s %s\n' "$(date)" "${LINKDIR} already contains necessary links to GRIB files"
fi

# clone the WPS prototype directory
WPSDIR=${BASEDIR}/WPS${MONTHLABEL}_B
printf '%s %s\n' "$(date)" "Cloning WPS directory to ${WPSDIR}"
cp -r ${BASEDIR}/WPS_dyndown_archivedir ${WPSDIR}

python generate_namelists.py -t wps ${MONTHLABEL}_B

cd ${WPSDIR}
cp wps.slurm ${MONTHLABEL}.slurm
./link_grib.csh ${LINKDIR}/*.grb
qsub ${MONTHLABEL}.slurm
