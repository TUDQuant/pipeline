"""Nightly data refresh.

    python data-pipelines/update_data.py --group equities
    python data-pipelines/update_data.py --group all --dry-run

Runs in GitHub Actions. Fetches, validates, writes parquet locally, then pushes
both the parquet and the quality report into the Shared Drive.

Design rule: a single bad symbol must never fail the whole run. Members arriving
the next morning need the other twenty datasets more than they need a red X.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import drive as drive_client  # noqa: E402

from tudquant import cache, config, data, validation  # noqa: E402

UNIVERSE = Path(__file__).parent / "universe.yml"
GROUPS = ("equities", "crypto", "macro")


def load_universe() -> dict:
    return yaml.safe_load(UNIVERSE.read_text())


def refresh_group(group: str, spec: dict) -> tuple[list, list]:
    """Returns (reports, failures)."""
    symbols = spec.get("symbols") or spec.get("series") or []
    start = spec.get("start")
    reports, failures = [], []

    for symbol in symbols:
        try:
            df = data.fetch_live(symbol, group, start=start)
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL  {symbol}: {exc}", flush=True)
            failures.append({"symbol": symbol, "group": group, "error": str(exc)})
            continue

        report = validation.validate(df, symbol, group, validation_calendar(group))
        cache.write(df, symbol, group)
        report.save(cache.quality_path_for(symbol, group))
        reports.append(report)

        verdict = "OK  " if report.ok else "BAD "
        print(f"  {verdict}  {symbol}: {len(df)} rows to {report.end}"
              f" ({len(report.errors)}E/{len(report.warnings)}W)", flush=True)

    return reports, failures


def validation_calendar(group: str) -> str:
    return data.CALENDARS.get(group, "business")


def write_summary(reports: list, failures: list, root: Path) -> Path:
    summary = validation.summarise(reports)
    root.mkdir(parents=True, exist_ok=True)
    path = root / "_summary.csv"
    summary.to_csv(path, index=False)

    (root / "_failures.json").write_text(json.dumps(failures, indent=2))

    print("\n--- summary ---")
    if not summary.empty:
        print(summary.to_string(index=False))
    print(f"{len(failures)} fetch failures, "
          f"{int(summary['errors'].sum()) if not summary.empty else 0} datasets with errors")
    return path


def sync_to_drive(local_root: Path) -> None:
    folder_id = os.environ.get("GDRIVE_FOLDER_ID")
    if not folder_id:
        raise RuntimeError("GDRIVE_FOLDER_ID is not set")

    service = drive_client.client()
    parquet_folder = drive_client.ensure_folder(service, "parquet", folder_id)
    quality_folder = drive_client.ensure_folder(service, "quality", folder_id)

    uploaded = 0
    for f in sorted((local_root / "parquet").glob("*.parquet")):
        drive_client.upload(service, f, parquet_folder)
        uploaded += 1
    for f in sorted((local_root / "quality").glob("*")):
        drive_client.upload(service, f, quality_folder, mime="application/json")
        uploaded += 1

    print(f"uploaded {uploaded} files to Drive")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", default="all", choices=(*GROUPS, "all"))
    parser.add_argument("--dry-run", action="store_true",
                        help="fetch and validate but do not touch Drive")
    args = parser.parse_args()

    universe = load_universe()
    groups = GROUPS if args.group == "all" else (args.group,)

    all_reports, all_failures = [], []
    for group in groups:
        spec = universe.get(group)
        if not spec:
            continue
        print(f"\n== {group} ==", flush=True)
        reports, failures = refresh_group(group, spec)
        all_reports.extend(reports)
        all_failures.extend(failures)

    root = config.resolve().data_root
    write_summary(all_reports, all_failures, root / "quality")

    if not args.dry_run:
        sync_to_drive(root)

    # Fail the workflow only if we got nothing at all. Partial data is normal
    # and must not page anyone at 3am.
    if not all_reports:
        print("\nNo datasets refreshed at all - failing the run.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
