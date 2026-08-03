# Remaining Keyword Reliability Work: Classification Corrections, Direct Travel Placement, Fresh Verification, and Balanced Promotion

Status: superseded and completed by `CODEX_SPEC_survivor_placement_and_promotion.md`. The final
authoritative measurement passed at 35/35 with zero supported-core disruption; production now
defaults to balanced.

## Implemented final measurement
- Batch: `scratch/fresh_keyword_corpus_exact_surface_final_20260731_0735/`
- Fingerprint: `fcec9dcb4cbd3c9c8c1ba0ddd17686d16585c419f363d9626796fa174f3c8d84`
- Completeness: 35/35 isolated builds, packaged audits, and authoritative two-page renders passed;
  active jobs and `output/` remained byte-identical.
- Locked outcomes: Amplify counterpart non-core; Direct Travel exact `cross functional` landed in
  one coordination carrier; Stord domain OR-family non-blocking; HD Supply unsupported domain gap
  non-blocking.
- Safety: PASS with zero false/non-requirement blockers and direct/workflow parity.
- Disruption: 0/35 (0.0%). Exact-surface placement closed Fisher Phillips
  `operational transformation`, Pragmatike `project management`, and Delta `digital transformation`.
- Decision: Option A. The objective clean gate passed, so the conditionally pre-approved promotion
  set the centralized default to balanced. Advisory and exhaustive remain explicit overrides.
- Historical context: 11.4% was the pre-correction four-survivor measurement; the archived figure of
  47 was a stale-output upper bound. Neither governs the current decision.

## Summary
Implement the four locked survivor adjudications through employer-neutral rules:
- Amplify `product owner`: counterpart-role context, non-core.
- Direct Travel `cross functional`: supported core; exact JD-surface placement.
- Stord `robotics integration`: domain OR-family, non-blocking.
- HD Supply `customer integration`: unsupported eProcurement-domain gap, non-blocking.

Three reported blockers are classification/support defects. Direct Travel is the only genuine
placement gap. Production remains advisory until the corrected 35-build measurement passes and the
user separately approves balanced.

## Phase 1 - Record the completed adjudication
Update decision artifacts and canonical specifications:

| Fixture | Final disposition | Action |
|---|---|---|
| Amplify | Counterpart-role context | Move outside core; no exact placement |
| Direct Travel | Supported core | Realize the JD's exact `cross functional` surface |
| Stord | Domain alternative family | Non-blocking; retain all alternatives diagnostically |
| HD Supply | Unsupported domain gap | Non-blocking; report honestly |

Retain 11.4% as the historical pre-correction disruption measurement, not the expected final result.
Exit gate: no preliminary table or later implementation section contradicts these decisions.

## Phase 2 - Generic classifier and support corrections

### Actor versus counterpart roles
Classify role nouns by their grammatical relationship to the candidate.
Assigned-role patterns: `serve as`, `act as`, `function as`, exact candidate title, or direct
assignment of that role's responsibilities.
Counterpart patterns: `partner with`, `collaborate with`, `work with`, `coordinate with`, and
comparable constructions where the role noun is the object.
Rules: counterpart-only role nouns enter breadth/context, not core; one genuine assigned occurrence
overrides counterpart occurrences; catalog presence alone cannot promote a counterpart role into core.
Controls (add both as permanent regressions): `partner closely with Product Owners` -> non-core
counterpart context; `serve as the product owner` -> assigned REQUIREMENT eligible for core.

### Alternative requirement families
Extend `RequirementElement` with `alternative_group_id: str` and `alternative_terms: tuple[str, ...]`.
Parse explicit `A, B, C, or D` qualification lists as one family. Score the family once; preserve
every exact alternative in diagnostics; an unchosen alternative cannot create an independent blocker;
record the supported alternative and its support level; if none is supported, report one family-level
Fit/domain gap.
Stord outcome: supply-chain systems, warehouse automation, robotics integration, and fulfillment
operations form one DOMAIN family; Amazon Robotics and warehouse-launch evidence may support the
warehouse-automation alternative adjacently; never claim robotics-systems integration;
`robotics integration` remains diagnostic and non-blocking.

### Domain precedence
Recognize supply-chain, warehouse, robotics, fulfillment, eProcurement, customer-integration product
capabilities, and comparable industry-specific phrases as DOMAIN before generic phrase-tail rules such
as `* integration`. DOMAIN contributes to breadth and Fit, remains visible in diagnostics and Resume
Notes, and never blocks balanced.
HD Supply outcome: `customer integration` remains an unsupported eProcurement-domain gap; EFT/ACH and
third-party diagnostic evidence cannot satisfy it.

### Direct-support boundary
Balanced eligibility requires all of:
```
candidate class = REQUIREMENT
validated requirement = true
requirement relation = assigned
support = supported-direct-unresolved
```
Only an exact approved-source surface or a context-valid evidence-catalog concept in the JD's sense
establishes direct support. `supported-adjacent` never blocks balanced. Tokens cannot be assembled
across paragraphs, employers, roles, actions, or objects; same-paragraph token overlap may establish
adjacent evidence only. Unsupported and domain findings remain Fit/bridge findings.
Expose diagnostics for `requirement_relation` (assigned, counterpart, domain_alternative, none),
alternative group and satisfied alternative, direct-support basis and source paragraph, and
balanced-eligibility reason.
Exit gate: Amplify, Stord, and HD Supply are non-blocking for their locked reasons; Direct Travel
remains supported core; assigned-role positive controls remain core; existing catalog, title, acronym,
noise, and domain controls pass; no employer-specific branch is introduced.

