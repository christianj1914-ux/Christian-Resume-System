# Codex Spec: ATS Keyword Upgrade (folds into the cleanup commit)

## Purpose
Raise real ATS callback rate by fixing what the keyword layer selects and writes, not
how it matches. This is the root-cause version of the bullet-stapling cleanup: when the
resume writes the JD's exact high-value term in the right place, the awkward
`strengthening {keyword}` tail is no longer needed. Do this in the same pass as the
prose cleanup, keep Adobe Sr PM and Blue Yonder Program Manager at PASS resume + PASS
cover, and preserve every truthfulness guardrail (no invented tools, methods, metrics,
or experience; weak fits stay honestly FAIL/BRIDGE).

## Design rule that must not change
Keep `contains_search_term` (resume_analysis.py) EXACT with its current light stemming.
Do NOT loosen matching to accept synonyms. Loosened matching would make the resume pass
our own audit while the literal ATS string is still absent, which costs callbacks. The
audit must keep forcing the literal term to appear; the fix below changes the WRITER so
the literal term actually gets written.

---

## Change 1 (highest impact): canonical JD-term mirroring in the output

Problem: the JD says "stakeholder management" but the generator writes "stakeholder
governance"; the JD says "requirements gathering" but we write "requirements definition."
Same concept, different surface string. The audit flags a gap and the ATS misses the
literal match, even though the concept is truthfully covered.

Fix: add a truthful-equivalence map and make the generator prefer the JD's exact surface
form when it is present in the JD and the concept is already supported by Christian's
evidence.

Implementation:
- Add `JD_TERM_MIRROR` in resume_analysis.py: a list of equivalence groups. Each group =
  `{ "resume_forms": [...], "jd_forms": [...] }`. These are TRUTHFUL equivalences only.
  Seed set (confirm each is truthful before enabling; drop any that are not):
  - stakeholder governance / stakeholder alignment  <->  stakeholder management
  - requirements definition  <->  requirements gathering
  - discovery-to-launch / discovery-to-delivery  <->  discovery to delivery
  - go live  <->  go-live
  - cross functional  <->  cross-functional
  - continuous improvement  <->  process improvement
  - program delivery / project delivery  <->  program management / project management
  - QBR / executive business review  <->  quarterly business review
  - UAT  <->  user acceptance testing
  - SOW  <->  statement of work
  - presales  <->  pre-sales
- New helper `jd_preferred_surface(concept_term, job_description)`: if a resume form is
  about to be written AND one of its JD equivalents literally appears in the JD, return
  the JD's exact surface string; else return the original.
- Wire this into the two writer paths that currently produce placement text:
  1. the top-bullet keyword weave in build_resume.py (the same code around the old
     `strengthening/strengthened {piece}` tails), and
  2. summary/skills phrasing where a mirrored concept is emitted.
- Acronym pairing: when a JD equivalence pair is an acronym + expansion (ERP, SaaS, KPI,
  RFP, UAT, QBR, SOW), ensure BOTH forms appear at least once across summary + skills, so
  a recruiter query on either form matches. Most already appear in Skills; add the missing
  side rather than duplicating.

Truthfulness guardrail: only mirror when the concept is already supported. If a JD term
has no truthful resume equivalent in `JD_TERM_MIRROR`, it is NOT mirrored and stays a
legitimate gap (or an honest FAIL driver). Never invent an equivalence to win a match.

This change is what lets the stapling be removed cleanly: place the mirrored literal term
inside the most content-relevant bullet, integrated into the sentence, never appended.

---

## Change 2: stop spending bullet space on generic filler

Problem: the live extractor ranks generic nouns (strategic, business, corporate, growth,
approach, deliver, executive) high enough that the placement audit wants them in an early
bullet. They add ~0 ATS value and crowd out hard skills.

Fix:
- Add `BULLET_PLACEMENT_EXCLUDED` in resume_analysis.py (seed: strategic, business,
  corporate, growth, approach, deliver, executive, enterprise-as-bare-adjective, solution
  as a bare noun). Confirm the set does not swallow a legitimate hard term.
