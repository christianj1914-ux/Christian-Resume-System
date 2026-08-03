# Targeted Survivor Placement (Exact Core-Surface Realization), Re-measurement, and Balanced Promotion

Status: IMPLEMENTED. Exact-surface targets, deterministic assigned-literal selection, and
orthographic pre-budget realization closed all supported-core survivors. Authoritative fingerprint
`fcec9dcb4cbd3c9c8c1ba0ddd17686d16585c419f363d9626796fa174f3c8d84` passed 35/35 isolated builds,
packaged audits, and two-page renders with zero false blockers and zero supported-core disruption.
The conditionally pre-approved promotion was executed; production now defaults to `balanced`, with
one-line rollback to `advisory`.

## Authoritative governance rule (CONFIRMED; resolves the conflict Codex flagged)
There is exactly one promotion rule: conditional auto-promotion (the pre-approval below). Christian
chose "auto-flip if perfect" on 2026-07-30 and reconfirmed it after Codex flagged the apparent
mismatch. This is now settled and supersedes any earlier or parallel planning language that says
balanced promotion requires a fresh manual approval or that "no automatic default change occurs."
On the clean path defined below, Codex flips the default automatically without pausing; on any
non-clean result it holds at advisory and returns a packet. Do not re-raise this as an open question.
(If Christian later prefers a manual gate, that is a one-line change to this rule.)

## Approvals (granted by Christian, 2026-07-30)
- Phases 1-2 (targeted placement pass): APPROVED. Proceed with the surface-realization fix and close
  the three survivors. No further approval needed to change generated content for this purpose.
- Phase 4 (balanced promotion): PRE-APPROVED, CONDITIONAL. Codex may flip the default to balanced
  automatically, without returning for another approval, only if the Phase 3 fresh re-measurement is
  clean, defined precisely as ALL of: safety PASS; 35/35 isolated builds, packaged audits, and
  two-page renders; active jobs and `output/` byte-identical; zero false or non-requirement blockers;
  zero breadth/domain/adjacent blockers; direct/workflow parity; and supported-core-miss disruption
  exactly 0. If disruption is greater than 0 or any gate fails, do NOT auto-promote: keep advisory and
  present the decision packet for a manual call. The flip is the one-line `DEFAULT_KEYWORD_POLICY`
  change with one-line rollback.

## Why (root cause, grounded in the fresh Resume Notes)
All three survivors are the same defect: the placement engine satisfies a supported CORE concept by
realizing the wrong surface of that concept, so the JD's exact scored must-have surface stays missing.

