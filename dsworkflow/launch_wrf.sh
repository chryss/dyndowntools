#!/bin/bash

# environment 
BASEDIR=/center1/DYNDOWN/cwaigl/ERA5_WRF
DATELABEL=$1
WPSLABEL=$2
SCRIPTDIR=`pwd`

module load slurm

cp -r ${BASEDIR}/WRF/run_active ${BASEDIR}/WRF/${DATELABEL}
cp ${BASEDIR}/WRF/run_active/dscD.slurm ${BASEDIR}/WRF/${DATELABEL}/${DATELABEL}.slurm
cd ${BASEDIR}/WRF/${DATELABEL}
ln -s ${BASEDIR}/${WPSLABEL}/met_em.d0* .

qsub ${DATELABEL}.slurm