# Codex Implementation Spec: Phase 5 - Consultative Stance and Mindset Module
## July 15, 2026 - Add a balanced consultative-delivery and nervous-system-grounding layer to the interview guide's reader-facing operating system

## Summary

The interview debriefs show a consistent pattern: strong substance undercut by anxiety-driven delivery (hedging, buried outcomes, volunteering salary, turning questions back) and a "selling myself" discomfort that reads as either eager-to-please or defensive. Two frameworks address the root, in balance: the consultative "diagnose, do not sell" stance (which also happens to be the literal Solution Consultant job), and a small set of nervous-system grounding tools. Phase 5 folds both into the guide as reader-facing operating-system content, weighted equally, so every generated guide teaches the mindset and the stance alongside the scripted answers.

Companion personal artifacts already exist and are the source of truth for the content shape: `output/Christian Estrada - Evidence Log (Confidence and Proof Bank).md` and `output/Christian Estrada - Daily Confidence and Consultative Delivery Practice.md`. Phase 5 makes the guide point at and reinforce those, it does not duplicate them.

Claude planned this; Codex implements after the gate below clears.

## GATE (do not start until both clear)

This is Phase 5. Its implementation is gated behind the two open loose ends from the Phase 1-4 landing:
1. `scratch/jd_library/index.csv` is resolved (parses cleanly through the archive subsystem and is committed or reverted; working tree clean except the disposable logs).
2. The F2 runtime checks have passed: a live qualifications build surfaces the software/communication/experience answers and the two new claims, and one unrelated-company guide build shows no Dematic/automation leakage.

Do not begin Phase 5 code until both are done, so this layers on a fully settled tree. Sequence it as the fifth entry in the master hand-off.

## Design principles

- Balanced: the consultative-skills content and the nervous-system content get roughly equal weight. Neither dominates.
- Non-clinical: the grounding content is practical performance guidance, not therapy. Encouraging tone; never pathologizing. Where depth is implied, a one-line note that a professional can help is acceptable, matching the personal daily-practice doc.
- Reader guidance, not scripted answers: the mindset/grounding content renders in the reader-facing operating-system section, NOT as spoken-answer strings. Therefore it must be OUTSIDE the `validate_delivery_principles` scope (same reasoning as finding H2: that validator only runs on answer strings). Do not let the grounding text, which may quote hedges as examples, trip the delivery validator.
- Confirmed facts only: any proof referenced stays inside the confirmed evidence set.

## Implementation Changes

### A. Consultative stance (in the general-answer operating system)

Extend `add_general_answer_operating_system` (in `scripts/build_detailed_interview_guide.py`) with a Consultative Stance block:
- Problem-first framing: open a story with the client's bottleneck, not credentials (Situation = the problem to diagnose). This complements the existing meat-first spine.
- Diagnostic posture: for the interviewer-questions section, prefer questions that probe the team's bottlenecks and where work gets stuck.
- The value formula as a reusable phrasing: "I help [client type] achieve [result] by [method], saving [time/money/risk]."
- Outcomes-not-hours: land every answer on the business result.

### B. Self-talk reframe (folded into the anti-hedge rule)

Extend the existing anti-hedge rule so it carries the reframe, because it is a stronger lever than willpower: sharing relevant expertise is a service, not bragging; withholding a solution that would help the interviewer is the actual disservice. Keep the banned-phrase list as is.

### C. Pre-interview grounding block (reader guidance)

Add a short, non-clinical grounding block to the operating system, rendered as reader guidance only:
- lower the bar (rehearse the one 30-second anchor, not the whole guide),
- separate feelings from facts (predictions are theories to test),
- name the intent (the nervousness is protection, not truth),
- expect the spike before performing (extinction burst = the change working),
- read the evidence log once before the call.
Keep it four to six lines. Do not render it as a spoken answer; do not run it through the delivery validator.

### D. Evidence-log reference

Where the guide currently lists proof points, add a one-line pointer to keep and review a personal evidence log of confirmed wins before each call (referencing the concept, not embedding the file). This ties the guide to the companion artifact without duplicating it.

## Guardrails

- No new CLI surface; no new mandatory document type. This is content added to the existing guide.
- Balanced weighting between the two halves; encouraging, non-clinical tone.
- Reader-guidance content stays outside `validate_delivery_principles`.
- Confirmed evidence only; obeys the Bumbling-to-Boardroom principles for any scripted phrasing.
- Company-agnostic: no Dematic/company-specific wording in shared output.

## Test and Acceptance Plan

1. Render a guide and confirm the operating-system section shows the Consultative Stance block, the reframed anti-hedge rule, and the grounding block, with the two halves roughly balanced.
2. Confirm the grounding block, which contains example hedge phrases, does NOT trip `validate_delivery_principles` (the validator still runs only on answer strings).
3. Confirm no new scripted claims are introduced and no company-specific wording leaks into a non-Dematic guide.
4. Regression: `python tasks.py validate` and `python scripts/smoke_test.py` pass; State Farm / Big Four guides still build.

## Assumptions

- Phases 1-4 are merged and the gate above is cleared before Phase 5 starts.
- The Evidence Log and Daily Practice personal docs remain the source-of-truth shape; the guide reinforces them rather than replacing them.
- This is content and reader-guidance work, not a new engine or command.
