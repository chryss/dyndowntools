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

# First of all generate a link directory for month 
LINKDIR=${BASEDIR}/era5_grib/${MONTHLABEL}_C
printf '%s %s\n' "$(date)" "Making links in ${LINKDIR}"
mkdir -p $LINKDIR

if [[ ! $(ls -1 $LINKDIR | wc -l) -ge 120 ]]; then
    cd $LINKDIR
    ln -sf ${BASEDIR}/era5_grib/${MONTHLABEL}/e5.oper.an.pl*${MONTHLABEL}1[0-9]*.grb .
    ln -sf ${BASEDIR}/era5_grib/${MONTHLABEL}/e5.oper.an.pl*${MONTHLABEL}2[0-7]*.grb .
    ln -sf ${BASEDIR}/era5_grib/${MONTHLABEL}/*e5.oper.an.sfc*.grb .
    ln -sf ${BASEDIR}/era5_grib/invar/*.grb .
    # delete empty links
    find -xtype l -delete
    cd $SCRIPTDIR
else 
    printf '%s %s\n' "$(date)" "${LINKDIR} already contains necessary links to GRIB files"
fi

# clone the WPS prototype directory
WPSDIR=${BASEDIR}/WPS${MONTHLABEL}_C
printf '%s %s\n' "$(date)" "Cloning WPS directory to ${WPSDIR}"
cp -r ${BASEDIR}/WPS_dyndown_archivedir ${WPSDIR}

python generate_namelists.py -t wps ${MONTHLABEL}_C

cd ${WPSDIR}
cp wps.slurm ${MONTHLABEL}WC.slurm
./link_grib.csh ${LINKDIR}/*.grb
sbatch ${MONTHLABEL}WC.slurm