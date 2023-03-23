#!/bin/bash

deploychinook="/center1/DYNDOWN/cwaigl/ERA5_WRF/scripts"

rsync -avz --progress -e 'ssh -i ~/.ssh/id_rsa.pub' * cwaigl@chinook.alaska.edu:${deploychinook}