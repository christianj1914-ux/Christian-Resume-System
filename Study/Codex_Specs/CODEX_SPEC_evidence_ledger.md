# Codex Spec: Supported-Evidence Ledger + Denominator Hygiene

## Purpose
Raise ATS breadth coverage on GOOD fits (target 80%+) without inflating weak fits, by
fixing the two real causes found across all 20 rebuilds (see
`KEYWORD_COVERAGE_FINDINGS_AND_PLAN.md`):

1. Truthful terms Christian owns are missed because they are not written in the JD's literal
   form (project management, vendor management, UAT, CRM, change management, incident
   management, professional services, system configuration, business process, client
   onboarding, end-to-end delivery, SaaS, technology adoption).
2. The breadth denominator is polluted with noise (school diploma, "may", "approaches
   throughout", "...training" tails, eight redundant "X integration" variants), which makes
   several scores meaninglessly low.

Do NOT build lane-variant source resumes. Use a single evidence ledger and reuse the
existing mirror/placement machinery. Stay on `codex-systemwide-docfixes`, do not merge.
Guardrails: exact matching preserved, no invented content, weak fits stay honestly
FAIL/BRIDGE, Word-only, do not stage generated outputs.

Suggested commit split: (1) denominator hygiene, (2) evidence ledger + placement, (3) Blue
Yonder output-name collision fix.

---

## Fix 1: denominator hygiene in `scripts/resume_analysis.py` (`ats_scan_terms`)
Remove non-keywords from the breadth set so the percentage is honest. Add these filters:

- Education/boilerplate: drop `school diploma`, `school equivalency`, `high school`, `ged`.
- Bare stopword/soft (extend the existing soft list): `may`, `what`, `such`, `its`, `help`,
  `total`, `long-term`, `nature scope`, `ideal candidate`, `highly preferred`,
  `leading edge`, `directly influence`, `independently manage`, `embraces diverse`.
- Preposition/gerund-tail fragments: drop any phrase that STARTS or ENDS with a preposition
  (`across, throughout, of, to, with, for, into, on`) or is a dangling gerund fragment.
  Examples killed: `approaches throughout`, `improve approaches throughout`,
  `solutions across`, `across department`, `translate high-level`, `translate physical`.
- Mis-attached `...training` tails: drop `<X> training` phrases where `training` is not the
  JD skill itself. Kill `agreement training`, `trade agreement training`,
  `orientation training`, `conduct orientation training`, `development technical training`,
  `virtual client training`, `executive briefings training`. Keep standalone `training`.
- Partial-phrase artifacts: drop `planning uat`, `test planning uat` (keep `uat`).
- Near-duplicate compound collapse: when several breadth terms share a head or tail noun
  (`X integration`, `X adoption`, `X delivery`, `X service`), keep the single canonical head
  noun plus at most one most-frequent compound; drop the rest. HD Supply eProcurement should
  not carry eight "integration" variants.

Also add the cheap correctness guard: any breadth term that `contains_search_term` finds in
the resume MUST count present (never list a written term as missing).

Effect: Delta, HD Supply eProcurement, Manhattan, Stord breadth rise to honest levels with
zero content change.

---

## Fix 2: the evidence ledger (auto-place truthful terms)

### 2a. Create `source/evidence_terms.py`
A single list of dicts. Each entry: `concept` (canonical), `variants` (literal JD surface
strings to match and to write), `anchor` (role + proof, for traceability), `strength`
(`strong` = place whenever the JD uses a variant; `moderate` = place only when the JD
context clearly supports it). SEED IT EXACTLY WITH THIS (confirm each against source before
enabling; all are drawn from Christian's existing resume bullets):

```python
EVIDENCE_TERMS = [
  {"concept":"project management","variants":["project management","program management",
    "technical program management","complex project management","project delivery"],
    "anchor":"PMP (in progress); 5-month EFT/ACH program across IT, finance, Aptean, Truist; warehouse + Amazon Robotics launch; five-site coordination","strength":"strong"},
  {"concept":"product ownership","variants":["product owner","product ownership",
    "technical product management"],
    "anchor":"De facto product owner of Aptean Intuitive ERP; requirements to backlog to adoption","strength":"strong"},
  {"concept":"vendor management","variants":["vendor management","vendor partner",
    "vendor coordination","partner relationship"],
    "anchor":"Coordinated Aptean vendor, Truist Bank, India dev team; vendor/cost/timeline tradeoffs","strength":"strong"},
  {"concept":"uat","variants":["uat","user acceptance testing","acceptance testing"],
    "anchor":"Epicor Kinetic cutover sandbox testing and UAT validation","strength":"strong"},
  {"concept":"change management","variants":["change management"],
    "anchor":"Migration readiness, adoption, training programs reducing resistance to system change","strength":"strong"},
  {"concept":"incident management","variants":["incident management"],
    "anchor":"ITIL 4 Foundation; Aderant enterprise application support (application, SQL Server, AD, integration issues)","strength":"strong"},
  {"concept":"crm","variants":["crm","crm system","crm tool"],
    "anchor":"Salesforce Service Cloud, Marketing Cloud, AppExchange (Aptean); Salesforce CRM + LivePerson (Home Depot)","strength":"strong"},
  {"concept":"client onboarding","variants":["client onboarding","customer onboarding"],
    "anchor":"Aptean customer enablement, go-live, hypercare, onboarding guides","strength":"strong"},
  {"concept":"professional services","variants":["professional services","professional service"],
    "anchor":"Aptean consultant across 80+ client engagements, discovery to delivery","strength":"strong"},
  {"concept":"system configuration","variants":["system configuration","configuration"],
    "anchor":"ERP configuration across five sites; Aptean implementation configuration","strength":"strong"},
  {"concept":"business process","variants":["business process","business process improvement"],
    "anchor":"78% manual-work reduction, 22% discrepancy reduction, process redesign standardized across five sites","strength":"strong"},
  {"concept":"end-to-end delivery","variants":["end-to-end delivery","end-to-end","end to end"],
    "anchor":"Discovery-to-go-live ownership; delivered enterprise technology projects end to end","strength":"strong"},
  {"concept":"saas","variants":["saas","software as a service"],
    "anchor":"Enterprise SaaS platforms (Aptean cloud ERP); already in Adobe header","strength":"strong"},
  {"concept":"technology adoption","variants":["technology adoption","feature adoption",
    "user adoption","platform adoption"],
    "anchor":"Drove technology adoption across operations/finance/engineering; training, onboarding, release comms","strength":"strong"},
  {"concept":"requirements","variants":["requirements gathering","requirements definition",
    "requirements management"],
    "anchor":"SOW/FRD; backlog-ready requirements and user stories","strength":"strong"},
  {"concept":"stakeholder management","variants":["stakeholder management","stakeholder alignment"],
    "anchor":"VP/director decisions; 60+ executive workshops; cross-functional alignment without authority","strength":"strong"},
  {"concept":"data migration","variants":["data migration"],
    "anchor":"ETL/SQL validation checks, cutover coordination","strength":"strong"},
  {"concept":"integration","variants":["integration","integration coordination","api configuration"],
    "anchor":"Third-party integration diagnostics (Aderant); EFT/ACH file integration; India dev deployment coordination","strength":"strong"},
  {"concept":"reporting","variants":["reporting","dashboards","kpi"],
    "anchor":"200+ SQL KPI dashboards, Crystal Reports, Power BI","strength":"strong"},
  {"concept":"pre-sales","variants":["pre-sales","presales"],
    "anchor":"Pre-sales product demonstrations and discovery for prospective clients","strength":"strong"},
  {"concept":"agile","variants":["agile","agile delivery"],
    "anchor":"Partnered with Product Management/Ownership on an Agile development team","strength":"strong"},
  {"concept":"digital transformation","variants":["digital transformation","transformation"],
    "anchor":"ERP migration/modernization; AI-assisted workflow modernization","strength":"moderate"},
  {"concept":"ai adoption","variants":["ai adoption","ai pilot","ai-assisted"],
    "anchor":"AI-assisted tooling (Claude); SMS chatbot logic pilot at Home Depot","strength":"moderate"},
  {"concept":"global program","variants":["global program"],
    "anchor":"Five-site global manufacturing footprint; cross-site program coordination","strength":"moderate"},
]
```

### 2b. Drive placement from the ledger
- Extend the mirror path (currently `JD_TERM_MIRROR` / `jd_preferred_surface` in
  resume_analysis.py) so ledger variants are the equivalence source. When a JD term (core or
  breadth) matches a ledger `variants` entry and the resume lacks the literal JD form, place
  that literal form. `strong` terms place whenever the JD uses a variant; `moderate` terms
  place only when the JD context clearly supports it (guard against forcing).
- Placement uses the EXISTING non-forcing ladder from the last commit: natural home in the
  bullet carrying the `anchor` evidence, else Skills. The same-stem, evidence-fit, and no
  identity-injection guards still apply and still win. Never force an awkward insertion.
- Every placed term must trace to a ledger `anchor`. No ledger entry means no auto-placement,
  so the term stays honestly missing.

---

## Fix 3 (optional, small): promote universal terms into core
Add the two most universal, always-supported concepts to the core must-place set so they are
placed even when a JD surfaces them only as breadth: `project management` and
`professional services`. Keep this list short and evidence-backed. Do not promote `moderate`
terms.

---

## Fix 4: Blue Yonder output-name collision (separate small commit)
Two Blue Yonder Advisor postings and the Program Manager collapse to the output target
"Blue Yonder" and overwrite each other. Disambiguate the output target name by including the
role title (as other targets already do) so batch runs stop clobbering.

---

## Tests (`scripts/smoke_test.py`)
- Hygiene: none of the Part 3B noise terms appear in `ats_scan_terms` output on the relevant
  JD fixtures; near-duplicate compounds collapse; a written term is never listed missing.
- Ledger match: a JD using `program management` places `project management` from the ledger;
  `crm system` places CRM; `system configuration` places configuration; each traces to an
  anchor.
- Non-forcing preserved: a `moderate` term is NOT placed when the JD lacks clear support;
  same-stem/identity guards still reject awkward insertions.
- Truthfulness: a JD term with no ledger entry and no resume evidence stays missing (e.g.
  `duty drawback`, `space management`).
- Both coverage lines still print on every status; breadth denominators stay >= 10.

## Rebuild and verification (required)
- Rebuild all 20 archived targets with byte-for-byte active `jobs/` restore after each swap.
- Record before/after core AND breadth for all 20.
- Acceptance:
  - Good-fit roles whose misses were ledger-backed reach 80%+ breadth (USAA, Advyzon,
    Shipium, both Stord, Manhattan IT Delivery, Blue Yonder x4, Adobe Sr PM).
  - Stretch roles stay honestly below 80% and their remaining misses are all genuine domain
    gaps, not ledger concepts (Intuitive trade compliance, Adobe GSO space/asset management,
    warehouse-hardware terms, Advyzon fintech).
  - Every auto-placed term traces to a ledger anchor; no invented claims; no known-bad
    phrases; Word-only, no PDFs.
- Priority roles remain resume PASS + cover PASS.

## Guardrails / assumptions
- No invented tools, methods, metrics, or experience. Ledger entries are evidence-backed.
- Exact matching unchanged; mirroring and non-forcing rules from prior commits preserved.
- Weak fits stay honestly FAIL/BRIDGE; the ledger never fabricates a domain Christian lacks.
- Ledger lives in `source/`; do not stage generated outputs, rebuilt archives, active
  `jobs/` files, or these spec docs unless kept as project documentation.
- Federal remains queued after this lands.
