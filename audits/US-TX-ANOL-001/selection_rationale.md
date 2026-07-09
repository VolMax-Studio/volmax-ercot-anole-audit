# US-TX-ANOL-001 — Asset Selection Rationale

**Protocol:** P10 v1.0
**Status:** CLOSED — all criteria verified pre-analysis (registry snapshot obtained 2026-07-09)
**Author:** Ivan Nestorov, VolMax Studio Lab
**Written:** 2026-07-09 (post-pull; pre-analysis.py)

> This document should have been written before data pull. It is written now
> because the pre-reg freeze did not include a formal selection criterion. The
> rule is being stated post-hoc but pre-analysis — no data has been examined
> yet. Any appearance of selection-by-convenience is a real risk that this
> document exists to address, not conceal.

---

## Intended Selection Criterion

The VolMax P10 audit series targets BESS assets selected by the following rule,
applied before data is seen:

> **"Largest registered ESR resource, operational through the full audit window,
> with a verifiable public nameplate claim pinned before data access."**

Sub-criteria (all must be satisfied):
1. **Registered ESR:** Asset appears in ERCOT SCED ESR registry with a confirmed
   resource ID before pull date.
2. **Operational through full window:** COD confirmed before window start
   (2025-12-05). Asset must not have been decommissioned or under extended
   outage during the window.
3. **Full SoC window:** Because this is the first P10 audit with SoC signal
   (RTC+B go-live 2025-12-05), the asset must have been operational and
   registered as an ESR from the first day of SoC availability.
4. **Verifiable public nameplate claim:** A verbatim MW/MWh claim from the
   operating entity, publicly accessible, pinnable via web.archive.org.
5. **Single resource ID:** Facility maps to one ESR resource ID (not split
   registration) to avoid scope ambiguity.

---

## Why ANOL_ESS_ESR1 (Anole BESS, esVolta, 240 MW / 480 MWh)

### Criteria satisfied

| Criterion | Evidence | Status |
|-----------|---------|--------|
| Registered ESR | `ANOL_ESS_ESR1` confirmed in SCED ESR registry (test query 2026-02-01) | ✅ |
| Operational through full window | COD: 2025-07-30 (PR Newswire). Full Dec 2025–Apr 2026 window covered. | ✅ |
| Full SoC window | L1: SoC 0% NULL across 42,918 rows from 2025-12-05 | ✅ |
| Verifiable nameplate claim | esVolta.com/projects: "240 MW / 480 MWh", page current 2026-07-08 | ✅ |
| Single resource ID | `dme=YANOLE` query returns only `ANOL_ESS_ESR1` (checked 2026-07-09) | ✅ |

### Criterion NOT confirmed

| Criterion | Gap | Risk |
|-----------|-----|------|
| **Largest registered ESR** | No ERCOT registry snapshot taken before pull. Cannot confirm Anole is the largest ESR in ERCOT operational through the full window. | **Selection bias risk if a larger asset exists and was not considered.** |

---

## § Registry Snapshot (post-pull, pre-analysis — 2026-07-09)

**Query:** All ERCOT ESR `resource_name` + `hsl` from `ercot_sced_esr_60_day`,
window `2025-12-05T06:00Z` to `2025-12-05T07:00Z` (first ERCOT operating hour
with RTC+B SoC). 306 ESRs active that day.

**Top 5 by HSL:**

| Rank | Resource | HSL (MW) |
|------|----------|----------|
| **1** | **ANOL_ESS_ESR1** | **240.0** |
| 2 | FIVEWSLR_ESR1 | 220.0 |
| 3 | ANEM_ESS_ESR1 | 200.0 |
| 3 | BYP_ESR1 | 200.0 |
| 3 | CACH_ESS_ESR1 | 200.0 |

**Result:** `ANOL_ESS_ESR1` is the largest registered ESR in ERCOT by HSL on the
first day of the audit window. The "largest" criterion is satisfied. Gap closed.

**Query method:** gridstatus.io API (same source as audit data). Not from
ERCOT primary registry. This is sufficient for selection documentation but
note that HSL is SCED model limit, not nameplate — they coincide here (240 MW)
but are not definitionally equivalent. Noted, not disputed.

**Status: CLOSED.** Selection criterion verified pre-analysis.

---

## Pre-Registration Commit Gap

**P10 Pillswood standard:** Selection criterion and registry snapshot should be
committed before data download, with a git hash pinning the pre-data state.

**Current state:** No git repository was initialized before data pull.
`pull_anole.py` ran against an uncommitted working directory. The frozen
`audit_prep.md` exists but has no commit hash.

**Consequence:** The "pre-registration" claim in `audit_prep.md` header is
procedurally unsupported. The document content is frozen (no data was consulted
when writing F1–F4), but the absence of a git hash means this cannot be proven
to an external reviewer.

**Remediation:**
```bash
cd /home/volmax-studio/volmax-projects/iot2/PORTFOLIO/volmax-ercot-anole-audit
git init
git add audit_prep.md sources.md selection_rationale.md .gitignore .env.template
git commit -m "US-TX-ANOL-001: pre-registration freeze (post-hoc commit, data already pulled)"
```
The commit message must honestly state "post-hoc commit" — the timestamp will
show it was made after pull. This is a declared procedural gap, not a falsified
timeline. Future audits start with git init before any pull.
