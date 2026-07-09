"""
cross_check.py — US-TX-ANOL-001 Primary Source Cross-Check
===========================================================
Purpose: Compare gridstatus.io CSV rows against ERCOT NP3-965-ER primary ZIPs.
         If cross-check passes, anchor class is restored to A.

Prerequisite: Manual download of ERCOT NP3-965-ER ZIPs into:
  audits/US-TX-ANOL-001/ercot_primary_zips/

ERCOT MIS download URL (browser only — WAF blocks scripts):
  https://mis.ercot.com/misapp/GetReports.do?reportTypeId=13052

ZIP naming convention (ERCOT):
  NP3-965-ER_<YYYYMMDD>.zip  — or similar; check MIS portal for exact name.

Each ZIP contains CSV files with SCED ESR data. Relevant column in ERCOT CSV:
  - Resource Name (maps to: resource_name)
  - Telemetered Net Output (maps to: telemetered_net_output)
  - Base Point (maps to: base_point)
  - HSL, LSL, SoC (where present)
  - SCED Timestamp (maps to: sced_timestamp_utc)

Usage:
  python3 cross_check.py

Outputs:
  audits/US-TX-ANOL-001/cross_check_report.md
  audits/US-TX-ANOL-001/primary_manifest.json  (SHA-256 of each ERCOT ZIP)
"""

import csv
import json
import hashlib
import zipfile
import datetime
from pathlib import Path
from collections import defaultdict

RESOURCE_NAME    = "ANOL_ESS_ESR1"
RAW_DATA_DIR     = Path(__file__).parent / "audits" / "US-TX-ANOL-001" / "raw_data"
ERCOT_ZIPS_DIR   = Path(__file__).parent / "audits" / "US-TX-ANOL-001" / "ercot_primary_zips"
REPORT_PATH      = Path(__file__).parent / "audits" / "US-TX-ANOL-001" / "cross_check_report.md"
PRIMARY_MANIFEST = Path(__file__).parent / "audits" / "US-TX-ANOL-001" / "primary_manifest.json"