- Pragmatike `project management` (concept `project_management`): the summary landed the sibling
  variant `project delivery` ("...digital transformation and project delivery connect to measurable
  execution..."), but the JD's core must-have surface `project management` never landed -> "missing
  after ledger placement." This is Christian's single strongest area (PMP in progress); it is a pure
  surface-selection failure, not a support gap.
- Delta `digital transformation` (concept `digital_transformation`): the summary landed the bare stem
  `transformation` twice ("...to transformation programs, with emphasis on transformation and ai
  adoption."), triggering a "repeated word stem" warning, while the exact JD surface
  `digital transformation` never landed.
- Fisher Phillips `operational transformation` (concept `operational_transformation`, variants include
  `process optimization` / `workflow optimization`): same class, a sibling variant satisfied the
  concept while the JD's exact surface stayed missing. Confirm during implementation.

This is the same family as the earlier Aptean `configuration` vs `system configuration` issue: the
concept is present, the exact JD surface is not. All three are `planned_but_unwritten`, catalog-backed,
and carry same-role east_west provenance (`project management` -> "Delivered enterprise technology
projects end to end"; `digital transformation` and `operational transformation` -> "Led enterprise
systems modernization"). The fix is honest surface selection, never new content.

## Guardrails (apply throughout)
- Honesty first. Realize only the exact surface of a concept that is already supported and already
  being placed. Do not add new claims, metrics, tools, industries, outcomes, ownership, employers, or
  roles. Do not invent evidence.
- Employer-neutral. Fix the generic surface-selection logic; never branch on employer or JD identity.
- Any change to generated content forces a fresh full 35-build re-measurement (Phase 3) before any
  promotion (Phase 4).
- Preserve exact ATS matching, source-truth rules, reorganization sentences, titles, role order,
  Education, Professional Development, formatting, two-page length, and Word-only output.
- Production remained advisory through measurement; the conditionally pre-approved Phase 4 gate
  passed and the centralized default is now balanced.

## Phase 1 - Exact JD core-surface realization (generic fix)
Goal: when a supported CORE concept is realized, emit the JD's exact scored surface for that concept,
not a sibling variant or a bare stem.

Preferred design (from Codex reconciliation): carry the exact scored surface as a first-class object
through the whole pipeline instead of re-inferring a preferred surface downstream, which is how
`project delivery` and bare `transformation` slipped in.
- Introduce an internal `KeywordPlacementTarget` carrying: exact JD surface; catalog concept ID; core
  or breadth tier; requirement relation and validating sentence; support basis and evidence anchor;
  permitted placement types; and final location plus landing result.
- Add `planned_supported_keyword_targets(...)` as the authoritative plan; keep the existing
  string-based `planned_supported_keyword_terms(...)` as a compatibility wrapper for current callers
  and tests.
- Planning rules: every validated, assigned, directly supported core surface becomes an exact target;
  deduplicate by normalized exact surface, not merely by concept; a sibling catalog variant or bare
  stem cannot satisfy that target; multiple variants remain separate only when the JD independently
  scores each; breadth surfaces are considered after core targets and never displace them; counterpart,
  domain, adjacent, unsupported, and OR-family alternatives stay non-blocking under their existing
  rules.
- Thread the selected target unchanged through summary weaving, bullet weaving, Skills fallback, bullet
  protection, and final landing diagnostics. Do not repeatedly infer a new preferred surface downstream.

Realization rules (applied to each unresolved core target):
1. Surface preference. The JD's own high-value/core scored surface wins over other catalog variants
   and over any shorter stem. Order: exact JD core must-have surface present in the posting, then exact
   JD breadth surface, then other catalog variants. A bare stem (`transformation`) must never satisfy a
   multiword JD surface (`digital transformation`). `jd_preferred_surface`
   (`scripts/resume_analysis.py` ~235) feeds the target once, at plan time, not repeatedly downstream.
2. Realize the scored surface. When the placement plan targets a core concept and the JD's must-have
   surface is a specific variant, the writer must land that exact surface in the summary or a
   first-role bullet. If a sibling variant of the same concept was already going to be placed (for
   example `project delivery`), prefer realizing the core surface (`project management`); keep the
   sibling only if it is itself a separately scored JD surface and doing so does not duplicate or pad.
3. Anti-stem and de-duplication. Do not satisfy a multiword core surface by repeating a bare stem, and
   do not place the same concept in both summary and Skills. This also clears the "repeated word stem"
   warning seen on Delta.
4. Landing verification uses the exact surface. The ledger landing check
   (`landing_text_for_term` / `contains_search_term`) already requires the exact literal; keep that
   strict. The fix is that the writer now emits the exact literal, so `landing` stops reporting
   "missing" for a concept that is genuinely placed.
5. Apply only during tailored-resume generation; never edit the source resumes.

Concrete targets (must land the exact surface, from their approved evidence):
- Pragmatike: `project management` in summary or first-role bullet (from "Delivered enterprise
  technology projects end to end" / PMP evidence).
- Delta: `digital transformation` (from "Led enterprise systems modernization"), replacing the bare
  double `transformation` stem.
- Fisher Phillips: `operational transformation` (from "Led enterprise systems modernization").

Exit gate: each of the three lands its exact JD core surface under the gates below; no bare-stem
substitution remains; no concept is double-placed.

## Phase 2 - Safety gates and regressions
Every realized surface must pass the existing safeguards: same-role provenance, ownership ceiling,
unchanged metrics/objects/scope/tools/outcomes, two-literals-per-bullet cap, prose repair,
writing-quality evaluation, packaged-audit equality, and exact two-page fit. If a surface cannot be
realized safely, leave the original prose and keep the honest review flag rather than forcing it.

Add permanent regressions:
- Core concept whose JD surface is a specific variant realizes that exact surface, not a sibling
  variant or bare stem (cover `project management` vs `project delivery`, and `digital transformation`
  vs bare `transformation`).
- No "repeated word stem" landing for a multiword core surface.
- Existing controls still pass: Aptean `system configuration` exact realization, Direct Travel
  `cross functional` active-JD surface, the four locked survivor dispositions, assigned-vs-counterpart
  controls, OR-family and domain-precedence controls, acronym/noise controls.
- No concept appears in both summary and Skills for the same build.

Exit gate: the three survivors resolve, all listed regressions pass, and no previously passing build
regresses.

## Phase 3 - Fresh 35-build re-measurement (mandatory, measurement only)
Because Phase 1 changes generated content, re-run the authoritative measurement on a new fingerprint
using the existing isolated harness and manifest-bound analyzer.
- Freeze production code; record the new fingerprint.
- Rebuild recent-15 and legacy-20 in isolation, one directory per fixture, resumable, with active job
  files and the full `output/` inventory hashed before and after and verified unchanged.
- Use render-image / fit-render-log page counts, not stale Word `docProps` metadata.
- Recompute advisory, balanced, and exhaustive readiness from each packaged DOCX; record supported
  core vs breadth misses, blocker provenance, placement disposition, requirement relation, and
  direct/workflow parity.
- Regenerate the recent, legacy, and combined CSVs, the safety/disruption summary, and a refreshed
  Claude promotion packet with a before/after survivor table.

Expected outcome: the three survivors land their exact surfaces, so supported core misses go from 3 to
0 (or a clearly smaller, individually justified set). Safety must remain PASS: zero false or
non-requirement blockers, zero breadth/domain/adjacent blockers, zero malformed-term INCOMPLETE,
direct/workflow parity, 35/35 packaged audits, 35/35 two-page renders, active workspace byte-identical.

Exit gate: fresh measurement complete on one new fingerprint; disruption recomputed; decision packet
refreshed. No production default changed.

## Phase 4 - Balanced promotion (production change; conditionally pre-approved)
This phase is governed by the pre-approval above, so Codex does not pause for another approval.
- Auto-promote path: if the Phase 3 result is clean per the exact gate in "Approvals" (safety PASS,
  35/35 builds/audits/two-page, byte-identical active workspace, zero false and zero
  breadth/domain/adjacent blockers, direct/workflow parity, and supported-core-miss disruption exactly
  0), change only `DEFAULT_KEYWORD_POLICY` in `scripts/config/keyword_policy.py` from `advisory` to
  `balanced`. Keep advisory and exhaustive selectable; re-run direct/workflow and dependent-document
  parity; verify Fit-only filenames; update help and docs; confirm the one-line rollback to advisory.
- Hold path: if disruption is greater than 0 or any gate fails, do not promote. Keep advisory, and
  produce the Claude decision packet listing the exact surviving terms, fixtures, evidence, and
  disposition so Christian can make a manual call.
Either way, record the fresh fingerprint, the disruption rate, the resulting default, and the
one-line rollback in the decision packet.

Exit gate: default is balanced only if the clean gate was met; otherwise advisory with a packet
explaining why.

## Phase 5 - Documentation and final verification
- Update the remaining-work spec, the combined classifier/ownership spec header, `SYSTEM_REFERENCE.md`,
  `ARCHITECTURE_MAP.md`, command help, and the Claude review bundle with: the surface-realization fix,
  the three closed survivors, the new fingerprint, the final disruption rate, the selected default, and
  the one-line rollback.
- Run: source lint; the full validation suite (current baseline 448/448);
  advisory, balanced, and exhaustive dry runs; direct/workflow, cover-letter, and qualifications
  parity; the full 35-build corpus; command inventory; representative Word render inspection across
  major lanes.

## Decision points (both resolved by the approvals above)
- Phase 1-2 targeted placement: approved; proceed.
- Phase 4 promotion: pre-approved conditional on a clean Phase 3 (disruption exactly 0 and all safety
  gates). No further pause required for the clean path; the hold path keeps advisory and returns a
  packet. Rollback is one line at any time.
