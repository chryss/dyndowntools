#!/bin/bash -e
#
# Note: -e must also be set explicitly below, not just in the shebang --
# invoking this as `bash preprocess_era_nc.sh ...` (no exec bit set) does
# not honor the shebang's -e, so a failed step (e.g. the python snow
# synthesis) would otherwise be silently ignored and the raw file left
# untouched.

# NetCDF ERA5 (AWS mirror) equivalent of preprocess_era.sh, for any month
# regardless of pipeline generation -- snow source (JRA-55 or JRA-3Q) is
# picked by preprocess_snow_nc.py's --jra-source (default auto, by date;
# see README.md for the crossover/recovery case: re-fetching a pre-cutover
# month's ERA5 from the AWS mirror while still sourcing snow from JRA-55).
# Two per-month steps ahead of a WPS run: snow synthesis and a
# soil-moisture floor clamp. era5_to_int locates its ERA5 input by building
# an exact filename per variable (no globbing), so both steps overwrite the
# downloaded file in place; the untouched original is archived first. No
# invariant-file handling here -- those are ungribbed once, separately, and
# referenced via namelist.wps's constants_name.
#
# Usage: preprocess_era_nc.sh YYYYMM [auto|jra55|jra3q]
#
# cwaigl@alaska.edu 2026/07

set -e

# environment
source "$HOME/.bashrc"
module purge
module load intel-compilers/2023.1.0 iimpi/2023a
module load NCO/5.1.3
conda activate dyndown
umask 002

# constants
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"
MONTHDIR=${1:-"202401"}
JRASOURCE=${2:-"auto"}
SFCDIR="${BASEDIR}/era5_nc/e5.oper.an.sfc/${MONTHDIR}"

# preprocess snow (writes synth_e5.oper.an.sfc.128_141_sd... alongside the raw file)
python "${SCRIPT_DIR}/preprocess_snow_nc.py" -m --jra-source "${JRASOURCE}" "${MONTHDIR}"

cd "${SFCDIR}"
mkdir -p archive

# archive the raw snow depth file, and separately copy the synthesized
# field to SNOW_ARCHIVE_DIR under its synth_-prefixed name -- replaces
# cleanup_snow.sh's cron sweep, which found files by that prefix and can no
# longer do so once the rename below drops it. Then install the
# synthesized field under the standard name era5_to_int expects.
SDFILE=$(ls e5.oper.an.sfc.128_141_sd.ll025sc.*.nc)
cp "${SDFILE}" archive/
cp "synth_${SDFILE}" "${SNOW_ARCHIVE_DIR}/"
mv "synth_${SDFILE}" "${SDFILE}"

# clamp soil moisture at 0.01, overwriting in place (ncap2 -O; far faster
# than the cdo -expr equivalent used for the GRIB-era pipeline). The four
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
