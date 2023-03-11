#!/bin/bash

deploychinook="/center1/DYNDOWN/cwaigl/ERA5_WRF/scripts"

rsync -avz --progress * cwaigl@chinook.alaska.edu:${deploychinook}