# Tolerance for float comparison (MW — SCED is 2 decimal places)
FLOAT_TOL = 0.01


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_gridstatus_rows() -> dict[str, dict]:
    """Load all gridstatus CSVs. Key: sced_timestamp_utc."""
    rows = {}
    for f in sorted(RAW_DATA_DIR.glob("*.csv")):
        with open(f, "r", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                ts = row.get("sced_timestamp_utc", "")
                rows[ts] = row
    print(f"Loaded {len(rows):,} gridstatus rows")
    return rows


def load_ercot_zip(zip_path: Path) -> list[dict]:
    """
    Extract and parse one ERCOT NP3-965-ER ZIP.
    Returns list of row dicts for ANOL_ESS_ESR1.

    NOTE: ERCOT CSV column names vary by report vintage.
    This function attempts common column name patterns.
    Adjust COL_MAP below if ERCOT changes their schema.
    """
    # Column name mappings (ERCOT name → our name)
    COL_MAP = {
        # Timestamp variants
        "SCED Timestamp": "sced_timestamp_utc",
        "SCEDTimestamp": "sced_timestamp_utc",
        "Interval Start": "sced_timestamp_utc",
        # Resource
        "Resource Name": "resource_name",
        "ResourceName": "resource_name",
        # Telemetry
        "Telemetered Net Output": "telemetered_net_output",
        "TelemNetOutput": "telemetered_net_output",
        "Base Point": "base_point",
        "BasePoint": "base_point",
        "HSL": "hsl",
        "LSL": "lsl",
        "SoC": "soc",
        "SOC": "soc",
        "Min SoC": "min_soc",
        "Max SoC": "max_soc",
        "Telemetered Resource Status": "telemetered_resource_status",
        "TelemResourceStatus": "telemetered_resource_status",
    }

    rows = []
    with zipfile.ZipFile(zip_path, "r") as z:
        for name in z.namelist():
            if not name.endswith(".csv"):
                continue
            with z.open(name) as fh:
                content = fh.read().decode("utf-8", errors="replace")
                reader = csv.DictReader(content.splitlines())
                for row in reader:
                    # Normalize column names
                    normalized = {}
                    for col, val in row.items():
                        mapped = COL_MAP.get(col.strip(), col.strip())
                        normalized[mapped] = val.strip()
                    # Filter to ANOL_ESS_ESR1
                    if normalized.get("resource_name", "").strip() == RESOURCE_NAME:
                        rows.append(normalized)
    return rows


def compare_row(gs_row: dict, ercot_row: dict, fields: list[str]) -> list[str]:
    """Return list of field mismatches."""
    mismatches = []
    for field in fields:
        gs_val = gs_row.get(field, "")
        er_val = ercot_row.get(field, "")
        # Float comparison
        try:
            if abs(float(gs_val) - float(er_val)) > FLOAT_TOL:
                mismatches.append(f"{field}: gs={gs_val} vs ercot={er_val}")
        except (ValueError, TypeError):
            if gs_val.strip() != er_val.strip():
                mismatches.append(f"{field}: gs={gs_val!r} vs ercot={er_val!r}")
    return mismatches


def main():
    if not ERCOT_ZIPS_DIR.exists() or not any(ERCOT_ZIPS_DIR.glob("*.zip")):
        print(f"""
ERROR: No ERCOT ZIP files found in:
  {ERCOT_ZIPS_DIR}

Manual download required:
  1. Open browser → https://mis.ercot.com/misapp/GetReports.do?reportTypeId=13052
  2. Download monthly NP3-965-ER ZIPs for 2025-12-05 through 2026-04-30
  3. Place ZIPs in: {ERCOT_ZIPS_DIR}
  4. Re-run: python3 cross_check.py
""")
        return

    ERCOT_ZIPS_DIR.mkdir(parents=True, exist_ok=True)

    gs_rows = load_gridstatus_rows()
    compare_fields = [
        "telemetered_net_output", "base_point", "hsl", "lsl",
        "soc", "min_soc", "max_soc", "telemetered_resource_status",
    ]

    primary_manifest = {
        "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "resource_name": RESOURCE_NAME,
        "purpose": "Primary ERCOT NP3-965-ER artifact hashes for anchor Class A verification",
        "zips": [],
    }

    total_ercot_rows = 0
    total_matched = 0
    total_mismatched = 0
    total_ercot_only = 0  # in ERCOT ZIP but not in gridstatus
    all_mismatches = []

    for zip_path in sorted(ERCOT_ZIPS_DIR.glob("*.zip")):
        sha = sha256_file(zip_path)
        print(f"\nProcessing: {zip_path.name}")
        print(f"  SHA-256: {sha}")

        ercot_rows = load_ercot_zip(zip_path)
        print(f"  ANOL_ESS_ESR1 rows in ZIP: {len(ercot_rows):,}")

        zip_mismatches = []
        zip_matched = 0
        zip_ercot_only = 0

        for er_row in ercot_rows:
            ts = er_row.get("sced_timestamp_utc", "")
            if ts not in gs_rows:
                zip_ercot_only += 1
                continue
            diffs = compare_row(gs_rows[ts], er_row, compare_fields)
            if diffs:
                zip_mismatches.append({"timestamp": ts, "diffs": diffs})
                total_mismatched += 1
            else:
                zip_matched += 1
                total_matched += 1

        total_ercot_rows += len(ercot_rows)
        total_ercot_only += zip_ercot_only
        all_mismatches.extend(zip_mismatches)

        primary_manifest["zips"].append({
            "filename": zip_path.name,
            "sha256": sha,
            "anol_rows": len(ercot_rows),
            "matched": zip_matched,
            "mismatched": len(zip_mismatches),
            "ercot_only_rows": zip_ercot_only,
            "sample_mismatches": zip_mismatches[:3],
        })

        print(f"  Matched: {zip_matched}  Mismatched: {len(zip_mismatches)}  ERCOT-only: {zip_ercot_only}")

    # Write primary manifest
    PRIMARY_MANIFEST.write_text(json.dumps(primary_manifest, indent=2), encoding="utf-8")

    # Determine anchor class
    mismatch_rate = total_mismatched / max(1, total_ercot_rows)
    if mismatch_rate == 0 and total_ercot_only == 0:
        anchor_class = "A"
        verdict = "PASS — gridstatus rendering verified against primary ERCOT artifact"
    elif mismatch_rate < 0.001:
        anchor_class = "A-"
        verdict = f"PASS WITH EXCEPTIONS — {total_mismatched} mismatches ({100*mismatch_rate:.3f}%), documented"
    else:
        anchor_class = "B"
        verdict = f"FAIL — {total_mismatched} mismatches ({100*mismatch_rate:.2f}%) — discrepancy is a finding"

    # Write report
    report_lines = [
        "# US-TX-ANOL-001 — Primary Source Cross-Check Report",
        "",
        f"**Generated:** {datetime.datetime.now(datetime.timezone.utc).isoformat()}",
        f"**Anchor class result:** {anchor_class}",
        f"**Verdict:** {verdict}",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| ERCOT ZIP rows (ANOL_ESS_ESR1) | {total_ercot_rows:,} |",
        f"| Gridstatus rows | {len(gs_rows):,} |",
        f"| Matched exactly | {total_matched:,} |",
        f"| Mismatched | {total_mismatched:,} |",
        f"| In ERCOT ZIP but not in gridstatus | {total_ercot_only:,} |",
        f"| Mismatch rate | {100*mismatch_rate:.4f}% |",
        "",
    ]
    if all_mismatches:
        report_lines += [
            "## Sample Mismatches (first 10)",
            "",
            "| Timestamp | Field | gridstatus | ERCOT ZIP |",
            "|-----------|-------|-----------|-----------|",
        ]
        for m in all_mismatches[:10]:
            for diff in m["diffs"]:
                report_lines.append(f"| {m['timestamp']} | {diff} |")
        report_lines.append("")

    REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"\n{'='*58}")
    print(f"CROSS-CHECK COMPLETE")
    print(f"  Anchor class: {anchor_class}")
    print(f"  Verdict: {verdict}")
    print(f"  Report: {REPORT_PATH}")
    print(f"  Primary manifest: {PRIMARY_MANIFEST}")


if __name__ == "__main__":
    main()
