"""
l1_integrity.py — US-TX-ANOL-001 L1 Data Integrity Check
=========================================================
P10 v1.0 pipeline order: Data Freeze → L1 Integrity → L2 Physics → L3 Stat → L4 Repro
This script MUST pass before analysis.py is run.

Checks:
  1. Duplicates on sced_timestamp_utc (chunk boundary overlap)
  2. Gap histogram between consecutive timestamps (mode, tails)
  3. December density analysis — where is the 4-row/day deficit concentrated
  4. UTC vs CPT boundary — does 2025-12-05T00:00Z include pre-ERCOT-day data
  5. telemetered_resource_status distinct values + frequencies
  6. NULL counts per column, especially soc/min_soc/max_soc
  7. Sign convention — positive TNO = export/discharge, confirmed from data

Outputs:
  audits/US-TX-ANOL-001/l1_report.md   — human-readable, goes into report
  audits/US-TX-ANOL-001/l1_flags.json  — machine-readable pass/warn/fail per check
"""

import csv
import json
import math
import datetime
from pathlib import Path
from collections import Counter, defaultdict

RAW_DATA_DIR  = Path(__file__).parent / "audits" / "US-TX-ANOL-001" / "raw_data"
REPORT_PATH   = Path(__file__).parent / "audits" / "US-TX-ANOL-001" / "l1_report.md"
FLAGS_PATH    = Path(__file__).parent / "audits" / "US-TX-ANOL-001" / "l1_flags.json"

EXPECTED_INTERVAL_S = 300   # 5 min nominal
ERCOT_DAY_START_HOUR_UTC = 6  # ERCOT CPT = UTC-6 in Dec/Jan/Feb


# ── Loaders ────────────────────────────────────────────────────────────────────

