# US-TX-ANOL-001 — Source Provenance Declaration

**Protocol:** P10 v1.0
**Audit ID:** US-TX-ANOL-001
**Author:** Ivan Nestorov, VolMax Studio Lab
**Last amended:** 2026-07-09 (anchor class downgrade, WAF terminology correction, license re-check, cross-check path added)

---

## Primary Source — Anchor Class B (Third-Party Rendering)

| Field | Value |
|-------|-------|
| **Source name** | gridstatus.io Hosted API |
| **Dataset** | `ercot_sced_esr_60_day` |
| **Endpoint** | `https://api.gridstatus.io/v1/datasets/ercot_sced_esr_60_day/query` |
| **Upstream origin** | ERCOT NP3-965-ER (SCED 60-Day Disclosure) |
| **Access model** | Commercial API, free tier; API key required; gridstatus.io ToU apply |
| **Redistribution** | Raw CSV not committed — gridstatus.io ToU prohibition (non-sublicensable, non-transferable) |
| **Anchor class** | **B — third-party rendering of regulatory data** (not Class A primary artifact) |
| **Verification token** | SHA-256 per monthly chunk in `data_manifest.json` — pins gridstatus.io rendering, not ERCOT ZIP |

> **Class A reinstatement path:** Manual download of ERCOT NP3-965-ER correction ZIPs via browser (ERCOT MIS portal, no WAF block for browser sessions), independent hashing, and row-level cross-check against gridstatus CSVs. If cross-check passes, gridstatus becomes verified convenience layer; anchor class restored to A. See § Cross-Check Path.

---

## License — gridstatus.io (Actual Source)

**This section supersedes the prior ERCOT ToU reference, which was incorrect for the actual data source.**

gridstatus.io is a commercial service with its own Terms of Use, distinct from ERCOT's data terms:

- License granted: internal use, non-sublicensable, non-transferable
- **Prohibited:** reselling, sublicensing, publishing datasets that substantially reproduce the service
- **Prohibited:** creating competing products or services
- Raw CSV redistribution not permitted — consistent with audit policy (CSV not committed)
- API access for non-commercial research audit purposes: permitted under free tier

**Audit use is compliant** with gridstatus.io ToU as currently understood:
- No redistribution of raw data (SHA-256 hashes only)
- Non-commercial, non-competitive purpose (public audit research)
- No product created that substitutes for the service

**Open question:** gridstatus.io ToU text not independently reviewed line-by-line (Cloudflare blocks automated fetch). User must confirm ToU acceptance at: `https://www.gridstatus.io/terms`. This section reflects best-available characterization from public sources.

---

## Provenance Chain

**Current state (Anchor Class B):**
```
ERCOT market operations
    │
    ▼ SCED settlement telemetry (5-min intervals)
ERCOT NP3-965-ER public disclosure (primary ERCOT artifact)
    │
    ▼ ERCOT MIS portal — WAF blocks automated scripts; browser access works
    ▼ NOT RETRIEVED as primary artifact — chain interrupted here
gridstatus.io ingestion + correction sync (third-party rendering)
    │
    ▼ REST API query (this audit — pull_anole.py)
raw_data/*.csv  ←  SHA-256 → data_manifest.json
    │
    ▼ analysis pipeline (analysis.py)
report.md
```

**Target state (Anchor Class A — pending cross-check):**
```
ERCOT NP3-965-ER correction ZIPs (primary artifact)
    │  manually downloaded via browser by auditor
    │  SHA-256 hashed → primary_manifest.json
    ▼
cross_check.py: row-level comparison vs raw_data/*.csv
    │
    ▼ PASS → gridstatus rendering verified
    ▼ FAIL → discrepancy documented as finding
report.md (anchor class A, cross-check result recorded)
```

---

## § Provenance Limitation

**Primary ERCOT artifact not retrieved** — ERCOT MIS access blocked by web application firewall at pull time; provenance terminates at third-party rendering (gridstatus.io). This is a structural gap in the chain, not a data quality issue within the gridstatus dataset.

**WAF/Geo-block Verification:** On 2026-07-10, an automated test was run on a US-region GitHub Actions public runner (run ID 29116383279) to probe ERCOT MIS. The probe was blocked by ERCOT's WAF (HTTP status code non-200 or timeout), confirming that ERCOT blocks US datacenter IP ranges in addition to non-US residential traffic. This verifies that automated public CI US-region retrieval is not possible, and validates our Class B anchor designation.

**Hash-pinning scope:** SHA-256 hashes in `data_manifest.json` pin gridstatus.io's rendering at pull time. They do not hash the ERCOT NP3-965-ER correction ZIP artifact. If gridstatus.io re-syncs a late correction after the pull date, hashes will diverge from a fresh pull — this is expected behavior, not tampering.

**Correction notice M-B020626-01:** ERCOT issued corrections covering early RTC+B SoC data (Dec 2025). Whether gridstatus.io serves pre- or post-correction values for the affected intervals is unknown at this time. Cross-check against primary ZIPs is the only way to confirm. L1 reports 0% SoC NULL but cannot verify correction version.

---

## § Cross-Check Path (Required for Class A)

**Step 1 — Manual download (user action):**

Download ERCOT NP3-965-ER SCED ESR 60-Day Disclosure ZIPs from ERCOT MIS portal via browser:
- URL: `https://mis.ercot.com/misapp/GetReports.do?reportTypeId=13052` (or current equivalent)
- Files needed: monthly ZIPs covering 2025-12-05 through 2026-04-30
- Place in: `audits/US-TX-ANOL-001/ercot_primary_zips/`

**Step 2 — Hash and cross-check (automated):**
```bash
python3 cross_check.py
```
Script: hashes each ZIP, extracts ANOL_ESS_ESR1 rows, compares against gridstatus CSVs field-by-field.

**Step 3 — Record result here:**

| Month | ERCOT ZIP SHA-256 | Rows in ZIP | Rows in gridstatus | Delta | Cross-check |
|-------|-------------------|-------------|-------------------|-------|-------------|
| 2025-12 | (TBD) | (TBD) | 7,800 | (TBD) | ⏳ Pending |
| 2026-01 | (TBD) | (TBD) | 9,076 | (TBD) | ⏳ Pending |
| 2026-02 | (TBD) | (TBD) | 8,182 | (TBD) | ⏳ Pending |
| 2026-03 | (TBD) | (TBD) | 9,046 | (TBD) | ⏳ Pending |
| 2026-04 | (TBD) | (TBD) | 8,814 | (TBD) | ⏳ Pending |

---

## Secondary Sources

| Source | Purpose | URL | Archive status |
|--------|---------|-----|----------------|
| esVolta project page | Claim 001a / 001b verbatim | https://www.esvolta.com/projects | To be pinned via web.archive.org at commit |
| PR Newswire (esVolta COD) | COD date anchor (2025-07-30) | (search-indexed) | Noted by search result date |
| ERCOT ESR registry (test query) | `ANOL_ESS_ESR1` resource ID + facility entity closure | gridstatus.io test query 2026-02-01; dme=YANOLE query 2026-07-09 | Recorded in `audit_prep.md` L0b, L0d; manifest |

---

## What Is NOT a Source

- EIS / cell-level electrochemical data: not available, not claimed. Relegated to Battery Annex per P10 Design Principles §6.
- Vendor SCADA / BMS direct feed: not accessible; operator-reported `soc` field used as-reported per Rule F3 caveat.
- ERCOT ToU: does not govern this audit's data access. gridstatus.io ToU governs.
