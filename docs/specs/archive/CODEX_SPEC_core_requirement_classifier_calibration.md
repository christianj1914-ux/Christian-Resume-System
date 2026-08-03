# Core Requirement Classifier Calibration (balanced-default enabler)

Status: implemented July 29-30, 2026. Follow-on to CODEX_SPEC_keyword_tailoring_reliability.md.
The four-class classifier now admits only validated REQUIREMENT concepts to core; COMPETENCY and
DOMAIN route to breadth, and NOISE remains excluded. Advisory remains the default because the
reconciled corpora contain genuine supported-but-unwritten core concepts, not false blockers.

## Implementation result
- Named generic false blockers route to breadth; the control concepts `system configuration`,
  `ERP implementation`, and `project delivery` remain core.
- Catalog-backed surface families count once in core while exact JD surfaces remain available for
  ATS diagnostics and placement.
- Recent corpus: average core coverage 84.9% -> 67.7%, breadth 65.7% -> 65.6%, projected balanced
  blockers 15 -> 10, with zero false or non-REQUIREMENT blockers.
- Legacy 20-role corpus: average core coverage 90.6% -> 72.1%, breadth 71.2% -> 71.4%, projected
  balanced blockers 12 -> 18, with zero false or non-REQUIREMENT blockers. The increase consists of
  genuine catalog-backed requirements that older scoring omitted.
- Classifier-specific job-language checks now recognize validated breadth surfaces so moving a term
  out of core cannot by itself create a Fit FAIL.
- Balanced was not promoted: 28 genuine supported core concepts remain unwritten across the two
  archived corpora. Advisory therefore remains the production default.

## Problem
Balanced mode cannot become the default. Per the corpus verification
(`scratch/keyword_reliability_corpus_summary.md`), balanced's shadow run produced 15 projected
blockers across 7 recent builds and 12 across 8 legacy builds. The blockers are generic surfaces
classified as core must-have requirements: `process`, `configuration`, `quality`, `status`,
`documentation reporting`, `client service` (recent) and `technical`, `measurement`, `process`,
`quality`, `scope` (legacy). These are not malformed noise (the known-noise cleanup succeeded and
holds at zero), but they are also not genuine standalone core requirements. Treating them as
supported-but-unwritten core misses would block otherwise-sendable builds, which fails the
zero-false-core-blocker promotion condition.

The goal is a core class that contains only genuine must-have requirement concepts, so balanced can
be promoted safely. Advisory and exhaustive behavior are unchanged.

## Root-cause anchor
There are two fix sites, not one. The standalone framing named only the first.

Site A, core admission: `scripts/resume_analysis.py` `audit_keywords` (~1673-1677) skips a term only
when it is NOISE or unvalidated, so validated COMPETENCY and DOMAIN terms enter the core denominator
alongside REQUIREMENT. Core admission must require `candidate_class == REQUIREMENT`; COMPETENCY and
DOMAIN route to breadth. Without this, tuning the REQUIREMENT boundary alone will not stop generic
terms from blocking balanced.

Site B, the REQUIREMENT boundary: `scripts/resume_analysis.py` `classify_keyword_candidate` (~1478). A term is routed to REQUIREMENT
(and therefore counted in core coverage) when it is `validated` (appears inside any parsed
requirement element, ~1509) and then passes one of the REQUIREMENT branches: catalog surface (~1538),
role-title phrase (~1545), or "requirement-shaped phrase" (~1563, length >= 2 with a valid phrase
tail or an important short term). The permissive path is that a generic token which merely co-occurs
in a requirement sentence, or a two-word phrase with a generic head and a whitelisted tail
(`documentation reporting`, `client service`), reaches REQUIREMENT even though it carries no distinct
must-have concept. `validated` measures presence in a requirement sentence, not that the term itself
is the requirement.

