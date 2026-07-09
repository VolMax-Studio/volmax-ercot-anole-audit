"""
pull_anole.py — US-TX-ANOL-001 Data Acquisition Script
=======================================================
Protocol:  P10 v1.0 — "Unfalsifiable-as-Stated"
Asset:     ANOL_ESS_ESR1 (esVolta Anole BESS, Seagoville TX)
Dataset:   ercot_sced_esr_60_day (gridstatus.io Hosted API)
Window:    2025-12-05 → 2026-04-30 (inclusive)

IMPORTANT — Reproducibility Class: Licensed API
  Raw CSV data is NOT committed to the repository.
  gridstatus.io ToU prohibits redistribution.
  SHA-256 hashes are written to data_manifest.json for verification.

Usage:
  1. Copy .env.template to .env and insert your gridstatus.io API key.
  2. python3 pull_anole.py
  3. Verify: data_manifest.json is written; raw_data/*.csv populated.

Correction dates: 2025-12-05, 2025-12-06
  ERCOT publishes correction ZIPs for these dates.
  gridstatus.io serves corrected data transparently — no special handling
  required at query level, but dates are flagged in the manifest.
"""

import os
import sys
import json
import hashlib
import time
import datetime
import requests
from dotenv import load_dotenv
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────
RESOURCE_NAME   = "ANOL_ESS_ESR1"
DATASET         = "ercot_sced_esr_60_day"
BASE_URL        = "https://api.gridstatus.io/v1/datasets"
WINDOW_START    = datetime.date(2025, 12, 5)
WINDOW_END      = datetime.date(2026, 4, 30)
CORRECTION_DATES = {"2025-12-05", "2025-12-06"}

FIELDS = [
    "sced_timestamp_utc",
    "resource_name",
    "telemetered_net_output",
    "base_point",
    "hsl",
    "lsl",
    "soc",
    "min_soc",
    "max_soc",
    "telemetered_resource_status",
]

# Chunk size: pull month-by-month to stay within API row limits
CHUNK_MONTHS = 1

RAW_DATA_DIR = Path(__file__).parent / "audits" / "US-TX-ANOL-001" / "raw_data"
MANIFEST_PATH = Path(__file__).parent / "audits" / "US-TX-ANOL-001" / "data_manifest.json"

# ── Helpers ────────────────────────────────────────────────────────────────────

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def month_chunks(start: datetime.date, end: datetime.date):
    """Yield (chunk_start, chunk_end) pairs, month by month."""
    current = start.replace(day=1)
    while current <= end:
        # last day of current month
        if current.month == 12:
            next_month = current.replace(year=current.year + 1, month=1, day=1)
        else:
            next_month = current.replace(month=current.month + 1, day=1)
        chunk_end = next_month - datetime.timedelta(days=1)
        yield (
            max(start, current),
            min(end, chunk_end),
        )
        current = next_month


def query_chunk(api_key: str, chunk_start: datetime.date, chunk_end: datetime.date) -> list[dict]:
    """Query gridstatus.io for one date chunk. Returns list of row dicts."""
    url = f"{BASE_URL}/{DATASET}/query"
    page_size = 50_000  # gridstatus.io max page_size

    all_rows = []
    page = 1
    while True:
        params = {
            "api_key": api_key,
            "filter_column": "resource_name",
            "filter_value": RESOURCE_NAME,
            "start_time": chunk_start.isoformat() + "T00:00:00Z",
            "end_time":   chunk_end.isoformat()   + "T23:59:59Z",
            "limit": page_size,
            "page": page,
            "return_format": "json",
        }

        resp = requests.get(url, params=params, timeout=60)
        if resp.status_code == 429:
            print("  ⚠ Rate limited — waiting 15s...")
            time.sleep(15)
            continue
        resp.raise_for_status()
        data = resp.json()
        rows = data.get("data", [])
        all_rows.extend(rows)
        total = data.get("meta", {}).get("total_rows", "?")
        print(f"  Page {page}: {len(rows)} rows (running total: {len(all_rows)} / {total})")
        if len(rows) < page_size:
            break  # last page
        page += 1
        time.sleep(1.5)  # polite pacing — stay under rate limit

    return all_rows


