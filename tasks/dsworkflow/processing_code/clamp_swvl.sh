#!/bin/bash -e
#
# Soil-moisture floor clamp only, no snow synthesis -- for months where
# preprocess_era_jra3q.sh already completed snow synthesis but failed
# before/during this step (2025 backfill: the ncap2 clamp loop below, lifted
# unchanged from preprocess_era_jra3q.sh). Re-running preprocess_era_jra3q.sh
# itself on such a month would re-run (and double-apply) snow synthesis --
# use this instead once synthesis is confirmed already done.
#
# cwaigl@alaska.edu 2026/07

source "$HOME/.bashrc"
module purge
module load intel-compilers/2023.1.0 iimpi/2023a
module load NCO/5.1.3
conda activate dyndown
umask 002

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"
MONTHDIR=${1:?"usage: clamp_swvl.sh YYYYMM"}
SFCDIR="${BASEDIR}/era5_nc/e5.oper.an.sfc/${MONTHDIR}"

cd "${SFCDIR}"
mkdir -p archive

# clamp soil moisture at 0.01, overwriting in place (ncap2 -O). The four
# layers are independent files -- run them in parallel. A bare `wait` always
# returns 0 regardless of the background jobs' exit codes, so under `set -e`
# it wouldn't catch a failed ncap2 call -- wait on each PID individually.
pids=()
for spec in "039_swvl1:SWVL1" "040_swvl2:SWVL2" "041_swvl3:SWVL3" "042_swvl4:SWVL4"; do
    code="${spec%%:*}"
    var="${spec##*:}"
    f=$(ls e5.oper.an.sfc.128_${code}.ll025sc.*.nc)
    cp "${f}" archive/
    ncap2 -O -s "where(${var} < 0.01) ${var} = 0.01" "${f}" "${f}" &
    pids+=("$!")
done
for pid in "${pids[@]}"; do
    wait "${pid}"
done