## Phase 3 - Centralize the policy default without changing it
Add `scripts/config/keyword_policy.py`:
```python
KEYWORD_POLICIES = ("advisory", "balanced", "exhaustive")
DEFAULT_KEYWORD_POLICY = "advisory"
```
Use it for every resume, workflow, dry-run, cover-letter, qualifications, argparse, and environment
fallback (replacing the six scattered "advisory" literals in `build_resume.py` ~590, ~599, ~6677 and
`run_resume_workflow.py` ~515, ~561, ~569).
Precedence: explicit CLI option, then explicit `RESUME_KEYWORD_POLICY`, then `DEFAULT_KEYWORD_POLICY`.
Exit gate: default behavior remains advisory; all explicit modes behave identically across direct and
workflow paths; Tailoring status remains absent from filenames.

## Phase 4 - Direct Travel exact-surface placement
Requires Phase C placement approval. The realization is active-JD-driven:
- If the JD uses `cross functional`, change exactly one selected `cross-functional coordination`
  surface to `cross functional coordination`.
- If the JD uses `cross-functional`, preserve the existing hyphenated form.
- If both appear, prefer the form used in the assigned requirement sentence.
- Transform only the coordination bullet; do not alter the separate `cross-functional initiative`
  surface.
- Apply only during tailored-resume generation; never edit either source resume.
- Do not duplicate the phrase in Summary or Skills.
Preserve action, object, ownership, metrics, scope, and sentence structure except required punctuation.
Run same-role provenance, two-literal, prose-quality, writing-quality, packaged-audit, and two-page
checks. Do not place Amplify `product owner`, Stord `robotics integration`, or HD Supply
`customer integration`.
Exit gate: Direct Travel lands its exact active-JD surface; only one carrier changes; other JDs retain
their own preferred spelling; Direct Travel remains exactly two pages.

## Phase 5 - Measurement-harness hardening
Complete before remeasurement.
- Path handling: short opaque fixture directories (ordinal plus 12-character hash); full IDs in
  manifest metadata; duplicate-target independence; render paths below Windows path limits.
- JSON encoding: write worker configs, manifests, and results as BOM-free UTF-8; accept `utf-8-sig`
  defensively when reading; test that generated JSON begins with `{`.
- Page-count authority: rendered page images, then successful Fit-render log, then Word `docProps` for
  diagnostics only. Fail closed when image and Fit-render counts disagree, neither authoritative source
  exists, or a two-page result cannot be reproduced.
- Fingerprint and isolation: exclude measurement-only scripts from the production fingerprint; hash
  active jobs and the complete `output/` inventory before and after and fail on any mutation; require
  exact manifest paths and prohibit active-output and source-resume fallback.
Exit gate: long-name, BOM, disagreement, duplicate-target, missing-artifact, and isolation tests pass.

## Phase 6 - Authoritative 35-build remeasurement
Freeze production code and rebuild recent-15 plus legacy-20 under one fingerprint. Every fixture
requires an isolated successful build; exact manifest-bound DOCX and Notes; packaged-audit equality;
exactly two pages; source lane and timestamp; all three policy outcomes; direct/workflow parity;
actor/counterpart and OR-family diagnostics; and separated core, breadth, domain, adjacent, and
unsupported findings.
Regenerate recent, legacy, and combined CSVs; the safety/disruption summary; the Claude promotion
packet; and the before/after survivor table.
Expected outcomes: Amplify no `product owner` blocker; Direct Travel exact `cross functional` landed;
Stord no independent `robotics integration` blocker; HD Supply `customer integration` an honest
non-blocking domain gap.
Safety requires zero false or non-requirement blockers; zero breadth, domain, or adjacent blockers;
zero malformed-term `INCOMPLETE`; direct/workflow parity; 35/35 packaged audits; 35/35 two-page
renders; and byte-identical active inputs and deliverables. No policy default changes during
measurement.

## Phase 7 - Balanced promotion decision
Produce a Claude packet with both options.
Option A, promote balanced: recommended when safety passes and disruption is acceptably low (expected
zero after these corrections); promotion still requires explicit user approval. After approval, change
only `DEFAULT_KEYWORD_POLICY` to `balanced`; retain explicit advisory and exhaustive overrides; rerun
direct/workflow and dependent-document parity; verify Fit-only filename matching; update help and
documentation; verify one-line rollback to advisory.
Option B, retain advisory: use when any safety gate fails, a genuine blocker remains, disruption
remains undesirable, Claude recommends more placement work, or the user has not explicitly approved
promotion. The centralized interface remains installed with advisory as its value.

## Phase 8 - Documentation and final verification
Update canonical specifications, architecture, system reference, command help, and Claude review
materials with the four locked adjudications; the corrected interpretation of the prior four blockers;
the final fingerprint and disruption; the selected default; the Direct Travel placement result; the
harness encoding/path/page rules; and the one-line rollback.
Run source lint; the full suite from the current 444-test baseline; assigned-role and counterpart-role
controls; OR-family and domain-precedence controls; advisory, balanced, and exhaustive dry runs;
direct/workflow, cover-letter, and qualifications parity; the full 35-build corpus; command inventory;
and representative Word inspection across major lanes.

## Approval boundaries
- The four adjudications are final; classification corrections are system-wide.
- Direct Travel is the only placement target and still requires Phase C approval.
- Balanced remains advisory until post-measurement user approval.
- Honesty outranks disruption reduction; exact ATS matching remains strict.
- Source resumes, titles, role order, company context, reorganization sentences, Education,
  Professional Development, formatting, two-page length, and Word-only output remain unchanged.
