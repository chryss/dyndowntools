# dyndowntools

Code created for dynamical downscaling project, IARC/CASC 2022-2024
Chris Waigl - cwaigl@alaska.edu

## Overview

The repo's content are as follows:

 - `config/`: files relating to the domain configuration as well as miscellaneous configuration files
 - `dsworkflow/`: the code that orchestrates all aspects of the downscaling process (see below for details)
 - `dsworkflow_legacy/`: previous iterations of workflow code, some inherited from others
 - `dyndowntools/`: placeholder for importable package
 - `Jupyter_Notebooks/`: exploratory or analysis code, as well as visualizations, to be run interactively
 - `scripts/`: stand-alone scripts
 - `dyndown_environment.yml`: environment file for `conda`

## Workflow components

### 1. Download and preprocess ERA5 files

Manually run `era5_download.sh [YEAR] [MONTH]` to download and preprocess ERA5 input files for a single month. For a whole year, edit/check script to enable list of months and run it `era5_download.sh [YEAR]`. Similarly, multiple years can be downloaded at once. 

The script first calls `rda_month.py YYYYMM`, which uses joblib to paralellize / accelerate download.

Once a month's worth of ERA5 data is downloaded, `era5_download.sh` calls and runs `preprocess_era.sh`. This script does two things: 

  - using `cdo` from the command line, it replaces negative values in the soil moisture files with a value of 0.01.
  - calling `preprocess_snow.py` on the snow input data it creates combined synthetic snow dataset including the (already downloaded) JRA55 data. **NOTE:** When working on data from before October 1958, replace  `preprocess_snow.py` with `preprocess_snow_fromclim.py` in  `preprocess_era.sh`, to use the (already generated) snow climatology instead of JRA55 data

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

For development and debugging purposes, the above steps can be run manually. But in production, the sequence WPS --> WRF --> data archiving needs to be automated. This is implemented through the following `crontab` entry:

```
# save synthetic snow
54 1 * * * /bin/bash /center1/DYNDOWN/cwaigl/ERA5_WRF/scripts/cleanup_snow.sh

# archive datafiles and clean up WRF directories
4  1,5,9,13,17,21 * * * /bin/bash /center1/DYNDOWN/cwaigl/ERA5_WRF/scripts/cleanup_datafiles.sh   

# check queue and add to it
19,49 * * * * /bin/bash /center1/DYNDOWN/cwaigl/ERA5_WRF/scripts/manage_queue.sh 
```

Details on these three scripts:

`cleanup_snow.sh` moves any new combined snow files to a storage location. This runs once every night. 

`cleanup_datafiles.sh` executes multiple actions that have for combined effect to move all extracted output data files to a storage location and delete the directories of completed WRF runs (including the `wrfout` files). In a first step, `move_datafiles.py` checks all subdirectories of the WRF working directory for completed WRF runs. For all completed runs, the output files are moved to a staging area and the directory marked for deletion via the file `status/wrfdir_fordeletion.txt`. Then the files are moved to the storage location. When the files have successfully been moved, the marked directories are deleted. This is run every 4h to keep storage use low and data moved.

`manage_queue.sh` is a wrapper around the Python script `run_queue.py`. This script checks the queue (see `check_queue.py`) for how many tasks are running and queued, respectively. If fewer than a certain number (default: 10) are queued, the next N (default: 3) lines of commands from `status/taskqueue.txt` are executed, which adds tasks to the queue. See below for how this file gets replenished with tasks.  

So the overall recipe for running production is as follows:

  - Run `era5_download.sh [YEAR]` for the two or three years before the current status (by default, we run backwards starting in 2023). Then manually check completeness of download (by watching error messages and counting downloaded files). These checks prevent failed incomplete WPS runs that often show up only at the WRF stage, so it saves time to check initially.
  - Run `addtoqueue.py` and once satisfied, pipe the output into `status/taskqueue.txt`. This script generates a year's worth of launch commands for WPS and WRF runs. For each month, there are two WPS runs  (for `_C` and `_B` folders) and one `launch_wrf.py` command for a month's worth of WRF runs. The WPS runs go from December to January (there is an option to reverse the order and run the dataset forward in time), and the WRF runs lag 4 months behind the WPS runs, so they go from April of the previously-run (=next in time) year to May. As long as there are tasks available in `status/taskqueue.txt`, they can be picked up and executed (and removed from the queue) by `manage_queue.sh`, run on the crontab. 
  - Once a year's worth of WRF runs is complete, check the output files in their final location. Approximately run per year typically terminates prematurely and needs to be re-run with a shorter timestep, using `launch_wrf.sh YYMMDD [WPSFOLDER] 30` (for 30s step). If entire WRF runs fail, the issue may be incomplete `met_em` files in the correspondin WPS folder, which is typically caused by incomplete downloads. 
  - Once the whole year's (or at least several months) worth of output is found satisfactory and quality-checked, delete the WPS folders and original ERA5 downloads. The synthetic combined snow will have been archived off before this point automatically. 

### 6. Prerequisites & housekeeping

The scripts presume the availability of a conda environment named `dyndown` with all the required Python dependencies installed. Use the provided `dyndown_environment.yml` file to install such an environment. Also, modules and paths are specific to the HPC environment `chinook` provided by the University of Alaska Fairbanks Research Computing Systems team. 

The mapping of datestamps for WRF runs to WPS folders is managed via the file `status.feather` in the `status/` folder. It can be generated and updated for the desired daterange using the `taskcontrol.ipynb` Jupyter Notebook. 