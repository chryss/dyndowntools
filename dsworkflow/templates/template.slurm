#!/bin/sh

#SBATCH --partition=t1small
#SBATCH --account=dyndown
#SBATCH --ntasks=56
#SBATCH --tasks-per-node=28
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
srun -l /bin/hostname | sort -n | awk '{print $2}' > ./nodes.$SLURM_JOB_ID
# Launch the MPI application
mpirun -np 16 real.exe
mpirun -np $SLURM_NTASKS -machinefile ./nodes.$SLURM_JOB_ID ./wrf.exe
# Clean up the machinefile
rm ./nodes.$SLURM_JOB_ID
