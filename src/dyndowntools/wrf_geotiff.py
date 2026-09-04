"""Write WRF-grid data to GeoTIFF in its native polar-stereographic CRS.

rioxarray's raster export needs x/y as indexed, north-up dimension
coordinates in projection units; the daily era5_wrf_dscale files only have
south_north/west_east dims and geographic XLAT/XLONG, so this reprojects onto
the WRF grid via wrf_projection.attach_projected_coords before handing off.
"""
from __future__ import annotations

from pathlib import Path

import rioxarray  # noqa: F401  (registers the .rio accessor)
import xarray as xr

from dyndowntools.wrf_projection import attach_projected_coords, wrf_crs


def _to_raster_ready(da: xr.DataArray) -> xr.DataArray:
    """Reindex a WRF-grid DataArray onto north-up x/y dimension coordinates."""
    if "x" not in da.coords or "y" not in da.coords:
        da = attach_projected_coords(da)
    da = da.swap_dims({"west_east": "x", "south_north": "y"})
    da = da.drop_vars([c for c in ("XLAT", "XLONG") if c in da.coords])
    da = da.sortby("y", ascending=False)  # north-up: row 0 = max y
    return da.rio.write_crs(wrf_crs())


def to_geotiff(da: xr.DataArray, out_path: Path | str, **to_raster_kwargs) -> Path:
    """Write a WRF-grid DataArray to a GeoTIFF in the native polar-stereographic CRS.

    Parameters
    ----------
    da : xr.DataArray
        Must have ``south_north``/``west_east`` dims, plus either XLAT/XLONG
        coordinates (reprojected on the fly) or existing ``x``/``y``
        projected coordinates (e.g. from a prior `attach_projected_coords`
        call). Size-1 dimensions (e.g. a single-value percentile axis) are
        squeezed out automatically. Of what remains, at most one additional
        dimension (e.g. Time) is allowed -- it is written as GeoTIFF bands.
        Data with more extra dims (e.g. both Time and a soil-layer dimension)
        must be sliced or looped over by the caller first.
    out_path : Path or str
        Destination .tif path; parent directory must already exist.
    **to_raster_kwargs
        Passed through to ``DataArray.rio.to_raster`` (e.g. ``compress``,
        ``dtype``, ``nodata``).

    Returns
    -------
    Path
        `out_path`, for chaining.

    Raises
    ------
    ValueError
        If `da` has more than one dimension besides south_north/west_east.
    """
    da = da.squeeze()
    extra_dims = [d for d in da.dims if d not in ("south_north", "west_east")]
    if len(extra_dims) > 1:
        raise ValueError(
            f"to_geotiff handles at most one non-spatial dimension (band axis), "
            f"got {extra_dims}. Select/loop over the extra dimensions first."
        )

    out_path = Path(out_path)
    raster = _to_raster_ready(da)
    raster = raster.transpose(*extra_dims, "y", "x")
    raster.rio.to_raster(out_path, **to_raster_kwargs)
    return out_path
