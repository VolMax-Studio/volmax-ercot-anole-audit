# US-TX-ANOL-001 — Findings

**Generated:** 2026-07-10T18:56:19.065087+00:00  
**Protocol:** P10 v1.0  
**Anchor class:** B (gridstatus.io third-party rendering; cross-check pending)  
**Rows analysed (post-dedup, ON only):** 42,422  

---

## Verdict Summary

| Rule | Claim | Verdict |
|------|-------|---------|
| F1 | 001a — 240 MW power | ✅ **Demonstrated** |
| F2 | 001b — 480 MWh energy | ✅ **Demonstrated** |
| F3 | SoC internal consistency (separate finding class) | ❌ **Inconsistent** |
| F4 | SoC field interpretation | ⏳ **Deferred** |

---

## F1 — Power Capacity (Claim 001a: 240 MW)

- Max observed `telemetered_net_output`: **240.0 MW**
- Max observed `base_point`: **240.0 MW**
- Max observed `hsl`: **240.0 MW**
- ON intervals: 42,422
- Intervals with BP ≥ 200.0 MW (83% nameplate): 3,264
- Not Verified intervals (|TNO−BP| > 7.2 MW at BP ≥ 200 MW): **601**
- L2 Anomaly intervals (TNO > 240 MW): **1226**
  - Max anomaly TNO: **240.0 MW** (separate L2 finding)

**Verdict: ✅ **Demonstrated****
> **Note:** The maximum observed output is exactly equal to the High Sustainable Limit (HSL) of 240.0 MW. This indicates the capacity is demonstrated at the SCED model ceiling, meaning the physical asset output is likely model-saturated at this value.

---

## F2 — Energy Capacity (Claim 001b: 480 MWh)

- Discharge blocks ≥ 30 min identified: **335**
- Largest block: **513.03 MWh**
- LSL-dispatch intervals (full-charge instruction): **4382**
- SoC-enhanced bounded: **False**
- Not Verified events: **101**

**Verdict: ✅ **Demonstrated****

---

## F3 — SoC Internal Consistency *(separate finding class)*

> **Caveat:** soc is operator-reported BMS estimate, not independent physical measurement. This test verifies internal consistency of operator telemetry only. Systematic BMS reporting errors would not be detected.

- Evaluable discharge events: **330**
- Consistent events (ratio ∈ [0.85, 1.0]): **182** (55.1%)
- Required: ≥ 80%
- Ratio range: [0.0187, 1.2545], mean=0.7136

**Verdict: ❌ **Inconsistent**** *(F3 is a standalone finding — does not modify F1/F2)*

---

## F4 — SoC Field Interpretation

- `max_soc` field observed: **560.32 MWh**
- Max `soc` value observed: **558.0 MWh**
- Unit confirmed MWh (not %): **True**
- Delta vs nameplate (480 MWh): **80.32 MWh**

> Observed max_soc = 560.32 MWh. Delta vs nameplate (480.0 MWh) = 80.32 MWh. Interpretation of this delta (buffer, SCED model limit, or other) requires ERCOT column definitions guide or equivalent DDL. No assumption made. Field used as-reported.

**Verdict: ⏳ **Deferred**** — pending ERCOT column definitions.

---

## Methodological Notes

- All verdicts rendered from frozen F1–F4 grammar in `audit_prep.md`.
- Anchor class B (gridstatus.io rendering). Cross-check vs ERCOT primary ZIPs pending.
- F3 is a new finding class introduced in this audit (first P10 with SoC signal).
  Its verdict does not affect F1 or F2 disposition.
- Dec 05 density gap (217 rows vs 291.7/day avg) documented in l1_report.md.
  Dec 05 rows included as-is per Rule CV (corrected data is authoritative).

*End of findings — proceed to report.md for final audit narrative.*