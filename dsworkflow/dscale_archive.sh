#!/bin/bash

echo "Deleting rsl files"
rm rsl.out.*
rm rsl.error.*


if [ -z $1 ]; then
    echo "Please provide an archive directory. Exiting"
    exit 1   
fi

if [ -d $1 ]; then
    echo "Directory ${1} exists. Please use a different one. Exiting" 
    exit 1 # die with error code 1
fi

mkdir -p $1

echo "Moving wrfout files to $1"
mv wrfout_* $1
echo "Moving wrfbdy file to $1"
mv wrfbdy* $1
echo "Moving wrfinput files to $1"
mv wrfinput* $1
echo "Moving wrflowinp files to $1"
mv wrflowinp* $1

echo "Copying namelists"
cp namelist.input $1
cp ../../WPS/namelist.wps $1

echo "Archived to $1:"
ls -lAF $1
