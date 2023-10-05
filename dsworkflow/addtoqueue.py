#!/usr/local/env python

YEAR = 1990

for ii in range(12, 0, -1):
    if (ii + 3) > 12:
        wrfmth = str(ii + 3 - 12).zfill(2)
        wrfyr = str(YEAR+1)
    else:
        wrfmth = str(ii + 3).zfill(2)
        wrfyr = str(YEAR)
    wpsmth = str(ii).zfill(2)
    wpsyr = str(YEAR)
    print(f"bash launch_wps_monthS.sh {wpsyr}{wpsmth}")
    print(f"bash launch_wps_bridgeS.sh {wpsyr}{wpsmth}")
    print(f"python launch_wrf.py -bb -ba {wrfyr}{wrfmth}")
