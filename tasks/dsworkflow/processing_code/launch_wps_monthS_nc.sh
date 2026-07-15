#!/bin/bash -e
#
# NetCDF-ERA5 (era5_to_int) equivalent of launch_wps_monthS.sh. No
# GRIB-linking step at all -- era5_to_int reads era5_nc/ directly by date
# range inside wps_nc.slurm, so there's nothing to symlink here.

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
WPSDIR=${BASEDIR}/WPS${MONTHLABEL}_C
printf '%s %s\n' "$(date)" "Cloning WPS directory to ${WPSDIR}"
cp -r ${BASEDIR}/WPS_dyndown_archivedir ${WPSDIR}

python generate_namelists.py -t wps -n ${MONTHLABEL}_C

cd ${WPSDIR}
cp wps_nc.slurm ${MONTHLABEL}WC_nc.slurm
sbatch ${MONTHLABEL}WC_nc.slurm
