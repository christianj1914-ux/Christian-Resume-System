# Codex Spec: ATS Finalize Pass (last polish before Federal)

## Purpose
The ATS-safe keyword commit (da108e5) landed the right things: stapling removed, cover
polish in, mirroring working, both priorities PASS/PASS, coverage metric printing. This
pass fixes the two issues that remain before we move to the Federal workflow:

1. The coverage number is not yet trustworthy as a callback signal. It measures against
   `high_value_audit_keywords`, which is the already-lean `audit_keywords` set minus
   filler, so it collapses to 4-8 terms (Blue Yonder 4/4, Adobe 8/8). 100% of 4 is not a
   real ATS read, and the metric got partially optimized by shrinking its own denominator.
2. The weave now forces keywords into unnatural or mildly inflated spots to satisfy the
   placement audit ("Delivered technical delivery projects", "automation-focused technical
   delivery leader", "customer-facing" on a warehouse/robotics setup).

Keep everything that already landed. Stay on `codex-systemwide-docfixes`, do not merge,
one focused commit. Guardrails hold: exact matching, no invented content, weak fits stay
honestly FAIL/BRIDGE, Word-only, do not stage generated outputs or active `jobs/` files.

---

## Change A: report TWO coverage numbers so the metric is trustworthy

Do NOT widen `high_value_audit_keywords`. Placement logic keys off it; changing it would
re-destabilize the weave. Instead keep it as the strict "core" number and ADD a broader
"breadth" number that approximates what a real ATS keyword scan sees.

- Add `ats_scan_terms(job_description)` in resume_analysis.py: a broader realistic keyword
  surface built from the JD requirement/responsibility text, not the lean audit set.
  Include hard skills, tools, named methods, and recurring 2-3 word noun phrases. Exclude
  only true stopwords, company/boilerplate tokens, and `is_generic_soft_keyword` filler.
  Target roughly 12-25 terms for a normal-length JD. Reuse existing extraction helpers
  (`keyword_set`, `line_ngram_phrases`, requirement parsing) rather than a new tokenizer.
- Extend `ats_coverage` to return both:
  - core: current metric over `high_value_audit_keywords` (the must-have terms).
  - breadth: percent present over `ats_scan_terms`, plus top missing breadth terms.
- Resume Notes print both lines on every status (PASS, BRIDGE, FAIL, POOR):
  - `ATS core coverage: NN% (X/Y must-have terms; missing: ...)`
  - `ATS breadth coverage: NN% (X/Y JD terms; missing: ...)`
- Anti-gaming guard (important, this is the failure mode we just saw): if a JD is longer
  than ~250 words and `ats_scan_terms` returns fewer than 10 terms, that is a bug signal,
  not a real 100%. Emit a notes line: `ATS breadth set unexpectedly small; coverage may be
  understated.` Do NOT silently shrink the set to hit 100%.
- Both numbers stay advisory. Neither changes fit status. Never pad unsupported terms to
  raise either number.

Rationale: core near 100% tells you the must-haves are placed; breadth in a meaningful
range (target 70%+ on a 12-25 term set) tells you the resume actually mirrors the posting.
Christian uses breadth for the real go/no-go decision.

---

## Change B: de-force the weave (natural-fit guard)

The placement audit requires high-value terms in the summary or first bullets, and the
weaver currently forces them even when no natural home exists. Add a natural-fit guard so
a forced, awkward, or inflated insertion is rejected in favor of Skills placement.

In build_resume.py weave path:
- Same-stem dedup: reject any rewrite that puts two words sharing a stem within the same
  sentence (e.g. "delivered ... delivery", "manage ... management"). If the only available
  rewrite trips this, do not ship it; fall back down the ladder.
- Evidence-fit check: a term may only be woven into a bullet whose underlying evidence
  actually supports that term. "customer-facing" must not attach to a warehouse/robotics
  setup bullet. If no top bullet's evidence supports the term, do not force it into a
  bullet; place it in Skills.
- No identity-line injection: never inject a lightly-supported term into the summary's
  headline identity clause. "automation-focused technical delivery leader" is out.
  Automation belongs in the AI/Workflow Automation Skills group (already present) or a
  truthful AI/robotics bullet, not the leader identity.
- Relocate ladder, revised terminal step: when a high-value term has no natural bullet or
  summary home, Skills placement SATISFIES it. In that case the placement audit must NOT
  raise a Priority 1/2 gap for that term, and core coverage still counts it present.
- Deterministic must-place boundary (do not leave this fuzzy): a term REQUIRES top-third
  placement (and may raise a gap) only if it is a JD title-phrase OR its JD frequency is
  >= 2. Every other term, including a low-frequency core term with no natural home, is
  Skills-satisfiable and must NOT trigger forced insertion or a placement gap. This is the
  rule that keeps a low-frequency core term like "automation" out of the identity line: it
  is core for coverage counting, but not must-place, so it lands in Skills instead of being
  forced into the summary. Membership in the core set alone is NOT sufficient to force
  placement; centrality (title-phrase or frequency) is required.
- Precedence: the natural-fit guard (same-stem, evidence-fit, no identity injection) ALWAYS
  wins. If even a must-place central term has no natural, non-redundant, evidence-supported
  home, it goes to Skills and does NOT raise a gap. The must-place requirement never
  justifies an awkward or inflated insertion. Placement is earned by a natural home, not
  forced to satisfy the audit.

Keep the existing early-window sizing fix (scale the top-bullet hit threshold to the number
of usable high-value terms) so a 4-term JD does not demand 6 hits.

---

## Change C: clear the specific artifacts in the two priority docs

These are the concrete regressions; fix the generators, then add tests.

- Adobe + Blue Yonder resumes: "Delivered technical delivery projects end to end" must
  become natural (e.g. "Delivered enterprise technology projects end to end") with
  "technical delivery" satisfied elsewhere naturally or in Skills, not by same-stem repeat.
- Adobe summary: remove the "automation-focused technical delivery leader" identity
  injection; the opener returns to the clean program-management identity, and automation is
  satisfied via Skills or a truthful bullet.
- Blue Yonder resume: "customer-facing system setup for a new warehouse operation" must not
  attach "customer-facing" to that bullet; relocate the term to an evidence-supported spot
  or Skills.

Regressions in smoke_test.py:
- No same-stem repetition within a bullet (assert on the two priority resumes).
- Summary identity clause contains no lightly-supported injected term.
- "customer-facing" appears only where evidence supports it.
- Both coverage lines (core + breadth) are present in generated notes for a PASS and a FAIL
  fixture.
- `ats_scan_terms` returns >= 10 terms for a normal-length JD fixture (guards the shrink).

---

## Test and rebuild plan
- Gates after changes: `python scripts\smoke_test.py`, `python tasks.py validate`,
  `python tasks.py source-lint`.
- Rebuild the two priority targets (`19_Adobe_Senior_Program_Manager_GSO`,
  `16_Blue_Yonder_Program_Manager`) with byte-for-byte active `jobs/` restore after each
  swap. Record BOTH coverage numbers before and after.
- Spot-check breadth only (not the full 20) on 3 roles from different lanes
  (`03_JBAndrews_Solutions_Engineer`, `13_Blue_Yonder_Functional_Solution_Architect`,
  `17_Manhattan_Associates_Senior_IT_Delivery_Manager`): confirm breadth set is >= 10
  terms and the number reads plausibly, not artificially 100%.
- Acceptance:
  - Adobe and Blue Yonder remain resume PASS + cover PASS.
  - Both notes files show core AND breadth coverage.
  - Breadth denominator is >= 10 on all normal-length JDs checked.
  - Artifact scan clean: no "delivered technical delivery" (or other same-stem repeat in a
    bullet), no "automation-focused ... leader" identity, no "customer-facing" on the
    warehouse bullet, plus the prior banned phrases (`strengthening`, `strengthened`,
    `teams delivery plans`, `The practical fit is`, lowercase `ai-assisted`,
    `the and plant controllers`, dangling `and.`).
  - Word-only, no PDFs.

## Assumptions / guardrails
- Do not widen `high_value_audit_keywords`; add breadth as a separate report only.
- Exact matching unchanged. Mirroring, cover polish, and prior fixes preserved.
- No invented tools, methods, metrics, or experience; Skills placement only for truthful
  terms. Weak fits stay honestly FAIL/BRIDGE; coverage never pads.
- One focused commit after gates + priority rebuild pass; do not stage generated outputs,
  rebuilt archives, active `jobs/` files, or this spec unless kept as project docs.
