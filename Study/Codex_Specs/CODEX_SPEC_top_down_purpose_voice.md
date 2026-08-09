# CODEX_SPEC: Top-Down and Higher-Purpose Voice Across the System

## Intent (bottom line up front)
Apply Christian's natural communication mode consistently across every generated document: **answer first, bottom line up front (BLUF / top-down)**, with a **higher-purpose "why" thread** ("turn ambiguous, cross-functional problems into structured delivery that people actually adopt; help teams adopt and understand technology safely"). This is a reinforcement pass, not a rebuild. Much of it already exists; the goal is consistency and a shared guardrail.

## Corrections applied from live-code grounding (read first)
- Professional Summary contract is **45 to 70 words** (`language_rules.PROFESSIONAL_SUMMARY_MIN_WORDS`/`MAX_WORDS`), not 75 to 140. The live validator wins over any spec text.
- Cover opening selection (`_select_opening_pattern()`) is **deterministic ordered rules**, not a weight table; implement item 3 as ordered-priority and lane-mapping changes.
- Interview pitch functions are wrappers over the shared `pitch_variants()`; make item 4 changes in the shared builder first.
- The `resume` Claude packet does not currently include the bullet-ordering functions; regenerate the stale packets and attach the relevant snippets and these specs to each review pass.
- The three per-output slices live in `CODEX_SPEC_top_down_voice_resume.md`, `_cover.md`, and `_interview.md`. Implement them one at a time; do item 5 (shared warn check) LAST, after all three are stable.

## What already implements this (do NOT duplicate or rebuild)
- `scripts/resume_content.py`: `build_problem_first_summary()` (summary is already problem-first); `strengthen_outcome_framing()` / `apply_outcome_framing_rewrites()` (duty-only -> outcome wording).
- `scripts/build_cover_letter.py`: `_pyramid_opening()` (BLUF), `_mission_opening()` (purpose), `enforce_result_first_ordering()`, `smooth_cover_letter_text()`.
- `scripts/build_interview_cheat_sheet.py` / `build_detailed_interview_guide.py`: `pyramid_answer()`, `caar_answer()`, the pitch ladder.
- `scripts/config/language_rules.py`: `DUTY_ONLY_OPENERS` detection.
- Daily practice doc already teaches "meat-first (answer in sentence one)."

## Targeted enhancements (severity-ranked)

### 1. (High) Verify result-first ordering on resume bullets, not just outcome wording
- Inspect: `resume_content.strengthen_outcome_framing()`, `apply_outcome_framing_rewrites()`.
- Change: ensure bullets lead with the result or the stakes, then the action, mirroring the cover letter's `enforce_result_first_ordering()`. Reorder existing supported clauses only.
- Guardrail: never invent or move metrics; only reorder supported content; keep `DUTY_ONLY_OPENERS` passing.
- Validate: `scripts/smoke_test.py`; confirm two-page fit and language rules still pass.

### 2. (High) Thread the purpose line through the Professional Summary, sharpened per lane
- Inspect: `resume_content.summary_positioning_sentence()`, `summary_job_poster_sentence()`, `build_problem_first_summary()`.
- Change: ensure the capability-plus-purpose positioning ("structured delivery that actually gets adopted, at the intersection of business, operations, and technology") is present and lane-sharpened.
- Guardrail: keep the summary within the live contract `PROFESSIONAL_SUMMARY_MIN_WORDS`..`PROFESSIONAL_SUMMARY_MAX_WORDS` (currently 45 to 70 words) in `scripts/config/language_rules.py`. Do NOT use the stale 75-to-140 figure. No first-person pronouns; no double-dashes; no unsupported claims; no ERP overreach for non-ERP roles.
- Validate: `assert_professional_summary_length()`; `smoke_test.py`.

### 3. (Medium) Raise BLUF and purpose priority in the ordered cover-letter opening selection
- Inspect: `build_cover_letter._select_opening_pattern()` and the opening variants.
- Change: `_select_opening_pattern()` is deterministic ordered rules, NOT a weight table. Raise the ordered priority and adjust the lane-to-opening mappings so `_pyramid_opening()` and `_mission_opening()` are preferred for his primary lanes, preserving variety. Do not introduce randomness or a weight table. Also fix the spaced-hyphen separators in `_pyramid_opening()`.
- Guardrail: keep `validate_cover_letter_specificity()` and `validate_cover_letter_text()`; no invented company values.
- Validate: `writing_eval.py` cover checks; `smoke_test.py`.

