#!/bin/bash

# environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"
SCRIPTDIR=$(pwd)
# LOGFILE=${$BASEDIR}/
umask 002

source "$HOME/.bashrc"
conda activate dyndown

# constants
# YEARS=(2021 2020)
YEARS=(2010)
# MONTHS=( 03 02 01 )
MONTHS=(12 11 10 09 08 07 06 05 04 03 02 01)
if [[ $# -gt 0 ]]
    then YEARS=($1)
fi
if [[ $# -gt 1 ]]
    then MONTHS=($2)
fi

for year in "${YEARS[@]}" ; do
    for month in "${MONTHS[@]}" ; do
        printf '%s %s\n' "$(date)" "Downloading ERA5 for ${year}${month}"
        python rda_month.py ${year}${month} >> status/era5download.log
        printf '%s %s\n' "$(date)" "Preprocessing ERA5 for ${year}${month}"
        bash preprocess_era.sh ${year}${month} & 
    done
done
