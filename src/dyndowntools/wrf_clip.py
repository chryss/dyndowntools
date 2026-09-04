"""Clip WRF-grid data to a vector polygon, via the WRF stereographic CRS.

Computing the clip (reprojecting the shapefile, finding the bounding-box
index range, rasterizing the polygon mask) is done once against a reference
dataset and reused across many files with the same static grid -- cheap
.isel()/.where() calls -- rather than repeating the reprojection/rasterize
step per file.
"""
from __future__ import annotations

from dataclasses import dataclass

import geopandas as gpd
import numpy as np
import rioxarray  # noqa: F401  (registers the .rio accessor)
import xarray as xr

from dyndowntools.wrf_projection import attach_projected_coords, wrf_crs


@dataclass
class ClipInfo:
    """Reusable clip definition for one shapefile against one WRF grid."""

    south_north: slice
    west_east: slice
    mask: xr.DataArray


def build_clip_info(reference_ds: xr.Dataset, shapefile_path: str, buffer_cells: int = 2) -> ClipInfo:
    """Compute the bounding-box index range and polygon mask for a shapefile.

    Parameters
    ----------
    reference_ds : xr.Dataset
        Any dataset on the target WRF grid, with south_north/west_east dims
        and XLAT/XLONG coordinates (or existing x/y projected coordinates).
        Only its grid geometry is used, so any single day's file will do --
        the grid is static across the whole record.
    shapefile_path : str
        Path to a vector file readable by geopandas (any CRS; reprojected
        into the WRF CRS internally).
    buffer_cells : int
        Extra grid cells kept around the shapefile's bounding box, so the
        polygon mask isn't clipped by an overly tight index range.

    Returns
    -------
    ClipInfo
        south_north/west_east slices for a cheap `.isel()` pre-crop, and a
        boolean mask (True inside the polygon) on that cropped subgrid.
    """
    ds = reference_ds
    if "x" not in ds.coords or "y" not in ds.coords:
        ds = attach_projected_coords(ds)

    gdf = gpd.read_file(shapefile_path).to_crs(wrf_crs())
    minx, miny, maxx, maxy = gdf.total_bounds

    x, y = ds["x"].values, ds["y"].values
    ix = np.where((x >= minx) & (x <= maxx))[0]
    iy = np.where((y >= miny) & (y <= maxy))[0]
    we_slice = slice(max(ix.min() - buffer_cells, 0), min(ix.max() + buffer_cells, len(x) - 1) + 1)
    sn_slice = slice(max(iy.min() - buffer_cells, 0), min(iy.max() + buffer_cells, len(y) - 1) + 1)

    # Build the mask from a single 2D coordinate array (XLAT), not the full
    # reference_ds -- clipping a whole Dataset would carry along any extra
    # dims (Time, soil layers, ...) its data variables happen to have.
    cropped = ds["XLAT"].isel(south_north=sn_slice, west_east=we_slice)
    mask = (
        cropped.swap_dims({"west_east": "x", "south_north": "y"})
        .rio.write_crs(wrf_crs())
        .rio.clip(gdf.geometry, gdf.crs, drop=False, invert=False, all_touched=False)
        .notnull()
        .swap_dims({"x": "west_east", "y": "south_north"})
        .reset_coords(drop=True)
    )
    mask.attrs = {}

    return ClipInfo(south_north=sn_slice, west_east=we_slice, mask=mask)


def apply_clip(ds: xr.Dataset | xr.DataArray, clip: ClipInfo) -> xr.Dataset | xr.DataArray:
    """Crop and mask a dataset/array to a previously computed ClipInfo.

    Parameters
    ----------
    ds : xr.Dataset or xr.DataArray
        Data on the same WRF grid `clip` was built from.
    clip : ClipInfo
        Result of `build_clip_info`.

    Returns
    -------
    xr.Dataset or xr.DataArray
        Cropped to the bounding box and masked to NaN outside the polygon.
    """
    return ds.isel(south_north=clip.south_north, west_east=clip.west_east).where(clip.mask)
