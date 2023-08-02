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
PREVLABEL=$(date -d "${MONTHLABEL}01 - 1 month" +%Y%m)   # previous yrmth eg 201204
PREVMONTH=${PREVLABEL:4:2}    # month alone, eg 02 or 11
LINKDIR=${BASEDIR}/era5_grib/${MONTHLABEL}_B
printf '%s %s\n' "$(date)" "Making links in ${LINKDIR}"
mkdir -p $LINKDIR

if [[ ! $(ls -1 $LINKDIR | wc -l) -ge 85 ]]; then
    cd $LINKDIR
    ln -s ${BASEDIR}/era5_grib/${MONTHLABEL}/e5.oper.an.pl*${MONTHLABEL}01*.grb .
    ln -s ${BASEDIR}/era5_grib/${MONTHLABEL}/e5.oper.an.pl*${MONTHLABEL}02*.grb .
    ln -s ${BASEDIR}/era5_grib/${MONTHLABEL}/e5.oper.an.pl*${MONTHLABEL}03*.grb .
    ln -s ${BASEDIR}/era5_grib/${MONTHLABEL}/*e5.oper.an.sfc*.grb .
    ln -s ${BASEDIR}/era5_grib/${PREVLABEL}/e5.oper.an.pl*${PREVLABEL}29*.grb .
    ln -s ${BASEDIR}/era5_grib/${PREVLABEL}/e5.oper.an.pl*${PREVLABEL}28*.grb .
    ln -s ${BASEDIR}/era5_grib/${PREVLABEL}/*e5.oper.an.sfc*.grb .
    ln -s ${BASEDIR}/era5_grib/invar/*.grb .
    if [[ ${PREVMONTH} != "02" ]] ; then            # it's not February
        ln -s ${BASEDIR}/era5_grib/${PREVLABEL}/e5.oper.an.pl*${PREVLABEL}3*.grb .  
    else                                            # it's February
        ln -s ${BASEDIR}/era5_grib/${PREVLABEL}/e5.oper.an.pl*${PREVLABEL}27*.grb .
        ln -s ${BASEDIR}/era5_grib/${PREVLABEL}/e5.oper.an.pl*${PREVLABEL}26*.grb .
    fi
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
qsub ${MONTHLABEL}WB.slurm
