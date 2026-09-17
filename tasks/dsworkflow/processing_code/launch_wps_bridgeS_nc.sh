#!/bin/bash -e
#
# NetCDF-ERA5 (era5_to_int) equivalent of launch_wps_bridgeS.sh. No
# GRIB-linking step, and no cross-month symlinking either -- era5_to_int
# resolves each requested date to the right era5_nc/{product}/{YYYYMM}/
# folder itself, so a bridge run spanning a month boundary needs nothing
# special here (unlike the GRIB pipeline, which had to manually symlink
# day-range subsets from both months into one directory before ungrib).

# environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"
MONTHLABEL=$1
umask 002

module purge
module load slurm
source "$HOME/.bashrc"
conda activate dyndown

# clone the WPS prototype directory
WPSDIR=${BASEDIR}/WPS${MONTHLABEL}_B
printf '%s %s\n' "$(date)" "Cloning WPS directory to ${WPSDIR}"
cp -r ${BASEDIR}/WPS_dyndown_archivedir ${WPSDIR}

python generate_namelists.py -t wps -n ${MONTHLABEL}_B

cd ${WPSDIR}
cp wps_nc.slurm ${MONTHLABEL}WB_nc.slurm
sbatch ${MONTHLABEL}WB_nc.slurm
