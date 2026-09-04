"""Polar-stereographic projection helpers for the downscaled ERA5/WRF grid.

The daily era5_wrf_dscale_*.nc files carry XLAT/XLONG (WGS84, cell centers) but
no projected x/y coordinates or CRS global attrs -- only a per-variable string
attribute (e.g. "PolarStereographic(stand_lon=-152.0, ...)"). The grid *is*
regular in this projection (verified: reprojecting XLAT/XLONG on a real 4km
file gives dx = dy = 4000.0 m +/- ~0.5 m), so projected coordinates can always
be reconstructed from XLAT/XLONG rather than relying on external grid files.

Confirmed against xwrf's own CRS derivation on a met_em file with full WRF
projection global attrs (stand_lon=-152, moad_cen_lat=64, truelat1=64,
pole_lat=90, spherical earth radius 6370000 m).
"""
from __future__ import annotations

import numpy as np
import xarray as xr
from pyproj import CRS, Transformer

WRF_STEREO_PROJ4 = (
    "+proj=stere +lat_0=90 +lat_ts=64 +lon_0=-152 +x_0=0 +y_0=0 "
    "+R=6370000 +units=m +no_defs=True"
)


def wrf_crs() -> CRS:
    """Return the polar-stereographic CRS used by the downscaled ERA5/WRF grid."""
    return CRS.from_proj4(WRF_STEREO_PROJ4)


def project_latlon(lat: np.ndarray, lon: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Project WGS84 lat/lon arrays into WRF polar-stereographic x/y (meters).

    Parameters
    ----------
    lat, lon : np.ndarray
        Arrays of the same shape, in degrees (WGS84).

    Returns
    -------
    x, y : np.ndarray
        Projected coordinates in meters, same shape as the inputs.
    """
    transformer = Transformer.from_crs("EPSG:4326", wrf_crs(), always_xy=True)
    x, y = transformer.transform(lon, lat)
    return x, y


def attach_projected_coords(
    ds: xr.Dataset | xr.DataArray, rtol: float = 1e-3
) -> xr.Dataset | xr.DataArray:
    """Add 1D projected ``x``/``y`` coordinates derived from XLAT/XLONG.

    Reprojects the 2D XLAT/XLONG cell-center coordinates into the WRF
    stereographic CRS, then collapses them to 1D ``x`` (west_east) and ``y``
    (south_north) coordinates after checking the grid is regular -- i.e. that
    x is constant along each column and y constant along each row, to within
    `rtol` of the grid spacing.

    Parameters
    ----------
    ds : xr.Dataset or xr.DataArray
        Must have 2D ``XLAT``/``XLONG`` coordinates on dims
        (south_north, west_east).
    rtol : float
        Maximum allowed relative deviation (fraction of grid spacing) of x
        along columns / y along rows, before raising. Default 1e-3 comfortably
        covers float32 XLAT/XLONG rounding noise (~1 m on a 4000 m grid)
        while still catching a genuinely non-regular grid.

    Returns
    -------
    xr.Dataset or xr.DataArray
        Input with ``x`` and ``y`` 1D coordinates added (meters, WRF CRS).

    Raises
    ------
    ValueError
        If the reprojected grid is not regular within `rtol`.
    """
    lat, lon = ds["XLAT"].values, ds["XLONG"].values
    x2d, y2d = project_latlon(lat, lon)

    dx = np.diff(x2d, axis=1).mean()
    dy = np.diff(y2d, axis=0).mean()
    x = x2d.mean(axis=0)
    y = y2d.mean(axis=1)

    if np.abs(x2d - x).max() > rtol * abs(dx):
        raise ValueError("Reprojected x is not constant along columns; grid is not regular.")
    if np.abs(y2d - y[:, None]).max() > rtol * abs(dy):
        raise ValueError("Reprojected y is not constant along rows; grid is not regular.")

    return ds.assign_coords(
        x=("west_east", x),
        y=("south_north", y),
    )
