# Codex Spec: Finish Phase 1 (naturalize answers) + Phase 2 (scorecard)

Continuation of `CODEX_SPEC_interview_career_system.md` (the master). Phase 1 built the
self-inventory, validation, one-pager, and the two answer builders. Christian accepts the
strengths/weaknesses CONTENT as-is for now. Two things remain: naturalize the answer phrasing
(Phase 1 finish), then build the per-JD scorecard (Phase 2). Keep the phased discipline: build
Phase 1-finish, verify, then Phase 2, then stop for review before Phase 3.

Guardrails unchanged: truthful only; weakness answers speak only interview_safe + improvement and
never honest_name; the honest_name string must never appear in any generated text; no fabricated
credentials (no Six Sigma belt, TOGAF, deep RAG/vector, or hardware ownership).

---

## Part A: Phase 1 finish - naturalize the answers (the only content fix)
The current answers read internal field labels out loud, which sounds like a mail-merge. Fix the
two insertion points so they sound spoken.

1. Strengths answer. Today it emits "The proof point I would anchor to is {story_tag}." Instead,
   weave a natural example clause using a spoken reference to the story, not its tag.
   - Add a `spoken_reference` field to each signature story in `source/self_inventory.json`: a
     short, natural "for example" clause. Seed:
     - Windows-95 discovery: "for example, at a client still running Windows-95-era systems, I led
       the discovery that surfaced the integration risks before they hit production"
     - East West fast ramp: "for example, I was dropped into a platform I had never used at East
       West and got up to speed fast enough to train the global teams on it"
     - EFT/ACH cross-functional replacement: "for example, a five-month EFT/ACH payment
       replacement where I aligned internal IT, global finance, the vendor, and the bank on one
       plan"
   - The strengths builder uses `spoken_reference` in place of "The proof point I would anchor to
     is {tag}."

2. Weaknesses answer. Today it emits "The active improvement is {improvement_action}." Instead,
   weave a natural ongoing-action clause, e.g. "so I've been {improvement}." Either phrase each
   `improvement_action` as a natural clause, or add an `improvement_spoken` field and use it.
   Seed spoken forms:
   - "so I've been drilling answer-first delivery: the headline, one example, the result, then I
     stop"
   - "so I now keep a running record of my outcomes to own my impact accurately without
     overstating it"
   - "so I'm actively working the certifications to catch the credentials up to the hands-on
     experience"

3. Do not otherwise change the strengths/weaknesses content; Christian approved it as-is.
4. Verify: rebuild the one-pager and regenerate both answers; confirm no field-label phrasing
   ("The proof point I would anchor to is", "The active improvement is") remains, no honest_name
   appears, and the answers still lead BLUF. Run the FULL `python scripts/smoke_test.py` and
   `python tasks.py validate` once with a longer window (the suite is heavy and timed out at 6
   min last run; confirm it passes, not just that targeted tests pass), plus `source-lint`.

---

## Part B: Phase 2 - per-JD interview scorecard (master Module 2)
Build per master spec Module 2 and the combined plan's Phase 2:
- Add `COMPETENCY_TAXONOMY` and `COMPETENCY_FRAMEWORKS` to `scripts/interview_intelligence.py`.
- `jd_competency_scorecard(job_description, resume_text, federal=False)` returns 4-8 entries:
  competency, triggering JD phrases, framework words to say, mapped signature story, support
  level, and an honest gap-pivot when support is weak. Reuse `resume_analysis.audit_keywords()`
  and the federal competency parser; do not build a parallel extractor.
- `map_stories_to_scorecard()` maps each competency to a signature story or flags a gap.
- `build_gap_pivot()` produces admit -> bridge (default East West fast ramp) -> smart question,
  never claiming an absent credential.
- Render the one-page scorecard into `build_interview_cheat_sheet.py`: a compact table of
  competency | words to say | best story or gap-pivot. Do not touch the detailed guide, daily
  prep, career plan, or debrief loop yet (those are Phases 3-6).

### Phase 2 tests
- Sample Solutions Consultant JD returns 4-8 competencies including discovery and stakeholder
  alignment; a process-improvement JD surfaces DMAIC / Lean Six Sigma language.
- Every competency maps to a supported story or an honest pivot; the 5 signature stories stay
  available and evidence-backed.
- Safety: no unsupported credential phrase appears; no honest_name appears.
- Gates: `python scripts/smoke_test.py`, `python tasks.py validate`, `python tasks.py source-lint`,
  `python tasks.py commands`.

---

## Stop point and next phases
After Phase 2, deliver: the naturalized one-pager and two answers, and a scorecard-enhanced cheat
sheet built against one sample Solutions Consultant JD (planning/test run only, not a batch).
Stop for Christian's review before Phase 3.

Phases 3-6 follow per the master spec, one phase per pass with a checkpoint each: Phase 3 detailed
guide with BLUF answers; Phase 4 daily prep plan (two modes) + progress log; Phase 5 career
operating plan linking gaps to the Study/ tracks; Phase 6 debrief feedback loop. Do not batch
them.

## Guardrails
- One focused commit per phase. Reuse existing generators/extraction. Word-only outputs to
  `output/`; no PDFs. Do not stage generated outputs, scratch logs, active jobs/ files, or spec
  docs.
