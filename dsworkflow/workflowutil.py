##############################################
# utilities 
# cwaigl@alaska.edu July 2023
##############################################

import datetime as dt
from pathlib import Path

STATUSFILE = Path('status/status.feather')

def get_bridge(date: dt.datetime) -> bool:
    if (
        date.month != (date + dt.timedelta(days=2)).month
        ) or (
        date.month != (date - dt.timedelta(days=1)).month):
        return 1
    else:
        return 0