- In `keyword_placement_audit` (build_resume.py): a term in `BULLET_PLACEMENT_EXCLUDED`
  may still count as present anywhere, but must NOT generate a Priority 1 or Priority 2
  gap for being absent from the summary/early bullets. It is allowed to live in Skills or
  the summary only.
- Net effect: every weaved bullet now carries a discriminating hard term, and PASS is no
  longer earned by placing filler.

---

## Change 3: prefer recurring multi-word phrases over unigrams

Problem: the ranker leans to single tokens (transformation, process, implementation);
ATS weight exact 2-3 word phrases more, and they discriminate better.

Fix:
- In `audit_keyword_sort_key` (resume_analysis.py), strengthen the existing phrase signal:
  a 2-3 word phrase that occurs >= 2 times in the JD ranks above any unigram that is a
  substring of it. Confirm `line_ngram_phrases` output is actually reaching the ranked set
  (the live run showed mostly unigrams surfacing at the top).
- Do not add phrases that are just filler-word pairs; `is_low_signal_audit_keyword`
  already guards trailing/leading noise, keep that.

---

## Change 4: ATS coverage metric (make callbacks measurable)

Add one number to every build so targeting stops being guesswork.

Definition:
- `ats_coverage(job_description, resume_text)` in resume_analysis.py.
- High-value term set = ranked `audit_keywords` MINUS `BULLET_PLACEMENT_EXCLUDED` MINUS
  `is_generic_soft_keyword`.
- Coverage % = (high-value terms present in resume via `contains_search_term`) / (total
  high-value terms), rounded to a whole number.
- Also report a short list of the top 5 missing high-value terms.

Surface it:
- Print `ATS coverage: NN% (missing: term1, term2, ...)` in the Resume Notes file for
  every build.
- Advisory only, not a hard gate: if coverage < 65%, add a non-blocking note
  "Below typical ATS threshold; review targeting before applying." Do NOT auto-fail and do
  NOT pad unsupported terms to inflate the number.

---

## Interaction with the prose cleanup pass
- Remove the `strengthening/strengthened {piece}` tail format as already planned.
- Replace the "skip the keyword if it will not weave naturally" fallback with:
  relocate, never drop. Order: (1) weave the mirrored literal term into the most relevant
  bullet body; (2) else the next relevant bullet or the summary; (3) else ensure it is in
  Skills; (4) skip ONLY if the term is unsupported by evidence.
- Keep the cover polish items (natural program close, `AI-assisted` casing, de-stacked
  proof phrases).

## Test plan
- Unit: `jd_preferred_surface` returns the JD form only when a JD equivalent is literally
  present and the resume form is supported; returns original otherwise.
- Unit: a `BULLET_PLACEMENT_EXCLUDED` term absent from bullets raises no Priority 1/2 gap.
- Unit: a 2x JD phrase outranks its component unigram.
- Unit: `ats_coverage` math on a fixture with a known present/absent split.
- Regression (content): Adobe Sr PM and Blue Yonder Program Manager resumes contain the
  JD's literal high-value terms (mirrored), contain no stapled tails, and their
  placement-audit gap count is EQUAL OR LOWER than before this change (assert, do not just
  eyeball).
- Gates: `python scripts\smoke_test.py`, `python tasks.py validate`,
  `python tasks.py source-lint`.
- Priority rebuild: Adobe Sr PM + Blue Yonder Program Manager resume + cover, both remain
  PASS; print and record their ATS coverage %.
- Spot check 3-4 borderline BRIDGE/PASS roles from the 20 to confirm coverage did not
  regress and no lane lost a supported keyword. Full 20 rerun not required.

## Assumptions / guardrails
- Matching stays exact; only selection, ranking, writing, and reporting change.
- No invented tools, methods, metrics, or experience; every mirror pair is a truthful
  equivalence and gets confirmed before enabling.
- Weak fits stay honestly FAIL/BRIDGE; coverage metric never pads unsupported terms.
- One focused commit after gates + priority rebuild pass; do not commit generated outputs
  or active jobs/ files.
