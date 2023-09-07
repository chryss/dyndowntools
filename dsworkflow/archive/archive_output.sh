#!/bin/bash

# environment 
BASEDIR=/center1/DYNDOWN/cwaigl/ERA5_WRF
ARCHIVEDIR=/import/SNAP/cwaigl/wrf_era5
YEAR="$1"
SCRIPTDIR=`pwd`
LOCKFILE=archive_clean.lock

# only proceed when there's no lock file. 
if [ -f ${LOCKFILE} ]; then
    echo "Process already running" && exit
else 
    touch ${LOCKFILE}
fi

yrlabel=$(date -d ${YEAR}0101 +%y)
cd ${BASEDIR}/WRF/

for FNsrc in ${yrlabel}* ; do
    FNtarget=${ARCHIVEDIR}/${YEAR}/${FNsrc}
    if [ -n "$(ls -A ${FNsrc}/wrfout_d0* 2>/dev/null)"  ] ; then 
        echo "$(ls -A ${FNsrc}/wrfout_d0* | wc -l)" wrfout files in $FNsrc
    else
        echo no wrfout files in $FNsrc
    fi
    if [ -d $FNtarget ] ; then 
        echo "$(ls -A ${FNtarget}/wrfout_d0* | wc -l)" wrfout files in $FNtarget
    else
        echo "Archive directory doesn't exist for ${FNtarget}"
    fi
done

rm ${SCRIPTDIR}/${LOCKFILE}
