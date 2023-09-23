#!/bin/bash

SCRIPTDIR=/center1/DYNDOWN/cwaigl/ERA5_WRF/scripts

# environment
source /home/cwaigl/.bashrc
module purge
module load slurm
conda activate dyndown
umask 002

# move datafiles to staging area
cd ${SCRIPTDIR}
python ./run_queue.py 
