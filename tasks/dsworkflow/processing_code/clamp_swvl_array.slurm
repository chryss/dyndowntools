#!/bin/bash -e
#SBATCH --partition=analysis
#SBATCH --account=cmip6
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:15:00
#SBATCH --mail-user=cwaigl@alaska.edu
#SBATCH --mail-type=FAIL
#SBATCH --output=status/clamp_%A_%a.log
#SBATCH --array=1-12
#
# Companion to preprocess_era_array.slurm for months where snow synthesis
# already completed but the ncap2 clamp step didn't run. --mem is tiny
# compared to preprocess_era_array.slurm's since ncap2 streams to disk
# rather than holding a full field in memory. SLURM_ARRAY_TASK_ID (1-12)
# maps to month, same as preprocess_era_array.slurm -- using literal YYYYMM
# as the task ID instead was tried and rejected (SLURM's MaxArraySize=1001
# caps task IDs well below any YYYYMM value). Submit only the months
# actually needed, e.g. sbatch --export=ALL,YEAR=2025 --array=2-12
# clamp_swvl_array.slurm for Feb-Dec. Use ALL,YEAR=..., not just YEAR=...:
# --export=YEAR=2025 alone replaces rather than extends the default
# full-environment inheritance, which dropped MODULEPATH and broke the NCO
# module load on 2026-07-13.
#
# cwaigl@alaska.edu 2026/07

module purge
module load slurm

MONTH=$(printf "%02d" "${SLURM_ARRAY_TASK_ID}")
cd "${SLURM_SUBMIT_DIR}"
bash clamp_swvl.sh "${YEAR}${MONTH}"
