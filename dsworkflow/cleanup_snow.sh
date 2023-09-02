#!/bin/bash 

DATADIR=/center1/DYNDOWN/cwaigl/ERA5_WRF/era5_grib
TARGETDIR=/import/SNAP/cwaigl/synthsnow/
SNOWPATTERN="??????/synth_e5.oper.an.sfc.128_141_sd.*.grb"

cd $DATADIR
rsync -avz  --progress ${SNOWPATTERN}  $TARGETDIR