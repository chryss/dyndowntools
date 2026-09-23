#!/bin/bash -e
#SBATCH --partition=t2small
#SBATCH --account=cmip6
#SBATCH --cpus-per-task=3
#SBATCH --mem=4G
#SBATCH --time=08:00:00
#SBATCH --mail-user=cwaigl@alaska.edu
#SBATCH --mail-type=FAIL
#SBATCH --output=status/era5_aws_%A_%a.log
#SBATCH --array=1-12
#
# Download ERA5 NetCDF input from the AWS mirror via aws_era5_month.py. 
# One array task per calendar month. This is I/O bound, so we use a 
# pool and boto3, not mpi. YEAR is passed at submission time
# (sbatch --export=YEAR=2025 aws_era5_array.slurm); SLURM_ARRAY_TASK_ID
# (1-12) maps directly to month.
#
# cwaigl@alaska.edu 2026/07

module purge
module load slurm
eval "$(conda shell.bash hook)"
conda activate dyndown

MONTH=$(printf "%02d" "${SLURM_ARRAY_TASK_ID}")
python "${SLURM_SUBMIT_DIR}/aws_era5_month.py" "${YEAR}${MONTH}"
