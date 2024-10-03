# take n lines off the top of a queue file and execute them

import subprocess
from pathlib import Path
import check_queue as cq

QUEUEFILE = Path('status/taskqueue.txt')
N = 3
MAX = 10

def main():
    print(f"Running {N} launch tasks")
    processes = []
    with open(QUEUEFILE, 'r') as src:
        lines = src.readlines()
        for line in lines[:N]:
            print(f"running: {line}")
            try: 
               process = subprocess.Popen(line.split(),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except Exception as e:
                print(e)
            else:
                processes.append(process)
            
    with open(QUEUEFILE, 'w') as dst:
        dst.writelines(lines[N:])
            
    for process in processes:            
        # wait for the process to finish and get the output
        stdout, stderr = process.communicate()
        # print the output
        print(stdout.decode())
        print(stderr.decode())

if __name__ == '__main__':
    queuestatus = cq.get_queuestatus()
    if queuestatus["queued"] < MAX:
        print(f"There are {queuestatus['queued']} processes queued. Adding new tasks.")
        main()
    else:
        print(f"There are {queuestatus['queued']} processes queued. Not adding any.")
