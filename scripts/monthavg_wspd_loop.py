# testing out whether xr.open_dataset() or xr.open_mfdataset() 
# is the way to go for extracting / aggregating data 
 
import time
from pathlib import Path
import pandas as pd
import xarray as xr
from  dask.distributed import Client

resolution = 12         # 4 or 12 km
datadir = Path(f"/import/SNAP/cwaigl/wrf_era5/{str(resolution).zfill(2)}km/")
filepattern = f"era5_wrf_dscale_{resolution}km"
chunking = {
    4: [225, 210],
    12: ['auto', 'auto']
}
outfn = f"windavg_monthly_{resolution}km.nc"
testyears_1 = ['2010', '2011', '2012', '2012']
years = [str(yr) for yr in range(1981, 2021)]
months = [str(item).zfill(2) for item in range (1, 13)]
Nmonths = 12

if __name__ == '__main__':
    client = Client()
    print(client.dashboard_link)
    initial_start_time = time.perf_counter()
    # loopyr = testyears_1
    loopyr = years
    loopmth = months[:Nmonths]
    collect = []
    accperiods = 0
    for idx, yr in enumerate(loopyr):
        collect_yr = []
        start_time = time.perf_counter ()
        timerange = pd.date_range(yr, freq="ME", periods=len(loopmth), name='time')
        # the data currently ends in June 2023
        if yr=='2023':
            timerange = pd.date_range(yr, freq="ME", periods=min(len(loopmth), 6), name='time')
        accperiods += len(timerange)
        print(f"Working on year {yr}")
        for mth in loopmth:
            # the data currently ends in June 2023
            if (yr=='2023') and (int(mth) > 6):
                continue
            fpths =  sorted(list((datadir / f"{yr}").glob(f"{filepattern}_{yr}-{mth}*.nc")))
            print(f"month {mth}, {len(fpths)} files")
            acc = [xr.open_dataset(pth, 
                                   chunks = {'Time':-1, 
                                             'south_north':chunking[resolution][0], 
                                             'west_east':chunking[resolution][1]}
                                   ).wspd10.mean(dim='Time') for pth in fpths]
            collect_yr.append(sum(acc)/len(acc))
        monthly_acc = xr.concat(collect_yr, dim=timerange)
        collect.append(monthly_acc)
        end_time = time.perf_counter()
        print(f"Loop for {yr} before saving file: {end_time - start_time:.2f}", "seconds")
        # write out file for each N completed years 
        # if idx%3 == 1:
        #     monthly_acc.to_netcdf(
        #         "windacc.nc",
        #         mode='a', 
        #         encoding={'acsnow': {"zlib": True, "complevel": 5}})
        #     end_time = time.perf_counter ()
        #     print(f"Loop for {yr} after saving intermediate result to file: {end_time - start_time:.2f}", "seconds")

    # one last time writing out results:
    print("Concatenating results")
    timerange = pd.date_range(loopyr[0], freq="ME", periods=accperiods, name='time')
    total_acc = xr.concat(collect, dim=timerange)
    print("Saving file")
    total_acc.to_netcdf(
        outfn, 
        encoding={'wspd10': {"zlib": True, "complevel": 5}})
    end_time = time.perf_counter()
    print("Execution time:")
    print(f"{end_time - initial_start_time:.2f}", "seconds")