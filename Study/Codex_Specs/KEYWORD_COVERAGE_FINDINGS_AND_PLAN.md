# Keyword Coverage: Full 20-Build Findings and Optimization Plan

Computed with the current code (`ats_coverage`) against each archived JD paired with its
rebuilt resume. Core = strict must-have set. Breadth = realistic 12-25 term JD surface.

## Part 1: What the system missed, all 20

Legend: T = truthful term Christian has but the resume did not write (SYSTEM FAILURE);
G = genuine domain gap (fine to miss, keep honest); N = extractor noise (should not be in
the denominator at all).

| # | Role | Core | Breadth | Truthful misses (T) | Genuine gaps (G) | Noise (N) |
|---|------|------|---------|---------------------|------------------|-----------|
| 01 | USAA P&C Product Mgmt (PASS) | 85% | 68% | program management, product dashboards | underwriting, local market, policy | such |
| 02 | JBAndrews Solutions Engineer (BRIDGE) | 100% | 64% | logistics | shuttle system, warehouse automation, material handling | its, help, development technical training |
| 03 | Delta Sr Ops Analyst (BRIDGE) | 76% | 20% | digital tool, ai adoption | digital transformation, emerging technology, generative ai | school diploma, school equivalency, approaches throughout, embraces diverse, across department, leading edge |
| 04 | Delta (collision dup) | 55% | 8% | (same as 03) | (same) | (same, plus title fragments) |
| 05 | Delta Marketing Sr PO (FAIL) | 59% | 16% | performance metrics | marketing use case, executable backlog | solutions across, translate high-level, prioritizations skill, product sponsor |
| 06 | Intuitive Logistics Compliance (FAIL) | 86% | 48% | time management | trade compliance, duty drawback, customs regulation, free trade, medical device | agreement training, trade agreement training, excellent time management |
| 07 | Advyzon Technical Consultant (PASS) | 92% | 68% | crm system, client onboarding, project management | wealth management, broker dealer, portfolio management | virtual client training |
| 08 | Shipium Lead Impl Consultant (BRIDGE) | 69% | 20% | project management, professional services, end-to-end delivery, api configuration | solutions architect, supply chain tech | highly preferred, directly influence, technical architectures api, utilizing ai |
| 09 | Stord Sr Deployment TPM (BRIDGE) | 71% | 36% | vendor management, acceptance testing, technical program management, robotics integration | warehouse floor, material flow, facility layout, deployment playbook | (n/a) |
| 10 | Stord Staff TPM (BRIDGE) | 83% | 24% | change management, technical product management, end-to-end | warehouse execution system, warehouse management | translate physical, architectural discussion, resolution release quality, beta lab integration |
| 11 | HD Supply eCommerce Ops (FAIL) | 84% | 56% | incident management, operational readiness | ecommerce platform | nature scope, may, long-term platform stability |
| 12 | HD Supply eProcurement (BRIDGE) | 90% | 8% | technology adoption, relationship management | catalog production, go-to-market | integration-variant dup family (x8), nature scope |
| 13 | Blue Yonder Functional Architect (PASS) | 79% | 64% | business process, system configuration, cross-functional delivery, UAT | (n/a) | executive briefings training, planning uat |
| 14 | Blue Yonder Advisor (collision) (PASS) | 68% | 56% | business process, system configuration, cross-functional | (n/a) | executive briefings training, coordinating cross-functional delivery |
| 15 | Blue Yonder Services Advisor (collision) (PASS) | 68% | 56% | business process, system configuration, cross-functional | (n/a) | (same) |
| 16 | Blue Yonder Program Manager (PASS) | 100% | 77% | implementation project, project management, saas | (n/a) | (n/a) |
| 17 | Manhattan Sr IT Delivery Mgr (BRIDGE) | 74% | 28% | business process, vendor management, complex project management, enterprise erp system, feature adoption | quality center | conduct orientation training, total service, own end-to-end service, report service delivery |
| 18 | Manhattan Sr Enablement Consultant (PASS) | 100% | 48% | professional services, productivity tool | learner feedback, ai-powered productivity | ideal candidate, independently manage |
| 19 | Adobe Sr Program Manager GSO (PASS) | 100% | 64% | global program, vendor partner, ai pilot | space management, asset management | what |
| 20 | Adobe Solutions Consultant (FAIL) | 79% | 56% | consultative approach, transformation | pdf services api, acrobat, digital document | growth solution consultant |

