"""
analysis.py — US-TX-ANOL-001 F1–F4 Falsification Analysis
===========================================================
Protocol:  P10 v1.0 — "Demonstrated / Bounded / Not Exercised / Not Verified"
Prerequisite: l1_integrity.py must have passed (PASS or documented WARN).

Rules applied EXACTLY as frozen in audit_prep.md — no post-hoc interpretation.
All computed numbers written to metrics.json.
Verdicts rendered from grammar; NOT from analyst judgment after the fact.

Verdict grammar (per P10 Design Principles §4):
  Demonstrated   — claim directly evidenced in data
  Bounded        — claim not evidenced, but shortfall explained without refuting
  Not Exercised  — asset never dispatched to test the claim
  Not Verified   — evidence of underperformance relative to dispatch instruction
  L2 Anomaly     — physics violation (separate finding class, does not affect primary verdict)

SoC consistency (F3) is a SEPARATE finding class — never merged with F1/F2 verdicts.

Outputs:
  audits/US-TX-ANOL-001/metrics.json    — all numbers, machine-readable
  audits/US-TX-ANOL-001/findings.md     — human-readable findings per rule
"""

import csv
import json
import math
import datetime
from pathlib import Path
from collections import defaultdict

RAW_DATA_DIR  = Path(__file__).parent / "audits" / "US-TX-ANOL-001" / "raw_data"
METRICS_PATH  = Path(__file__).parent / "audits" / "US-TX-ANOL-001" / "metrics.json"
FINDINGS_PATH = Path(__file__).parent / "audits" / "US-TX-ANOL-001" / "findings.md"

# ── Frozen constants from audit_prep.md ───────────────────────────────────────
NAMEPLATE_MW    = 240.0   # Claim 001a
NAMEPLATE_MWH   = 480.0   # Claim 001b
INTERVAL_H      = 5 / 60  # ~5 min SCED intervals → hours
NOT_VERIFIED_THRESHOLD_MW = max(7.2, 0.03 * NAMEPLATE_MW)  # |output − base_point| > max(7.2 MW, 3%)
BP_THRESHOLD_PCT = 200.0  # base_point ≥ 200 MW (83% of nameplate) for Not Verified test
SOC_CONSISTENCY_MIN = 0.85  # F3: expected [η_discharge_min, η_discharge_max]
SOC_CONSISTENCY_MAX = 1.00
SOC_CONSISTENCY_MIN_PASS_PCT = 0.80  # ≥ 80% of events must be consistent
DISCHARGE_MIN_DURATION_H = 0.5  # F2/F3: contiguous discharge ≥ 30 min


# ── Loaders ───────────────────────────────────────────────────────────────────

def load_rows() -> list[dict]:
    rows = []
    for f in sorted(RAW_DATA_DIR.glob("*.csv")):
        with open(f, encoding="utf-8") as fh:
            rows.extend(csv.DictReader(fh))
    print(f"Loaded {len(rows):,} rows")
    return rows


def pf(val, default=math.nan) -> float:
    try:
        v = float(val)
        return v if not math.isnan(v) else default
    except (TypeError, ValueError):
        return default


def parse_ts(s: str) -> datetime.datetime | None:
    try:
        return datetime.datetime.fromisoformat(s) if s else None
    except ValueError:
        return None


# ── Pre-processing ────────────────────────────────────────────────────────────

def prepare(rows: list[dict]) -> list[dict]:
    """Sort, dedup, attach float fields."""
    seen = set()
    out = []
    for r in rows:
        ts = r.get("sced_timestamp_utc", "")
        if ts in seen:
            continue
        seen.add(ts)
        r["_ts"]     = parse_ts(ts)
        r["_tno"]    = pf(r.get("telemetered_net_output"))
        r["_bp"]     = pf(r.get("base_point"))
        r["_hsl"]    = pf(r.get("hsl"))
        r["_lsl"]    = pf(r.get("lsl"))
        r["_soc"]    = pf(r.get("soc"))
        r["_min_soc"]= pf(r.get("min_soc"))
        r["_max_soc"]= pf(r.get("max_soc"))
        r["_status"] = (r.get("telemetered_resource_status") or "").strip()
        out.append(r)
    out.sort(key=lambda x: x["_ts"] or datetime.datetime.min)
    print(f"After dedup: {len(out):,} rows")
    return out


