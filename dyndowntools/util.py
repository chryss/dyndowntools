import pandas as pd
import numpy as np

COLNAMES = ["Tmax_F", "Tmin_F", "Tavg_F", "precip_in", "sd_m", "swe"]

def station2df(stationpth, tempunit='K'):
    df = pd.read_csv(stationpth, header=1, 
        names=COLNAMES, parse_dates=True)
    df = df.replace("M", "-9999",)
    df = df.replace("T", 0.01,)
    df['Tavg_F'] = df['Tavg_F'].astype(float)
    df['Tmax_F'] = df['Tmax_F'].astype(float)
    df['Tmin_F'] = df['Tmin_F'].astype(float)
    for col in ['Tavg_F', 'Tmin_F', 'Tmax_F']:
        df[col] = df[col].replace(-9999, np.nan)
    df['precip_in'] = df['precip_in'].astype(float)
    df['year'] = df.index.year
    return df