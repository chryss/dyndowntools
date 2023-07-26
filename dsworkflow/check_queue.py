import subprocess
import pandas as pd
import json
from io import StringIO

cmd = ['squeue']
pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE)
csvout = StringIO(pipe.communicate()[0].decode('utf-8'))

df = pd.read_csv(csvout, delim_whitespace=True)
df = df[df.USER=='cwaigl']
outdic = {
    "running": df[df.ST=='R'].size(),
    "queued": df[df.ST=='PD'].size()
}
print(json.dumps(outdic, indent=2))