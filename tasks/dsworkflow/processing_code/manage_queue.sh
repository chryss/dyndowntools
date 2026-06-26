#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

# environment
source "$HOME/.bashrc"
module purge
module load slurm
conda activate dyndown
umask 002

# move datafiles to staging area
cd ${SCRIPTDIR}
python ./run_queue.py 
