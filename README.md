# dyndowntools

Code created for dynamical downscaling project, IARC/CASC 2022-2026
Chris Waigl - cwaigl@alaska.edu

## Overview

The repo is organized around three task areas under `tasks/`, plus shared/cross-cutting code at the root:

 - `tasks/dsworkflow/`: orchestrates all aspects of the ERA5/WRF downscaling process — see `tasks/dsworkflow/README.md` for details (also the subject of a separate Zenodo code publication)
 - `tasks/extraction/`: ERA5/WRF variable extraction and the wind-speed quantile/exceedance analysis (`scripts/`, `notebooks/`, `docs/`)
 - `tasks/evaluation/`: station-comparison and regridding evaluation against ACIS/Daymet data (`scripts/`, `notebooks/`, plus the `auxdata/`, `weatherstationdata/`, `working/`, `figures/`, `archive/` data directories)
 - `src/dyndowntools/`: the installable shared package (editable install via pixi)
 - `config/`: files relating to the domain configuration as well as miscellaneous configuration files
 - `Jupyter_Notebooks/`: cross-cutting exploratory notebooks not specific to one task area (case studies, snow/precip prototyping, visualization utilities)

One-time setup per clone: notebooks are kept output-light via an `nb-clean` git filter. Run once:
```
git config filter.nb-clean.clean 'pixi run nb-clean clean --remove-empty-cells --preserve-cell-outputs'
git config filter.nb-clean.required true
```
(the `.gitattributes` mapping itself is tracked; the filter *command* is not, by git's design, so this one line is needed per clone.)

## License

All code is open source. The MIT license in the `LICENSE` file applies where not otherwise indicated. The data processing code under `tasks/dsworkflow` is licensed under a [Creative Commons CC0 1.0 Universal License](https://creativecommons.org/publicdomain/zero/1.0/) as required by the U.S. Geological Service. The license deed is available also in `dsworkflow/LICENSE.md`