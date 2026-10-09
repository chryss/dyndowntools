"""Backfill CF coordinate attributes on XLAT/XLONG in existing daily output files.

Files written by extract_vars.py before the mid-2026 update (2026-07-14) lack
units/standard_name/long_name on XLAT and XLONG. Attributes are edited in place
(no data rewrite); files already carrying the attributes are skipped.
"""

import argparse
import logging
import os
import stat
from multiprocessing import Pool
from pathlib import Path

from netCDF4 import Dataset

OUTROOT = Path("/import/SNAP/cwaigl/wrf_era5")
SUBDIRS = ["04km", "12km"]
FILEGLOB = "era5_wrf_dscale_*.nc"
NPROC = 8
# keep in sync with extract_vars.py
COORD_ATTRS = {
    "XLONG": {"units": "degrees_east", "standard_name": "longitude", "long_name": "longitude"},
    "XLAT": {"units": "degrees_north", "standard_name": "latitude", "long_name": "latitude"},
}


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns
    -------
    argparse.Namespace
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-r", "--root", type=Path, default=OUTROOT,
                        help="root directory holding the resolution subdirectories")
    parser.add_argument("-y", "--years", nargs="+", default=None,
                        help="restrict to these year subdirectories (default: all)")
    parser.add_argument("-n", "--dry-run", action="store_true",
                        help="report files needing updates without modifying them")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="switch on debugging output")
    return parser.parse_args()


def find_files(root: Path, years: list[str] | None) -> list[Path]:
    """Collect daily output files under the resolution subdirectories.

    Parameters
    ----------
    root : Path
        Root directory containing `SUBDIRS`.
    years : list of str or None
        Year subdirectories to include; all if None.

    Returns
    -------
    list of Path
        Sorted output file paths.
    """
    files = []
    for sub in SUBDIRS:
        yeardirs = [root / sub / yr for yr in years] if years else sorted((root / sub).glob("[0-9]" * 4))
        for yeardir in yeardirs:
            files.extend(yeardir.glob(FILEGLOB))
    return sorted(files)


def missing_attrs(ds: Dataset) -> dict[str, dict[str, str]]:
    """Return the coordinate attributes absent or differing in an open dataset.

    Parameters
    ----------
    ds : netCDF4.Dataset
        Open dataset.

    Returns
    -------
    dict
        Variable name -> {attribute: value} still to be set.
    """
    todo = {}
    for var, attrs in COORD_ATTRS.items():
        if var not in ds.variables:
            raise KeyError(f"{var} not found")
        current = ds.variables[var].__dict__
        diff = {k: v for k, v in attrs.items() if current.get(k) != v}
        if diff:
            todo[var] = diff
    return todo


def process_file(fn: Path, dry_run: bool = False) -> str:
    """Add missing coordinate attributes to one file in place.

    File permissions and modification time are restored afterwards.

    Parameters
    ----------
    fn : Path
        NetCDF file to update.
    dry_run : bool, optional
        If True, only check; do not modify.

    Returns
    -------
    str
        One of "ok" (already compliant), "updated", "would update", or "error".
    """
    try:
        with Dataset(fn, "r") as ds:
            todo = missing_attrs(ds)
        if not todo:
            return "ok"
        if dry_run:
            logging.debug(f"{fn.name}: would set {todo}")
            return "would update"
        st = fn.stat()
        os.chmod(fn, st.st_mode | stat.S_IWUSR)
        try:
            with Dataset(fn, "r+") as ds:
                for var, attrs in todo.items():
                    ds.variables[var].setncatts(attrs)
        finally:
            os.chmod(fn, stat.S_IMODE(st.st_mode))
            os.utime(fn, ns=(st.st_atime_ns, st.st_mtime_ns))
        logging.debug(f"{fn.name}: updated")
        return "updated"
    except Exception as err:
        logging.error(f"{fn}: {err}")
        return "error"


def _init_logging(level: int) -> None:
    # workers start via forkserver and don't inherit the parent's logging config
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")


def _worker(item: tuple[Path, bool]) -> tuple[Path, str]:
    return item[0], process_file(*item)


def main() -> None:
    """Run the backfill over all matching files."""
    args = parse_arguments()
    loglevel = logging.DEBUG if args.debug else logging.INFO
    _init_logging(loglevel)
    files = find_files(args.root, args.years)
    logging.info(f"{len(files)} files found under {args.root}")

    counts: dict[str, int] = {}
    with Pool(NPROC, initializer=_init_logging, initargs=(loglevel,)) as pool:
        for i, (fn, status) in enumerate(
                pool.imap_unordered(_worker, [(fn, args.dry_run) for fn in files], chunksize=16), 1):
            counts[status] = counts.get(status, 0) + 1
            if i % 1000 == 0:
                logging.info(f"{i}/{len(files)} processed: {counts}")
    logging.info(f"done: {counts}")


if __name__ == "__main__":
    main()
