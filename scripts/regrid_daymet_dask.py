from pathlib import Path
import xarray as xr
import numpy as np
import xesmf as xe
import time
import warnings
from  dask.distributed import Client
import dask.array as da

warnings.filterwarnings("ignore")

daymetpath = Path("/Volumes/cwdata1/Daymet/")
outdir = daymetpath / 'regridded_to_era5_dscale'
outdir.mkdir(parents=True, exist_ok=True)
# daymetvars = ['prcp', 'tmax', 'tmin']
daymetvars = ['tmin']
sampleidx = 0
era5dscpath = Path().absolute().parents[1]/'dyndowndata/DSCALE_data'
regridderpath = Path().absolute().parents[0]/'evaluation/regridders'
sample = 'era5_wrf_dscale_{res}_2014-12-22.nc'
resolutions = [
    '4km', 
    '12km',
]
startyear = 1985
generate_regridder = False
regrid_sample = False
regrid_all = True

#def load ERA_dsc template
def load_era_dsc_template(res):
    templateDS = xr.open_dataset(era5dscpath / sample.format(res=res), chunks='auto')
    templateDS = templateDS.rename({"XLONG": "lon", "XLAT": "lat", 'XTIME': 'time'})
    templateDS["lat"].attrs["standard_name"] = "latitude"
    templateDS["lat"].attrs["units"] = "degrees_north"
    templateDS["lon"].attrs["standard_name"] = "longitude"
    templateDS["lon"].attrs["units"] = "degrees_east"
    return templateDS

def format_elapsed_time(elapsed_time):
    days = 0
    if elapsed_time >= 86400:
        days = int(elapsed_time / 86400)
    elapsed = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
    if days == 0:
        return f"{elapsed}"
    else:
        return f"{days}:{elapsed}"

if __name__ == "__main__":
    client = Client()
    print(client.dashboard_link)
    
    start_time_total = time.perf_counter()
    regridders = {}
    daymetvar = daymetvars[sampleidx]
    for res in resolutions:
        print(f"Working on resolution: {res}")
        start_time = time.perf_counter()
        template = load_era_dsc_template(res)
        print("Loaded downscaled ERA5 template")

        #load and mask Daymet sample
        daymet_sample = sorted(list(daymetpath.glob(f'daymet_v4_daily_na_{daymetvar}_*.nc')))[0]
        daymet_sampleDS = xr.open_dataset(daymet_sample, chunks='auto')
        mask_in = (daymet_sampleDS.lat > 50) & (daymet_sampleDS.lat < 76) & (daymet_sampleDS.lon < -100)
        daymet_sampleDS['mask'] = xr.where(mask_in, 1, 0)
        print("Loaded Daymet sample")
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        print(f"Time taken for data loading: {format_elapsed_time(elapsed_time)}")
        # dataArray = daymet_sampleDS[daymetvar]

        # calculate and save regridder or load from file
        start_time = time.perf_counter()
        if generate_regridder:
            print(f"starting calculation of regridder for {res}")

            regrid_daymet_to_era5DSCALE = xe.Regridder(daymet_sampleDS, 
                                                    template, method='bilinear', parallel=True)
            regrid_daymet_to_era5DSCALE.to_netcdf(f"regridder_daymet_to_era5_{res}.nc")
            print("Regridder calculated and saved")
        else:
            regrid_daymet_to_era5DSCALE = xe.Regridder(daymet_sampleDS, 
                                                    template, 
                                                    weights= regridderpath / f"regridder_daymet_to_era5_{res}.nc",
                                                    method='bilinear')
        regridders[res] = regrid_daymet_to_era5DSCALE
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        print(f"Time taken for regridder retrieval at {res}: {format_elapsed_time(elapsed_time)}")

        # regrid and save regridded file
        if regrid_sample:
            print(f"regridding sample for {daymetvar} at resolution {res}")
            start_time = time.perf_counter()
            # regrid_source = da.from_array(daymet_sampleDS[daymetvar])
            # regridded_data = regrid_daymet_to_era5DSCALE(regrid_source, keep_attrs=True)
            # regridded_data.compute()
            regridded_data = regrid_daymet_to_era5DSCALE(daymet_sampleDS[daymetvar], keep_attrs=True)
            regridded_data.to_netcdf(
                f"regridded_daymet_to_era5_{daymetvar}_{res}.nc",
                )
            end_time = time.perf_counter()
            elapsed_time = end_time - start_time
            print(f"Time taken for regridding and saving: {format_elapsed_time(elapsed_time)}")
        daymet_sampleDS.close()
        template.close()
    if regrid_all:
        print(f"regridding for all variables in {', '.join(daymetvars)} at resolution {res}")
        for daymetvar in daymetvars:
            for fp in sorted(list(daymetpath.glob(f'daymet_v4_daily_na_{daymetvar}_*.nc'))):
                start_time = time.perf_counter()
                year = fp.stem[-4:]
                if int(year) < startyear:
                    continue    
                else:
                    print(f"*** regridding {fp.name}")
                with xr.open_dataset(fp, chunks='auto') as src:
                    src['mask'] = xr.where(mask_in, 1, 0)
                    src_array = src[daymetvar]
                for res in resolutions: 
                    print(f"**** Resolution: {res}")
                    regridder = regridders[res]
                    regridded_data = regridder(src_array, keep_attrs=True)
                    outfn = f"regridded_daymet_to_era5_{daymetvar}_{res}_{year}.nc"
                    print(f"Saving {outdir}/{outfn}")
                    regridded_data.to_netcdf(
                        outdir / outfn,
                    )
                end_time = time.perf_counter()
                elapsed_time = end_time - start_time
                print(f"Time taken for regridding and saving {daymetvar} for {year}: {format_elapsed_time(elapsed_time)}")
            print()
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time_total
    print(f"Total time taken: {format_elapsed_time(elapsed_time)}")
