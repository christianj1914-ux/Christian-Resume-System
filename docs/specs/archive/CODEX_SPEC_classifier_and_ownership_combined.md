# Combined System-Wide Classifier Calibration and Ownership Audit Upgrade

Status: implemented and finally verified 2026-07-31. Merges and sequences the two follow-on specs
(`CODEX_SPEC_core_requirement_classifier_calibration.md` and
`CODEX_SPEC_top_third_ownership_language.md`) into one gated increment structure. Those two files
remain the detailed references for each workstream; this file governs order and shared gates.

Final authoritative verification: 35/35 isolated builds succeeded at exactly two pages under
fingerprint `fcec9dcb4cbd3c9c8c1ba0ddd17686d16585c419f363d9626796fa174f3c8d84`.
Balanced safety passed with zero false/non-requirement blockers and zero supported-core disruption.
Ownership produced no system-wide FAIL requiring verb-lift infrastructure. The conditional promotion
gate passed, so balanced is now the production default; advisory and exhaustive remain explicit
overrides.

## Summary
Implement both follow-ups across all commercial employers, roles, and source lanes:
1. Calibrate the core-requirement boundary so generic competencies and domain terms cannot block
   balanced policy.
2. Correct the top-third ownership audit so it evaluates the actual skim zone and recognizes truthful
   execution verbs.

Sequence the classifier first because it is the higher-value change and may enable balanced as the
default. Ownership restructuring and verb-lift infrastructure remain conditional on post-detector
corpus evidence.

## Incremental Implementation

### Increment 1 - Baselines and diagnostics
Extend the corpus analyzer to record for every core candidate: final class; classifier admission
reason; validating requirement text; catalog concept; core or breadth placement; balanced blocking
effect. Also record ownership findings with the exact segments currently audited. Capture baseline
rows for the 15-build recent corpus, 20-role legacy corpus, and existing commercial outputs,
including Fit, Tailoring, alignment score, fail-floor result, coverage, and page count.
Exit gate: every projected balanced blocker and ownership warning has a traceable admission path and
source text.

### Increment 2 - Core-requirement calibration
Preserve the four classes: REQUIREMENT, COMPETENCY, DOMAIN, NOISE. Correct both admission layers:
`classify_keyword_candidate` distinguishes appearing in a requirement sentence from being the
requirement concept; `audit_keywords` admits only validated REQUIREMENT terms into core; validated
COMPETENCY and DOMAIN terms enter breadth; NOISE remains excluded.

A term reaches REQUIREMENT only through: a supported canonical catalog concept or meaningful multiword
permitted surface; a validated role-title phrase; or a multiword phrase whose head and tail jointly
carry requirement meaning.

Calibration behavior:
- Generic singletons such as process, configuration, quality, status, technical, measurement, and
  scope become breadth unless represented by a stronger canonical concept.
- Generic-head phrases such as documentation reporting and client service become breadth or collapse
  into their parent concept.
- A one-word catalog alias cannot create a separate core concept when its canonical multiword concept
  is absent.
- Genuine concepts such as system configuration, ERP implementation, and project delivery remain core
  when supported by catalog or title context.
- Exact JD literals remain available for ATS matching and placement even when their scoring tier is
  breadth.
- Existing shape and noise gates remain unchanged; no denylist is added.
Exit gate: named false blockers classify as breadth, genuine controls remain core, and known noise
remains excluded.

### Increment 3 - Classifier corpus and Fit-safety gate
Run the classifier changes independently before changing ownership behavior. Record: old/new core
denominators and coverage; breadth changes; supported core misses; balanced blockers; alignment
scores and fail-floor results; Fit and Tailoring transitions; direct/workflow gating parity.

Mandatory Fit safeguard:
- No existing PASS or BRIDGE build may become FAIL solely because a COMPETENCY or DOMAIN term moved
  from core to breadth.
- If such a transition occurs, stop and correct denominator normalization or alignment-score coupling
  before proceeding.
- A Fit change is acceptable only when a separately identified genuine requirement or evidence
  blocker justifies it.

Balanced promotion:
- Promote balanced only if false core blockers are zero, every remaining core blocker is genuine and
  supported, breadth-only misses never block, malformed terms never produce INCOMPLETE, and
  direct/workflow gates agree.
- Otherwise advisory remains the default and residual blockers are documented.
- Exhaustive behavior remains unchanged.
After concept reconciliation, collapse overlapping Resume Notes entries to one primary concept line
while retaining exact surfaces in diagnostics.
Exit gate: the default-policy decision is evidence-backed, and the Fit-safety condition passes.

