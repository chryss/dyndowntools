#!/bin/sh

#SBATCH --partition=t2small
#SBATCH --time=18:00:00
#SBATCH --account=cmip6
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
export NETCDF=/usr/local/pkg/MPI/intel/2023.1.0/impi/2021.9.0/netCDF-Fortran/4.6.1/

cd $SLURM_SUBMIT_DIR
# Create a lockfile against output moving
touch ./.dontmove_debug
# Launch the MPI application
mpirun -np $SLURM_NTASKS ./real.exe
mpirun -np $SLURM_NTASKS ./wrf.exe
# Extract variables
eval "$(conda shell.bash hook)"
conda activate dyndown
python extract_vars.py -w `pwd`
chmod 664 era5_wrf_dscale_*