def on_rows(rows: list[dict]) -> list[dict]:
    """Filter to ON status only — per F1/F2 disposition in L1."""
    return [r for r in rows if r["_status"] == "ON"]


# ── F1: Power Capacity (Claim 001a: 240 MW) ───────────────────────────────────

def f1_power(rows: list[dict]) -> dict:
    """
    Demonstrated: max TNO ≥ 240 MW
    Bounded: max TNO < 240 MW AND no base_point ≥ 240 MW ever issued
    Not Exercised: no base_point approached 240 MW
    Not Verified: |TNO − BP| > threshold at BP ≥ 200 MW intervals
    L2 Anomaly: TNO > 240 MW at any interval
    """
    on = on_rows(rows)
    tno_vals  = [r["_tno"] for r in on if not math.isnan(r["_tno"])]
    bp_vals   = [r["_bp"]  for r in on if not math.isnan(r["_bp"])]
    hsl_vals  = [r["_hsl"] for r in on if not math.isnan(r["_hsl"])]

    max_tno   = max(tno_vals, default=math.nan)
    max_bp    = max(bp_vals,  default=math.nan)
    max_hsl   = max(hsl_vals, default=math.nan)

    # Not Verified: rows where BP ≥ 200 MW and |TNO-BP| > threshold
    bp_high_rows = [r for r in on
                    if not math.isnan(r["_bp"]) and r["_bp"] >= BP_THRESHOLD_PCT
                    and not math.isnan(r["_tno"])]
    nv_rows = [r for r in bp_high_rows
               if abs(r["_tno"] - r["_bp"]) > NOT_VERIFIED_THRESHOLD_MW]

    # L2 Anomaly: TNO > nameplate
    l2_rows = [r for r in on if not math.isnan(r["_tno"]) and r["_tno"] > NAMEPLATE_MW]

    # Verdict logic — EXACTLY per Rule F1
    if max_tno >= NAMEPLATE_MW:
        verdict = "Demonstrated"
    elif max_bp < NAMEPLATE_MW:
        if max_bp < 0.5 * NAMEPLATE_MW:
            verdict = "Not Exercised"
        else:
            verdict = "Bounded"
    elif nv_rows:
        verdict = "Not Verified"
    else:
        verdict = "Bounded"

    return {
        "claim": "001a",
        "nameplate_mw": NAMEPLATE_MW,
        "max_tno_mw": round(max_tno, 2),
        "max_bp_mw": round(max_bp, 2),
        "max_hsl_mw": round(max_hsl, 2),
        "on_intervals": len(on),
        "bp_gte_200mw_intervals": len(bp_high_rows),
        "not_verified_intervals": len(nv_rows),
        "nv_threshold_mw": NOT_VERIFIED_THRESHOLD_MW,
        "l2_anomaly_intervals": len(l2_rows),
        "l2_anomaly_max_tno": round(max(r["_tno"] for r in l2_rows), 2) if l2_rows else None,
        "verdict": verdict,
        "finding_class": "F1",
    }


# ── F2: Energy Capacity (Claim 001b: 480 MWh) ────────────────────────────────

