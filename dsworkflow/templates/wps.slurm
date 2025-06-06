#!/bin/sh

#SBATCH --partition=t2small
#SBATCH --account=cmip6
#SBATCH --ntasks=24
#SBATCH --tasks-per-node=24
#SBATCH --time=04:00:00
#SBATCH --mail-user=cwaigl@alaska.edu
#SBATCH --mail-type=FAIL
#SBATCH --output=wrf.%j

ulimit -s unlimited
ulimit -l unlimited
export WRFIO_NCD_LARGE_FILE_SUPPORT=1
export WRF_EM_CORE=1
export WRF_NMM_CORE=0
export WRF_CHEM=0
export WRF_KPP=0

# Load any desired modules, usually the same as loaded to compile
. /etc/profile.d/modules.sh
module purge
module load slurm
# new chinook
module load intel-compilers/2023.1.0 iimpi/2023a 
module load netCDF/4.9.2 netCDF-Fortran/4.6.1
# old chinook 
# module load data/netCDF-Fortran/4.4.4-pic-intel-2016b

cd $SLURM_SUBMIT_DIR
# Generate a list of allocated nodes; will serve as a machinefile for mpirun
# run ungrib and metgrid
./ungrib.exe > /dev/null
./avg_tsfc.exe > /dev/null
mpirun -np 24 ./metgrid.exe 
# Clean up the intermediary files
rm ./FILE*