### Increment 4 - Final-document audit consistency
Make the packaged DOCX the audit authority: package the final DOCX; re-read its visible content;
recompute the final audit snapshot with the original build inputs; write Resume Notes from that
snapshot. Compare pre-package and packaged snapshots. Fail on changes to: Fit or Tailoring;
core/breadth coverage; alignment score or fail-floor result; ownership findings; supported misses or
genuine gaps; prose findings; policy blockers. This is a consistency safeguard, not a presently
confirmed stale-notes defect.
Exit gate: the final DOCX and Resume Notes always derive from the same content state.

### Increment 5 - Correct top-third extraction and detection
Add a dedicated ownership skim-zone extractor containing: Professional Summary; first visible
experience role summary; first two bullets under that same role; no lower-role content. Retain
broader multi-role extraction for keyword-placement auditing.

Classify clause-leading verbs: accountable (owned, managed, ran, was responsible for); leadership
(led, drove, guided); execution (delivered, built, implemented, launched, designed, developed,
protected, improved, accelerated, resolved, stabilized); coordination (coordinated, aligned);
collaboration (partnered, contributed, worked with); support (supported, helped, assisted, involved
in). Treat an identity-led first summary sentence as valid and the second sentence as the primary
proof sentence.

Severity: PASS when execution-or-stronger proof leads the proof sentence or first-role opening and
strong segments outnumber soft segments; REVIEW when valid ownership proof exists but repeated soft
clauses dilute it; FAIL when the corrected skim zone lacks execution-or-stronger proof or soft
language dominates without an accountable carrier. Only FAIL lowers Fit; REVIEW remains a quality
warning.
Exit gate: lower-role bullets no longer pollute ownership auditing, valid execution verbs count, and
support-heavy fixtures still fail.

### Increment 6 - Ownership measurement gate and conditional repair
Re-run both corpora and existing commercial outputs after Increment 5.
Mandatory decision:
- If no ownership FAIL remains, stop; do not build lift infrastructure.
- If a remaining FAIL is honestly support-level with no stronger same-role evidence, preserve it and
  stop.
- If stronger exact same-role evidence exists, first use existing summary selection, clause
  consolidation, or bullet ordering.
- Add ownership metadata and automatic lifting only when a FAIL remains after restructuring and exact
  source evidence proves a stronger verb for the same action and object.
If activated: add structured ownership_ceiling and permitted_ownership_verbs only to required catalog
entries; validate them through source lint and paragraph fingerprints; permit lifts only for
catalog-linked or exact same-role clauses; reject changes to metrics, objects, scope, tools,
outcomes, employer, role, or authority; preserve the original prose when provenance, quality, or
layout validation fails.
Exit gate: either no lift infrastructure is built, or every implemented lift is exercised and
provenance-safe.

### Increment 7 - Full verification and documentation
Run: source lint; full smoke and validation suites; advisory and balanced dry runs; direct resume,
cover-letter, and qualifications workflows; both keyword corpora; commercial-output ownership
analysis; command inventory; representative Word render inspections across major lanes.
Report after every increment: completed checklist; files and major behaviors changed; tests and
builders run; core/breadth and alignment deltas; false and genuine blockers; Fit and Tailoring
changes; ownership-severity changes; page count; selected default policy; conditional ownership-lift
decision; regressions, blockers, and next increment. Update command help, system references,
architecture documentation, corpus summaries, and both canonical follow-up specs.

## Interfaces and Tests
Internal additions: classifier diagnostics expose admission reason and validating requirement text;
core consumers require candidate_class == REQUIREMENT; ownership auditing consumes ordered skim-zone
segments; a final-audit snapshot becomes the source for Resume Notes and packaged-output consistency;
no new user-facing CLI is required.

Required regressions:
- Every named generic false blocker routes to breadth unless promoted by a canonical concept.
- system configuration, ERP implementation, and project delivery remain core controls.
- COMPETENCY and DOMAIN never enter balanced's core denominator.
- Known noise remains excluded.
- Breadth-only misses never block balanced.
- No preexisting PASS or BRIDGE build becomes FAIL solely from core-to-breadth recalibration.
- Corrected ownership extraction excludes lower-role bullets.
- Identity-led summaries with strong proof pass.
- Mixed ownership produces at most REVIEW; support-heavy content remains FAIL.
- Execution verbs such as launched, protected, and improved count correctly.
- Final packaged DOCX findings match Resume Notes.
- No employer-specific production branch is introduced.
- Reorganization sentences, company context, titles, role order, Education, Professional Development,
  formatting, and two-page compliance remain intact.

## Assumptions
- Classifier calibration proceeds regardless of the ownership measurement outcome.
- Balanced is promoted only when every promotion and Fit-safety condition passes.
- Ownership rewriting remains conditional and may correctly result in no new infrastructure.
- Exact ATS matching remains strict.
- Honest support-level work is never relabeled as leadership to improve Fit.
- Source resumes receive no keyword variants or ownership rewrites.
