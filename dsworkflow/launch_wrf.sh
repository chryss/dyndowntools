#!/bin/bash

# environment 
BASEDIR=/center1/DYNDOWN/cwaigl/ERA5_WRF
SCRIPTDIR=${BASEDIR}/scripts/
TEMPLATEDIR=${BASEDIR}/scripts/templates
DATELABEL=$1
WPSLABEL=$2
TIMESTEP=${3:-"60"}
umask 002

module load slurm
source /home/cwaigl/.bashrc
conda activate dyndown

WRFDIR=${BASEDIR}/WRF/${DATELABEL}
# clone a WRF run directory with the correct date label (eg 200504 for the run from May 4 to 5, 2020.)
cp -r ${BASEDIR}/WRF/run_active ${WRFDIR}/
# copy iovars files into WRF run directory
cp ${TEMPLATEDIR}/iovars_d0?.txt ${WRFDIR}/
# copy extraction script into to WRF run directory
cp ${SCRIPTDIR}/extract_vars.py ${WRFDIR}/
# if there are more than three args, this is a debugging run - different slurm scripts to copy over
if [[ $# -gt 2 ]]; then
    echo "This is a debug run - it won't auto-archive and has timestep ${TIMESTEP}"
    cp ${TEMPLATEDIR}/dscDebug.slurm ${WRFDIR}/${DATELABEL}.slurm
else 
    cp ${TEMPLATEDIR}/dscD.slurm ${WRFDIR}/${DATELABEL}.slurm
fi
# in the run directory, symbolically link the appropriate met_em files
cd ${WRFDIR}
ln -s ${BASEDIR}/${WPSLABEL}/met_em.d0* .
# in the script directory, launch namelist generation for the new run 
cd ${SCRIPTDIR}
python generate_namelists.py -t wrf -T ${TIMESTEP} ${DATELABEL}
# in the run directory, submit SLURM job
cd ${WRFDIR}
qsub ${DATELABEL}.slurm