def rows_to_csv(rows: list[dict], fields: list[str]) -> str:
    """Convert list of row dicts to CSV string."""
    lines = [",".join(fields)]
    for row in rows:
        cells = []
        for f in fields:
            val = row.get(f, "")
            if val is None:
                val = ""
            cells.append(str(val))
        lines.append(",".join(cells))
    return "\n".join(lines) + "\n"


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    load_dotenv()
    api_key = os.getenv("GRIDSTATUS_API_KEY")
    if not api_key:
        print("ERROR: GRIDSTATUS_API_KEY not set in .env")
        sys.exit(1)

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output dir: {RAW_DATA_DIR}")
    print(f"Pulling {RESOURCE_NAME} | {WINDOW_START} → {WINDOW_END}\n")

    manifest = {
        "protocol": "P10 v1.0",
        "audit_id": "US-TX-ANOL-001",
        "resource_name": RESOURCE_NAME,
        "dataset": DATASET,
        "window_start": WINDOW_START.isoformat(),
        "window_end": WINDOW_END.isoformat(),
        "pulled_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "correction_dates_flagged": sorted(CORRECTION_DATES),
        "files": [],
    }

    total_rows = 0
    for chunk_start, chunk_end in month_chunks(WINDOW_START, WINDOW_END):
        label = f"{chunk_start.strftime('%Y-%m')}"
        filename = f"ANOL_ESR1_SCED_{chunk_start.isoformat()}_{chunk_end.isoformat()}.csv"
        out_path = RAW_DATA_DIR / filename

        print(f"── {label} ({chunk_start} → {chunk_end})")

        # Skip if already pulled (allow resume)
        if out_path.exists():
            print(f"  ✓ Already exists — skipping (delete to re-pull)")
            sha = sha256_file(out_path)
            row_count = sum(1 for _ in open(out_path)) - 1  # minus header
            manifest["files"].append({
                "filename": filename,
                "chunk_start": chunk_start.isoformat(),
                "chunk_end": chunk_end.isoformat(),
                "sha256": sha,
                "row_count": row_count,
                "correction_dates_in_chunk": [
                    d for d in CORRECTION_DATES if chunk_start.isoformat() <= d <= chunk_end.isoformat()
                ],
                "status": "cached",
            })
            total_rows += row_count
            continue

        rows = query_chunk(api_key, chunk_start, chunk_end)
        if not rows:
            print(f"  ⚠ No data returned for this chunk.")
            manifest["files"].append({
                "filename": filename,
                "chunk_start": chunk_start.isoformat(),
                "chunk_end": chunk_end.isoformat(),
                "sha256": None,
                "row_count": 0,
                "correction_dates_in_chunk": [
                    d for d in CORRECTION_DATES if chunk_start.isoformat() <= d <= chunk_end.isoformat()
                ],
                "status": "empty",
            })
            continue

        csv_content = rows_to_csv(rows, FIELDS)
        out_path.write_text(csv_content, encoding="utf-8")
        sha = sha256_file(out_path)
        print(f"  → Saved {len(rows)} rows → {filename}")
        print(f"  → SHA-256: {sha}")

        manifest["files"].append({
            "filename": filename,
            "chunk_start": chunk_start.isoformat(),
            "chunk_end": chunk_end.isoformat(),
            "sha256": sha,
            "row_count": len(rows),
            "correction_dates_in_chunk": [
                d for d in CORRECTION_DATES if chunk_start.isoformat() <= d <= chunk_end.isoformat()
            ],
            "status": "pulled",
        })
        total_rows += len(rows)
        time.sleep(1.0)  # polite between chunks

    manifest["total_rows"] = total_rows
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\n✅ Done. {total_rows} total rows across {len(manifest['files'])} chunks.")
    print(f"   Manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
