# US-TX-ANOL-001 — L1 Data Integrity Report

**Generated:** 2026-07-09T18:14:10.648876+00:00  
**Protocol:** P10 v1.0  
**Rows loaded (pre-dedup):** 42,918  

---

## Summary

| Check | Flag |
|-------|------|
| 1. Duplicates | ✅ PASS |
| 2. Gap histogram | ⚠️ WARN |
| 3. December density | ⚠️ WARN |
| 4. UTC/CPT boundary | ✅ PASS |
| 5. Resource status | ℹ️ INFO |
| 6. NULL counts (SoC) | ✅ PASS |
| 7. Sign convention | ✅ PASS |

---

## 1. Duplicates

- Rows loaded: **42,918**
- Unique timestamps: **42,918**
- Duplicate timestamps: **0**
- Extra rows (to drop on dedup): **0**

## 2. Gap Histogram

- Mode gap: **300s** (12,259 occurrences, 28.56%)
- Gaps < 300s: 16507
- Gaps = 300s: 12,259
- Gaps 300s–600s: 14146
- Gaps ≥ 600s: **5** (largest: 16.7 min)

## 3. December Density

- Dec avg: **288.9/day** vs Jan: **292.8/day**
- Dec 05 rows: **217**
- Dec 06 rows: **291**
- Dec 05–06 avg: **254.0/day**
- Dec 07–31 avg: **291.7/day**
- **Deficit is in Dec 05-06 (correction dates + RTC+B go-live)**

## 4. UTC / CPT Boundary

- Dec 05 rows before 06:00Z (ERCOT day 2025-12-04): **0**
- Dec 05 rows after 06:00Z (ERCOT day 2025-12-05): **217**
- Earliest row in dataset: `2025-12-05T06:00:19+00:00`

> No pre-06:00Z rows on Dec 05. UTC and CPT windows are aligned for this day.

## 5. Resource Status

- `ON`: 42,422 rows (98.84%)
- `ONTEST`: 311 rows (0.72%)
- `OUT`: 123 rows (0.29%)
- `NULL`: 60 rows (0.14%)
- `ONOS`: 2 rows (0.0%)

> F1/F2 falsification tests should filter to ON rows only. OUT rows: asset not dispatched — telemetered_net_output not meaningful for capacity claims. ONTEST/ONRR: review before inclusion in F-tests.

## 6. NULL Counts

| Column | NULLs | % | Flag |
|--------|-------|---|------|
| `sced_timestamp_utc` | 0 | 0.0% | ✅ PASS |
| `telemetered_net_output` | 0 | 0.0% | ✅ PASS |
| `base_point` | 0 | 0.0% | ✅ PASS |
| `hsl` | 0 | 0.0% | ✅ PASS |
| `lsl` | 0 | 0.0% | ✅ PASS |
| `soc` | 0 | 0.0% | ✅ PASS |
| `min_soc` | 0 | 0.0% | ✅ PASS |
| `max_soc` | 0 | 0.0% | ✅ PASS |
| `telemetered_resource_status` | 60 | 0.14% | ✅ PASS |

> SoC NULL% is the key metric — F3 auditability depends on it.

## 7. Sign Convention

| Pattern | Count | Interpretation |
|---------|-------|----------------|
| TNO > 0, SoC ↓ | 5,423 | ✅ Discharge (positive = export) |
| TNO > 0, SoC ↑ | 153 | ⚠️ Anomaly |
| TNO < 0, SoC ↑ | 8,129 | ✅ Charge (negative = import) |
| TNO < 0, SoC ↓ | 1,645 | ⚠️ Anomaly |

Sign convention confirmed from data: **True**

---
*End of L1 report — proceed to analysis.py only if all flags are PASS or WARN with documented disposition.*