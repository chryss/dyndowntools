"""Command-line entry points for dyndowntools.

Currently just nc-to-geotiff (see [project.scripts] in pyproject.toml): write
one variable from a WRF-grid NetCDF file to a GeoTIFF. Opens the file,
selects the variable, applies any --sel/--isel dimension selections needed to
get down to at most one non-spatial dimension (which becomes GeoTIFF bands),
and writes via wrf_geotiff.to_geotiff().
"""
from __future__ import annotations

import argparse
from pathlib import Path

import xarray as xr

from dyndowntools.wrf_geotiff import to_geotiff


def parse_isel(pairs: list[str]) -> dict[str, int]:
    """Parse repeated "dim=index" strings into an isel-ready dict.

    Parameters
    ----------
    pairs : list[str]
        Strings of the form "dim=index", e.g. ["Time=0", "soil_layers_stag=1"].

    Returns
    -------
    dict[str, int]
        Mapping from dimension name to integer index.
    """
    isel = {}
    for pair in pairs:
        dim, _, index = pair.partition("=")
        if not _:
            raise ValueError(f"--isel expects 'dim=index', got {pair!r}")
        isel[dim] = int(index)
    return isel


def _coerce(value: str) -> float | str:
    """Convert a CLI value string to float if possible, else leave it as str."""
    try:
        return float(value)
    except ValueError:
        return value


def parse_sel(pairs: list[str]) -> dict[str, float | str]:
    """Parse repeated "dim=value" strings into a sel-ready dict (label-based).

    Parameters
    ----------
    pairs : list[str]
        Strings of the form "dim=value", e.g. ["percentile=0.9", "season=DJF"].

    Returns
    -------
    dict[str, float | str]
        Mapping from dimension name to coordinate label (float where parseable,
        otherwise the raw string).
    """
    sel = {}
    for pair in pairs:
        dim, _, value = pair.partition("=")
        if not _:
            raise ValueError(f"--sel expects 'dim=value', got {pair!r}")
        sel[dim] = _coerce(value)
    return sel


def apply_sel(da: xr.DataArray, sel: dict[str, float | str]) -> xr.DataArray:
    """Apply label-based selection, using nearest-match only for numeric labels.

    Numeric coordinates (e.g. a percentile threshold) use method="nearest" to
    tolerate float precision; string coordinates (e.g. a season label) require
    an exact match, since "nearest" is undefined for them.
    """
    for dim, value in sel.items():
        method = "nearest" if isinstance(value, float) else None
        da = da.sel({dim: value}, method=method)
    return da


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for NetCDF-to-GeoTIFF conversion."""
    parser = argparse.ArgumentParser(
        description="Write one variable from a WRF-grid NetCDF file to a GeoTIFF."
    )
    parser.add_argument("--input", type=Path, required=True, help="Source NetCDF file.")
    parser.add_argument("--variable", required=True, help="Variable to extract.")
    parser.add_argument("--output", type=Path, required=True, help="Destination .tif path.")
    parser.add_argument(
        "--sel",
        action="append",
        default=[],
        metavar="DIM=VALUE",
        help=(
            "Select a single coordinate label along a dimension before writing, "
            "e.g. --sel percentile=0.9 or --sel season=DJF. Repeatable. Numeric "
            "values match nearest (float precision); others must match exactly. "
            "Needed when the variable has more than one non-spatial dimension, "
            "since to_geotiff allows at most one (used as the band axis)."
        ),
    )
    parser.add_argument(
        "--isel",
        action="append",
        default=[],
        metavar="DIM=INDEX",
        help=(
            "Select a single index along a dimension before writing, e.g. "
            "--isel Time=0. Repeatable. Applied after --sel."
        ),
    )
    parser.add_argument("--compress", default=None, help="GeoTIFF compression (e.g. deflate).")
    parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite --output if it already exists."
    )
    return parser.parse_args()


def main() -> None:
    """Convert one variable from a NetCDF file to a GeoTIFF."""
    args = parse_args()
    if args.output.exists() and not args.overwrite:
        print(f"{args.output} already exists, skipping (use --overwrite to redo).")
        return

    ds = xr.open_dataset(args.input)
    da = ds[args.variable]
    sel = parse_sel(args.sel)
    if sel:
        da = apply_sel(da, sel)
    isel = parse_isel(args.isel)
    if isel:
        da = da.isel(isel)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    to_raster_kwargs = {"compress": args.compress} if args.compress else {}
    out_path = to_geotiff(da, args.output, **to_raster_kwargs)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
