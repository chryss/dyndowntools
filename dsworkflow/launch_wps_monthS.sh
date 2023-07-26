#!/bin/bash -e

# environment 
BASEDIR=/center1/DYNDOWN/cwaigl/ERA5_WRF
MONTHLABEL=$1
umask 002

module purge
module load slurm
module load data/netCDF-Fortran/4.4.4-pic-intel-2016b
source /home/cwaigl/.bashrc
conda activate dyndown

WPSDIR=${BASEDIR}/WPS${MONTHLABEL}
# clone the WPS prototype directory
cp -r ${BASEDIR}/WPS_dyndown_archivedir ${WPSDIR}

python generate_namelists.py -t wps ${MONTHLABEL}

cd ${WPSDIR}
cp wps.slurm ${MONTHLABEL}W.slurm
./link_grib.csh ${BASEDIR}/era5_grib/${MONTHLABEL}/*.grb
qsub ${MONTHLABEL}W.slurm