## Proposed approach
1. Instrument first, then tighten. Add a temporary diagnostic (or extend the corpus analyzer
   `scratch/keyword_reliability_corpus.py`) that, for every projected balanced blocker in both
   corpora, records which `classify_keyword_candidate` branch admitted it and the requirement element
   text that validated it. Do not tighten blind; the exact admitting branch per term must be known.
2. Separate "appears in a requirement" from "is a requirement concept." Core REQUIREMENT should
   require one of: a validated evidence-catalog concept surface; a role-title phrase; or a multi-word
   phrase whose head (not only its tail) carries a domain or skill signal. A lone generic noun
   (`process`, `configuration`, `quality`, `status`, `scope`, `technical`, `measurement`) should not
   reach core on co-occurrence alone; route it to COMPETENCY or DOMAIN (breadth) instead, where it is
   still reported and still eligible for placement but never blocks under balanced.
3. Treat generic-head two-word phrases (`documentation reporting`, `client service`) as breadth
   competency surfaces, or fold them into the larger catalog concept they belong to, rather than as
   independent core requirements.
4. Prefer catalog-driven promotion. Where a generic surface is genuinely core for a specific role
   (for example `configuration` for an ERP configuration role), let it reach core only because it is
   a permitted surface of a catalog concept that the role context supports, not because of raw
   frequency or sentence co-occurrence. This keeps the rule employer-neutral and data-driven.
5. Keep the shape and noise gates exactly as shipped. This change refines the REQUIREMENT-versus-
   COMPETENCY boundary only; it must not reintroduce any denylist behavior or move a real requirement
   out of core.

## Secondary cleanup (optional, low priority)
Resume Notes "Placed Supported Terms" currently lists overlapping sub-surfaces of one placed phrase
as separate lines (for example `professional services consultant`, `professional services`,
`professional service`, `services consultant`; and `multiple implementation project` /
`projects`). Collapse reporting to the primary concept surface so the notes read cleanly. This is
cosmetic; coverage math is already correct.

## Validation and acceptance
- Re-run the corpus analyzer on both the July 27-29 and legacy 20-role corpora. Acceptance:
  projected balanced core blockers reach zero, with each former blocker either correctly reclassified
  to breadth or confirmed as a genuine, evidence-supported, still-unwritten core requirement that the
  placement engine then realizes.
- No build that is PASS or BRIDGE today may become blocked by a breadth-only term under balanced.
- No existing PASS or BRIDGE build flips to FAIL solely because of the core-to-breadth denominator
  recalibration. Moving COMPETENCY and DOMAIN terms out of core changes core-coverage percentages,
  which the alignment score and FAIL floor read; verify no build crosses the fail floor as a side
  effect of the denominator change.
- Known noise remains at zero in core and breadth (no regression of the shipped classifier).
- The Aptean fixture keeps zero supported core misses, apparel/fashion/textile as the only gap, and
  exactly two pages.
- Add unit tests: each named false blocker (`process`, `configuration`, `quality`, `status`,
  `scope`, `technical`, `measurement`, `documentation reporting`, `client service`) classifies as
  breadth, not core, unless promoted through a catalog concept; and a control set of genuine core
  requirements (for example `erp implementation`, `system configuration` when catalog-supported,
  `project delivery`) still classifies as core.
- Run `python scripts/smoke_test.py`, `python tasks.py validate`, `python tasks.py source-lint`, and
  a representative balanced dry run.
- Only after zero false core blockers across both corpora and direct/workflow gating parity, promote
  balanced to the default per the rollout rules. If the condition is not met, advisory stays default
  and the residual blockers are documented.

## Guardrails and non-goals
- Employer-neutral: no rule may branch on employer identity; promotion to core is via catalog
  concepts, title phrases, and phrase shape only.
- Do not weaken exact ATS matching, and do not remove any genuine requirement from core.
- Do not reintroduce standalone denylists; refine classification, not filtering.
- Advisory and exhaustive semantics are unchanged.
- No change to source resumes, formatting, two-page length, or Word-only output.
