#!/bin/bash

echo "Removing old met_em files"
rm met_em.d0*
echo "Removing metgid log"
rm metgrid.log
echo "Removing ungrib log"
rm ungrib.log
echo "Removing old intermediate ungribbed files"
rm FILE\:*

echo "Running ungrib again"
./ungrib.exe

echo "Runnin metgrid again"
./metgrid.exe

echo "Done. Please consult ungrib and metgrid logfiles"
