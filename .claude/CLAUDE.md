# Repo rules

- Never launch WRF (the weather model itself).
- Never launch WPS (WRF Preprocessing System) runs.
- Never run `deploy.py`, or otherwise sync `tasks/dsworkflow/processing_code/` out to `BASEDIR/scripts` (the live HPC runtime copy).

Any of the above only if the user explicitly overrules this for that specific instance — not implied by "verify the fix" or similar.
