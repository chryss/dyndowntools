#!/bin/bash

# environment
source /home/cwaigl/.bashrc
module purge
module load data/CDO/1.7.2-pic-intel-2016b
conda activate dyndown
umask 002

# constants
BASEDIR=/center1/DYNDOWN/cwaigl/ERA5_WRF
MONTHDIR=${1:-"202212"}
SCRIPTDIR=`pwd`

# preprocess snow
python preprocess_snow.py ${MONTHDIR}

cd ${BASEDIR}/era5_grib/${MONTHDIR}
mkdir -p archive

# Take care of the soil moisture files 
cdo -expr,'var39 = ((var39 > 0.01)) ? var39 : (0.01)'\
 e5.oper.an.sfc.128_039_swvl1.ll025sc.${MONTHDIR}0100_${MONTHDIR}??23.grb\
 pos_e5.oper.an.sfc.128_039_swvl1.ll025sc.${MONTHDIR}.grb
cdo -expr,'var40 = ((var40 > 0.01)) ? var40 : (0.01)'\
 e5.oper.an.sfc.128_040_swvl2.ll025sc.${MONTHDIR}0100_${MONTHDIR}??23.grb\
 pos_e5.oper.an.sfc.128_040_swvl2.ll025sc.${MONTHDIR}.grb
cdo -expr,'var41 = ((var41 > 0.01)) ? var41 : (0.01)'\
 e5.oper.an.sfc.128_041_swvl3.ll025sc.${MONTHDIR}0100_${MONTHDIR}??23.grb\
 pos_e5.oper.an.sfc.128_041_swvl3.ll025sc.${MONTHDIR}.grb
cdo -expr,'var42 = ((var42 > 0.01)) ? var42 : (0.01)'\
 e5.oper.an.sfc.128_042_swvl4.ll025sc.${MONTHDIR}0100_${MONTHDIR}??23.grb\
 pos_e5.oper.an.sfc.128_042_swvl4.ll025sc.${MONTHDIR}.grb

# link invariant files in monthly file 
ln -s ../invar/*.grb .

# move changed files to archive
mv e5.oper.an.sfc.128_*swvl?.ll025sc.*.grb archive/
mv e5.oper.an.sfc.128_141* archive/

