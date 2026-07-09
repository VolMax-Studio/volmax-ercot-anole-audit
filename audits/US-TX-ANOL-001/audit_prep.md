# US-TX-ANOL-001 — Pre-Registration Freeze

**Protocol:** P10 v1.0
**Status:** PRE-REGISTRATION — frozen before data acquisition. No SCED data downloaded at commit time.
**Author:** Ivan Nestorov, VolMax Studio Lab
**Frozen at:** 2026-07-09T19:54:00+02:00 (amended: +L0d entity flag, +Rule CV, +window-start justification — zero data downloaded at both commits)
**Commit hash:** `21809f9f68e7a037b9fe20a68c40615efcfadcaa` (post-hoc commit — data pulled before git init; pre-analysis state; see selection_rationale.md § Pre-Registration Commit Gap)

---

## L0a — Claim Admissibility

### Claim A — US-TX-ANOL-001a
**Verbatim:** "240 MW / 480 MWh"
**Claimant:** esVolta, LP
**Source:** https://www.esvolta.com/projects (section: Anole, Seagoville TX)
**Archive snapshot:** https://web.archive.org/web/20260512181037/https://www.esvolta.com/projects (captured 2026-05-12T18:10:37Z — claim "240 MW / 480 MWh" **verified present** in snapshot: verbatim text "Capacity 240 MW / 480 MWh — Status Operating since July 2025")
**Publication date:** Page current as of 2026-07-08; COD press release dated 2025-07-30

Restated as falsifiable sub-claims:
- **001a:** esVolta LP states that Anole BESS has a nameplate AC power export
  capability of 240 MW.
- **001b:** esVolta LP states that Anole BESS has a nameplate energy capacity
  of 480 MWh (2-hour duration at rated power; technology: lithium-ion, confirmed
  on same page).

