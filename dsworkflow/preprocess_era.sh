#!/bin/bash

# environment
source /home/cwaigl/.bashrc
module purge
module load data/CDO/1.7.2-pic-intel-2016b
conda activate cwtools
umask 002

# constants
BASEDIR=/center1/DYNDOWN/cwaigl/ERA5_WRF
MONTHDIR="202212"

# VARIDS=("39" "40" "41" "42")
# SOILMOISTURELABELS=("swvl1" "swvl2" "swvl3" "swvl4")
# SOILMOISTUREPREFIX="e5.oper.an.sfc.128_0"
# SOILMOISTURESUFFIX=".ll025sc.2022120100_2022123123.grb"

cd ${BASEDIR}/era5_grib/${MONTHDIR}
mkdir -p archive

# Take care of the soil moisture files 
cdo -expr,'var39 = ((var39 > 0.0)) ? var39 : (0.01)'\
 e5.oper.an.sfc.128_039_swvl1.ll025sc.${MONTHDIR}0100_${MONTHDIR}??23.grb\
 pos_e5.oper.an.sfc.128_039_swvl1.ll025sc.${MONTHDIR}.grb
cdo -expr,'var40 = ((var40 > 0.0)) ? var40 : (0.01)'\
 e5.oper.an.sfc.128_040_swvl2.ll025sc.${MONTHDIR}0100_${MONTHDIR}??23.grb\
 pos_e5.oper.an.sfc.128_040_swvl2.ll025sc.${MONTHDIR}.grb
cdo -expr,'var41 = ((var41 > 0.0)) ? var41 : (0.01)'\
 e5.oper.an.sfc.128_041_swvl3.ll025sc.${MONTHDIR}0100_${MONTHDIR}??23.grb\
 pos_e5.oper.an.sfc.128_041_swvl3.ll025sc.${MONTHDIR}.grb
cdo -expr,'var42 = ((var42 > 0.0)) ? var42 : (0.01)'\
 e5.oper.an.sfc.128_042_swvl4.ll025sc.${MONTHDIR}0100_${MONTHDIR}??23.grb\
 pos_e5.oper.an.sfc.128_042_swvl4.ll025sc.${MONTHDIR}.grb
mv e5.oper.an.sfc.128_*swvl?.ll025sc.*.grb archive/

