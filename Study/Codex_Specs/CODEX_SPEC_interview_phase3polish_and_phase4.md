# Codex Spec: Phase 3 Prose Polish + Phase 4 Daily Prep

Continuation of `CODEX_SPEC_interview_career_system.md` (master). Phase 3 substance is approved
(scorecard BLUF bank, story distribution, relationship-building + adaptability competencies, all
tests green at 401/401). This pass fixes three prose-assembly bugs in the detailed guide, then
builds Phase 4 (the daily prep habit loop + progress log). Build, verify, stop for review before
Phase 5.

Guardrails unchanged: truthful only; weakness text speaks only interview_safe + improvement,
never honest_name; honest_name never appears in any generated text; no fabricated credentials;
gap-pivots admit -> bridge -> smart question only. Full smoke/validate must PASS on a long window
(15+ min), not time out; a timeout is reported as an unresolved blocker, never called passed.

---

## Part A: Phase 3 prose fixes (in the BLUF answer assembly)
1. Kill the doubled lead-in. Answers currently read "A concrete example is for example, at a
   client...". The spoken_reference already opens with "for example,". Fix ONE side only: either
   drop the "A concrete example is" prefix entirely (preferred, the spoken_reference flows on its
   own), or strip a leading "for example," from the reference when a prefix is added. Result must
   contain no "is for example" and no other doubled example/for-example phrasing.
2. Keep spoken_references intact as clean sentences. The adaptability answer currently splits into
   a subjectless fragment ("...at East West. Got up to speed fast enough to train..."). Do not
   split a spoken_reference into a sentence that loses its subject; keep it as authored (one
   sentence with "and got up to speed...") or re-attach a subject if a split step runs.
3. Consistent inline assembly for EVERY competency. Some answers (e.g. customer relationship
   building) put the example/result only in the bullet list and omit them from the spoken prose.
   Every BLUF prose answer must weave the example clause AND the result inline (Answer ->
   Example -> Result -> Relevance), so the paragraph reads straight through, including the two new
   competencies.

Phase 3 fix tests: no generated answer contains "is for example" or a doubled example phrase; no
spoken_reference renders as a subjectless sentence; every BLUF prose answer contains an example
clause and a result sentence (or is a flagged gap-pivot). Re-render the sample detailed guide.

---

## Part B: Phase 4 - daily prep habit loop (master Module 4)
Add a sustainable, non-linear practice system with two modes, reusing the existing daily-practice
material in `interview_prep/`.

- Add `build_daily_prep_plan(mode)` in `scripts/interview_intelligence.py`, mode in
  {"job_search", "on_the_job"}, returning a rotating rep set drawn from:
  - self-inventory rehearsal (say the 3 strengths + 3 development areas aloud, BLUF),
  - delivery drill (one BLUF rep; tally hedges: "just", "kind of", "broadly speaking", "it
    depended"),
  - story rep (one of the 5 signature stories; score lead-with-point + a number),
  - scorecard rep (build a scorecard from a live JD in ~5 minutes),
  - weakness rep (one concrete action on an active development area).
  Rotate the emphasis daily so it does not go stale (non-linear).
- Mode weighting: job_search weights delivery + scorecard + applications; on_the_job weights the
  Study/ learning path + logging new wins into the self-inventory + staying interview-ready.
- Progress log: append to `scratch/prep_log.csv` (gitignored) with columns date, mode, reps_done,
  hedge_count, self_rated_clarity. Advisory only; the point is a visible streak, never a gate.
- Add `scripts/build_daily_prep_plan.py` to render a Word-only plan into `output/`, and a
  `tasks.py` command `daily-prep` (accepts the mode).
- Do NOT build the career operating plan (Phase 5) or the debrief loop (Phase 6) in this pass.

### Phase 4 tests
- `build_daily_prep_plan("job_search")` and `("on_the_job")` each return a rotating set covering
  the five rep types, with mode-appropriate weighting that differs between modes.
- The plan references the real self-inventory strengths/weaknesses and signature stories.
- The progress log writes/appends the expected columns; it is under scratch/ and not staged.
- `daily-prep` command builds a Word plan into output/.
- Safety: no honest_name, no unsupported credential phrase in the plan text.

---

## Gates (both parts)
`python scripts/smoke_test.py` and `python tasks.py validate` (long window, must pass),
`python tasks.py source-lint`, `python tasks.py commands`.

## Stop point
Deliver: the re-rendered detailed guide (with the three prose fixes) and a sample daily prep plan
in both modes, plus the log format. Stop for Christian's review before Phase 5 (career operating
plan linking gaps to the Study/ tracks) and Phase 6 (debrief feedback loop), each a separate
checkpointed pass.

## Guardrails
- One focused commit per part (Phase 3 fixes, then Phase 4) if commits are requested. Reuse
  existing generators/extraction. Word-only outputs to `output/`; the log is csv in scratch/.
  Do not stage generated outputs, scratch logs, active jobs/ files, or spec docs.