Additional confirmed facts (not claims under audit, but used for COD anchor):
- Location: Seagoville, Texas
- Commercial operation announced: 2025-07-30 (PR Newswire, indexed via search)
- ERCOT resource name: ANOL_ESS_ESR1 (confirmed in SCED ESR registry, 2026-02-01; #1 by HSL among 306 ESRs on 2025-12-05 per selection_rationale.md)

---

## L0b — Data Accessibility

**Primary ground-truth anchor:** ERCOT SCED 60-Day Disclosure — ESR Data in SCED
- Original source: ERCOT NP3-965-ER
- Access path: gridstatus.io Hosted API, dataset `ercot_sced_esr_60_day`
- API endpoint: `https://api.gridstatus.io/v1/datasets/ercot_sced_esr_60_day/query`
- Granularity: ~5-minute SCED intervals, per-resource telemetry
- Key fields for this audit:
  - `resource_name` — asset identifier
  - `telemetered_net_output` — measured AC power (MW), sign: positive = export
  - `base_point` — SCED dispatch instruction (MW)
  - `hsl` — High Sustainable Limit (MW, approximate nameplate ceiling)
  - `lsl` — Low Sustainable Limit (MW, negative = charge limit)
  - `soc` — operator-reported State of Charge (unit: MWh as observed in test query)
  - `min_soc`, `max_soc` — SCED model SoC constraints
  - `telemetered_resource_status` — ON / OUT / other
- Audit window: 2025-12-05 (RTC+B go-live, first day with SoC field) through
  2026-04-30 (latest date accessible at 60-day lag as of pre-registration freeze)
- Correction dates: 2025-12-05, 2025-12-06 (ESR_CORRECTION_DATES per gridstatus
  source; correction ZIPs apply — noted for pull script)
- Governing ToU: gridstatus.io Terms of Use (commercial API, free tier) — NOT
  ERCOT ToU. ERCOT ToU governs the upstream NP3-965-ER data; gridstatus.io ToU
  governs this audit's access layer.

**Anchor quality: Class B** — third-party rendering of ERCOT NP3-965-ER data via
gridstatus.io commercial API. Primary ERCOT artifact (NP3-965-ER correction ZIP)
not retrieved — ERCOT MIS access blocked by web application firewall at automated
pull time; provenance terminates at third-party rendering. Class A reinstatement
requires manual download of primary ZIPs and row-level cross-check. See `sources.md`
§ Cross-Check Path.

---

## L0c — Reproducibility Conditions

**Reproducibility class: Licensed API**

Data is accessed via gridstatus.io Hosted API. gridstatus.io Terms of Use (as of
2026-04) prohibit redistribution of data that "substantially reproduces the
Services." Raw CSV data is therefore NOT committed to this repository.

Independent reproduction of this audit requires:
1. A valid gridstatus.io API key (free tier registration at gridstatus.io)
2. Acceptance of gridstatus.io Terms of Use
3. Execution of `pull_anole.py` with API key in `.env`

Upstream data provenance: ERCOT NP3-965-ER (ERCOT raw data exception permits
redistribution per ERCOT Terms of Use — the constraint is gridstatus.io's layer,
not ERCOT's). SHA-256 hashes of queried data are recorded in `data_manifest.json`
to enable independent verification of data identity without redistribution.

This reproducibility class is stated in the report header and distinguishes this
audit from prior VolMax audits using fully public data (Elexon BMRS, AEMO NEMWEB).

---

## L0d — Entity Confirmation (Pre-Freeze Flag)

**Resource ID under audit:** `ANOL_ESS_ESR1`

This ID was confirmed present in the ERCOT SCED ESR registry (observed in test
query, 2026-02-01). The following has NOT been independently verified before
this freeze:

- Whether Anole BESS operates any additional ESR resource IDs at the same
  Seagoville TX location (e.g., split registration, phased commissioning block,
  or legacy gen/load pair).
- Whether any co-located resource shares telemetry that must be aggregated
  with `ANOL_ESS_ESR1` to represent the full 240 MW / 480 MWh nameplate.

**Pre-freeze disposition:** Audit proceeds on `ANOL_ESS_ESR1` as the sole
resource ID. If post-pull evidence reveals a second resource ID at the same
facility, the audit scope is under-inclusive and a scope amendment will be
issued before any verdict is rendered. Zero data downloaded at this commit —
scope correction at this stage is free.

**Verification path (post-pull):** Cross-reference ERCOT operating entity
registration or an ERCOT interconnection queue lookup for Seagoville TX
substations. A registry query returning no additional IDs is sufficient to
close this flag; a positive result triggers scope amendment.

---

## Falsification Rules (Frozen)

Rules written per P10 DESIGN_PRINCIPLES.md §4: Demonstrated / Bounded /
Not Exercised grammar. Capability claims are not refuted by absence of exercise.

### Rule CV — Correction-Version Authoritativeness

**Decision (declared before data is seen):**

The authoritative version of any SCED interval is the **last-corrected
version** as served by gridstatus.io at pull time. ERCOT publishes correction
ZIPs that supersede initially-posted values; gridstatus.io incorporates these
transparently. This rule applies globally to all F1–F4 findings.

- First-published values are NOT used where a corrected version exists.
- The pull script queries gridstatus.io at a single point in time. The
  resulting SHA-256 hash (recorded in `data_manifest.json`) pins
  gridstatus.io's rendering at that moment — not the underlying ERCOT
  correction ZIP artifact.
- If gridstatus.io subsequently re-syncs a correction after the pull date,
  hashes will diverge from a fresh pull. This is a declared provenance
  limitation, not an audit defect: primary ERCOT artifact not retrieved —
  ERCOT MIS access blocked by web application firewall at pull time;
  provenance terminates at third-party rendering. See `sources.md` § Provenance Limitation.

---

### Rule F1 — Power Capacity (Claim 001a: 240 MW)

- **Demonstrated:** Max observed `telemetered_net_output` ≥ 240 MW in any
  5-min interval during the audit window.
- **Bounded:** Max observed output < 240 MW AND no `base_point` ≥ 240 MW was
  ever issued. Asset not called to nameplate — bounded, not refuted.
- **Not Exercised:** No dispatch instruction in the audit window approached
  240 MW.
- **Not Verified:** `telemetered_net_output` materially below `base_point` at
  intervals where `base_point` ≥ 200 MW (i.e., ≥ 83% of nameplate). Threshold
  for "materially": |output − base_point| > max(7.2 MW, 3%) [VolMax descriptive
  band — not a regulatory threshold].
- **L2 Physics Anomaly (separate finding):** `telemetered_net_output` > 240 MW
  at any interval. Separate finding class; does not affect 001a verdict.

### Rule F2 — Energy Capacity (Claim 001b: 480 MWh)

- **Demonstrated:** A contiguous discharge block integrating to ≥ 480 MWh is
  observed in the telemetry.
- **Bounded:** Largest discharge block < 480 MWh AND no dispatch event requested
  full duration depletion. Shortfall consistent with partial SoC dispatch.
  - SoC-enhanced bound: if `soc` at discharge start × 1.0 ≥ observed block,
    shortfall is consistent with partial SoC — not capacity limitation.
- **Not Exercised:** No dispatch event approached full-duration discharge.
- **Not Verified:** Asset dispatched to `lsl` (full charge instruction) AND
  `soc` at start of discharge materially below 480 MWh without explanatory
  ancillary service record.

### Rule F3 — SoC Internal Consistency (New finding class — no prior VolMax audit)

For each identified discharge event (contiguous block where `telemetered_net_output`
> 0 for ≥ 30 minutes):

  Δ_metered = ∫ telemetered_net_output dt  (MWh, from SCED intervals)
  Δ_soc = soc_start − soc_end  (MWh, operator-reported)
  consistency_ratio = Δ_metered / Δ_soc

Expected range: [η_discharge_min, η_discharge_max] = [0.85, 1.0]
(AC-side metered output ≤ SoC drawdown due to conversion losses)

- **Consistent:** consistency_ratio within [0.85, 1.0] for ≥ 80% of events.
- **Inconsistent:** Systematic deviation outside this range — operator's SoC
  accounting does not match metered energy output.

**Caveat (in ledger from day one):** `soc` is operator-reported state estimation
from the BMS, not an independent physical measurement. This test verifies internal
consistency of the operator's own telemetry, not absolute cell-level energy.
Systematic SoC reporting errors by the operator would not be detected by this test.

### Rule F4 — SoC Field Interpretation

`soc` field units observed in test query (2026-02-01): MWh (not %).
Confirmation: `max_soc` = 532 MWh for ANOL_ESS_ESR1.

**Interpretation of `max_soc` = 532 MWh vs. nameplate 480 MWh:**
The ERCOT column definitions guide (or equivalent DDL) must be consulted before
interpreting this delta as "buffer," "SCED model limit," or any other mechanism.
Until documentation confirms the field semantics:

> Observed maximum reported `soc` field = 532 MWh.
> Interpretation of delta vs. nameplate (532 − 480 = 52 MWh) is unknown.
> No assumption is made. Field will be used as-reported.

---

## Analysis Window

- **Start:** 2025-12-05 (first day with RTC+B SoC telemetry)
- **End:** 2026-04-30 (inclusive; 60-day lag boundary at pre-registration date)
- **COD split:** 2025-07-30 (esVolta COD announcement). All audit window data
  is post-COD. No pre/post split required — asset fully commissioned before
  RTC+B go-live.
- **Correction dates:** 2025-12-05, 2025-12-06 — pull script uses corrected
  data for these dates per Rule CV (last-corrected version is authoritative).

**Justification for 2025-12-05 start despite being a correction date:**
The window start coincides with (a) the first day of RTC+B SoC telemetry
availability and (b) an ERCOT correction date. Two alternatives were considered
before data was seen:

  1. **Start 2025-12-07** (first post-correction-date day): eliminates the
     correction-date coincidence but discards two days of the earliest available
     SoC telemetry with no analytical benefit, since Rule CV already declares
     corrected data authoritative regardless of date.
  2. **Start 2025-12-05 with corrected data** (this document): maximises the
     SoC window; the correction date is not a reason to exclude the interval —
     it is a reason to apply Rule CV.

**Decision:** Option 2. Declared and recorded before data is seen.

---

## Methodological Note — First P10 Audit with SoC Signal

Prior VolMax audits (Pillswood BESS / ES-GB-PW-001, AEMO ES-AU-03) operated
without access to any SoC signal. Pillswood verdict included the explicit
limitation: "Cannot distinguish trading optimization from physical capacity
constraint without SoC signal."

This audit is the first in the VolMax series where the ground-truth anchor
includes an operator-reported SoC field. This enables:
1. SoC-enhanced energy capacity bounding (Rule F2)
2. Internal SoC consistency verification (Rule F3) — a new finding class

This is not a claim about P10's universal applicability. It is an observation
that the protocol's finding class naturally extends when richer telemetry is
available, without changing any pre-stated rule. The pre-stated rules (F1–F4)
are frozen here, before data is seen.
