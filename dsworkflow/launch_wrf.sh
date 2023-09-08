#!/bin/bash

# environment 
BASEDIR=/center1/DYNDOWN/cwaigl/ERA5_WRF
DATELABEL=$1
WPSLABEL=$2
DEBUGLOCK=$3
SCRIPTDIR=`pwd`
umask 002

module load slurm
source /home/cwaigl/.bashrc
conda activate dyndown

# clone a WRF run directory with the correct date label (eg 200504 for the run from May 4 to 5, 2020.)
cp -r ${BASEDIR}/WRF/run_active ${BASEDIR}/WRF/${DATELABEL}
# rename the SLURM script
cp ${BASEDIR}/WRF/run_active/dscD.slurm ${BASEDIR}/WRF/${DATELABEL}/${DATELABEL}.slurm
# in the run directory, symbolically link the appropriate met_em files
cd ${BASEDIR}/WRF/${DATELABEL}
ln -s ${BASEDIR}/${WPSLABEL}/met_em.d0* .
# if this is a debugging run, lock output against moving
if [[ $# -gt 2 ]]
    then touch ./.dontmove_fordebug
fi
# in the script directory, launch namelist generation for the new run 
cd ${SCRIPTDIR}
python generate_namelists.py -t wrf ${DATELABEL}
# in the run directory, submit SLURM job
cd ${BASEDIR}/WRF/${DATELABEL}
qsub ${DATELABEL}.slurm
