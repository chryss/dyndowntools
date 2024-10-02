import subprocess
import pandas as pd
import json
from io import StringIO

def get_cmd(user='cwaigl'):
    return ['squeue', '-u', user, '-o', "%.18i %.9P %.16j %.8u %.2t %.10M %.6D %N"]

def get_queuestatus(user='cwaigl'):
    cmd = get_cmd(user=user)
    pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    csvout = StringIO(pipe.communicate()[0].decode('utf-8'))

    df = pd.read_csv(csvout, sep='\s+')
    df = df[df.USER==user]
    return {
        "running": len(df[df.ST=='R']),
        "queued": len(df[df.ST=='PD'])
    }

if __name__ == '__main__':
    outdic = get_queuestatus()
    print(json.dumps(outdic, indent=2))
