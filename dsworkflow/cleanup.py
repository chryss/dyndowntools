### TBD

with open(  , 'r') as src:
    for fn in src:
        shutil.rmtree((here.parent / 'WRF' / fn.rstrip()))