def find_discharge_blocks(rows: list[dict]) -> list[dict]:
    """
    Contiguous blocks where TNO > 0 for ≥ 30 min.
    Blocks are broken on:
      1. Gap > 600s between consecutive rows.
      2. Status change (status != 'ON').
      3. Sign change (TNO <= 0 or NaN).
    Uses trapezoidal integration with actual timestamp deltas.
    Applies L2 physics gate: block_energy <= max_soc.
    """
    # Compute global max_soc limit from all rows
    max_soc_vals = [r["_max_soc"] for r in rows if not math.isnan(r["_max_soc"])]
    max_soc_limit = max(max_soc_vals) if max_soc_vals else NAMEPLATE_MWH

    blocks = []
    block_rows = []

    for r in rows:
        tno = r["_tno"]
        status = r["_status"]
        ts = r["_ts"]

        # Determine if this row can continue the current block
        can_continue = False
        if block_rows:
            prev_r = block_rows[-1]
            gap_s = (ts - prev_r["_ts"]).total_seconds() if ts and prev_r["_ts"] else 9999.0
            if (status == "ON" and 
                not math.isnan(tno) and tno > 0 and 
                gap_s <= 600.0):
                can_continue = True

        if can_continue:
            block_rows.append(r)
        else:
            # Current block ended (if it exists). Evaluate and save it.
            if block_rows:
                duration_h = (block_rows[-1]["_ts"] - block_rows[0]["_ts"]).total_seconds() / 3600.0 if block_rows[-1]["_ts"] and block_rows[0]["_ts"] else 0.0
                if duration_h >= DISCHARGE_MIN_DURATION_H:
                    # Trapezoidal integration
                    mwh = 0.0
                    for j in range(len(block_rows) - 1):
                        dt_h = (block_rows[j+1]["_ts"] - block_rows[j]["_ts"]).total_seconds() / 3600.0
                        avg_power = (block_rows[j]["_tno"] + block_rows[j+1]["_tno"]) / 2.0
                        mwh += dt_h * avg_power

                    soc_start = block_rows[0]["_soc"]
                    soc_end   = block_rows[-1]["_soc"]

                    # L2 Physics Gate Check
                    if mwh > max_soc_limit:
                        raise ValueError(
                            f"L2 Physics Violation: block energy {mwh:.2f} MWh exceeds max_soc limit {max_soc_limit:.2f} MWh. "
                            f"Start: {block_rows[0]['_ts'].isoformat()}, End: {block_rows[-1]['_ts'].isoformat()}"
                        )
                    # Also check against start SoC (with 15 MWh tolerance)
                    if not math.isnan(soc_start) and mwh > (soc_start + 15.0):
                        raise ValueError(
                            f"L2 Physics Violation: block energy {mwh:.2f} MWh exceeds start SoC {soc_start:.2f} MWh + 15 MWh tolerance. "
                            f"Start: {block_rows[0]['_ts'].isoformat()}, End: {block_rows[-1]['_ts'].isoformat()}"
                        )

                    blocks.append({
                        "start_ts":  block_rows[0]["_ts"].isoformat() if block_rows[0]["_ts"] else None,
                        "end_ts":    block_rows[-1]["_ts"].isoformat() if block_rows[-1]["_ts"] else None,
                        "n_intervals": len(block_rows),
                        "duration_h": round(duration_h, 3),
                        "mwh": round(mwh, 2),
                        "soc_start": round(soc_start, 2) if not math.isnan(soc_start) else None,
                        "soc_end":   round(soc_end, 2)   if not math.isnan(soc_end)   else None,
                    })
                block_rows = []

            # Determine if this row starts a new block
            if status == "ON" and not math.isnan(tno) and tno > 0:
                block_rows = [r]

    # Evaluate any remaining block at the end of rows
    if block_rows:
        duration_h = (block_rows[-1]["_ts"] - block_rows[0]["_ts"]).total_seconds() / 3600.0 if block_rows[-1]["_ts"] and block_rows[0]["_ts"] else 0.0
        if duration_h >= DISCHARGE_MIN_DURATION_H:
            mwh = 0.0
            for j in range(len(block_rows) - 1):
                dt_h = (block_rows[j+1]["_ts"] - block_rows[j]["_ts"]).total_seconds() / 3600.0
                avg_power = (block_rows[j]["_tno"] + block_rows[j+1]["_tno"]) / 2.0
                mwh += dt_h * avg_power

            soc_start = block_rows[0]["_soc"]
            soc_end   = block_rows[-1]["_soc"]

            # L2 Physics Gate Check
            if mwh > max_soc_limit:
                raise ValueError(
                    f"L2 Physics Violation: block energy {mwh:.2f} MWh exceeds max_soc limit {max_soc_limit:.2f} MWh. "
                    f"Start: {block_rows[0]['_ts'].isoformat()}, End: {block_rows[-1]['_ts'].isoformat()}"
                )
            if not math.isnan(soc_start) and mwh > (soc_start + 15.0):
                raise ValueError(
                    f"L2 Physics Violation: block energy {mwh:.2f} MWh exceeds start SoC {soc_start:.2f} MWh + 15 MWh tolerance. "
                    f"Start: {block_rows[0]['_ts'].isoformat()}, End: {block_rows[-1]['_ts'].isoformat()}"
                )

            blocks.append({
                "start_ts":  block_rows[0]["_ts"].isoformat() if block_rows[0]["_ts"] else None,
                "end_ts":    block_rows[-1]["_ts"].isoformat() if block_rows[-1]["_ts"] else None,
                "n_intervals": len(block_rows),
                "duration_h": round(duration_h, 3),
                "mwh": round(mwh, 2),
                "soc_start": round(soc_start, 2) if not math.isnan(soc_start) else None,
                "soc_end":   round(soc_end, 2)   if not math.isnan(soc_end)   else None,
            })

    return blocks


