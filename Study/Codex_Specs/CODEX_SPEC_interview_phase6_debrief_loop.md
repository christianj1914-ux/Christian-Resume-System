# Codex Spec: Phase 6 - Debrief Feedback Loop (final phase) + capitalization cleanup

Final continuation of `CODEX_SPEC_interview_career_system.md` (master, Module 6). Phases 1-5 are
done and approved. This pass adds a one-line prose cleanup, then builds the debrief feedback loop
that closes the system so each interview updates the self-inventory and re-aims the next day's
practice. Build, verify, then run a full-system end-to-end check.

Guardrails unchanged: truthful only; honest_name never spoken or printed; no fabricated
credentials; full smoke/validate must PASS on a long window (15+ min) or be reported as a blocker.
Critical new guardrail below: the debrief must NEVER auto-harden Christian's certified
self-inventory; it writes to a review queue only.

---

## Part A: capitalization cleanup
Woven examples currently render lowercase after a period: "...following through in writing. for
example, when a client's CEO...". When a spoken_reference lands at the start of a sentence (after
the answer's period), capitalize its first letter so it reads "For example, when a client's
CEO...". Do not change spoken_references that are woven mid-sentence. Add a test that no BLUF
answer contains ". for example" (lowercase after a period). Re-render the sample guide.

---

## Part B: Phase 6 - debrief feedback loop
Extend `scripts/post_interview_debrief.py` (and `interview_intelligence.py`) so a completed
interview debrief feeds the system.

Debrief capture (structured, from Christian's notes): role/JD, competencies probed, a quick
self-rating per answer (landed / rambled / missed), hedge observations, any new story that
surfaced, and any development area that showed up as a real gap.

Two feedback outputs, both advisory and review-gated:
1. `scratch/prep_focus.json`: which rep types / competencies to emphasize next (e.g. delivery
   rambled -> weight the delivery drill; a competency had no ready story -> flag it). Extend
   `build_daily_prep_plan(mode, ...)` to read `prep_focus.json` when present and bias the
   rotation toward the flagged areas. It stays advisory; absent file = current behavior.
2. `scratch/inventory_candidates.json`: a REVIEW QUEUE of proposed self-inventory updates, new
   story candidates, added evidence for a strength, a weakness whose status should change. These
   are proposals Christian reviews and promotes manually.

HARD guardrail: the debrief must NOT write to `source/self_inventory.json`. That file is
Christian's certified self-model; only he promotes candidates into it. The loop proposes; he
disposes. Never fabricate a story or claim from a debrief.

Surface it: keep/extend the existing debrief Word output (what went well, what to fix, next-day
focus). Ensure any `debrief` / post-interview command is registered and truthful in
`tasks.py commands`.

### Phase 6 tests
- A sample debrief writes `prep_focus.json` and `inventory_candidates.json` under scratch/, and
  writes nothing to `source/self_inventory.json`.
- With a `prep_focus.json` present, `build_daily_prep_plan()` biases the rotation toward the
  flagged rep type; without it, behavior is unchanged.
- Candidate stories/evidence land in the review queue, never auto-merged into the certified
  inventory.
- Safety: no honest_name, no unsupported credential phrase in any debrief output.
- Existing debrief behavior preserved.

---

## Full-system end-to-end check (this is the last phase)
After Phase 6, run one cohesive pass for a single sample Solutions Consultant JD and confirm the
whole system works together:
- self-inventory one-pager, scorecard-enhanced cheat sheet, detailed guide (all examples inline,
  correct capitalization), both daily prep plans, career operating plan, and a sample debrief
  cycle that produces prep_focus + inventory_candidates and re-weights the next daily plan.
- Gates: `python scripts/smoke_test.py`, `python tasks.py validate` (long window, must pass),
  `python tasks.py source-lint`, `python tasks.py commands`.

## Stop point
Deliver: the re-rendered guide (capitalization fixed), a sample debrief output, the resulting
prep_focus.json / inventory_candidates.json, and a daily plan showing the re-weighting. This
completes the interview & career operating system; report it as the final phase.

## Guardrails
- One focused commit per part (capitalization, then debrief loop). Reuse existing generators.
  Word-only outputs to `output/`; scratch state under `scratch/`. The debrief never writes the
  certified self-inventory. Do not stage generated outputs, scratch state, active jobs/ files, or
  spec docs.