def load_all_rows() -> list[dict]:
    files = sorted(RAW_DATA_DIR.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files in {RAW_DATA_DIR}")
    all_rows = []
    for f in files:
        with open(f, "r", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        print(f"  {f.name}: {len(rows):,} rows")
        all_rows.extend(rows)
    print(f"  TOTAL before dedup: {len(all_rows):,}")
    return all_rows


def parse_ts(s: str) -> datetime.datetime | None:
    if not s:
        return None
    try:
        return datetime.datetime.fromisoformat(s)
    except ValueError:
        return None


def parse_float(s: str) -> float:
    try:
        return float(s)
    except (TypeError, ValueError):
        return math.nan


# ── Check 1: Duplicates ────────────────────────────────────────────────────────

def check_duplicates(rows: list[dict]) -> dict:
    ts_counts = Counter(r["sced_timestamp_utc"] for r in rows)
    dupes = {ts: cnt for ts, cnt in ts_counts.items() if cnt > 1}
    return {
        "total_rows_pre_dedup": len(rows),
        "unique_timestamps": len(ts_counts),
        "duplicate_timestamps": len(dupes),
        "duplicate_extra_rows": sum(cnt - 1 for cnt in dupes.values()),
        "sample": list(dupes.items())[:5],
        "flag": "PASS" if not dupes else "WARN",
    }


# ── Check 2: Gap histogram ─────────────────────────────────────────────────────

def check_gaps(rows: list[dict]) -> dict:
    parsed = sorted(
        [(parse_ts(r["sced_timestamp_utc"]), r) for r in rows
         if parse_ts(r["sced_timestamp_utc"])],
        key=lambda x: x[0],
    )
    gaps_s = [
        int((parsed[i][0] - parsed[i-1][0]).total_seconds())
        for i in range(1, len(parsed))
    ]
    c = Counter(gaps_s)
    mode_gap, mode_cnt = c.most_common(1)[0] if c else (None, 0)

    # Tail buckets
    lt_300   = sum(cnt for g, cnt in c.items() if 0 < g < 300)
    eq_300   = c.get(300, 0)
    gt_300_lt_600 = sum(cnt for g, cnt in c.items() if 300 < g < 600)
    gte_600  = sum(cnt for g, cnt in c.items() if g >= 600)
    largest  = max(gaps_s) if gaps_s else 0

    # Large gaps detail (>= 30 min)
    large_gap_events = []
    for i in range(1, len(parsed)):
        g = int((parsed[i][0] - parsed[i-1][0]).total_seconds())
        if g >= 1800:
            large_gap_events.append({
                "from": parsed[i-1][0].isoformat(),
                "to":   parsed[i][0].isoformat(),
                "gap_minutes": round(g / 60, 1),
            })

    return {
        "total_gaps": len(gaps_s),
        "mode_gap_seconds": mode_gap,
        "mode_gap_count": mode_cnt,
        "mode_gap_pct": round(100 * mode_cnt / len(gaps_s), 2) if gaps_s else 0,
        "lt_300s": lt_300,
        "eq_300s": eq_300,
        "gt_300s_lt_600s": gt_300_lt_600,
        "gte_600s": gte_600,
        "largest_gap_seconds": largest,
        "largest_gap_minutes": round(largest / 60, 1),
        "gaps_gte_30min": large_gap_events,
        "flag": "PASS" if gte_600 == 0 else ("WARN" if largest < 7200 else "FAIL"),
    }


# ── Check 3: December density ──────────────────────────────────────────────────

def check_dec_density(rows: list[dict]) -> dict:
    daily: dict[datetime.date, int] = defaultdict(int)
    for r in rows:
        ts = parse_ts(r["sced_timestamp_utc"])
        if ts:
            daily[ts.date()] += 1

    dec = {d: c for d, c in daily.items() if d.year == 2025 and d.month == 12}
    jan = {d: c for d, c in daily.items() if d.year == 2026 and d.month == 1}

    dec_05 = daily.get(datetime.date(2025, 12, 5), 0)
    dec_06 = daily.get(datetime.date(2025, 12, 6), 0)
    dec_rest = {d: c for d, c in dec.items()
                if d > datetime.date(2025, 12, 6)}
    dec_rest_avg = sum(dec_rest.values()) / len(dec_rest) if dec_rest else 0
    jan_avg = sum(jan.values()) / len(jan) if jan else 0

    concentrated = (dec_05 + dec_06) / 2 < dec_rest_avg * 0.95

    return {
        "dec_total_rows": sum(dec.values()),
        "dec_days": len(dec),
        "dec_avg_per_day": round(sum(dec.values()) / len(dec), 1) if dec else 0,
        "jan_avg_per_day": round(jan_avg, 1),
        "dec_05_rows": dec_05,
        "dec_06_rows": dec_06,
        "dec_05_06_avg": round((dec_05 + dec_06) / 2, 1),
        "dec_07_31_avg": round(dec_rest_avg, 1),
        "deficit_concentrated_in_first_48h": concentrated,
        "interpretation": (
            "Deficit is in Dec 05-06 (correction dates + RTC+B go-live)"
            if concentrated else
            "Deficit is spread across full December — not a boundary artefact"
        ),
        "daily_dec": {str(d): c for d, c in sorted(dec.items())},
        "flag": "WARN" if concentrated else "PASS",
    }


# ── Check 4: UTC vs CPT boundary ──────────────────────────────────────────────

def check_utc_cpt(rows: list[dict]) -> dict:
    """
    ERCOT operates on CPT = UTC-6 (CST) in December.
    ERCOT operating day 2025-12-05 starts at 2025-12-05T06:00Z.
    Data from 2025-12-05T00:00Z to 2025-12-05T05:59Z belongs to
    ERCOT trading day 2025-12-04 — i.e., before the audit window
    as defined in local ERCOT time.
    """
    dec_05 = datetime.date(2025, 12, 5)
    ts_dec05 = [
        parse_ts(r["sced_timestamp_utc"])
        for r in rows
        if parse_ts(r["sced_timestamp_utc"]) and
           parse_ts(r["sced_timestamp_utc"]).date() == dec_05
    ]

    before_ercot_day = [ts for ts in ts_dec05 if ts.hour < ERCOT_DAY_START_HOUR_UTC]
    after_ercot_day  = [ts for ts in ts_dec05 if ts.hour >= ERCOT_DAY_START_HOUR_UTC]

    has_pre_day = len(before_ercot_day) > 0
    note = (
        "Dec 05 data before 06:00Z (ERCOT day 2025-12-04) is present. "
        "If pre-reg window was defined in CPT, these rows are outside scope. "
        "Decision required: trim or retain with annotation."
        if has_pre_day else
        "No pre-06:00Z rows on Dec 05. UTC and CPT windows are aligned for this day."
    )

    earliest = min(ts_dec05).isoformat() if ts_dec05 else "N/A"

    return {
        "dec_05_total_rows": len(ts_dec05),
        "dec_05_before_0600z": len(before_ercot_day),
        "dec_05_after_0600z": len(after_ercot_day),
        "earliest_row_utc": earliest,
        "ercot_cpt_offset_hours": -6,
        "ercot_day_start_utc": "T06:00:00Z",
        "has_pre_ercot_day_data": has_pre_day,
        "note": note,
        "flag": "WARN" if has_pre_day else "PASS",
    }


# ── Check 5: Resource status ───────────────────────────────────────────────────

def check_status(rows: list[dict]) -> dict:
    counter = Counter(
        (r.get("telemetered_resource_status") or "NULL")
        for r in rows
    )
    total = len(rows)
    return {
        "total_rows": total,
        "distinct_values": {
            k: {"count": v, "pct": round(100 * v / total, 2)}
            for k, v in counter.most_common()
        },
        "on_rows": counter.get("ON", 0),
        "out_rows": counter.get("OUT", 0),
        "note": (
            "F1/F2 falsification tests should filter to ON rows only. "
            "OUT rows: asset not dispatched — telemetered_net_output not meaningful for capacity claims. "
            "ONTEST/ONRR: review before inclusion in F-tests."
        ),
        "flag": "INFO",
    }


# ── Check 6: NULL counts ───────────────────────────────────────────────────────

def check_nulls(rows: list[dict]) -> dict:
    cols = [
        "sced_timestamp_utc", "telemetered_net_output", "base_point",
        "hsl", "lsl", "soc", "min_soc", "max_soc", "telemetered_resource_status",
    ]
    total = len(rows)
    result = {}
    for col in cols:
        n_null = sum(1 for r in rows if not r.get(col))
        result[col] = {
            "null_count": n_null,
            "null_pct": round(100 * n_null / total, 2),
            "flag": (
                "FAIL" if n_null / total > 0.4 else
                "WARN" if n_null / total > 0.05 else
                "PASS"
            ),
        }
    soc_pct = result["soc"]["null_pct"]
    overall = (
        "FAIL" if soc_pct > 40 else
        "WARN" if soc_pct > 5 else
        "PASS"
    )
    return {"total_rows": total, "columns": result, "flag": overall,
            "note": "SoC NULL% is the key metric — F3 auditability depends on it."}


# ── Check 7: Sign convention ───────────────────────────────────────────────────

def check_sign(rows: list[dict]) -> dict:
    """
    Confirm from data (not documentation) that positive TNO = discharge/export.
    Method: consecutive pairs (gap ≤ 10 min) where both soc values are valid.
    Classify by (TNO sign, SoC delta direction).
    """
    parsed = sorted(
        [
            (parse_ts(r["sced_timestamp_utc"]),
             parse_float(r.get("telemetered_net_output", "")),
             parse_float(r.get("soc", "")))
            for r in rows
            if parse_ts(r["sced_timestamp_utc"])
        ],
        key=lambda x: x[0],
    )

    pos_soc_down = 0   # TNO>0, SoC↓ → positive = discharge ✓
    pos_soc_up   = 0   # TNO>0, SoC↑ → anomaly
    neg_soc_up   = 0   # TNO<0, SoC↑ → negative = charge ✓
    neg_soc_down = 0   # TNO<0, SoC↓ → anomaly
    skipped_nan  = 0

    for i in range(1, len(parsed)):
        ts0, tno0, soc0 = parsed[i-1]
        ts1, tno1, soc1 = parsed[i]
        if (ts1 - ts0).total_seconds() > 600:
            continue
        if any(math.isnan(x) for x in [tno0, soc0, soc1]):
            skipped_nan += 1
            continue
        delta_soc = soc1 - soc0
        if abs(delta_soc) < 0.5:   # noise threshold
            continue
        if tno0 > 1.0:
            if delta_soc < 0:
                pos_soc_down += 1
            else:
                pos_soc_up += 1
        elif tno0 < -1.0:
            if delta_soc > 0:
                neg_soc_up += 1
            else:
                neg_soc_down += 1

    total = pos_soc_down + pos_soc_up + neg_soc_up + neg_soc_down
    confirmed = (
        total > 0 and
        pos_soc_down > pos_soc_up and
        neg_soc_up   > neg_soc_down
    )

    return {
        "pos_tno_soc_decreasing_discharge": pos_soc_down,
        "pos_tno_soc_increasing_anomaly":   pos_soc_up,
        "neg_tno_soc_increasing_charge":    neg_soc_up,
        "neg_tno_soc_decreasing_anomaly":   neg_soc_down,
        "skipped_nan_pairs": skipped_nan,
        "total_classified": total,
        "sign_convention_confirmed": confirmed,
        "note": "positive TNO = export/discharge, confirmed empirically from SoC delta correlation.",
        "flag": "PASS" if confirmed else "FAIL",
    }


# ── Markdown report ────────────────────────────────────────────────────────────

def write_report(checks: dict, path: Path):
    d = checks
    now = d["generated_at_utc"]
    c = d["checks"]

    def flag_icon(f): return {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌", "INFO": "ℹ️"}.get(f, "?")

    lines = [
        f"# US-TX-ANOL-001 — L1 Data Integrity Report",
        f"",
        f"**Generated:** {now}  ",
        f"**Protocol:** P10 v1.0  ",
        f"**Rows loaded (pre-dedup):** {d['total_rows_pre_dedup']:,}  ",
        f"",
        f"---",
        f"",
        f"## Summary",
        f"",
        f"| Check | Flag |",
        f"|-------|------|",
        f"| 1. Duplicates | {flag_icon(c['duplicates']['flag'])} {c['duplicates']['flag']} |",
        f"| 2. Gap histogram | {flag_icon(c['gaps']['flag'])} {c['gaps']['flag']} |",
        f"| 3. December density | {flag_icon(c['dec_density']['flag'])} {c['dec_density']['flag']} |",
        f"| 4. UTC/CPT boundary | {flag_icon(c['utc_cpt']['flag'])} {c['utc_cpt']['flag']} |",
        f"| 5. Resource status | {flag_icon(c['status']['flag'])} {c['status']['flag']} |",
        f"| 6. NULL counts (SoC) | {flag_icon(c['nulls']['flag'])} {c['nulls']['flag']} |",
        f"| 7. Sign convention | {flag_icon(c['sign']['flag'])} {c['sign']['flag']} |",
        f"",
        f"---",
        f"",
        f"## 1. Duplicates",
        f"",
        f"- Rows loaded: **{c['duplicates']['total_rows_pre_dedup']:,}**",
        f"- Unique timestamps: **{c['duplicates']['unique_timestamps']:,}**",
        f"- Duplicate timestamps: **{c['duplicates']['duplicate_timestamps']}**",
        f"- Extra rows (to drop on dedup): **{c['duplicates']['duplicate_extra_rows']}**",
        f"",
        f"## 2. Gap Histogram",
        f"",
        f"- Mode gap: **{c['gaps']['mode_gap_seconds']}s** ({c['gaps']['mode_gap_count']:,} occurrences, {c['gaps']['mode_gap_pct']}%)",
        f"- Gaps < 300s: {c['gaps']['lt_300s']}",
        f"- Gaps = 300s: {c['gaps']['eq_300s']:,}",
        f"- Gaps 300s–600s: {c['gaps']['gt_300s_lt_600s']}",
        f"- Gaps ≥ 600s: **{c['gaps']['gte_600s']}** (largest: {c['gaps']['largest_gap_minutes']} min)",
        f"",
    ]

    if c['gaps']['gaps_gte_30min']:
        lines.append("**Gaps ≥ 30 min:**")
        lines.append("")
        lines.append("| From | To | Gap (min) |")
        lines.append("|------|----|-----------|")
        for g in c['gaps']['gaps_gte_30min']:
            lines.append(f"| {g['from']} | {g['to']} | {g['gap_minutes']} |")
        lines.append("")

    lines += [
        f"## 3. December Density",
        f"",
        f"- Dec avg: **{c['dec_density']['dec_avg_per_day']}/day** vs Jan: **{c['dec_density']['jan_avg_per_day']}/day**",
        f"- Dec 05 rows: **{c['dec_density']['dec_05_rows']}**",
        f"- Dec 06 rows: **{c['dec_density']['dec_06_rows']}**",
        f"- Dec 05–06 avg: **{c['dec_density']['dec_05_06_avg']}/day**",
        f"- Dec 07–31 avg: **{c['dec_density']['dec_07_31_avg']}/day**",
        f"- **{c['dec_density']['interpretation']}**",
        f"",
        f"## 4. UTC / CPT Boundary",
        f"",
        f"- Dec 05 rows before 06:00Z (ERCOT day 2025-12-04): **{c['utc_cpt']['dec_05_before_0600z']}**",
        f"- Dec 05 rows after 06:00Z (ERCOT day 2025-12-05): **{c['utc_cpt']['dec_05_after_0600z']}**",
        f"- Earliest row in dataset: `{c['utc_cpt']['earliest_row_utc']}`",
        f"",
        f"> {c['utc_cpt']['note']}",
        f"",
        f"## 5. Resource Status",
        f"",
    ]

    for status, info in c['status']['distinct_values'].items():
        lines.append(f"- `{status}`: {info['count']:,} rows ({info['pct']}%)")

    lines += [
        f"",
        f"> {c['status']['note']}",
        f"",
        f"## 6. NULL Counts",
        f"",
        f"| Column | NULLs | % | Flag |",
        f"|--------|-------|---|------|",
    ]

    for col, info in c['nulls']['columns'].items():
        lines.append(f"| `{col}` | {info['null_count']:,} | {info['null_pct']}% | {flag_icon(info['flag'])} {info['flag']} |")

    lines += [
        f"",
        f"> {c['nulls']['note']}",
        f"",
        f"## 7. Sign Convention",
        f"",
        f"| Pattern | Count | Interpretation |",
        f"|---------|-------|----------------|",
        f"| TNO > 0, SoC ↓ | {c['sign']['pos_tno_soc_decreasing_discharge']:,} | ✅ Discharge (positive = export) |",
        f"| TNO > 0, SoC ↑ | {c['sign']['pos_tno_soc_increasing_anomaly']:,} | ⚠️ Anomaly |",
        f"| TNO < 0, SoC ↑ | {c['sign']['neg_tno_soc_increasing_charge']:,} | ✅ Charge (negative = import) |",
        f"| TNO < 0, SoC ↓ | {c['sign']['neg_tno_soc_decreasing_anomaly']:,} | ⚠️ Anomaly |",
        f"",
        f"Sign convention confirmed from data: **{c['sign']['sign_convention_confirmed']}**",
        f"",
        f"---",
        f"*End of L1 report — proceed to analysis.py only if all flags are PASS or WARN with documented disposition.*",
    ]

    path.write_text("\n".join(lines), encoding="utf-8")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("Loading CSV chunks...")
    rows = load_all_rows()

    print("\n[1/7] Duplicates...")
    dup = check_duplicates(rows)

    print("[2/7] Gap histogram...")
    gaps = check_gaps(rows)

    print("[3/7] December density...")
    dec = check_dec_density(rows)

    print("[4/7] UTC/CPT boundary...")
    utc = check_utc_cpt(rows)

    print("[5/7] Resource status...")
    status = check_status(rows)

    print("[6/7] NULL counts...")
    nulls = check_nulls(rows)

    print("[7/7] Sign convention...")
    sign = check_sign(rows)

    flags = {
        "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_rows_pre_dedup": len(rows),
        "checks": {
            "duplicates": dup,
            "gaps": gaps,
            "dec_density": dec,
            "utc_cpt": utc,
            "status": status,
            "nulls": nulls,
            "sign": sign,
        },
    }

    FLAGS_PATH.write_text(json.dumps(flags, indent=2, default=str), encoding="utf-8")
    write_report(flags, REPORT_PATH)

    # Console summary
    fi = lambda f: {"PASS": "✅", "WARN": "⚠ ", "FAIL": "❌", "INFO": "ℹ "}.get(f, "? ")
    print(f"\n{'='*58}")
    print("L1 INTEGRITY SUMMARY")
    print(f"{'='*58}")
    print(f"  Rows (pre-dedup):  {len(rows):,}")
    print(f"  Duplicates:        {fi(dup['flag'])} {dup['duplicate_timestamps']} dup timestamps")
    print(f"  Gaps:              {fi(gaps['flag'])} mode={gaps['mode_gap_seconds']}s  ≥600s:{gaps['gte_600s']}  largest:{gaps['largest_gap_minutes']}min")
    print(f"  Dec density:       {fi(dec['flag'])} {dec['interpretation'][:60]}")
    print(f"    Dec05: {dec['dec_05_rows']}  Dec06: {dec['dec_06_rows']}  Dec07-31avg: {dec['dec_07_31_avg']}/day")
    print(f"  UTC/CPT:           {fi(utc['flag'])} Dec05 before 06:00Z: {utc['dec_05_before_0600z']} rows")
    print(f"  Status:            {fi(status['flag'])} {dict(list(status['distinct_values'].items())[:4])}")
    print(f"  NULLs (soc):       {fi(nulls['flag'])} {nulls['columns']['soc']['null_pct']}%")
    print(f"  Sign conv.:        {fi(sign['flag'])} confirmed={sign['sign_convention_confirmed']}")
    print(f"{'='*58}")
    print(f"  Report: {REPORT_PATH}")
    print(f"  Flags:  {FLAGS_PATH}")

    return flags


if __name__ == "__main__":
    main()
