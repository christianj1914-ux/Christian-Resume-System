# Codex Implementation Spec: Phase 4 - Prep-Output Patterns and Debrief-to-Prep Overlay
## July 14, 2026 - Fold the reusable structures from the Dematic prep documents into the shared stage-aware guide system, and turn structured debriefs into next-round guidance

## Summary

The Dematic prep documents Claude produced (recruiter-screen prep, team-round prep addendum, 90-day one-pager, hero-story pack, TMAY ladder) proved out several reusable structures. Phase 4 folds the strongest of them into the shared, stage-aware interview-prep system so every future guide benefits, with all company-specific wording sourced from scoped debrief and company notes rather than hardcoded. Phase 4 also adds a debrief-to-prep overlay so recent interview misses become structured next-round content instead of manual notes.

Phase 4 depends on Phase 1 (scripted-answer model), Phase 2 (stage system), and Phase 3 (shared answer-shaping and the de-duped answer engine). Do not start until those are merged. Planning artifact only; Codex implements.

## Non-negotiable guardrails (carried from Phase 3)

- No company-specific term (Dematic, KION, Jennifer, Dematic iQ, AutoStore, conveyor, PLC) may appear in shared generator output for a different company. Such specifics come only from that job's scoped company research or debrief notes.
- Barcode exposure stays narrow; least-privilege stays scoped; salary stays flexible with no hardcoded range.
- Every scripted answer obeys the Bumbling-to-Boardroom principles and passes `validate_delivery_principles`.
- Reuse the existing stage logic and shared answer engine; do NOT add new document types or new CLI surface. The Dematic standalone docs are design prototypes, not new mandatory deliverables.

## Implementation Changes

### A. Debrief-to-prep overlay (the highest-value, highest-risk item)

Add an internal overlay helper that reads the latest structured round record for the active company (via the existing debrief pipeline, no schema change) and normalizes it into reusable, company-scoped next-round guidance:
- top delivery risks (for example BLUF risk, technical-boundary clarity, 90-day readiness, story quality, question quality)
- "fix this next time" cards
- recent interviewer language to echo back
- recent unexpected questions to rehearse
- company-scoped product or role terms that are safe to repeat

Consume the overlay from both the cheat sheet and the detailed guide; do not duplicate it. Empty-state is mandatory: with no debrief present, render nothing (no empty fix-cards, no dangling feedback headers). Keep the debrief schema unchanged; the current raw-notes, unexpected-questions, role-language, feedback-received, company-intelligence, and story-followup fields are sufficient.

### B. HR-screen stage upgrades (in the `hr_screen` stage from Phase 2)

- Company snapshot block: what the company is, relevant product/platform names from scoped research, and the role in one line. Sourced from scoped company notes, never hardcoded.
- The TMAY time ladder rendered as a stage element (30-second anchor, 60 to 90 second expansion, 2-minute proof beat), reusing the Phase 1 ladder builder.
- SAY THIS / DIG DEEPER answer pairs for the likely recruiter questions.
- Comp and availability handling that stays generic by default and only becomes company-specific when a scoped debrief or company note supports it.
- A short recruiter-stage delivery checklist.

### C. Hiring-manager and team-round stage upgrades (in `hiring_manager`, flowing to `panel` and `final`)

- A First-90-Days glance block near the front, sourced from the SAME shared first-90-days answer built in Phase 3 so the short and long versions never drift.
- The software-boundary opener and the hardware-gap bridge (from Phase 3) surfaced in these stages for automation-style roles.
- A four-anchor-stories section (discovery risk, redirecting an unattainable ask, rapid ramp, cross-functional alignment) drawn from the confirmed story bank.
- A story-anchor table compressing each core story into story / anchor / result for rehearsal.
- A top-recurring-answer-risks section driven by the debrief overlay from section A.

### D. Cheat-sheet consolidation (optional, prioritized)

Prioritize the two items with confirmed gaps: the prepared first-90-days answer and the software-boundary opener. Treat the fuller compact-prep expansion (role focus, pre-call routine, pacing guide, anti-hedge reminders, likely questions, recent debrief questions, three-point spine, compact story cards, questions to ask, four-step close, thank-you template, red flags, self-scorecard) as optional and additive; do not let it duplicate the detailed guide or bloat the cheat sheet.

## Test Plan

- Stage renders: `python tasks.py guide --stage hr_screen` shows the company snapshot, TMAY ladder, SAY THIS / DIG DEEPER recruiter bank, and recruiter checklist; `python tasks.py guide --stage hiring_manager` shows the First-90-Days glance block, software-boundary opener, hardware-gap bridge when the role signals automation, and the anchor-story table; `python tasks.py guide` keeps shared core once with stage blocks under the right headers.
- Debrief overlay: with a structured debrief present, recent feedback and unexpected questions appear in the next guide; with no debrief present, nothing empty renders.
- Leakage: a non-Dematic job produces no Dematic / Jennifer / KION / AutoStore / Dematic iQ / conveyor / PLC wording unless those terms are in that job's scoped notes.
- Sync: the First-90-Days glance block and the full guide answer come from the same shared source.
- Full: `python tasks.py validate` and `python scripts/smoke_test.py`; rebuild one Dematic guide and one unrelated company guide to confirm the shared patterns help both without company-specific bleed.

## Assumptions

- Phases 1 to 3 are merged and green before Phase 4 starts.
- The debrief schema is sufficient as-is; the overlay is a read-and-normalize layer, not a schema change.
- The 90-day one-pager, recruiter-screen script shape, and team-round fix cards become reusable guide structures; company names, product names, recruiter names, and comp specifics remain scoped to company research and debrief context.
