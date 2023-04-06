#!/bin/bash

# environment 
BASEDIR=/center1/DYNDOWN/cwaigl/ERA5_WRF
ARCHIVEDIR=/import/SNAP/cwaigl/wrf_era5
YEAR="$1"
SCRIPTDIR=`pwd`
LOCKFILE=archive_clean.lock

# only proceed when there's no lock file. 
if [ -f ${LOCKFILE} ]; then
    printf '%s %s\n' "$(date) - $0 - " "Process already running" && exit
else 
    touch ${LOCKFILE}
fi

yrlabel=$(date -d ${YEAR}0101 +%y)
cd ${BASEDIR}/WRF/

for FNsrc in ${yrlabel}* ; do 
    if [ -d $FNsrc ] ; then 
        FNtarget=${ARCHIVEDIR}/${YEAR}/${FNsrc}
        if [ -d $FNtarget ] ; then 
            for wrfoutfile in ${FNsrc}/wrfout_d0* ; do
                if [ -f ${ARCHIVEDIR}/${YEAR}/${wrfoutfile} ] ; then 
                    cmp ${wrfoutfile} ${ARCHIVEDIR}/${YEAR}/${wrfoutfile} >/dev/null
                    if [  `echo $?` -eq 0 ]
                    then
                        printf '%s %s\n' "$(date) - $0 - " "${wrfoutfile} has been archived and will be removed from CENTER1"
                        rm ${wrfoutfile}
                    else
                        printf '%s %s\n' "$(date) - $0 - " "${wrfoutfile} exists in both and they are different - pls check"
                    fi
                fi
            done
        fi
    fi
done

rm ${SCRIPTDIR}/${LOCKFILE}