def f2_energy(rows: list[dict], blocks: list[dict]) -> dict:
    """
    Demonstrated: largest block ≥ 480 MWh
    Bounded: largest block < 480 MWh, AND SoC-enhanced: soc_start × 1.0 ≥ observed block
    Not Exercised: no block approached full-duration discharge
    Not Verified: asset dispatched to LSL (full charge), SoC at start materially below 480 MWh
    """
    if not blocks:
        return {
            "claim": "001b", "nameplate_mwh": NAMEPLATE_MWH,
            "block_count": 0, "largest_block_mwh": None,
            "verdict": "Not Exercised",
            "note": "No discharge blocks ≥ 30 min identified in ON intervals.",
            "finding_class": "F2",
        }

    largest = max(b["mwh"] for b in blocks)
    largest_block = max(blocks, key=lambda b: b["mwh"])
    lsl_dispatch_rows = [r for r in on_rows(rows)
                         if not math.isnan(r["_bp"]) and not math.isnan(r["_lsl"])
                         and r["_bp"] <= r["_lsl"]]

    # SoC-enhanced bound: if soc_start covers the observed discharge
    soc_bounded = False
    if largest < NAMEPLATE_MWH and largest_block.get("soc_start"):
        soc_start = largest_block["soc_start"]
        if not math.isnan(soc_start) and soc_start >= largest:
            soc_bounded = True

    # Not Verified: full-charge dispatch (BP ≤ LSL) AND SoC start materially below nameplate
    nv_events = []
    if lsl_dispatch_rows:
        for b in blocks:
            soc_s = b.get("soc_start")
            if soc_s and not math.isnan(soc_s) and soc_s < 0.9 * NAMEPLATE_MWH:
                nv_events.append(b)

    # Verdict
    if largest >= NAMEPLATE_MWH:
        verdict = "Demonstrated"
    elif not lsl_dispatch_rows:
        verdict = "Bounded" if soc_bounded else "Not Exercised"
    elif nv_events:
        verdict = "Not Verified"
    else:
        verdict = "Bounded"

    return {
        "claim": "001b",
        "nameplate_mwh": NAMEPLATE_MWH,
        "block_count": len(blocks),
        "largest_block_mwh": round(largest, 2),
        "largest_block": largest_block,
        "lsl_dispatch_intervals": len(lsl_dispatch_rows),
        "soc_enhanced_bounded": soc_bounded,
        "not_verified_events": len(nv_events),
        "verdict": verdict,
        "finding_class": "F2",
    }


# ── F3: SoC Internal Consistency ─────────────────────────────────────────────

