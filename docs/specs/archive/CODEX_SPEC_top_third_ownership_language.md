# Top-Third Ownership Language (Fit quality, honesty-bounded)

Status: implemented July 29-30, 2026. The detector now evaluates the actual recruiter skim zone and
uses tiered PASS/REVIEW/FAIL severity. Only FAIL affects Fit.

## Implementation result
- The production ownership skim contains the Professional Summary, first visible role summary, and
  first two bullets under that role. Lower-role bullets no longer contribute.
- Identity-led summaries use the second sentence as the primary proof sentence. Accountable,
  leadership, execution, coordination, collaboration, and support verbs are classified separately;
  launched, protected, and improved count as execution.
- PASS requires execution-or-stronger proof in the summary proof sentence or first-role opening.
  REVIEW records truthful-but-diluted ownership language without lowering Fit. FAIL remains reserved
  for a skim zone without execution proof or one dominated by soft language without accountability.
- Measurement gate: recent corpus 14 PASS / 1 REVIEW / 0 FAIL; legacy corpus 19 / 1 / 0; all 71
  commercial outputs 67 / 4 / 0.
- Because no genuine ownership FAIL remained, catalog ownership metadata and automatic verb-lift
  infrastructure were intentionally not built. No resume claim was rewritten or inflated.
- The packaged DOCX is now re-read and audited before Resume Notes are written; pre-package and
  packaged snapshots must agree on Fit, Tailoring, coverage, alignment, ownership, gaps, prose, and
  policy blockers.

## Verified root cause and sequencing (added after code grounding)
Investigation showed the primary defect is detector scope, not missing rewrite machinery. The
ownership audit is fed by `role_top_bullet_texts(document_xml, AUDIT_TOP_ROLE_TITLES, ...)`
(`build_resume.py` ~2911), which collects bullets from every recognized role, not the actual top
third. A soft verb in a lower role pollutes the audit, which is why only about 1 of 75 commercial
outputs trips it and why the Aptean warning appears. The detector also omits valid execution verbs
(launched, protected, improved).

Therefore sequence the cheap fixes first: correct the skim-zone extraction (summary plus first-role
summary plus that role's first one or two bullets) and expand the strong-verb vocabulary, then
re-measure both corpora. Build the heavier provenance-bounded verb-lift and structured catalog
ownership fields only if genuinely support-heavy top thirds remain after the detector is honest.
Make "re-measure before building the lift machinery" an explicit gate so unused infrastructure is
not built.

Resolved: the saved notes are not stale. Running the current detector against the final DOCX collects
four bullets (two East West plus two from the lower Aptean role) and reproduces the warning; an
earlier "no warning" spot check used only the first two East West bullets, which accidentally
simulated the corrected skim zone. DOCX and notes share the same build timestamp. This is the same
scope bug, not an earlier-content-state defect. Still, add an audit-state consistency safeguard
(recompute ownership findings from the packaged final DOCX and require exact agreement with the
findings written to Resume Notes) because it protects the trustworthiness of all audit notes going
forward.

## Problem
`top_third_ownership_issues` (`scripts/build_resume.py` ~4617) flags a build when soft verbs
(`supported`, `worked with`, `helped`, `assisted`, `involved in`) appear at least twice in the
summary plus top bullets and strong ownership verbs do not outnumber them
(`soft_hits >= 2 and strong_hits <= soft_hits`, ~4629). The Aptean summary trips this with clauses
like "Supported customer-facing delivery through customer training, structured issue ownership, and
stakeholder communication." The detector fires but nothing rewrites the top third, so the build stays
FAIL on a quality warning even though every claim is truthful and supported.

This is a resume-honesty-sensitive area. The East West and Aptean roles are genuinely partly
support-level (both carry mandatory reorganization sentences), so the fix must improve verb strength
only within provenance limits. Relabeling genuine support work as ownership would be a
misrepresentation and is out of bounds.

## Anchors
- Detector: `top_third_ownership_issues` (~4617); softeners `TOP_THIRD_OWNERSHIP_SOFTENERS` (~304);
  strong-verb regex `TOP_THIRD_STRONG_OWNERSHIP_RE` (~311); `OWNERSHIP_VERB_LADDER`
  (`owned, led, was responsible for, coordinated, supported`, ~303).
- Summary and role-summary composition live in `scripts/resume_content.py`; the provenance and
  rewrite-safety gates from the prior increments (same-role evidence, unchanged metrics and
  ownership, prose repair, writing evaluation) are the machinery any fix must reuse.

## Proposed approach
Two complementary moves; implement the first, consider the second only if needed.

1. Provenance-bounded verb lift in the top third. When the detector would fire, attempt to raise the
   weakest soft clause to the strongest ownership verb the same-role evidence actually supports,
   using the existing rewrite-safety gates. The verb ladder gives the ordering; the catalog evidence
   strength and ownership limits for the sourcing role set the ceiling. If evidence supports only
   "coordinated," lift to "coordinated," not "owned." Never raise a clause above its cataloged
   ownership limit. Re-run the writing-quality and prose-repair checks on any rewritten clause.

2. Honest restructuring when lift is not permitted. Where the evidence is genuinely support-level and
   no stronger verb is licensed, reduce soft-verb density instead of faking ownership: lead the top
   third with a different clause that is genuinely owned and supported, consolidate two soft clauses
   into one, or move the support clause out of the skim zone. The objective is an accurate ownership
   signal in the top third, not a forced strong verb.

Also review the detector threshold. A single unavoidable "supported" plus one "worked with" can trip
`soft_hits >= 2` even in an otherwise strong summary. Consider weighting by whether a strong ownership
verb already leads the first sentence, so an accurate, ownership-led summary with one trailing support
clause is not penalized.

## Validation and acceptance
- Aptean rebuild: the top-third ownership warning clears through licensed verb lift or honest
  restructuring, with no new invented ownership, no changed metrics, and the mandatory reorganization
  sentence intact. Target outcome: Fit moves off FAIL for this reason, keyword placement stays
  complete, exactly two pages.
- No build gains an ownership verb its source evidence does not support. Add a test that a
  support-level clause is never lifted above its cataloged ownership limit.
- Add tests for the detector threshold change: an ownership-led summary with one trailing support
  clause does not flag; a genuinely support-heavy top third still flags.
- Run `python scripts/smoke_test.py` (including the existing `top_third_ownership_issues` assertions
  around ~2758 and ~2922), `python tasks.py validate`, and representative render inspections across
  lanes to confirm summaries still read naturally.

## Guardrails and non-goals
- Honesty first: never claim ownership, leadership, metrics, or scope beyond approved same-role
  evidence. This constraint outranks clearing the warning.
- Preserve the mandatory "Position impacted by company reorganization." sentences and all source-truth
  rules.
- Keep first-person pronouns out, keep the summary within its length rules, keep two-page fit.
- This is a top-third quality change only; it does not touch keyword classification, coverage math,
  or policy modes.
