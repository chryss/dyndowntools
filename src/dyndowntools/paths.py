"""Resolve canonical data-source paths from config/paths.yaml.

Each named resource lists candidate absolute paths in priority order.
`resolve` returns the first candidate that exists on the current host, since
some resources (e.g. wrf_era5_root) have independent copies on different
filesystems rather than a single stale-vs-current pair.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
PATHS_CONFIG = REPO_ROOT / "config" / "paths.yaml"


@lru_cache(maxsize=1)
def _load_config() -> dict:
    with open(PATHS_CONFIG) as f:
        return yaml.safe_load(f)


def resolve(name: str, user: str | None = None) -> Path:
    """Return the resolved path for a named resource in config/paths.yaml.

    Parameters
    ----------
    name : str
        Resource name, as defined in config/paths.yaml.
    user : str, optional
        Substituted for ``{user}`` placeholders in candidate paths;
        defaults to the ``USER`` environment variable.

    Returns
    -------
    Path
        For resources with ``must_exist: false`` (e.g. scratch dirs), the
        first candidate, unconditionally. Otherwise the first candidate that
        exists on this host.

    Raises
    ------
    KeyError
        If `name` is not defined in config/paths.yaml.
    FileNotFoundError
        If `must_exist` and none of the candidates exist on this host.
    """
    config = _load_config()
    if name not in config:
        raise KeyError(f"No path resource named '{name}' in {PATHS_CONFIG}")

    entry = config[name]
    user = user or os.environ.get("USER", "cwaigl")
    candidates = [
        Path(c.format(repo_root=REPO_ROOT, user=user)) for c in entry["candidates"]
    ]

    if not entry.get("must_exist", True):
        return candidates[0]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    tried = ", ".join(str(c) for c in candidates)
    raise FileNotFoundError(f"No candidate path exists for '{name}': tried {tried}")
