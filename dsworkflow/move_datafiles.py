from pathlib import Path
import argparse
import sys
import shutil
import datetime as dt

WRFDIR = "/center1/DYNDOWN/cwaigl/ERA5_WRF/WRF/"
OUTSUBDIR = 'staging'
LOCK = "move_local.lock"
LOCKDIR = "status"
PREFIX = "era5_wrf_dscale"
DONEFN = "wrfdir_fordeletion.txt"
MOVELOCKFILE = ".dontmove"

def parse_arguments():
    parser = argparse.ArgumentParser(description='Move files with extacted variables to staging area')
    parser.add_argument('-t', '--testing',
        help='run as testing',
        action='store_true')
    parser.add_argument('-d', '--delete',
        help='delete listed directories',
        action='store_true')
    return parser.parse_args()

def set_lock(lockpath):
    lockpath.touch()

def release_lock(lockpath):
    lockpath.unlink()

def get_year(datestr):
    twodigyear = int(datestr[:2])
    if twodigyear < 40:
        return str(2000 + twodigyear)
    return str(1900 + twodigyear)
    
def files_ready(dir):
    era5files = list(dir.glob(f"{PREFIX}*"))
    lockfiles = list(dir.glob(f"{MOVELOCKFILE}*"))
    # first condition: There are four outfiles
    cond1 = len(era5files) == 4
    if not cond1: return False
    # second condition: No locking against moving
    cond2 = len(lockfiles) == 0
    if not cond2: return False
    # third condition: the files were generated at least 5 min ago
    now = dt.datetime.now()
    cond3 = max(
        [(dt.datetime.fromtimestamp(item.stat().st_mtime) - now).seconds 
         for item in era5files]
    ) >= 300
    # both conditions need to be true
    return cond3 

if __name__ == '__main__':
    here = Path(__file__).resolve().parent
    lockpath = here / LOCKDIR / LOCK
    if lockpath.exists():
        sys.exit("Process is locked.")
    set_lock(lockpath)

    args = parse_arguments()

    if not args.delete:
        wrfpth = Path(WRFDIR)
        donelist = []
        for dir in sorted(wrfpth.glob('[0-9]'*6)):
            if files_ready(dir):
                if args.testing: 
                    print(dir)
                else:
                    for res in ['04', '12']:
                        for fpth in dir.glob(f"{PREFIX}_{res.replace('0', '')}km*"):
                            year = get_year(dir.stem)
                            if year not in fpth.stem:
                                if str(int(year) - 1) in fpth.stem:
                                    year = str(int(year) - 1)
                                elif str(int(year) + 1) in fpth.stem:
                                    year = str(int(year) + 1)
                                else:
                                    raise Exception(f"Can't find right year for {fpth} - its not {year}")
                            outdir = Path(WRFDIR) / OUTSUBDIR / f'{res}km' / year
                            outdir.mkdir(parents=True, exist_ok=True)
                            print(f"Moving {fpth} to {outdir}")
                            shutil.move(fpth, outdir / fpth.name)
                    donelist.append(dir.stem)
        if not args.testing:
            with open(here / LOCKDIR / DONEFN, "w") as dst:
                dst.write("\n".join(donelist))
                dst.write("\n")
    else:
        with open(here / LOCKDIR / DONEFN, "r") as src:
            for fn in src:
                if (
                    (here.parent / 'WRF' / fn.rstrip()).is_dir() and
                    len(fn.rstrip()) == 6):
                    print(f"Deleting {fn.rstrip()}")
                    try:
                        shutil.rmtree((here.parent / 'WRF' / fn.rstrip()))
                    except OSError as err:
                        print(f"There was an error trying to delete {fn.rstrip()}")
                        print("Check deletion file and proceed manually.")
                        print(err)
                        break
    release_lock(lockpath)
