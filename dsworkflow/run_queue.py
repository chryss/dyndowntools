# take n lines off the top of a queue file and execute them

import subprocess
from pathlib import Path
import check_queue as cq

QUEUEFILE = Path('status/taskqueue.txt')
N = 2

with open(QUEUEFILE, 'r') as src:
    lines = src.readlines()
    for line in lines[:N]:
        subprocess.Popen(line.split(),
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)

with open(QUEUEFILE, 'w') as dst:
    dst.writelines(lines[N:])
