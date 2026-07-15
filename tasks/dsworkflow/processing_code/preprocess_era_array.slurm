#!/bin/bash -e
#SBATCH --partition=analysis
#SBATCH --account=cmip6
#SBATCH --cpus-per-task=2
#SBATCH --mem=40G
#SBATCH --time=00:45:00
#SBATCH --mail-user=cwaigl@alaska.edu
#SBATCH --mail-type=FAIL
#SBATCH --output=status/preprocess_%A_%a.log
#SBATCH --array=1-12
#
# One array task per calendar month, running preprocess_era_jra3q.sh (snow
# synthesis + soil-moisture clamp) on the NetCDF ERA5/JRA-3Q input. analysis
# is the only shared/packable t2small-adjacent partition here -- t2small
# assigns whole nodes exclusively per job, so array tasks there just queue
# up one at a time regardless of --mem/--cpus-per-task. --mem is sized for
# the snow-synthesis step's peak footprint (float64 promotion during
# combine_first on a ~6GB SD field; 31-33GB observed via MaxRSS, revised up
# from an initial 25G estimate); SLURM packs as many array tasks as fit on
# analysis's 3 BigMem nodes and queues the rest. YEAR is passed at
# submission time -- sbatch --export=ALL,YEAR=2025 preprocess_era_array.slurm.
# Use ALL,YEAR=... , not just YEAR=... : --export=YEAR=2025 alone replaces
# rather than extends the default full-environment inheritance, which
# dropped MODULEPATH and broke the NCO module load on 2026-07-13 (see
# clamp_swvl_array.slurm, written to recover from that). SLURM_ARRAY_TASK_ID
# (1-12) maps to month.
#
# cwaigl@alaska.edu 2026/07

module purge
module load slurm

MONTH=$(printf "%02d" "${SLURM_ARRAY_TASK_ID}")
cd "${SLURM_SUBMIT_DIR}"
bash preprocess_era_jra3q.sh "${YEAR}${MONTH}"
