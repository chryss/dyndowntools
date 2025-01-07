import xarray as xr

infn = "snowacc_4km.nc"

with xr.open_dataset(infn) as src:
    print(src.time)