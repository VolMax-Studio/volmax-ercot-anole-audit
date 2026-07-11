# P10 Telemetry Audit Report: US-TX-ANOL-001 (esVolta Anole BESS)

**Audit ID:** US-TX-ANOL-001  
**Entity under Audit:** esVolta Anole BESS (ERCOT Resource ID: `ANOL_ESS_ESR1`)  
**Capacity Claims:** 240 MW Power Capacity (Claim 001a) / 480 MWh Energy Capacity (Claim 001b)  
**Audit Protocol:** VolMax P10 "Unfalsifiable-as-Stated" Protocol (v1.0)  
**Anchor Class:** **Class B (Third-Party Rendering)** — Provenance terminates at gridstatus.io Hosted API  
**Lead Auditor:** Ivan Nestorov (`volmax.core@gmail.com`), VolMax Studio Lab  
**Date of Issue:** 2026-07-10  

---

## 1. Executive Summary

This audit evaluates the grid-scale performance and physical telemetry consistency of the **esVolta Anole BESS (ANOL_ESS_ESR1)** located in Seagoville, Texas, using regulatory telemetry from **2025-12-05 through 2026-04-30** (inclusive). The audit marks the first deployment of the VolMax P10 protocol using State of Charge (SoC) telemetry, enabling direct physical integrity checks on the battery energy storage system.

Based on strict adherence to the frozen rules, the audit renders the following verdicts:
- **Power Capacity (Claim 001a - 240 MW):** ✅ **Demonstrated** at the SCED model ceiling (max output = 240.0 MW).
- **Energy Capacity (Claim 001b - 480 MWh):** ✅ **Demonstrated** (largest continuous block = 513.03 MWh, representing 107% of nominal capacity).
- **SoC Internal Consistency (F3):** ❌ **Inconsistent** under the strict 80% pass rule for all discharge events (55.2% pass rate), but rises to **81.8%** in an exploratory post-hoc analysis of major events (≥10 MWh). The overall verdict is Inconsistent as the post-hoc threshold was not pre-registered.
- **SoC Field Interpretation (F4):** ⏳ **Deferred** pending ERCOT column definition documentation (observed max SoC of 560.3 MWh, representing a delta of +80.3 MWh above nominal nameplate).

---

## 2. Capacity Claim Pinning & Registry Selection

The primary claims under audit were pinned to a historical snapshot prior to the analysis freeze:
1. **Wayback Machine Pin:** Verified against snapshot `web/20260512181037/esvolta.com/projects` showing:
   > *"Capacity: 240 MW / 480 MWh — Status: Operating since July 2025"*
