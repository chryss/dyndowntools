#!/bin/bash

SCRIPTDIR=`pwd`
DATADIR=/center1/DYNDOWN/cwaigl/ERA5_WRF/WRF/staging
TARGETDIR=/import/SNAP/cwaigl/wrf_era5

# environment
source /home/cwaigl/.bashrc
module purge
conda activate dyndown
umask 002

# move datafiles to staging area
python move_datafiles.py 

# move datafiles 
cd $DATADIR
rsync -avz -R --remove-source-files --progress * $TARGETDIR

# checking and moving
cd $SCRIPTDIR
num1=$(find ${DATADIR} -type f -name era5_wrf_dscale_* | wc -l)
num2=$(cat status/wrfdir_fordeletion.txt | wc -l)
if (( $num1 == 4 * $num2 )); then
    echo "Everything looks right, moving files"
    cd $DATADIR
    rsync -avz -R --remove-source-files --progress *  $TARGETDIR
    if [ "$?" -eq "0" ]; then
        echo "rsync finished successfully; deleting directories"
        cd $SCRIPTDIR
        python move_datafiles.py -d
    else 
        echo "rsync finished with error; aborting. please check."
        exit 1
    fi 
else
    echo "Only ${num1} files staged, but ${num2} runs completed - please check. Aborting"
    exit 1
fi

# getting file status
cd ${TARGETDIR}/04km
find . -type f | cut -d"/" -f2 | uniq -c | sort -k 2
