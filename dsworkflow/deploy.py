#!/bin/bash

import os
import subprocess

deploychinook="/center1/DYNDOWN/cwaigl/ERA5_WRF/scripts/"
hostname = os.uname().nodename

if hostname in ['discernment.local', 'Christines-MacBook-Pro.local']: 
    subprocess.call(['rsync', '-avzu', '--progress', '-e', 'ssh -i ~/.ssh/id_rsa.pub', '--include=*', '.', f'cwaigl@chinook.alaska.edu:{deploychinook}'])
    # rsync -avzu --progress -e 'ssh -i ~/.ssh/id_rsa.pub' cwaigl@chinook.alaska.edu:${deploychinook}/* . 
elif hostname.startswith('chinook'):
    subprocess.call(['rsync', '-avzu', '--progress', '--include=*', '.', deploychinook])
