### TBD

with open("wrfdir_fordeletion.txt", 'r') as src:
    for fn in src:
        shutil.rmtree((here.parent / 'WRF' / fn.rstrip()))