## Part 2: The recurring truthful misses (this is the real failure)

These terms are ones Christian genuinely has, yet the resume did not contain the literal
JD string. Ranked by how many good-fit (PASS/BRIDGE) roles missed them:

1. project management / program management / technical program management - USAA, Advyzon,
   Shipium, Stord (both), Manhattan, Blue Yonder PM. This is the single biggest leak. He is
   PMP-in-progress and ran the EFT/ACH and warehouse programs. There is no reason a resume
   should ever miss "project management."
2. business process - Blue Yonder (x3), Manhattan.
3. system configuration / configuration - Blue Yonder (x3).
4. vendor management / vendor partner - Stord, Manhattan, Adobe.
5. UAT / acceptance testing - Stord, Blue Yonder.
6. professional services - Shipium, Manhattan.
7. end-to-end delivery - Shipium, Stord.
8. change management - Stord.
9. incident management - HD Supply (ITIL / Aderant).
10. CRM system - Advyzon (Salesforce).
11. client onboarding - Advyzon.
12. technology / feature adoption - HD Supply, Manhattan.
13. transformation / digital transformation - Delta, Adobe, Manhattan (partial-truthful).
14. saas - Blue Yonder PM (and it is already in the Adobe header, so inconsistent).

Genuine gaps to leave honest (do NOT engineer these in): underwriting; trade compliance,
duty drawback, customs; broker-dealer, wealth/portfolio management; warehouse execution /
management systems and shuttle / material-flow / facility-layout hardware; space and asset
management (facilities); PDF Services API / Acrobat depth; catalog production; medical
device. When these dominate the misses, a low breadth score is the honest signal you asked
for, and it should stay low.

## Part 3: Root cause (three distinct failure modes)

A. Truthful-but-unwritten terms. The mirror map (`JD_TERM_MIRROR`) is tiny and hardcoded,
   and the non-forcing rule only naturally places a term that already has an obvious home.
   So a term Christian truthfully owns but that is phrased differently in his source (or
   not present at all) never gets placed. This is Part 2 above, and it is most of the loss
   on good fits.

B. Denominator noise. `ats_scan_terms` is pulling junk into the breadth set that no ATS
   would key on: education boilerplate (school diploma/equivalency), bare stopwords/soft
   (may, what, such, its, help, total service, long-term, nature scope, ideal candidate,
   highly preferred, leading edge), preposition/gerund-tail fragments (approaches
   throughout, solutions across, translate high-level), mis-attached "...training" tails
   (orientation training, agreement training, executive briefings training), "planning uat"
   fragments, and redundant near-duplicate compound families (HD Supply eProcurement had
   eight "X integration" variants). This is why Delta and HD Supply eProcurement show 8-20%:
   the denominator is mostly noise, so the percentage is meaningless and unfairly low.

C. Minor matching guard. The matcher itself is basically sound (it correctly rejects "uat"
   inside "evaluate"), but add a cheap guard: any breadth term that `contains_search_term`
   finds in the resume must count as present, so a genuinely written term can never be
   listed missing.

## Part 4: The fix. A supported-evidence ledger, NOT lane-variant source resumes.

Lane-variant bullets (writing a resume/bullet set per lane) is the wrong tool: it is
O(lanes x bullets) of hand-written content to keep in sync, it goes stale, it drifts from
the truth, and the whole system was built to avoid hand-maintained per-target content.

Do this instead, in three parts.