### 4. (Medium) Make interview answers lead with the point, and surface the purpose early
- Inspect: the shared `pitch_variants()` builder FIRST, then its wrappers `sixty_second_pitch()`, `ninety_second_pitch()`, `behavioral_answer_scripts()`, and guide `story_sample_answer()`.
- Change: make edits in the shared `pitch_variants()` builder first (the public pitch functions are thin wrappers); adjust `behavioral_answer_scripts()` and the detailed-guide story answers only where drift remains. Ensure the result or insight leads, then support; move the human/purpose line earlier (COMMON_CHANGE_AREAS flags "human-element language landing too late").
- Guardrail: source-supported stories only; keep shared cover/interview pitch logic in sync.
- Validate: `utils.enforce_prose_quality()` warn checks.

### 5. (Medium) Add ONE shared, warn-only "buried lede" check  (do this LAST, after slices 1 to 3 are stable)
- Inspect: `scripts/writing_eval.py` (`ARTIFACT_CHOICES`, `evaluate_text()`), `scripts/utils.py` (`enforce_prose_quality()`).
- Change: add a warn-only rule that flags an opening sentence which delays the result or key point (for example, a long lead clause before any outcome). Apply across artifact families so the voice rule lives in the shared layer, not one output.
- Guardrail: warn-only, never a blocker; keep the regex narrow so normal prose is not flagged.
- Validate: `smoke_test.py`; run on recent outputs and confirm low false positives.

### 6. (Low) Career Operating Manual and advisory docs open BLUF
- Inspect: `build_general_advice.py` section builders; `build_linkedin_update.py`; `build_thank_you.py`.
- Change: open each section with the point, then support; thread the purpose statement once near the top. Low risk (advisory or short docs).
- Validate: `smoke_test.py`.

## Guardrails that must hold (from the repo rules)
- Source truth only. Never claim unsupported requirements, invent metrics, or invent company values.
- No first-person pronouns in the resume; no double-dashes; no banned AI-writing words.
- Preserve two-page fit, Carlito font, Core Competencies formatting, and the KPMG visual rhythm.
- Keep each change in the module that owns the function (see `.context/SCRIPT_INDEX.md`).
- After any config or script change, run `scripts/smoke_test.py`; then a full resume + cover + interview build with a render check.

## Canonical execution checklist (authoritative)
This is the agreed order of operations, grounded against live code. It supersedes any looser ordering elsewhere in this file. Implementation for a slice does not begin until that slice's Claude review-and-plan pass is complete.

1. **Resume slice, review.** Regenerate the stale packet: `python tasks.py claude-packet --mode resume`, then `python tasks.py claude-prompt review --packet-mode resume`. Attach the slice-1 spec and the missing bullet-ordering snippets (`strengthen_outcome_framing()`, `apply_outcome_framing_rewrites()`) to the review context. Get the plan pass before editing.
2. **Resume slice, implement.** Add the purpose thread inside the existing summary builders, preserving **45 to 70 words**, source truth, no first person, no double-dashes, no ERP overreach, and two-page fit. Then apply conservative result-first bullet reordering only where a supported result already exists.
3. **Cover slice.** Build only after a clean matching resume exists. Regenerate the cover packet, review with Claude, then adjust the ordered opening priority and proof ordering (no weight table, no invented company values), and fix the spaced-hyphen separators in `_pyramid_opening()`.
4. **Interview slice.** Regenerate the interview packet, review with Claude, then make pitch and behavioral-answer changes through the shared `pitch_variants()` and story logic so cover and interview positioning stay aligned.
5. **Shared warning check (last).** Only after slices 1 to 3 are stable, add the buried-lede check once in `writing_eval.py` / `utils.py` as warn-only, with narrow matching and low false-positive expectations. Advisory docs (item 6) can follow at any point after.

## Test plan
- After each implementation slice: `python scripts/smoke_test.py`.
- After resume edits: `python tasks.py validate`, build the resume, render-check it, and confirm exactly two pages.
- After cover edits: build the matching resume first, then build the cover letter and run cover QC.
- After interview edits: build the cheat sheet and detailed guide, then manually check that pitches and stories lead with the point and stay source-supported.
- For the shared buried-lede warning: add smoke coverage proving it warns without blocking builds.

## Assumptions (hold these)
- The live validator wins over spec text wherever they conflict.
- Claude review packets are generated artifacts to refresh, not source truth.
- No implementation starts until the matching Claude review-and-plan pass is complete for that slice.

## Validation checklist
- `smoke_test.py` passes (lane detection, language rules, summary length).
- One full build: resume + cover + interview; render check clean; resume stays two pages.
- Manual read: does each document answer-first and carry the purpose thread, with no new unsupported claims?

## Note for Claude review pass
Before implementing, generate the matching packet and review prompt per the repo workflow:
`python tasks.py claude-packet --mode resume` (and `--mode cover`, `--mode interview`), then
`python tasks.py claude-prompt review --packet-mode resume`. Feed findings back for a plan pass before Codex applies edits.
