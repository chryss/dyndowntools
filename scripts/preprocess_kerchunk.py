from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import re
from pathlib import Path

import fsspec
import ujson
from dask import compute, delayed
from dask.diagnostics import ProgressBar
from kerchunk.combine import MultiZarrToZarr
from kerchunk.hdf import SingleHdf5ToZarr


DEFAULT_KEEP_PREFIXES = [
    "wspd10",
    "T2",
    "XLAT",
    "XLONG",
    "latitude",
    "longitude",
    "Time",
    "XTIME",
    "south_north",
    "west_east",
]

DEFAULT_REQUIRED_PREFIXES = [
    "wspd10",
    "T2",
    "Time",
]

DEFAULT_ALLOWED_DIMS = [
    "Time",
    "south_north",
    "west_east",
    "interp_level",
    "soil_layers_stag",
]

DEFAULT_CATALOG_GRANULARITY = "all"

DEFAULT_METADATA_PREFIXES = [
    "XLAT",
    "XLONG",
    "latitude",
    "longitude",
    "Time",
    "XTIME",
    "south_north",
    "west_east",
]

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTDIR = PROJECT_ROOT / "extraction" / "kerchunk_refs"
FILENAME_DATE_RE = re.compile(r"_(\d{4})-(\d{2})-(\d{2})\.nc$")
SEASON_BY_MONTH = {
    12: "djf",
    1: "djf",
    2: "djf",
    3: "mam",
    4: "mam",
    5: "mam",
    6: "jja",
    7: "jja",
    8: "jja",
    9: "son",
    10: "son",
    11: "son",
}


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for Kerchunk preprocessing and validation."""
    parser = argparse.ArgumentParser(
        description="Build a Kerchunk reference catalog for WRF ERA5 NetCDF files."
    )
    parser.add_argument(
        "--datadir",
        type=Path,
        default=Path("/beegfs/CMIP6/wrf_era5"),
        help="Base directory containing per-year folders.",
    )
    parser.add_argument(
        "--resolution",
        type=int,
        default=4,
        help="Resolution in km (used in folder and filename pattern).",
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=1959,
        help="First year (inclusive).",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=2022,
        help="Last year (inclusive).",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=DEFAULT_OUTDIR,
        help="Directory where the Kerchunk catalog is written.",
    )
    parser.add_argument(
        "--outfile",
        type=Path,
        default=None,
        help="Optional explicit output JSON path.",
    )
    parser.add_argument(
        "--required-prefix",
        nargs="+",
        default=DEFAULT_REQUIRED_PREFIXES,
        help=(
            "Prefixes that must be preserved in each file and should be present in every "
            "accepted NetCDF file."
        ),
    )
    parser.add_argument(
        "--catalog-granularity",
        choices=["all", "season", "month"],
        default=DEFAULT_CATALOG_GRANULARITY,
        help="Build one catalog for all files, or split catalogs by season/month using filenames.",
    )
    return parser.parse_args()


def collect_files(datadir: Path, resolution: int, start_year: int, end_year: int) -> list[str]:
    """Collect NetCDF paths for the requested resolution/year range."""
    filepattern = f"era5_wrf_dscale_{resolution}km_*.nc"
    res_dir = datadir / f"{resolution:02d}km"
    files: list[str] = []
    for year in range(start_year, end_year + 1):
        year_dir = res_dir / str(year)
        files.extend(str(p) for p in sorted(year_dir.glob(filepattern)))
    return files


def parse_file_date(nc_path: str) -> tuple[int, int, int]:
    """Extract a YYYY-MM-DD date tuple from the filename."""
    match = FILENAME_DATE_RE.search(Path(nc_path).name)
    if match is None:
        raise ValueError(f"Could not parse date from filename: {nc_path}")
    return tuple(int(part) for part in match.groups())


def group_label_for_path(nc_path: str, catalog_granularity: str) -> str:
    """Return the catalog group label implied by the filename."""
    if catalog_granularity == "all":
        return "all"

    _, month, _ = parse_file_date(nc_path)
    if catalog_granularity == "season":
        return SEASON_BY_MONTH[month]
    return f"m{month:02d}"


def group_files_by_granularity(files: list[str], catalog_granularity: str) -> dict[str, list[str]]:
    """Partition files into all/season/month groups based on filename dates."""
    grouped: dict[str, list[str]] = {}
    for nc_path in files:
        label = group_label_for_path(nc_path, catalog_granularity)
        grouped.setdefault(label, []).append(nc_path)

    if catalog_granularity == "season":
        order = ["djf", "mam", "jja", "son"]
    elif catalog_granularity == "month":
        order = [f"m{month:02d}" for month in range(1, 13)]
    else:
        order = ["all"]

    return {label: grouped[label] for label in order if label in grouped}


def build_output_name(resolution: int, start_year: int, end_year: int, group_label: str) -> str:
    """Build a catalog filename that includes the grouping label when needed."""
    if group_label == "all":
        return f"era5_wrf_dscale_{resolution}km_{start_year}_{end_year}_kerchunk.json"
    return f"era5_wrf_dscale_{resolution}km_{group_label}_{start_year}_{end_year}_kerchunk.json"


def build_report_name(stem: str, group_label: str, suffix: str) -> str:
    """Build a report filename, adding the group label for split catalogs."""
    if group_label == "all":
        return f"{stem}{suffix}"
    return f"{stem}_{group_label}{suffix}"


def resolve_output_path(base_outfile: Path | None, outdir: Path, filename: str) -> Path:
    """Resolve the output path, allowing a file path or directory-like outfile."""
    if base_outfile is None:
        return outdir / filename
    if base_outfile.suffix:
        return base_outfile.with_name(filename)
    return base_outfile / filename


@delayed
def build_single_ref(
    nc_path: str,
    keep_prefixes: tuple[str, ...],
    cache_dir: str,
) -> dict:
    """Translate one NetCDF file to Kerchunk refs, with optional cache reuse."""
    cache_path = Path(cache_dir) / f"{hashlib.sha1(nc_path.encode()).hexdigest()}.json"
    try:
        if cache_path.exists():
            try:
                with cache_path.open("r") as infile:
                    ref = ujson.load(infile)
                return {
                    "path": nc_path,
                    "status": "ok",
                    "stage": "cache_load",
                    "cache_path": str(cache_path),
                    "ref": ref,
                }
            except Exception:
                pass

        with fsspec.open(nc_path, "rb") as infile:
            ref = SingleHdf5ToZarr(
                infile,
                nc_path,
            ).translate()

        filtered = filter_ref_prefixes(ref, set(keep_prefixes))
        with cache_path.open("w") as outfile:
            ujson.dump(filtered, outfile)

        return {
            "path": nc_path,
            "status": "ok",
            "stage": "translated",
            "cache_path": str(cache_path),
            "ref": filtered,
        }
    except Exception as exc:
        return {
            "path": nc_path,
            "status": "error",
            "stage": "translate",
            "reason": str(exc),
            "cache_path": str(cache_path),
        }


def filter_ref_prefixes(ref: dict, keep_prefixes: set[str]) -> dict:
    """Filter a Kerchunk reference dict to selected top-level prefixes."""
    filtered = dict(ref)
    filtered_refs = {}
    for key, value in ref.get("refs", {}).items():
        if key.startswith("."):
            filtered_refs[key] = value
            continue
        prefix = key.split("/", 1)[0]
        if prefix in keep_prefixes:
            filtered_refs[key] = value
    filtered["refs"] = filtered_refs
    return filtered


def build_keep_prefixes(required_prefixes: set[str]) -> set[str]:
    """Return the fixed metadata prefixes plus the requested data prefixes."""
    return set(required_prefixes) | set(DEFAULT_METADATA_PREFIXES)


def _parse_ref_json_blob(blob: object) -> dict | None:
    """Parse a ref JSON payload from dict/str/bytes, skipping unsupported blobs."""
    if blob is None:
        return None
    if isinstance(blob, dict):
        return blob
    if isinstance(blob, bytes):
        blob = blob.decode()
    if isinstance(blob, str):
        if blob.startswith("base64:"):
            try:
                raw = base64.b64decode(blob.split(":", 1)[1])
                parsed = ujson.loads(raw.decode())
            except (ValueError, UnicodeDecodeError):
                return None
            if isinstance(parsed, dict):
                return parsed
            return None
        try:
            parsed = ujson.loads(blob)
        except ValueError:
            return None
        if isinstance(parsed, dict):
            return parsed
    return None


def build_schema(ref: dict, keep_prefixes: set[str]) -> dict:
    """Extract per-prefix schema metadata used for compatibility checks."""
    refs = ref.get("refs", {})
    schema = {}
    for prefix in sorted(keep_prefixes):
        zarray = _parse_ref_json_blob(refs.get(f"{prefix}/.zarray"))
        zattrs = _parse_ref_json_blob(refs.get(f"{prefix}/.zattrs"))
        if zarray is None or zattrs is None:
            continue
        dims = zattrs.get("_ARRAY_DIMENSIONS")
        if not isinstance(dims, list):
            continue
        shape = zarray.get("shape")
        chunks = zarray.get("chunks")
        if not isinstance(shape, list) or not isinstance(chunks, list):
            continue
        schema[prefix] = {
            "dims": dims,
            "shape": shape,
            "chunks": chunks,
            "dtype": zarray.get("dtype"),
        }
    return schema


def validate_schema(
    path: str,
    schema: dict,
    baseline: dict,
    required_prefixes: set[str],
    allowed_dims: set[str],
    concat_dim: str,
) -> list[str]:
    """Validate a file schema against required prefixes, dim rules, and baseline."""
    reasons = []

    missing_required = sorted(prefix for prefix in required_prefixes if prefix not in schema)
    if missing_required:
        reasons.append(f"missing required prefixes: {missing_required}")

    # Enforce spatial dimensions by inspecting kept variable metadata,
    # not by requiring dimension names as top-level Kerchunk prefixes.
    has_south_north = any("south_north" in meta.get("dims", []) for meta in schema.values())
    has_west_east = any("west_east" in meta.get("dims", []) for meta in schema.values())
    missing_spatial_dims = []
    if not has_south_north:
        missing_spatial_dims.append("south_north")
    if not has_west_east:
        missing_spatial_dims.append("west_east")
    if missing_spatial_dims:
        reasons.append(f"missing required dimensions: {missing_spatial_dims}")

    has_x = "XLAT" in schema and "XLONG" in schema
    has_named = "latitude" in schema and "longitude" in schema
    if not (has_x or has_named):
        reasons.append("missing lat/lon pair: need XLAT/XLONG or latitude/longitude")

    for prefix, meta in schema.items():
        dims = meta["dims"]
        bad_dims = [dim for dim in dims if dim not in allowed_dims]
        if bad_dims:
            reasons.append(f"{prefix}: unexpected dims {bad_dims}")

    if not baseline:
        return reasons

    for prefix, base in baseline.items():
        cur = schema.get(prefix)
        if cur is None:
            reasons.append(f"{prefix}: missing prefix in file")
            continue

        if cur["dims"] != base["dims"]:
            reasons.append(f"{prefix}: dims differ, got {cur['dims']} expected {base['dims']}")
            continue

        if cur["dtype"] != base["dtype"]:
            reasons.append(f"{prefix}: dtype differs, got {cur['dtype']} expected {base['dtype']}")

        dims = cur["dims"]
        for field in ("shape", "chunks"):
            cur_vals = cur[field]
            base_vals = base[field]
            if len(cur_vals) != len(base_vals):
                reasons.append(
                    f"{prefix}: {field} rank differs, got {len(cur_vals)} expected {len(base_vals)}"
                )
                continue
            for idx, dim_name in enumerate(dims):
                # Allow differing total length along concat dim (e.g., 23 vs 24 hours),
                # but chunk sizes along concat dim must still match for reliable combine.
                if dim_name == concat_dim and field == "shape":
                    continue
                if cur_vals[idx] != base_vals[idx]:
                    reasons.append(
                        f"{prefix}: {field} mismatch at dim {dim_name}, "
                        f"got {cur_vals[idx]} expected {base_vals[idx]}"
                    )

    return reasons


def build_catalog_for_group(
    group_label: str,
    paths: list[str],
    args: argparse.Namespace,
    keep_prefixes: set[str],
    required_prefixes: set[str],
    allowed_dims: set[str],
) -> None:
    """Translate, validate, and combine one file group into a Kerchunk catalog."""
    cache_dir = args.outdir / "per_file"
    cache_dir.mkdir(parents=True, exist_ok=True)

    report_stem = "kerchunk_report"
    skipped_stem = "kerchunk_skipped"
    report_json = args.outdir / build_report_name(report_stem, group_label, ".json")
    report_csv = args.outdir / build_report_name(skipped_stem, group_label, ".csv")
    out_name = build_output_name(args.resolution, args.start_year, args.end_year, group_label)
    out_path = resolve_output_path(args.outfile, args.outdir, out_name)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    concat_dim = "Time"
    concat_selector = "cf:Time"

    print(f"[{group_label}] {len(paths)} files found for Kerchunk translation.")
    tasks = [
        build_single_ref(
            path,
            tuple(sorted(keep_prefixes)),
            str(cache_dir),
        )
        for path in paths
    ]
    print(f"[{group_label}] Starting per-file Kerchunk translation...")
    with ProgressBar():
        results = compute(*tasks, scheduler="threads")

    skipped = []
    accepted = []
    baseline_schema = {}

    print(f"[{group_label}] Per-file translation complete. Validating schemas...")
    for result in results:
        if result.get("status") != "ok":
            skipped.append(result)
            continue

        ref = result["ref"]
        schema = build_schema(ref, keep_prefixes)
        reasons = validate_schema(
            path=result["path"],
            schema=schema,
            baseline=baseline_schema,
            required_prefixes=required_prefixes,
            allowed_dims=allowed_dims,
            concat_dim=concat_dim,
        )

        if reasons:
            skipped.append(
                {
                    "path": result["path"],
                    "status": "error",
                    "stage": "schema_validation",
                    "reasons": reasons,
                    "cache_path": result.get("cache_path", ""),
                }
            )
            continue

        if not baseline_schema:
            baseline_schema = schema

        accepted.append(result)

    print(
        f"[{group_label}] Validation complete: accepted={len(accepted)}, skipped={len(skipped)}, "
        f"total={len(results)}"
    )

    report_obj = {
        "group": group_label,
        "total_files": len(paths),
        "accepted_files": len(accepted),
        "skipped_files": len(skipped),
        "accepted": [
            {
                "path": item.get("path", ""),
                "stage": item.get("stage", ""),
                "cache_path": item.get("cache_path", ""),
            }
            for item in accepted
        ],
        "skipped": skipped,
        "settings": {
            "catalog_granularity": args.catalog_granularity,
            "keep_prefixes": sorted(keep_prefixes),
            "required_prefixes": sorted(required_prefixes),
            "allowed_dims": sorted(allowed_dims),
            "concat_dim": concat_dim,
            "cache_dir": str(cache_dir),
        },
    }

    if not accepted:
        write_reports(report_json, report_csv, report_obj)
        raise RuntimeError(
            f"No valid references available for group {group_label}. "
            "See JSON/CSV reports for skip reasons."
        )

    print(f"[{group_label}] Combining accepted references...")
    refs = [item["ref"] for item in accepted]
    mzz = MultiZarrToZarr(
        refs,
        coo_map={concat_dim: concat_selector},
        concat_dims=[concat_dim],
        identical_dims=["south_north", "west_east"],
    )
    catalog = mzz.translate()

    print(f"[{group_label}] Writing catalog to {out_path}...")
    with out_path.open("w") as outfile:
        ujson.dump(catalog, outfile)

    print(
        f"[{group_label}] Wrote Kerchunk catalog: {out_path}"
    )
    print(
        f"[{group_label}] Catalog includes {len(accepted)} accepted files out of {len(paths)} total"
    )

    write_reports(report_json, report_csv, report_obj)
    print(f"[{group_label}] Wrote report JSON: {report_json}")
    print(f"[{group_label}] Wrote report CSV: {report_csv}")


def write_reports(report_json: Path, report_csv: Path, report_obj: dict) -> None:
    """Write JSON and CSV diagnostics for accepted/skipped files."""
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_csv.parent.mkdir(parents=True, exist_ok=True)

    with report_json.open("w") as outfile:
        ujson.dump(report_obj, outfile, indent=2)

    with report_csv.open("w", newline="") as outfile:
        writer = csv.DictWriter(
            outfile,
            fieldnames=["path", "status", "stage", "reason", "cache_path"],
        )
        writer.writeheader()
        for row in report_obj["skipped"]:
            writer.writerow(
                {
                    "path": row.get("path", ""),
                    "status": row.get("status", ""),
                    "stage": row.get("stage", ""),
                    "reason": "; ".join(row.get("reasons", [row.get("reason", "")]))
                    if isinstance(row.get("reasons"), list)
                    else row.get("reason", ""),
                    "cache_path": row.get("cache_path", ""),
                }
            )


def main() -> None:
    """Run translation, validation, combine, and report generation end-to-end."""
    args = parse_args()
    allowed_dims = set(DEFAULT_ALLOWED_DIMS)

    files = collect_files(args.datadir, args.resolution, args.start_year, args.end_year)
    print(len(files), "files found for Kerchunk translation.")
    if not files:
        raise FileNotFoundError(
            f"No files found under {args.datadir} for resolution {args.resolution} km and years "
            f"{args.start_year}-{args.end_year}."
        )
    print(f"Writing to {args.outdir} with catalog granularity '{args.catalog_granularity}'")
    required_prefixes = set(args.required_prefix)
    keep_prefixes = build_keep_prefixes(required_prefixes)
    print(f"Keeping prefixes for combine: {sorted(keep_prefixes)}")
    print(f"Required prefixes: {sorted(required_prefixes)}")

    grouped_files = group_files_by_granularity(files, args.catalog_granularity)
    if not grouped_files:
        raise RuntimeError("No files matched the requested grouping.")

    print(f"Catalog granularity: {args.catalog_granularity}")
    for group_label, group_paths in grouped_files.items():
        build_catalog_for_group(
            group_label=group_label,
            paths=group_paths,
            args=args,
            keep_prefixes=keep_prefixes,
            required_prefixes=required_prefixes,
            allowed_dims=allowed_dims,
        )


if __name__ == "__main__":
    main()