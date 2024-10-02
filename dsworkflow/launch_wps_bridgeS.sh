#!/bin/bash -e

# environment 
BASEDIR=/center1/DYNDOWN/cwaigl/ERA5_WRF
MONTHLABEL=$1
SCRIPTDIR=$(pwd)
umask 002

module purge
module load slurm
# new chinook
module load intel-compilers/2023.1.0 iimpi/2023a 
module load netCDF/4.9.2 netCDF-Fortran/4.6.1
# old chinook 
# module load data/netCDF-Fortran/4.4.4-pic-intel-2016b
source /home/cwaigl/.bashrc
conda activate dyndown

# First of all generate a link directory for month and previous month
PREVLABEL=$(date -d "${MONTHLABEL}01 - 1 month" +%Y%m)   # previous yrmth eg 201204
PREVMONTH=${PREVLABEL:4:2}    # month alone, eg 02 or 11
LINKDIR=${BASEDIR}/era5_grib/${MONTHLABEL}_B
printf '%s %s\n' "$(date)" "Making links in ${LINKDIR}"
mkdir -p $LINKDIR

if [[ ! $(ls -1 $LINKDIR | wc -l) -ge 130 ]]; then
    cd $LINKDIR
    ln -sf ${BASEDIR}/era5_grib/${MONTHLABEL}/e5.oper.an.pl*${MONTHLABEL}0[1-9]*.grb .
    ln -sf ${BASEDIR}/era5_grib/${MONTHLABEL}/e5.oper.an.pl*${MONTHLABEL}1[0-2]*.grb .
    ln -sf ${BASEDIR}/era5_grib/${PREVLABEL}/e5.oper.an.pl*${PREVLABEL}2[5-9]*.grb .
    ln -sf ${BASEDIR}/era5_grib/${PREVLABEL}/e5.oper.an.pl*${PREVLABEL}3*.grb . 
    ln -sf ${BASEDIR}/era5_grib/${MONTHLABEL}/*e5.oper.an.sfc*.grb .
    ln -sf ${BASEDIR}/era5_grib/${PREVLABEL}/*e5.oper.an.sfc*.grb .
    ln -sf ${BASEDIR}/era5_grib/invar/*.grb .
    # delete empty links
    find -xtype l -delete
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
cp wps.slurm ${MONTHLABEL}WB.slurm
./link_grib.csh ${LINKDIR}/*.grb
sbatch ${MONTHLABEL}WB.slurm
