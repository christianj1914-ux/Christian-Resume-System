# Codex Spec: Relax the Skills Cap (recover coverage, keep junk filter)

## Purpose
The Skills-insertion guardrail (cea5eba) correctly removed junk (job titles, bare vague
nouns, non-skill fragments) and that part must stay. But the hard per-group cap of 8 also
dropped LEGITIMATE, coverage-bearing skills, which cut core coverage on ~12 roles versus the
prior run and pushed two roles from BRIDGE to FAIL (Delta Crew Tech PO, Adobe Solutions
Consultant). Example of over-trim: "Business Process" (a real competency and JD term) was
removed from Manhattan IT to satisfy the cap.

The dump problem was the JUNK, not the count. A group of 10-11 genuine, relevant skills reads
fine. For a callback-maximizing system, dropping legitimate ATS terms to hit an aesthetic
number is the wrong trade. Fix: keep the junk filter, make the cap soft, and never drop a
coverage-bearing or source skill.

Stay on `codex-systemwide-docfixes`, one focused commit, no merge.

## Keep unchanged (do NOT touch)
- The junk filter from cea5eba: reject JD title phrases/role names, bare vague single-word
  nouns, and non-skill-shaped fragments; allow multi-word competencies even when they start
  with a denied word (Business Process Improvement, Service Delivery). This is correct.
- Render-boundary placement, core-promotion gating, denominator hygiene, coverage metrics,
  the four polished ledger labels, and the six priority terms.

## Change: make the cap soft and coverage-protecting
In the targeted insertion path in `scripts/build_resume.py`
(`add_targeted_core_competencies(...)` and its trim logic):

1. Raise the per-group trim threshold from 8 to 11. Groups at or under 11 are NOT trimmed.
2. Trim a group ONLY when it exceeds 11 items AFTER the junk filter has run (so trimming
   never removes junk-vs-real; junk is already gone).
3. When trimming, rank items by JD relevance (JD frequency / `audit_keyword_sort_key`) and
   drop from the BOTTOM, but NEVER drop an item that is:
   - an original source-resume skill, OR
   - the sole carrier of a JD core or breadth match (i.e., removing it would flip a JD term
     from present to missing anywhere in the resume). Check via `contains_search_term` over
     the rest of the document before dropping.
4. If the only remaining droppable items are protected, STOP trimming and leave the group
   slightly over 11. A group of 12 clean, relevant, coverage-bearing skills is acceptable;
   losing a covered ATS term is not.

Net effect: junk is always removed; legitimate coverage is preserved; only genuinely oversized
groups of low-value redundant items get trimmed.

## Tests
- A group of 10-11 legitimate skills is not trimmed at all.
- Junk (title phrases, bare vague nouns) is still rejected regardless of group size.
- Trimming never removes a source skill or the sole carrier of a JD core/breadth term; if only
  protected items remain, the group is left slightly over threshold.
- The four polished labels and six priority terms remain present.
- Run once before commit: `python scripts\smoke_test.py`, `python tasks.py validate`,
  `python tasks.py source-lint`.

## Verification rebuild (targeted)
- Rebuild: the two priorities (`16_Blue_Yonder_-_Program_Manager`,
  `19_Adobe_-_Senior_Program_Manager_GSO`) plus the roles that regressed under the hard cap:
  `04_Delta_Crew_Tech_PO`, `20_Adobe_-_Solutions_Consultant`, `13_Blue_Yonder_Functional_Architect`,
  `09_Stord_Sr_Deployment_TPM`, `17_Manhattan_..._IT_Delivery_Manager`, `18_Manhattan_Enablement`.
  Restore active jobs/ after each swap.
- Assert:
  - Priorities remain resume PASS + cover PASS, six terms present, four labels intact.
  - Core coverage on the regressed roles recovers to at least the prior peak-run levels (e.g.
    Adobe Solutions core back toward ~93, Blue Yonder Architect toward ~95, Manhattan
    Enablement back to 100); any residual lower value is explained by junk removal, not a lost
    real skill.
  - Delta Crew and Adobe Solutions return to at least BRIDGE unless they FAIL for a genuine
    non-coverage reason (state which).
  - No Skills group contains a job title or bare vague noun; no group is a keyword dump.
- Then rebuild the remaining targets in batches of five (finish each batch); stop only on the
  regression signature (promoted term missing + core drop).

## Report
- Commit hash; per-role core/breadth before (prior run) vs after (this run) for the rebuilt
  roles, plus Skills count and max group size; confirmation Delta Crew and Adobe Solutions
  recovered (or genuine-FAIL explanation); 0 current bad phrases; 0 PDFs; active jobs/ restored.

## Guardrails
- One focused commit. Do not stage generated outputs, scratch folders, active jobs/ files,
  archive churn, or spec docs. Weak fits stay honestly FAIL/BRIDGE. Federal remains queued
  until this verifies.
