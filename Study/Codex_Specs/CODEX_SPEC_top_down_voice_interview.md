# CODEX_SPEC: Top-Down and Purpose Voice — Interview Outputs (slice 3 of 3)

## Intent (bottom line up front)
Make interview answers and pitches **lead with the result or key insight**, and **surface the human/purpose line early** rather than late. Keep the shared cover-and-interview pitch logic in sync. Reinforcement only; source-supported content only.

## Already implemented (do NOT duplicate)
- `scripts/build_interview_cheat_sheet.py`: `pyramid_answer()`, `caar_answer()`, `sixty_second_pitch()`, `ninety_second_pitch()`, `pitch_for_profile()`, `behavioral_answer_scripts()`, `interview_pitch_parts()`, `pitch_variants()`.
- `scripts/build_detailed_interview_guide.py`: `story_sample_answer()`, `behavioral_sample_answers()`, `build_extended_tmay_sections()`.

## Changes

### I1. (Medium) Lead the pitch ladder with the point; purpose early
- Inspect: `pitch_variants()` (the shared builder), then its wrappers `sixty_second_pitch()`, `ninety_second_pitch()`, `pitch_for_profile()`, `interview_pitch_parts()`.
- Change: make the edit in the **shared builder `pitch_variants()` first**, since the public pitch functions are thin wrappers over it; only adjust the wrappers if tests expose drift. Ensure the result or capability leads the pitch, and the purpose line ("structured delivery that gets adopted; help teams use technology well") appears in the first third, not the tail.
- Guardrail: keep shared cover/interview pitch logic in sync (`pitch_variants()`, `human_motivation_sentence()`); make no claim stronger than the resume supports.
- Validate: `utils.enforce_prose_quality()` warn checks; `scripts/smoke_test.py`.

### I2. (Medium) Result-first behavioral answers with the human line earlier
- Inspect: `behavioral_answer_scripts()`, `story_sample_answer()`, `story_human_connection_line()`, `add_extended_tmay_section()`.
- Change: order answers result-first (the pyramid/CAAR frame already supports this), and move the human/purpose connection earlier so long answers do not feel canned (COMMON_CHANGE_AREAS: "human-element language landing too late").
- Guardrail: stories must be source-supported (`supported_story_bank()`, `hero_stories()`); do not invent motivation or culture-fit language beyond notes or supported patterns.
- Validate: `story_quality_audit()`; warn-only prose checks; `scripts/smoke_test.py`.

## Guardrails that must hold
Source truth only; interview prep must not claim more than the resume; keep cover and interview pitch logic aligned; warn-only prose checks stay warn-only (not blockers); no invented company values. Keep edits in the interview builders per `.context/SCRIPT_INDEX.md`.

## Order and validation
Do I1, then I2. After each: run `scripts/smoke_test.py`, build the cheat sheet and detailed guide, and read for answer-first structure with the purpose line landing early and every story source-supported.

## Claude review workflow (before Codex applies)
`python tasks.py claude-packet --mode interview` then `python tasks.py claude-prompt review --packet-mode interview`; feed findings back for a plan pass. Shared "buried lede" warn check: see `CODEX_SPEC_top_down_purpose_voice.md` item 5 (implement once, in the shared layer, `writing_eval.py` / `utils.py`).
