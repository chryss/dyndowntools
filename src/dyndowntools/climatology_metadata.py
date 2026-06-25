"""CF-compliant metadata for monthly climatologies (CF Conventions section 7.4).

Only the monthly-climatology-over-multiple-years case is implemented (e.g. the
mean of all Januaries 1981-2010). Seasonal or sub-daily climatologies (CF
examples 7.8, 7.10, 7.12) use a different bounds construction and would need
their own function.
"""

import numpy as np
import pandas as pd
import xarray as xr

CONVENTIONS = "CF-1.8"
INSTITUTION = "University of Alaska Fairbanks, International Arctic Research Center (IARC)"
CREATOR_NAME = "Chris Waigl"
CREATOR_EMAIL = "cwaigl@alaska.edu"


def _next_month_start(year: int, month: int) -> pd.Timestamp:
    """First day of the month after `month` in `year`, wrapping December into January."""
    return pd.Timestamp(year + 1, 1, 1) if month == 12 else pd.Timestamp(year, month + 1, 1)


def add_monthly_climatology_metadata(
    ds: xr.Dataset,
    climatology_start: int,
    climatology_end: int,
    reference_year: int,
    within_year_statistic: str,
) -> xr.Dataset:
    """Add CF-compliant monthly-climatology metadata (CF Conventions section 7.4).

    Replaces an integer ``month`` coordinate (1-12) with a climatological
    ``time`` coordinate (month starts in `reference_year`) and a
    ``climatology_bounds`` variable spanning each calendar month's full
    `climatology_start`-`climatology_end` range, following CF's worked
    example for decadal-average climatologies generalized to 12 months.
    Sets ``cell_methods`` on every data variable, standard_name/units on
    XLAT and XLONG, and Conventions plus author/organization globals.

    Parameters
    ----------
    ds : xr.Dataset
        Dataset with an integer ``month`` coordinate (values 1-12, as
        produced by ``groupby("time.month").mean()``) and XLAT/XLONG
        coordinates.
    climatology_start, climatology_end : int
        First and last calendar year averaged into the climatology (e.g.
        1981, 2010).
    reference_year : int
        Calendar year used to date the nominal ``time`` coordinate values
        (month starts). CF requires only that these be "representative",
        not tied to any real year in the climatology.
    within_year_statistic : str
        The statistic computed within each year before averaging across
        years (e.g. "mean", "maximum", "sum"), used to build each data
        variable's ``cell_methods``, e.g. "time: maximum within years
        time: mean over years".

    Returns
    -------
    xr.Dataset
        Dataset with CF-compliant climatological time metadata.
    """
    months = ds["month"].values
    month_starts = pd.date_range(f"{reference_year}-01-01", periods=12, freq="MS")[months - 1]
    bounds = np.array(
        [
            (pd.Timestamp(climatology_start, month, 1), _next_month_start(climatology_end, month))
            for month in months
        ]
    )

    ds = ds.rename({"month": "time"})
    ds = ds.assign_coords(time=("time", month_starts))
    ds["climatology_bounds"] = (("time", "nv"), bounds)

    epoch_units = f"days since {reference_year}-01-01"
    ds["time"].encoding.update(units=epoch_units, calendar="standard", dtype="int32")
    ds["climatology_bounds"].encoding.update(units=epoch_units, calendar="standard", dtype="int32")
    ds["time"].attrs.update(
        standard_name="time", long_name="time", axis="T", climatology="climatology_bounds"
    )

    cell_methods = f"time: {within_year_statistic} within years time: mean over years"
    for var in ds.data_vars:
        if var != "climatology_bounds":
            ds[var].attrs["cell_methods"] = cell_methods

    ds["XLAT"].attrs.update(standard_name="latitude", long_name="latitude", units="degrees_north")
    ds["XLONG"].attrs.update(standard_name="longitude", long_name="longitude", units="degrees_east")

    ds.attrs.update(
        Conventions=CONVENTIONS,
        institution=INSTITUTION,
        creator_name=CREATOR_NAME,
        creator_email=CREATOR_EMAIL,
        description=f"Monthly climatology, {climatology_start}-{climatology_end}.",
    )
    return ds
