# Codex Spec: Phase 3 - Detailed Interview Guide (+ scorecard refinements)

Continuation of `CODEX_SPEC_interview_career_system.md` (master, Module 3). Phase 1 (self-
inventory + naturalized answers) and Phase 2 (scorecard in the cheat sheet) are done and
approved. This pass folds in two scorecard refinements from review, then builds the detailed
guide with full BLUF answers. Build it, verify, stop for review before Phase 4.

Guardrails unchanged: truthful only; weakness text speaks only interview_safe + improvement,
never honest_name; the honest_name string must never appear in any generated text; no fabricated
credentials (no Six Sigma belt, TOGAF, deep RAG/vector, hardware ownership); gap-pivots are
admit -> bridge -> smart question only.

---

## Part A: scorecard refinements (in `scripts/interview_intelligence.py`)
The Phase 2 scorecard reused one story (Windows-95 discovery) for three competencies and left the
CEO escalation and fast-ramp stories unused. Fix both:

1. Distribute distinct stories. Update `map_stories_to_scorecard()` so each competency prefers
   the best-matching UNUSED signature story before reusing one. When there are 5+ competencies,
   all 5 signature stories should be used before any story repeats. Only reuse a story when no
   unused story genuinely fits that competency (fit still governed by real relevance; never force
   a story that does not fit, mark a gap-pivot instead). Cap any single story at 2 competencies
   unless unavoidable.

2. Add two competencies the taxonomy missed, both common in Solutions Consultant / discovery
   roles and each backed by a currently-unused story:
   - Customer relationship building. Triggers: relationships, stakeholders, trusted advisor,
     customer-facing, coach clients, manage expectations. Frameworks/words: trusted advisor,
     expectation management, written confirmation (FRD), executive cadence, escalation path.
     Default story: CEO escalation.
   - Adaptability / fast ramp. Triggers: fast-paced, ambiguity, learn quickly, new domains,
     wear many hats, ramp. Frameworks/words: learning agility, ramp-up, comfort with ambiguity,
     map-to-fundamentals, cross-training. Default story: East West fast ramp.
   Add both to `COMPETENCY_TAXONOMY` and `COMPETENCY_FRAMEWORKS`. They surface only when the JD
   triggers them (do not force them onto every JD).

---

## Part B: Phase 3 - detailed interview guide
Extend `scripts/build_detailed_interview_guide.py` to generate full BLUF answers, anchored to the
self-inventory and the refined scorecard.

- For EACH scorecard competency, a full answer in BLUF shape: Answer (one sentence) -> Example
  (the competency's mapped story, told with its spoken_reference) -> Result (number when the
  ledger/story has one) -> Relevance (one sentence tying to this JD). Weak competencies get the
  gap-pivot instead.
- Standard high-stakes prompts every time, all BLUF, anchored to the inventory:
  - why this role / why this company
  - walk me through your last role (lead with the skill/software category, do not make them ask)
  - build productive relationships (CEO escalation)
  - get alignment when perspectives differ (a second concrete story, not a method lecture)
  - your 3 greatest strengths (reuse the naturalized spoken strengths answer)
  - 3 development areas (reuse the naturalized spoken weaknesses answer; interview_safe only)
  - your biggest gap for this role (honest gap-pivot)
  - a role-specific 30/60/90 (learn -> lead portions -> run independently), phrased "here's my
    plan, does that match?"
  - 2-3 consultative questions to ask the interviewer
- Keep the guide Word-only into `output/`; render for the sample Solutions Consultant JD via the
  `_for_inputs` path so active `jobs/` files are not touched. Do not build daily prep, career
  plan, or the debrief loop (Phases 4-6).

---

## Test plan
- Story distribution: for the sample JD (>=5 competencies), the scorecard/guide uses at least 5
  distinct signature stories and no story maps to more than 2 competencies unless the count of
  competencies forces it; CEO escalation and fast-ramp are used, not just Windows-95.
- New competencies: a JD emphasizing relationships and fast-paced/ambiguous work surfaces
  Customer relationship building (mapped to CEO escalation) and Adaptability (mapped to
  fast ramp); a JD without those triggers does not surface them.
- BLUF answers: every generated answer starts with a direct answer sentence, includes an example
  and (where supported) a result, and ends with a relevance sentence.
- Standard prompts: all listed prompts render; strengths/weaknesses reuse the naturalized spoken
  answers; the biggest-gap answer is an honest pivot.
- Safety: no honest_name anywhere; no unsupported credential phrase; gap-pivots never claim an
  absent credential.
- Gates: `python scripts/smoke_test.py` and `python tasks.py validate` (long window, at least
  15 min; must PASS, not time out - if it times out, report as an unresolved blocker, do not call
  it passed), plus `python tasks.py source-lint` and `python tasks.py commands`.

## Stop point
After Phase 3 deliver, for the sample Solutions Consultant JD only: the detailed interview guide,
and confirmation the refined scorecard now spreads stories and includes relationship-building and
adaptability where triggered. Stop for Christian's review before Phase 4 (daily prep + progress
log). Phases 4-6 follow per the master spec, one pass each with a checkpoint.

## Guardrails
- One focused commit (or two: scorecard refinements, then detailed guide). Reuse existing
  generators/extraction. Word-only outputs to `output/`; no PDFs. Do not stage generated outputs,
  scratch logs, active jobs/ files, or spec docs.
