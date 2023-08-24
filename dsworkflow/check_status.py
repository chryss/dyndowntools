from pathlib import Path
import pandas as pd
import workflowutil as wu

if __name__ == '__main__':
    statusdf = pd.read_feather(wu.STATUSFILE)
    print(statusdf)