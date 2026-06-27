# dyndowntools

Code created for dynamical downscaling project, IARC/CASC 2022-2026
Chris Waigl - cwaigl@alaska.edu

## Overview

The repo is organized around three task areas under `tasks/`, plus shared/cross-cutting code at the root:

 - [`tasks/dsworkflow/`](/tasks/dsworkflow/): orchestrates all aspects of the ERA5/WRF downscaling process — see [`tasks/dsworkflow/README.md`](/tasks/dsworkflow/README.md) for details (also the subject a [Zenodo code publication](https://zenodo.org/records/20808364))
 - [`tasks/extraction/`](/tasks/extraction/): ERA5/WRF variable extraction tasks
 - [`tasks/evaluation/`](/tasks/evaluation/): station-comparison and regridding evaluation against ACIS/Daymet data and other evaluation tasks
 - [`src/dyndowntools/`](/src/dyndowntools/): the installable shared package
 - [`config/`](/config/): files relating to the domain configuration and other global
 - [`Jupyter_Notebooks/`](/Jupyter_Notebooks/): cross-cutting exploratory notebooks 

One-time setup per clone: notebooks are kept output-light via an `nb-clean` git filter. Run once:
```
git config filter.nb-clean.clean 'pixi run nb-clean clean --remove-empty-cells --preserve-cell-outputs'
git config filter.nb-clean.required true
```
(the `.gitattributes` mapping itself is tracked; the filter *command* is not, by git's design, so this one line is needed per clone.)

## License

All code is open source. The MIT license in the [`LICENSE`](/LICENSE) file applies where not otherwise indicated. The data processing code under [`tasks/dsworkflow`](/tasks/dsworkflow) is licensed under a [Creative Commons CC0 1.0 Universal License](https://creativecommons.org/publicdomain/zero/1.0/) as required by the U.S. Geological Service. The license deed is available also in [`tasks/dsworkflow/LICENSE.md`](/tasks/dsworkflow/LICENSE.md)