### Fix 1: denominator hygiene (makes the metric honest, fast win)
- Tighten `ats_scan_terms`: drop education boilerplate, the bare stopword/soft list above,
  any phrase that begins or ends with a preposition or is a gerund-tail fragment, any
  "...training" tail that is not itself a JD skill, and collapse near-duplicate compound
  families to one canonical term (one "integration," not eight).
- Add the Fix C guard so written terms are never marked missing.
- Effect: Delta, HD Supply eProcurement, Manhattan, Stord breadth numbers rise to honest
  levels purely by removing junk, with zero content change.

### Fix 2: the supported-evidence ledger (auto-places truthful terms)
- Create ONE structured ledger, `source/evidence_terms.py` (or `.yml`): a list of concepts
  Christian can truthfully claim. Each entry = { concept, surface_variants (the literal
  strings JDs use), evidence_anchor (the exact role/bullet that proves it) }. Seed it from
  Part 2, e.g.:
  - project management / program management / technical program management -> PMP-in-progress; EFT/ACH program; warehouse + Amazon Robotics launch
  - vendor management -> Aptean, Truist, India dev team coordination
  - UAT / acceptance testing -> Epicor cutover sandbox testing and UAT validation
  - change management -> migration readiness and adoption
  - incident management -> ITIL 4; Aderant enterprise support
  - CRM (system) -> Salesforce Service/Marketing Cloud
  - client onboarding -> Aptean customer enablement and go-live
  - professional services -> Aptean consultant, 80+ client engagements
  - system configuration -> ERP configuration across five sites
  - business process -> 78% manual-work reduction, process redesign
  - end-to-end delivery -> discovery-to-go-live ownership
  - SaaS -> enterprise SaaS platforms (already in the Adobe header)
- Drive the EXISTING mirror/placement from the ledger instead of the tiny hardcoded map:
  when a JD term (core or breadth) matches a ledger concept and the resume lacks the literal
  form, place that literal JD surface form naturally in the bullet carrying the evidence
  anchor (preferred) or Skills (fallback). This reuses all the placement machinery already
  built; it just feeds it a richer, truthful, single-source equivalence set.
- Guardrail: only ledger-backed terms are auto-placed. Every placed term must trace to an
  evidence anchor. A JD term with no ledger entry stays missing, so stretch roles stay
  honestly low. This is what keeps Adobe GSO at a true ~76% (global program, vendor partner,
  AI pilot added; space/asset management correctly still missing) instead of a fake 100%.

Why the ledger beats lane resumes: one source of truth, truthful by construction (each entry
names its proof), composes across all lanes automatically, and no per-target content to
maintain.

### Fix 3 (optional, small): promote a few ledger concepts into the core must-have set
- Terms this central and this universally supported (project management, professional
  services) can be added to the core set so they are always placed, not just when a JD
  surfaces them as breadth. Keep this list short and evidence-backed.

## Part 5: Verification (required)
- Rebuild the 20. Assert:
  - Every good-fit (PASS/BRIDGE) role whose misses were ledger-backed rises to 80%+ breadth.
  - Stretch roles (Intuitive trade compliance, Adobe GSO facilities, warehouse-hardware
    Stord/JBAndrews, fintech Advyzon) stay honestly below 80%, and their remaining misses
    are all genuine domain gaps, not ledger concepts.
  - Every auto-placed term traces to a ledger evidence anchor (no invented claims).
  - Denominator noise terms from Part 3B no longer appear in any breadth set; no normal-JD
    breadth set is thin (>= 10) or junk-inflated.
- Record before/after core and breadth for all 20 so the lift is measurable.

## Guardrails
- No invented tools, methods, metrics, or experience. Ledger entries are evidence-backed or
  they do not exist.
- Weak fits stay honestly FAIL/BRIDGE; the ledger never fabricates a domain Christian lacks.
- Word-only; do not stage generated outputs, the ledger stays in source/, one focused commit
  (or two: hygiene, then ledger).
- Also fix the Blue Yonder output-name collision (Advisor vs Services Advisor vs Program
  Manager collapsing to "Blue Yonder") so batch runs stop overwriting each other; separate
  small commit.
