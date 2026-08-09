# Codex Spec: Skills-Insertion Guardrail (last commercial item)

## Purpose
The 20-run rebuild succeeded: no core regressions, breadth up on good fits, priorities clean.
But the bias-to-Skills placement now over-stuffs the Skills section on higher-count roles.
Concrete example, Manhattan IT Delivery, first skills group (13 items):
"Structured Discovery | Requirements Definition | Solution Design | SOW and FRD Development |
Service Delivery | Multi-Workstream Coordination | Process Management | Senior Delivery Manager
| Quality | Accounting | Stakeholder Management | Feature Adoption | Project Management".
Problems: "Senior Delivery Manager" is a JOB TITLE, not a skill; "Quality" and "Accounting"
are bare vague nouns pulled from the JD. This reads as a keyword dump to a recruiter.

Fix the Skills insertion so it only adds real, skill-shaped, truthful terms and caps group
size. Do NOT touch anything else that works. Stay on `codex-systemwide-docfixes`, one focused
commit, no merge.

## Where
The insertion path builds `skill_terms` and calls
`add_targeted_core_competencies(document_xml, skill_terms, job_description, limit=8,
allow_over_target=True)` in `scripts/build_resume.py` (around lines 3890-3893), with
candidates gathered near line 3794 (`skills_candidates.append(surface)`). Apply the guardrail
by filtering candidates before insertion and enforcing the cap.

## Guardrail rules (filter a candidate OUT of Skills insertion if any apply)
1. JOB TITLE / ROLE NAME: drop any candidate that is a JD title-phrase or role name. Reuse the
   existing title detection (`title_phrase_candidates` / `is_valid_job_title`). "Senior
   Delivery Manager", "Product Owner", "Solutions Consultant", etc. never become skills.
2. BARE VAGUE NOUN: drop single-word candidates that are not genuine skills/tools/methods.
   Deny bare nouns like `quality`, `accounting`, `business`, `operations`, `service`,
   `strategy`, `growth`, `innovation`, `transformation` UNLESS the term is an explicit ledger
   concept or a known tool/method. A bare noun must be on a real-skill allowlist (or ledger)
   to qualify.
3. NOT SKILL-SHAPED: only insert a candidate that is one of: a ledger concept variant, a known
   tool/platform/certification, a recognized method/framework, or a multi-word skill phrase
   that reads as a competency. Anything else (raw JD n-gram, sentence fragment) is dropped.
4. Keep exact ATS value: the four polished ledger labels stay
   (`Implementation Project Delivery`, `Global Program Management`, `Vendor Partner Management`,
   `AI Pilot Programs`) and the six priority terms remain present. Do not regress them.

## Cap and ranking
- Enforce a hard per-group cap of 8 items (stop using `allow_over_target=True` as an unbounded
  override). If more qualified candidates exist than the cap allows, rank by JD relevance
  (JD frequency / `audit_keyword_sort_key`) and keep the top ones; drop the marginal.
- Never drop a pre-existing genuine source skill to make room for a newly added JD term; if the
  group is already at cap with real skills, do not add more (presence in a bullet/summary or
  simply not-added is fine; truthfulness and readability beat one more keyword).

## Keep unchanged
- Render-boundary placement, core-promotion gating, denominator hygiene, coverage metrics,
  Phase A priority behavior, and the report-only naturalness diagnostics all stay.
- Truthfulness: only real, supported skills. No invented tools or domains.

## Tests
- A JD title-phrase (e.g. "Senior Delivery Manager") is never inserted into Skills.
- Bare vague nouns (`quality`, `accounting`) are not inserted unless ledger/allowlisted.
- A skills group never exceeds the cap after insertion.
- The four polished ledger labels and the six priority terms still insert and match.
- Run once before commit: `python scripts\smoke_test.py`, `python tasks.py validate`,
  `python tasks.py source-lint`.

## Verification rebuild (targeted, not another blind 20)
- Rebuild the two priorities (`16_Blue_Yonder_-_Program_Manager`,
  `19_Adobe_-_Senior_Program_Manager_GSO`) and the three bloated roles
  (`03_Delta_-_Senior_Operations_Analyst`, `17_Manhattan_..._IT_Delivery_Manager`,
  `07_Advyzon_Technical_Consultant`). Restore active jobs/ after each swap.
- Assert: no job titles or bare vague nouns appear in any Skills group; every group <= cap;
  the two priorities remain resume PASS + cover PASS with the six terms present and the four
  polished labels intact; breadth on the priorities does not materially drop (a small
  reduction is acceptable if it came from removing a non-skill term).
- Report per-role Skills-count before/after to confirm the dump shrank (Manhattan IT, Delta,
  Advyzon should drop back toward the low-to-mid 20s).
- Then rebuild the remaining targets in batches of five (finish each batch); stop only on the
  known regression signature (promoted term missing + core drop).

## Report-only items to check in passing (do not block on these)
- Confirm the four polished ledger labels actually landed on the two priority resumes in the
  final output (state present/absent).
- Delta Marketing breadth went 16 -> 8 (the only breadth drop); note the cause; it is an
  off-lane FAIL role so it is not a blocker.
- Blue Yonder Solutions Advisor and Services Advisor FAIL at 100% core; confirm the FAIL is a
  genuine evidence blocker, not a scoring quirk.

## Guardrails
- One focused commit. Do not stage generated outputs, scratch folders, active jobs/ files,
  archive churn, or spec docs.
- Weak fits stay honestly FAIL/BRIDGE. Federal remains queued until this verifies.
