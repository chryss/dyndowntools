#!/bin/bash

import os
import subprocess
import workflowutil as wu

deploychinook = f"{wu.SCRIPTDIR}/"
hostname = os.uname().nodename

# hostnames below are user-specific; adapt to your own machine names to deploy elsewhere
if hostname in ['discernment.local', 'Christines-MacBook-Pro.local', 'Christines-MBP']:
    subprocess.call(['rsync', '-avzu', '--progress', '-e', 'ssh -oHostKeyAlgorithms=+ssh-dss', '--include=*', '.', f'cwaigl@chinook04.alaska.edu:{deploychinook}'])
    # rsync -avzu --progress -e 'ssh -i ~/.ssh/id_rsa.pub' cwaigl@chinook.alaska.edu:${deploychinook}/* . 
elif hostname.startswith('chinook'):
    subprocess.call(['rsync', '-avzu', '--progress', '--include=*', '.', deploychinook])
