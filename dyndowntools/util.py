from pathlib import Path
import pandas as pd
import numpy as np

COLNAMES = ["Tmax_F", "Tmin_F", "Tavg_F", "precip_in", "sd_m", "swe"]
STARTDATE = '1981-01-01'
ENDDATE = '2020-12-31'
AGG = 'mean'
RESOLUTIONS = ['4km', '12km']
STATIONS = {
    "ANCHORAGE_TED_STEVENS_INTERNATIONAL_AIRPORT": "ANC_PANC",
    "FAIRBANKS_INTL_AP": "FAI_PAFA",
    "BARROW_AIRPORT": "UTQ_PABR",
    "BETHEL_AIRPORT": "BTH_PABE"
}
dataroot = Path().absolute().parent 
datadir = dataroot / "evaluation/working"
figdir = dataroot / "evaluation/figures"
stationdir = dataroot / "evaluation/weatherstationdata/ACIS"
filepattern_ERA5_dscale = 't2m_{agg}_{airport}_1981_2020_{resolution}.csv'
filepattern_ERA5_orig = 'era5_{airport}_Tmean_1981_2020_monthly.csv'
filepattern_station = '{station}_T_max_min_avg_pcpn_sd_swe.csv'

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

def add_significance_suffix(row):
    if row['pvalue'] < 0.05:
        return ' (**)'
    elif row['pvalue'] < 0.1:
        return ' (*)'
    else: return ''

def add_significance_suffix_fontweight(trendvalue, p_value):
    if p_value < 0.05:
        return f'**{trendvalue}**'
    elif p_value < 0.1:
        return f'*{trendvalue}*'
    else: return ''

def rmse(reference, modelvals):
    return np.sqrt(((reference - modelvals) ** 2).mean())

def F2C(temp_F):
    """Convert temperature from °F to °C"""
    return (temp_F - 32.0) * 5.0/9.0

def get_dataframe_ERA5(var, station, datadir=datadir, 
                       filepattern_ERA5_dscale=filepattern_ERA5_dscale,
                       agg=AGG, 
                       resolutions=RESOLUTIONS, stations=STATIONS,
                       startdate=STARTDATE, enddate=ENDDATE):
    dfs = {}
    varagg = f'{var}_{agg}'
    for res in resolutions:
        dfs[res] = pd.read_csv(
            datadir / filepattern_ERA5_dscale.format(airport=stations[station], agg=agg, resolution=res))
        dfs[res]['Time'] = pd.to_datetime(dfs[res]['Time'])
        if var == 'T2':
            print(f"var is {var}")
            dfs[res][varagg] = dfs[res][varagg] - 273.15      # K to C
        dfs[res].rename(columns={varagg: f"{varagg}_{res}"}, inplace=True)
    dfs['4km'][f'{varagg}_12km'] = dfs['12km'][f'{varagg}_12km']
    return dfs['4km']

def get_dataframe_station(var, station, stationdir=stationdir, 
                          filepattern_station=filepattern_station,
                          agg=AGG,
                          startdate=STARTDATE, enddate=ENDDATE):
    stationpth = stationdir / filepattern_station.format(station=station)
    df = station2df(stationpth)
    # return df
    if var=='T2':
        if agg=='max':
            df['Tmax_station'] = F2C(df['Tmax_F'].astype(float))
            return df['Tmax_station'].loc[startdate:enddate]
        elif agg=='mean':
            df['Tmean_station'] = F2C(df['Tavg_F'])
            return df['Tmean_station'].loc[startdate:enddate]
    return df.loc[startdate:enddate]

def get_dataframe(var, station, stationdir=stationdir, datadir=datadir, 
                filepattern_station=filepattern_station, 
                filepattern_ERA5_dscale=filepattern_ERA5_dscale,
                agg=AGG, startdate=STARTDATE, enddate=ENDDATE):
    ERA5df = get_dataframe_ERA5(var, station, datadir=datadir, 
                filepattern_ERA5_dscale=filepattern_ERA5_dscale,
                agg=agg, 
                startdate=startdate, enddate=enddate)
    stationdf = get_dataframe_station(var, station, 
                stationdir=stationdir, 
                filepattern_station=filepattern_station,
                agg=agg,
                startdate=startdate, enddate=enddate)
    print(f"in {__file__}. var is {var}")
    ERA5df.set_index('Time', inplace=True)
    ERA5df.index = pd.to_datetime(ERA5df.index)
    stationdf.index.name = 'Time'
    stationdf.index = pd.to_datetime(stationdf.index)
    return pd.merge(ERA5df, stationdf,
            how='inner', left_index=True, right_index=True)

def get_name(location):
    """Provide location name in title case, replacing Barrow"""
    name = location.split(' ')[0].title()
    if name == 'Barrow':
        return 'Utqiaġvik'
    else:
        return name

def get_monthly(var, dailyDF,
                startdate=STARTDATE, enddate=ENDDATE,
                agg=AGG):
    dailyDF = dailyDF.loc[startdate:enddate]
    if var=='T2':
        monthly_avg = dailyDF[[f'T2_{agg}_4km', f'T2_{agg}_12km', f'T{agg}_station']].groupby(
            pd.Grouper(freq='M')).mean()
    monthly_avg['year'] = monthly_avg.index.year
    monthly_avg['month'] = monthly_avg.index.month
    return monthly_avg
    
def get_stats(var, station, monthlyDF,
              stations=STATIONS, agg=AGG):
    output = []
    for variable in (f'T{agg}', f'T2_{agg}_4km', f'T2_{agg}_12km', f'T{agg}_station'):
        for mth in range(1, 13):
            X = monthlyDF.query(f'month == {mth}')['year']
            Y = monthlyDF.query(f'month == {mth}')[variable]
            slope, _, r_value, p_value, _ = stats.linregress(X, Y)
            mean = Y.mean()
            output.append({
                "location": stations[station][4:],
                'variable': variable,
                'month': mth, 
                'mean_monthly_T': mean, 
                'trend': slope, 
                'p_value': p_value, 
                'r_value':r_value})
    return output
