#!/bin/bash -e

#SBATCH --partition=t2small
#SBATCH --account=cmip6
#SBATCH --ntasks=28
#SBATCH --tasks-per-node=28
#SBATCH --time=04:00:00
#SBATCH --mail-user=cwaigl@alaska.edu
#SBATCH --mail-type=FAIL
#SBATCH --output=wrf.%j
#
# NetCDF-ERA5 (era5_to_int) equivalent of wps.slurm -- replaces ungrib.exe
# with era5_to_int, which is single-threaded by design (its own source is a
# plain serial per-timestep loop, no multiprocessing), so it's run here as
# $SLURM_NTASKS parallel date-range chunks writing disjoint ERA5:<time>
# files into the same directory. LANDSEA and SOILGEO are explicitly skipped
# -- era5_to_int has its own native handling for those two invariant
# fields, sourced from a fixed 197901/ folder we never populate, but the
# Vtable confirms the one-time-ungribbed INVAR file already supplies them
# (as LANDSEA and the derived SOILHGT) under the same WPS names, so
# era5_to_int doesn't need to source them itself. The rest of the
# invariants (~12 fields the old GRIB pipeline uses that era5_to_int has no
# native support for at all) are likewise covered by INVAR, referenced via
# namelist.wps's constants_name. BASEDIR is inherited from the submitting
# shell's environment (config.sh exports it, sbatch propagates env by
# default) -- not sourced directly, since this script is cloned into a WPS
# run directory with no fixed relative path back to config.sh.

ulimit -s unlimited
ulimit -l unlimited
export WRFIO_NCD_LARGE_FILE_SUPPORT=1
export WRF_EM_CORE=1
export WRF_NMM_CORE=0
export WRF_CHEM=0
export WRF_KPP=0

. /etc/profile.d/modules.sh
module purge
module load slurm
module load intel-compilers/2023.1.0 iimpi/2023a
module load netCDF/4.9.2 netCDF-Fortran/4.6.1
source "$HOME/.bashrc"
conda activate dyndown

cd "$SLURM_SUBMIT_DIR"

# era5_to_int takes its date range as CLI arguments rather than reading
# namelist.wps itself -- pull start_date/end_date/interval_seconds from the
# namelist already generated here, so there's one source of truth.
STARTDATE=$(grep -oP "start_date\s*=\s*'\K[^',]+" namelist.wps | head -1)
ENDDATE=$(grep -oP "end_date\s*=\s*'\K[^',]+" namelist.wps | head -1)
INTSEC=$(grep -oP "interval_seconds\s*=\s*\K[0-9]+" namelist.wps)
HOURINT=$((INTSEC / 3600))

# era5_to_int's date parser doesn't accept WPS's own YYYY-MM-DD_HH:MM:SS
# form -- truncate to YYYY-MM-DD_HH, which it does accept.
STARTDATE=${STARTDATE%%:*}
ENDDATE=${ENDDATE%%:*}

ERADIR="${BASEDIR}/era5_nc"
NCHUNKS=${SLURM_NTASKS}

# WPS/ERA5 dates are UTC with no DST concept, but chinook's default
# timezone is America/Anchorage -- every `date` call here must be forced
# to -u (UTC), otherwise a run spanning a DST transition silently mislabels
# chunk boundaries by an hour (discovered via a real WPS202403_B failure:
# a chunk boundary landed on 2024-03-10, the actual US DST transition date,
# and every chunk after it was off by one hour, leaving a gap at exactly
# the skipped timestamp with no error -- era5_to_int parses date strings
# naively with no timezone awareness of its own, and its find_time_index
# silently falls back to index 0 on a lookup miss rather than erroring).
STARTSEC=$(date -u -d "${STARTDATE/_/ }" +%s)
ENDSEC=$(date -u -d "${ENDDATE/_/ }" +%s)
NSTEPS=$(( (ENDSEC - STARTSEC) / INTSEC + 1 ))
STEPSPERCHUNK=$(( (NSTEPS + NCHUNKS - 1) / NCHUNKS ))

pids=()
chunkstartsec=${STARTSEC}
while [ "${chunkstartsec}" -le "${ENDSEC}" ]; do
    chunkendsec=$(( chunkstartsec + (STEPSPERCHUNK - 1) * INTSEC ))
    if [ "${chunkendsec}" -gt "${ENDSEC}" ]; then
        chunkendsec=${ENDSEC}
    fi
    chunkstart=$(date -u -d "@${chunkstartsec}" +%Y-%m-%d_%H)
    chunkend=$(date -u -d "@${chunkendsec}" +%Y-%m-%d_%H)
    era5_to_int "${ERADIR}" "${chunkstart}" "${chunkend}" --hour-interval "${HOURINT}" \
        --skip-vars LANDSEA,SOILGEO &
    pids+=("$!")
    chunkstartsec=$(( chunkendsec + INTSEC ))
done
for pid in "${pids[@]}"; do
    wait "${pid}"
done
ERA5COUNT=$(ls -1 ERA5:* 2>/dev/null | wc -l)
if [ "${ERA5COUNT}" -ne "${NSTEPS}" ]; then
    echo "Expected ${NSTEPS} ERA5:* intermediate files (one per timestep), found ${ERA5COUNT} -- aborting before metgrid." >&2
    exit 1
fi

./avg_tsfc.exe > /dev/null
mpirun -np "${SLURM_NTASKS}" ./metgrid.exe
# Clean up the intermediary files
rm ./ERA5*
