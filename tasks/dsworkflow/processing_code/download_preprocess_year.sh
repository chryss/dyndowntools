#!/bin/bash -e
#
# Drives a year's (or partial year's) ERA5 download + preprocess. Works for
# any era, current (NetCDF/AWS mirror + JRA-3Q, 2024-01-26 onward) or
# pre-cutover (NetCDF/AWS mirror + JRA-55) alike -- the AWS mirror covers
# the full historical ERA5 record, and its ~2-month lag behind RDA/GDEX
# only matters for the most recent couple of months, so old years use the
# same downloader (aws_era5_month.py) as current ones. rda_month.py is a
# separate, RDA-sourced tool for that narrow recent-data-not-yet-mirrored
# window and isn't used here.
#
# JRA source is auto-selected per month by date, mirroring
# preprocess_snow_nc.py's --jra-source auto (see workflowutil.py's
# JRA_CUTOVER_YRMONTH) -- pass an explicit third argument (jra55/jra3q) to
# override, e.g. for the 202401 straddle month or a recovery scenario (see
# README.md).
#
# Either JRA generation is presumed already downloaded once per campaign
# (rda_JRA_yr.py, toggling USEJRA3Q) rather than fetched here -- this
# script only checks presence for the requested months before submitting
# the ERA5 download and preprocess SLURM arrays, chained so preprocess for
# each month starts as soon as (and only if) that month's download
# succeeds (--dependency=aftercorr, not afterok: no need to wait on the
# slowest download task before starting the rest).
#
# Usage: download_preprocess_year.sh YYYY [START-END] [auto|jra55|jra3q]
#   START-END is an inclusive month range, e.g. 4-4 for April only.
#   Defaults to 1-12 and auto if omitted.
#
# cwaigl@alaska.edu 2026/07

module purge
module load slurm

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"
YEAR=${1:?"usage: download_preprocess_year.sh YYYY [START-END] [auto|jra55|jra3q]"}
RANGE=${2:-1-12}
JRASOURCE=${3:-"auto"}
START=${RANGE%-*}
END=${RANGE#*-}
# JRA_CUTOVER_YRMONTH comes from config.sh (sourced above) -- shared with
# workflowutil.py's copy of the same value, single source of truth.

# Mirrors preprocess_snow_nc.py's resolve_jra_source(): prints jra55/jra3q
# for one YYYYMM, or "error" for the unresolvable 202401 straddle month
# when JRASOURCE is auto.
resolve_jra_source() {
    local yrmonth="$1"
    if [[ "${JRASOURCE}" != "auto" ]]; then
        printf '%s' "${JRASOURCE}"
        return
    fi
    if [[ "${yrmonth}" == "202401" ]]; then
        printf 'error'
        return
    fi
    if [[ "${yrmonth}" -ge "${JRA_CUTOVER_YRMONTH}" ]]; then
        printf 'jra3q'
    else
        printf 'jra55'
    fi
}

missing=()
for m in $(seq "${START}" "${END}"); do
    month=$(printf "%02d" "${m}")
    yrmonth="${YEAR}${month}"
    source=$(resolve_jra_source "${yrmonth}")
    case "${source}" in
        error)
            missing+=("${yrmonth} (202401 straddles the cutover mid-month -- pass an explicit jra55/jra3q)")
            ;;
        jra3q)
            pattern="${BASEDIR}/jra3q_nc/jra3q.anl_surf.0_1_13.weasd-sfc-an-gauss.${yrmonth}*.nc"
            ls ${pattern} >/dev/null 2>&1 || missing+=("${yrmonth} (jra3q)")
            ;;
        jra55)
            if [[ "${YEAR}" -lt 2014 ]]; then
                pattern="${BASEDIR}/jra55_grib/anl_land.065_snwe.reg_tl319.${YEAR}010100_${YEAR}123118*"
            else
                lastday=$(date -d "${yrmonth}01 +1 month -1 day" +%d)
                pattern="${BASEDIR}/jra55_grib/anl_land.065_snwe.reg_tl319.${yrmonth}0100_${yrmonth}${lastday}18*"
            fi
            ls ${pattern} >/dev/null 2>&1 || missing+=("${yrmonth} (jra55)")
            ;;
    esac
done
if [[ ${#missing[@]} -gt 0 ]]; then
    echo "Problems with JRA data for: ${missing[*]}" >&2
    echo "If missing: edit startyear/endyear (and USEJRA3Q) in rda_JRA_yr.py, then run it directly (python rda_JRA_yr.py)." >&2
    exit 1
fi

cd "${SCRIPT_DIR}"
DL_JOBID=$(sbatch --parsable --array="${RANGE}" --export=ALL,YEAR="${YEAR}" aws_era5_array.slurm)
echo "Submitted ERA5 download array: ${DL_JOBID} (months ${RANGE})"

PP_JOBID=$(sbatch --parsable --array="${RANGE}" --dependency=aftercorr:"${DL_JOBID}" --export=ALL,YEAR="${YEAR}",JRASOURCE="${JRASOURCE}" preprocess_era_array.slurm)
echo "Submitted preprocess array: ${PP_JOBID} (each month waits on the matching download task)"
