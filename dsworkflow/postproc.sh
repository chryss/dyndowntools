#!/bin/bash

# environment
umask 002

# constants
BASEDIR=/center1/DYNDOWN/cwaigl/ERA5_WRF
OUTDIR=/import/SNAP/cwaigl/wrf_era5
DSET=$1
SCRIPTDIR=`pwd`

targetdir=${OUTDIR}/${DSET}/
mkdir -p $targetdir
cd ${BASEDIR}/WRF/${DSET}

rsync -avz ./wrfout* $targetdir
cp namelist.input $targetdir