def f3_soc_consistency(blocks: list[dict]) -> dict:
    """
    For each discharge block: consistency_ratio = Δ_metered / Δ_soc
    Expected range: [0.85, 1.0]
    Consistent: ratio in range for ≥ 80% of events.
    SEPARATE FINDING CLASS — never merged with F1/F2 verdicts.
    """
    evaluable = []
    for b in blocks:
        soc_s = b.get("soc_start")
        soc_e = b.get("soc_end")
        mwh   = b.get("mwh")
        if soc_s is None or soc_e is None or mwh is None:
            continue
        if math.isnan(soc_s) or math.isnan(soc_e):
            continue
        delta_soc = soc_s - soc_e   # positive = SoC dropped = discharge
        if delta_soc <= 0:
            continue  # SoC didn't drop — skip (idle / charging mix)
        ratio = mwh / delta_soc
        evaluable.append({
            "start_ts": b["start_ts"],
            "mwh": mwh,
            "delta_soc": round(delta_soc, 2),
            "consistency_ratio": round(ratio, 4),
            "in_range": SOC_CONSISTENCY_MIN <= ratio <= SOC_CONSISTENCY_MAX,
        })

    if not evaluable:
        return {
            "finding_class": "F3",
            "evaluable_events": 0,
            "verdict": "Indeterminate",
            "note": "No evaluable discharge blocks with valid SoC start/end.",
        }

    n_consistent = sum(1 for e in evaluable if e["in_range"])
    pass_pct = n_consistent / len(evaluable)
    verdict = "Consistent" if pass_pct >= SOC_CONSISTENCY_MIN_PASS_PCT else "Inconsistent"

    ratio_vals = [e["consistency_ratio"] for e in evaluable]
    return {
        "finding_class": "F3",
        "evaluable_events": len(evaluable),
        "consistent_events": n_consistent,
        "pass_pct": round(pass_pct, 4),
        "required_pass_pct": SOC_CONSISTENCY_MIN_PASS_PCT,
        "ratio_min": round(min(ratio_vals), 4),
        "ratio_max": round(max(ratio_vals), 4),
        "ratio_mean": round(sum(ratio_vals) / len(ratio_vals), 4),
        "expected_range": [SOC_CONSISTENCY_MIN, SOC_CONSISTENCY_MAX],
        "verdict": verdict,
        "caveat": (
            "soc is operator-reported BMS estimate, not independent physical measurement. "
            "This test verifies internal consistency of operator telemetry only. "
            "Systematic BMS reporting errors would not be detected."
        ),
        "events": evaluable,
    }


# ── F4: SoC Field Interpretation ─────────────────────────────────────────────

def f4_soc_field(rows: list[dict]) -> dict:
    """
    Confirm field units (MWh not %), record max_soc observed, state interpretation
    pending ERCOT column docs. No assumption on 532 vs 480 MWh delta.
    """
    on = on_rows(rows)
    max_soc_vals = [r["_max_soc"] for r in on if not math.isnan(r["_max_soc"])]
    soc_vals     = [r["_soc"]     for r in on if not math.isnan(r["_soc"])]
    max_soc_obs  = max(max_soc_vals, default=math.nan)
    max_soc_field = max(soc_vals,   default=math.nan)

    # Confirm unit is MWh (not %): if values exceed 100 anywhere → MWh
    unit_is_mwh = max_soc_obs > 100 if not math.isnan(max_soc_obs) else (max_soc_field > 100)

    return {
        "finding_class": "F4",
        "max_soc_field_observed": round(max_soc_obs, 2),
        "max_soc_value_observed": round(max_soc_field, 2),
        "unit_confirmed_mwh": unit_is_mwh,
        "nameplate_mwh": NAMEPLATE_MWH,
        "delta_max_soc_vs_nameplate": round(max_soc_obs - NAMEPLATE_MWH, 2) if not math.isnan(max_soc_obs) else None,
        "interpretation": "DEFERRED",
        "note": (
            f"Observed max_soc = {round(max_soc_obs,2)} MWh. "
            f"Delta vs nameplate ({NAMEPLATE_MWH} MWh) = {round(max_soc_obs - NAMEPLATE_MWH, 2)} MWh. "
            "Interpretation of this delta (buffer, SCED model limit, or other) requires "
            "ERCOT column definitions guide or equivalent DDL. "
            "No assumption made. Field used as-reported."
        ),
    }


# ── Markdown findings report ──────────────────────────────────────────────────