2. **Registry Status:** Verified Anole BESS as the largest operating ESR in the ERCOT market by High Sustainable Limit (HSL) as of 2025-12-05 (240 MW, ranking #1 out of 306 registered ESRs).
3. **Entity Closure:** Confirmed that `ANOL_ESS_ESR1` is the only active Resource ID representing the facility (DME code: `YANOLE`).

---

## 3. Data Provenance & Limitations (Anchor Class B)

The retrieval pipeline for this audit operates under **Anchor Class B (Third-Party Rendering)**:
- **Upstream Origin:** ERCOT SCED 60-Day ESR telemetry disclosure (Report ID: `NP3-965-ER` / Report Type ID: `13052`).
- **Convenience Rendering:** `gridstatus.io` REST API (Dataset: `ercot_sced_esr_60_day`).
- **Licensing Constraint:** Raw CSV files are not redistributed in this repository to comply with the gridstatus.io Terms of Use. Verification of data identity is preserved via SHA-256 hashes of all raw monthly chunks in `data_manifest.json`.

### WAF / Geo-Block Verification
Due to ERCOT's Web Application Firewall (WAF) blocking non-US residential traffic, automated direct download of primary ERCOT ZIPs was blocked at pull time. On 2026-07-10, an automated check was run on a US-region GitHub Actions public runner (Run ID: `29136602701`) to test direct ERCOT MIS and Terms of Use page access. Both requests were blocked by the firewall, proving that ERCOT's WAF blocks US datacenter IP ranges in addition to residential traffic. The provenance chain therefore terminates at `gridstatus.io`. The manual browser download and row-level cross-check path is preserved in `sources.md` to allow future restoration to Anchor Class A.

---

## 4. L1 Data Integrity Summary

A preliminary L1 integrity audit (`l1_integrity.py`) was executed against the raw dataset (42,918 rows) prior to the falsification run. All checks passed:
- **Temporal Continuity:** 0 missing days; average of 291.8 rows/day (SCED execution interval ~4.9 minutes).
- **SoC Telemetry Availability:** 0.0% NULLs or NaNs in the `soc` column after 2025-12-05, confirming a complete SoC record.
- **Value Bounds:** Zero negative values in physical columns (`tno`, `bp`, `hsl`, `lsl`, `soc`).
- **Correction notices:** Dec 05-06 records were pulled using ERCOT's last-corrected sync per Rule CV.

---

## 5. Falsification Findings (F1–F4)

### F1 — Power Capacity (Claim 001a: 240 MW)
- **Max net output (`telemetered_net_output`):** **240.0 MW**
- **Max base point (`base_point`):** **240.0 MW**
- **Max High Sustainable Limit (`hsl`):** **240.0 MW**
- **Not Verified intervals:** 0 intervals (where base point ≥ 200 MW and output deviated by > 7.2 MW).
- **L2 Anomaly intervals (TNO > 240 MW):** 0 intervals.
- **Verdict:** ✅ **Demonstrated**
- *Note:* The peak output matches the HSL and base point ceiling exactly. Net power capacity is demonstrated precisely at the SCED model limit, indicating the physical asset is model-saturated at 240.0 MW.

### F2 — Energy Capacity (Claim 001b: 480 MWh)
- **Discharge Blocks (≥ 30 min):** 335 blocks identified.
- **Largest Continuous discharge block:** **513.03 MWh** (exceeding the 480.0 MWh nameplate claim by 6.8%).
  - **Start Time:** 2026-02-11T23:35:15+00:00 (SoC = 547.67 MWh, carrying the F4 semantic caveat)
  - **End Time:** 2026-02-12T01:45:17+00:00 (SoC = 11.89 MWh)
  - **Duration:** 2.167 hours
  - **L2 Physics Gate:** Passed (513.03 MWh ≤ 547.67 MWh start SoC; energy is physically consistent with charge depletion).
  - **Discharge-side SoC-accounting ratio:** 0.958 (a one-way ratio of metered discharge vs. SoC drop, not round-trip efficiency).
- **Verdict:** ✅ **Demonstrated**
- *Note:* The F2 verdict stands solely on metered energy (integrated telemetered output of 513.03 MWh), which is fully independent of the operator-reported SoC telemetry.

### F3 — SoC Internal Consistency (Separate Finding Class)
This test evaluates the physical relationship between AC-side metered output and DC-side SoC drawdown ($\Delta_{metered} / \Delta_{soc}$). The expected thermodynamic range is $[0.85, 1.0]$.
- **Total Evaluable events:** 330
- **Consistent events (ratio in range $[0.85, 1.0]$):** 182 (**55.2%**)
- **Verdict:** ❌ **Inconsistent** (under strict 80% pass rule)
- **Exploratory Post-Hoc Stratification:**
  As a post-hoc analysis (not pre-registered), filtering the events to major discharge cycles (energy ≥ 10 MWh) increases the consistency rate to **81.8%** (180 out of 220 events), clustering in the expected $[0.85, 1.0]$ physical band with a mean ratio of 0.94. This suggests micro-discharges (< 10 MWh) dominate the telemetry inconsistency due to timing skew and self-discharge. This threshold was not pre-registered and serves as a hypothesis for future audits, not a verdict modifier.
  
  Within the major cycles, 38 out of 220 events (17.3%) exhibit a consistency ratio strictly greater than 1.0 (ranging from 1.0009 to 1.2545). Since a ratio > 1.0 is thermodynamically impossible, these events are attributed to telemetry lag (SoC update delay relative to SCED net output at block boundaries) and minor BMS calibration offsets.

### F4 — SoC Field Interpretation
- **Max `max_soc` column value:** 560.3 MWh
- **Max `soc` value observed:** 558.0 MWh
- **Unit Confirmation:** Confirmed as MWh (values > 100).
- **Interpretation:** **Deferred**
- *Note:* The observed maximum SoC and `max_soc` limits are +80 MWh above the nominal 480 MWh nameplate. Without official ERCOT DDL documentation, it is impossible to determine whether this delta represents a physical battery over-sizing buffer, a model limit adjustment, or an alternative telemetry scaling factor. Field telemetry is utilized as-reported.

---

## 6. Verdict Ledger

| Claim | Description | Target | Metric Observed | Verdict |
|-------|-------------|--------|-----------------|---------|
| **001a** | Power Capacity | 240 MW | 240.0 MW | ✅ **Demonstrated** |
| **001b** | Energy Capacity | 480 MWh | 513.03 MWh | ✅ **Demonstrated** |
| **F3** | SoC telemetry consistency | ≥ 80% pass | 55.2% (81.8% major) | ❌ **Inconsistent** (caveated) |
| **F4** | SoC telemetry units/limit | - | Max SoC = 558.0 MWh | ⏳ **Deferred** |

---
*End of Report.*
