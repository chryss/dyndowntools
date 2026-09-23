#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

# environment
module purge
module load slurm
eval "$(conda shell.bash hook)"
conda activate dyndown
umask 002

# move datafiles to staging area
cd ${SCRIPTDIR}
python ./run_queue.py 
