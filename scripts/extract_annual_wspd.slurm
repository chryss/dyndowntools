#!/bin/sh

# Single-node Dask/xarray batch job for scripts/extract_annual_wspd.py.
# Unlike the WRF/WPS templates in dsworkflow/templates/, this is not an MPI
# job: one Python process runs one Dask worker with multiple threads, so we
# request a single task/node rather than --ntasks/--tasks-per-node.
#
# Defaults below assume the "analysis" queue's big-memory nodes. If that
# queue isn't available, switch to t1small (t2small access is uncertain per
# 2026-06 notes) and lower --mem/--cpus-per-task and the script's
# --memory-limit/--threads-per-worker to match that node's actual resources.

#SBATCH --job-name=extract_annual_wspd
#SBATCH --partition=analysis
#SBATCH --account=cmip6
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=80G
#SBATCH --time=18:00:00
# analysis queue: 3 shared BigMem nodes, 28 cores each, 4-day max walltime,
# meant for serial pre/post-processing. 16 cores (4 workers x 4 threads)
# leaves 12 free for other users. The 576.9s/year benchmark (2026-06-18) was
# with the old 1-worker/14-thread/float32 config; re-check timing with this
# worker layout and --pack-int16 before trusting the 18h estimate.
#SBATCH --mail-user=cwaigl@alaska.edu
#SBATCH --mail-type=END,FAIL
#SBATCH --output=extract_annual_wspd.%j.out

. /etc/profile.d/modules.sh
module purge
module load slurm

cd "$SLURM_SUBMIT_DIR"

# `pixi run` resolves the project env from pyproject.toml in the cwd above -
# no manual activate/module load needed for the Python side.
pixi run python scripts/extract_annual_wspd.py \
    --start-year 1959 \
    --end-year 2022 \
    --n-workers 4 \
    --threads-per-worker 4 \
    --memory-limit 16GB \
    --pack-int16
