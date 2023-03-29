import pandas as pd
from pathlib import Path

STATUSFILE = Path('conf/status.feather')

statusdf = pd.read_feather(STATUSFILE)
print(statusdf)