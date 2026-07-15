#!/bin/bash -e
#
# Drives a year's (or partial year's) download + preprocess for the NetCDF
# ERA5 (AWS mirror) + JRA-3Q pipeline (2024-01-26 onward -- see README.md
# for the mixed-pipeline transitional period around that cutover). JRA-3Q
# is presumed already downloaded once for the whole campaign (edit
# startyear/endyear in rda_JRA_yr.py, then run it directly) rather than
# fetched here -- this script only checks it's present for the requested
# months before submitting the ERA5 download and preprocess SLURM arrays,
# chained so preprocess for each month starts as soon as (and only if) that
# month's download succeeds (--dependency=aftercorr, not afterok: no need
# to wait on the slowest download task before starting the rest).
#
# Usage: download_preprocess_year.sh YYYY [START-END]
#   START-END is an inclusive month range, e.g. 4-4 for April only.
#   Defaults to 1-12 (the full year) if omitted.
#
# cwaigl@alaska.edu 2026/07

module purge
module load slurm

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"
YEAR=${1:?"usage: download_preprocess_year.sh YYYY [START-END]"}
RANGE=${2:-1-12}
START=${RANGE%-*}
END=${RANGE#*-}
JRA3QDIR="${BASEDIR}/jra3q_nc"

missing=()
for m in $(seq "${START}" "${END}"); do
    month=$(printf "%02d" "${m}")
    ls "${JRA3QDIR}"/jra3q.anl_surf.0_1_13.weasd-sfc-an-gauss."${YEAR}${month}"*.nc >/dev/null 2>&1 \
        || missing+=("${YEAR}${month}")
done
if [[ ${#missing[@]} -gt 0 ]]; then
    echo "Missing JRA-3Q data for: ${missing[*]}" >&2
    echo "Download it first: edit startyear/endyear in rda_JRA_yr.py to ${YEAR}, then run it directly (python rda_JRA_yr.py)." >&2
    exit 1
fi

cd "${SCRIPT_DIR}"
DL_JOBID=$(sbatch --parsable --array="${RANGE}" --export=YEAR="${YEAR}" aws_era5_array.slurm)
echo "Submitted ERA5 download array: ${DL_JOBID} (months ${RANGE})"

PP_JOBID=$(sbatch --parsable --array="${RANGE}" --dependency=aftercorr:"${DL_JOBID}" --export=ALL,YEAR="${YEAR}" preprocess_era_array.slurm)
echo "Submitted preprocess array: ${PP_JOBID} (each month waits on the matching download task)"
