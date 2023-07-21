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
python preprocess_snow_experimental.py ${MONTHDIR}

cd ${BASEDIR}/era5_grib/${MONTHDIR}
mkdir -p archive

# move changed files to archive
mv e5.oper.an.sfc.128_141* archive/