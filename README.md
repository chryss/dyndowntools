# dyndowntools

Code created for dynamical downscaling project, IARC/CASC 2022-2024
Chris Waigl - cwaigl@alaska.edu

## Overview

The repo's content are as follows:

 - `config/`: files relating to the domain configuration as well as miscellaneous configuration files
 - `dsworkflow/`: the code that orchestrates all aspects of the downscaling process (see below for details)
 - `dsworkflow_legacy\`: previous iterations of workflow code, some inherited from others
 - `dyndowntools/`: placeholder for importable package
 - `Jupyter_Notebooks/`: exploratory or analysis code, as well as visualizations, to be run interactively
 - `scripts/`: stand-alone scripts
 - `dyndown_environment.yml`: environment file for `conda`

## Workflow components

### 1. Download and preprocess ERA5 files

Manually run `era5_download.sh [YEAR] [MONTH]` for a single month. For a whole year, edit/check script to enable list of months and run it `era5_download.sh [YEAR]`. Similarly, multiple years can be downloaded at once. 

The script first calls `rda_month.py YYYYMM`, which uses joblib to paralellize / accelerate download.

Once a month's worth of ERA5 data is downloaded, `era5_download.sh` calls `preprocess_era.sh` is run. It does two things: 

  - using `cdo` from the command line, replace negative values in the soil moisture files with 0.01.
  - calling `preprocess_snow.py` on the snow input data to create combined synthetic snow dataset including the (already downloaded) JRA55 data. **NOTE:** Before 1958/10, replace  `preprocess_snow.py` with `preprocess_snow_fromclim.py` in  `preprocess_era.sh`, to use (already generated) snow climatology instead of JRA55 data

### 2. WRF Preprocessing System (WPS)

We execute two WPS runs for each month of downscaling data, in folders `WPSYYMM_C` and `WPSYYYYMM_B`. Each future 2-day run of WRF with 6 h of spin-up time has its own unique WPS folder to use. Start dates betweent the 1st and the 10th of the month use `WPSYYYYMM_B`. Between the 11th and the 25th, use `WPSYYYYMM_C`. Between the 25th and month-end (whichever day that is), use the *next* month's `WPSYYYYMM_B` folder. The scripts select the correct WPS folder automatically (including correct handling of leap years). 

For a manually generated run, use `launch_wps_bridgeS.sh YYYYMM` to generate a WPS run for the `_B` folder for that year/month combination, and `launch_wps_monthS.sh YYYYMM` for the `_C` folder. These use `slurm` to submit a job to chinook. There are versions of these scripts without the `S` in the legacy scripts folder, which run on the login node. But a) `metgrid.exe` is parallelized, so using SLURM represents a speedup and b) the process is very demanding in memory, so runnin multiple WPS processes on the login node in production isn't good practice.

The WPS scripts call `generate_namelist.py` to generate the correct namelist. 

### 3. WRF

A WRF run for a 2-day run (54h including 6h spin-up starting at 18:00 UTC the day before the nominal start day) is `launch_wrf.sh [datestamp] [WPS folder] [timestep]`. 

`[timestep]` is optional and when present will kick of a debugging run in which files are not auto-archived. This is mostly used for re-running failed run with a smaller time step. 

`[datestamp]` is of the form `YYMMDD`, eg. `740402` for the run for April 2-3, 1974 or `051115` for May 11-12, 2005. This will also be the name of the folder the `wrfout` and then data extraction files will be generated

`[WPS Folder]` is of the form `WPSYYYYMM_B` or `WPSYYYYMM_C`. 

This script will 
  - create a folder for this WRF run
  - link the correct `met_em` files
  - generate a namelist (using `generate_namelist.py`) and SLURM script
  - submit the slurm script

The SLURM script also will run the variable extraction script (see below) once the WRF run has completed. This is necessary because it would take too long on the login node, especially if multiple process run simultaneously. 

The Python script `launch_wrf.py` can be used to launch a whole month's worth of WRF processes. 

### 4. Variable extraction

The variable extraction script `extract_vars.py` is run to turn the `wrfout` files into daily outputs containing a pre-defined subset of variables, with one file for each domain. (So typically 4 NetCDF output files for a 2-day run on 2 nested domains.) It's usually run as `extract_vars.py -w [WRF directory]` and figures out the correct dates automatically. 

Some conventions: Variables that are just taken from the `wrfout` files and written out (except for possibly interpolation to pressure levels) are kept in all-uppercase. Variables that are at least somewhat transformed are in lowercase. 

Some transformations are:

  - Splits up `wspd_wdir10` into `wspd10` and `wdir10`
  - Splits up `uvmet10` into `u10` and `v10`
  - Splits up `uvmet` into `u` and `v`
  - Renames `wa` to `w` for consistency
  - Interpolates all 4D atmospheric variables to the predefined list of pressure levels
  - Aggregates the variables `rainnc`, `rainc`, `acsnow` to hourly accumulation
  - Adds metadata and NetCDF compression

### 5. Automation & cleanup

*TODO: Write about `crontab` configuration and cleanup scripts *

### 6. Prerequisites & housekeeping

*TODO: Write about `status.feather` and how it is used and updated.*



