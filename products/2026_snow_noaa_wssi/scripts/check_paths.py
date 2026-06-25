"""Pre-flight check: verify source data completeness for both domains and
output directory writability before running compute_snow_climatologies.py.
"""

import calendar
from pathlib import Path

YEAR_START = 1981
YEAR_END = 2010
RESOLUTIONS = (4, 12)
MONTHS = [str(m).zfill(2) for m in range(1, 13)]
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def check_source_files(resolution: int) -> bool:
    """Verify every 1981-2010 month has the expected number of daily files.

    Parameters
    ----------
    resolution : int
        Domain resolution in km (4 or 12).

    Returns
    -------
    bool
        True if every month in range has the expected file count.
    """
    source_dir = Path(f"/import/beegfs/CMIP6/wrf_era5/{resolution:02d}km/")
    filepattern = f"era5_wrf_dscale_{resolution}km"
    if not source_dir.is_dir():
        print(f"  MISSING source directory: {source_dir}")
        return False
    ok = True
    for yr in range(YEAR_START, YEAR_END + 1):
        for mth in MONTHS:
            expected = calendar.monthrange(yr, int(mth))[1]
            fpths = sorted((source_dir / str(yr)).glob(f"{filepattern}_{yr}-{mth}*.nc"))
            if len(fpths) != expected:
                print(f"  {yr}-{mth}: expected {expected} files, found {len(fpths)}")
                ok = False
    return ok


def check_output_dir() -> bool:
    """Verify the output directory exists and is writable.

    Returns
    -------
    bool
        True if OUTPUT_DIR exists and a test file can be written to it.
    """
    if not OUTPUT_DIR.is_dir():
        print(f"  MISSING output directory: {OUTPUT_DIR}")
        return False
    probe = OUTPUT_DIR / ".write_test"
    try:
        probe.write_text("ok")
        probe.unlink()
    except OSError as exc:
        print(f"  output directory not writable: {OUTPUT_DIR} ({exc})")
        return False
    return True


if __name__ == "__main__":
    results = {}
    for res in RESOLUTIONS:
        print(f"Checking {res}km source files ({YEAR_START}-{YEAR_END})")
        results[res] = check_source_files(res)
        print("  OK" if results[res] else "  FAILED")

    print(f"Checking output directory {OUTPUT_DIR}")
    results["output"] = check_output_dir()
    print("  OK" if results["output"] else "  FAILED")

    if not all(results.values()):
        raise SystemExit(1)
    print("All checks passed.")