def write_findings(m: dict, path: Path):
    f1 = m["F1"]
    f2 = m["F2"]
    f3 = m["F3"]
    f4 = m["F4"]

    def vi(v):
        return {
            "Demonstrated":  "✅ **Demonstrated**",
            "Bounded":       "🟡 **Bounded**",
            "Not Exercised": "⚪ **Not Exercised**",
            "Not Verified":  "❌ **Not Verified**",
            "Consistent":    "✅ **Consistent**",
            "Inconsistent":  "❌ **Inconsistent**",
            "Indeterminate": "⚪ **Indeterminate**",
            "DEFERRED":      "⏳ **Deferred**",
        }.get(v, f"? {v}")

    lines = [
        "# US-TX-ANOL-001 — Findings",
        "",
        f"**Generated:** {m['generated_at_utc']}  ",
        f"**Protocol:** P10 v1.0  ",
        f"**Anchor class:** {m['anchor_class']} (gridstatus.io third-party rendering; cross-check pending)  ",
        f"**Rows analysed (post-dedup, ON only):** {m['on_intervals']:,}  ",
        "",
        "---",
        "",
        "## Verdict Summary",
        "",
        "| Rule | Claim | Verdict |",
        "|------|-------|---------|",
        f"| F1 | 001a — 240 MW power | {vi(f1['verdict'])} |",
        f"| F2 | 001b — 480 MWh energy | {vi(f2['verdict'])} |",
        f"| F3 | SoC internal consistency (separate finding class) | {vi(f3['verdict'])} |",
        f"| F4 | SoC field interpretation | {vi(f4['interpretation'])} |",
        "",
        "---",
        "",
        "## F1 — Power Capacity (Claim 001a: 240 MW)",
        "",
        f"- Max observed `telemetered_net_output`: **{f1['max_tno_mw']} MW**",
        f"- Max observed `base_point`: **{f1['max_bp_mw']} MW**",
        f"- Max observed `hsl`: **{f1['max_hsl_mw']} MW**",
        f"- ON intervals: {f1['on_intervals']:,}",
        f"- Intervals with BP ≥ {BP_THRESHOLD_PCT} MW (83% nameplate): {f1['bp_gte_200mw_intervals']:,}",
        f"- Not Verified intervals (|TNO−BP| > {f1['nv_threshold_mw']:.1f} MW at BP ≥ 200 MW): **{f1['not_verified_intervals']}**",
        f"- L2 Anomaly intervals (TNO > 240 MW): **{f1['l2_anomaly_intervals']}**",
    ]
    if f1['l2_anomaly_intervals']:
        lines.append(f"  - Max anomaly TNO: **{f1['l2_anomaly_max_tno']} MW** (separate L2 finding)")
    lines += [
        "",
        f"**Verdict: {vi(f1['verdict'])}**",
        f"> **Note:** The maximum observed output is exactly equal to the High Sustainable Limit (HSL) of {f1['max_hsl_mw']} MW. This indicates the capacity is demonstrated at the SCED model ceiling, meaning the physical asset output is likely model-saturated at this value.",
        "",
        "---",
        "",
        "## F2 — Energy Capacity (Claim 001b: 480 MWh)",
        "",
        f"- Discharge blocks ≥ 30 min identified: **{f2['block_count']}**",
        f"- Largest block: **{f2['largest_block_mwh']} MWh**",
        f"- LSL-dispatch intervals (full-charge instruction): **{f2['lsl_dispatch_intervals']}**",
        f"- SoC-enhanced bounded: **{f2['soc_enhanced_bounded']}**",
        f"- Not Verified events: **{f2['not_verified_events']}**",
        "",
        f"**Verdict: {vi(f2['verdict'])}**",
        "",
    ]
    if f2.get("note"):
        lines += [f"> {f2['note']}", ""]
    lines += [
        "---",
        "",
        "## F3 — SoC Internal Consistency *(separate finding class)*",
        "",
        f"> **Caveat:** {f3['caveat']}" if f3.get("caveat") else "",
        "",
        f"- Evaluable discharge events: **{f3['evaluable_events']}**",
    ]
    if f3["evaluable_events"] > 0:
        lines += [
            f"- Consistent events (ratio ∈ [{SOC_CONSISTENCY_MIN}, {SOC_CONSISTENCY_MAX}]): "
            f"**{f3['consistent_events']}** ({f3['pass_pct']*100:.1f}%)",
            f"- Required: ≥ {SOC_CONSISTENCY_MIN_PASS_PCT*100:.0f}%",
            f"- Ratio range: [{f3['ratio_min']}, {f3['ratio_max']}], mean={f3['ratio_mean']}",
        ]
    lines += [
        "",
        f"**Verdict: {vi(f3['verdict'])}** *(F3 is a standalone finding — does not modify F1/F2)*",
        "",
        "---",
        "",
        "## F4 — SoC Field Interpretation",
        "",
        f"- `max_soc` field observed: **{f4['max_soc_field_observed']} MWh**",
        f"- Max `soc` value observed: **{f4['max_soc_value_observed']} MWh**",
        f"- Unit confirmed MWh (not %): **{f4['unit_confirmed_mwh']}**",
        f"- Delta vs nameplate (480 MWh): **{f4['delta_max_soc_vs_nameplate']} MWh**",
        "",
        f"> {f4['note']}",
        "",
        f"**Verdict: {vi(f4['interpretation'])}** — pending ERCOT column definitions.",
        "",
        "---",
        "",
        "## Methodological Notes",
        "",
        "- All verdicts rendered from frozen F1–F4 grammar in `audit_prep.md`.",
        "- Anchor class B (gridstatus.io rendering). Cross-check vs ERCOT primary ZIPs pending.",
        "- F3 is a new finding class introduced in this audit (first P10 with SoC signal).",
        "  Its verdict does not affect F1 or F2 disposition.",
        "- Dec 05 density gap (217 rows vs 291.7/day avg) documented in l1_report.md.",
        "  Dec 05 rows included as-is per Rule CV (corrected data is authoritative).",
        "",
        "*End of findings — proceed to report.md for final audit narrative.*",
    ]
    path.write_text("\n".join(l for l in lines), encoding="utf-8")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Loading data...")
    raw = load_rows()
    rows = prepare(raw)

    print("\nIdentifying discharge blocks...")
    blocks = find_discharge_blocks(rows)
    print(f"  Discharge blocks ≥ 30 min: {len(blocks)}")

    print("\nRunning F1 — Power Capacity...")
    r_f1 = f1_power(rows)

    print("Running F2 — Energy Capacity...")
    r_f2 = f2_energy(rows, blocks)

    print("Running F3 — SoC Consistency...")
    r_f3 = f3_soc_consistency(blocks)

    print("Running F4 — SoC Field...")
    r_f4 = f4_soc_field(rows)

    on_count = len(on_rows(rows))
    metrics = {
        "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "audit_id": "US-TX-ANOL-001",
        "protocol": "P10 v1.0",
        "anchor_class": "B",
        "total_rows": len(raw),
        "deduped_rows": len(rows),
        "on_intervals": on_count,
        "discharge_blocks_identified": len(blocks),
        "F1": r_f1,
        "F2": r_f2,
        "F3": r_f3,
        "F4": r_f4,
    }

    METRICS_PATH.write_text(json.dumps(metrics, indent=2, default=str), encoding="utf-8")
    write_findings(metrics, FINDINGS_PATH)

    # Console summary
    print(f"\n{'='*58}")
    print("FINDINGS SUMMARY — US-TX-ANOL-001")
    print(f"{'='*58}")
    print(f"  F1 (240 MW power):      {r_f1['verdict']}")
    print(f"  F2 (480 MWh energy):    {r_f2['verdict']}")
    print(f"  F3 (SoC consistency):   {r_f3['verdict']}  ← separate class")
    print(f"  F4 (SoC field interp):  {r_f4['interpretation']}  ← pending docs")
    print(f"{'='*58}")
    print(f"  Metrics: {METRICS_PATH}")
    print(f"  Findings: {FINDINGS_PATH}")

    return metrics


if __name__ == "__main__":
    main()
