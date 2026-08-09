# CODEX_SPEC: Top-Down and Purpose Voice — Resume (slice 1 of 3)

## Intent (bottom line up front)
Make the tailored resume answer-first and carry Christian's purpose thread: **lead each bullet with the result or the stakes**, and **thread the capability-plus-purpose positioning** ("turn ambiguous, cross-functional problems into structured delivery that people actually adopt") through the Professional Summary, sharpened per lane. Reinforcement only; do not rebuild.

## Already implemented (do NOT duplicate)
- `scripts/resume_content.py`: `build_problem_first_summary()`, `strengthen_outcome_framing()`, `apply_outcome_framing_rewrites()`.
- `scripts/config/language_rules.py`: `DUTY_ONLY_OPENERS`.

## Changes

### R1. (High) Purpose thread in the Professional Summary, lane-sharpened
- Inspect: `resume_content.summary_positioning_sentence()`, `summary_job_poster_sentence()`, `build_problem_first_summary()`, `rewrite_professional_summary_for_role()`.
- Change: ensure the capability-plus-purpose line is present and sharpened to the detected lane; keep it the first idea, not buried behind stacked clauses.
- Guardrail: keep the summary within the live contract `PROFESSIONAL_SUMMARY_MIN_WORDS`..`PROFESSIONAL_SUMMARY_MAX_WORDS` (currently **45 to 70 words**) in `scripts/config/language_rules.py`. Do NOT use the stale 75-to-140 figure from an earlier note; do not change the 45-to-70 range unless that is a deliberate, separate formatting decision. Also: no first-person pronouns; no double-dashes; no unsupported claims; no ERP overreach for non-ERP roles (`scrub_erp_language_for_non_erp_text()`, `rebalance_professional_summary_erp_mentions()`).
- Validate: `build_resume.assert_professional_summary_length()`, `assert_resume_language_rules()`; `scripts/smoke_test.py`.

### R2. (High) Verify result-first ordering on bullets, not just outcome wording
- Inspect: `resume_content.strengthen_outcome_framing()`, `apply_outcome_framing_rewrites()`; compare against `build_cover_letter.enforce_result_first_ordering()` for the pattern.
- Change: where a bullet already contains a supported outcome, order it so the result or stakes lead, then the action. Reorder existing supported clauses only.
- Guardrail: never invent, add, or move metrics onto unsupported bullets; keep `DUTY_ONLY_OPENERS` and all language rules passing; do not change factual meaning.
- Validate: `scripts/smoke_test.py`; confirm two-page fit is unaffected (`role_bullet_budget()`, `select_experience_bullets_for_two_page_resume()`, `pack_docx_with_page_fit()`, `apply_fit_font_sizing()`).

## Guardrails that must hold
Source truth only; no invented metrics or company values; no first-person pronouns; no double-dashes; no banned AI-writing words; preserve two pages, Carlito, and Core Competencies formatting. Keep edits in `resume_content.py` / `resume_analysis.py` per `.context/SCRIPT_INDEX.md`.

## Order and validation
Do R1, then R2. After each: run `scripts/smoke_test.py`, then a full resume build with a render check; confirm the resume stays two pages and reads answer-first with the purpose thread intact and no new claims.

## Claude review workflow (before Codex applies)
`python tasks.py claude-packet --mode resume` then `python tasks.py claude-prompt review --packet-mode resume`; feed findings back for a plan pass.

Packet-coverage caveats (verified against live code):
- The current `resume` packet does NOT include the bullet-ordering functions this slice touches. Manually add `resume_content.strengthen_outcome_framing()` and `apply_outcome_framing_rewrites()` (and this spec) to the review context, or the review pass will be under-informed on R2.
- Packet and manifest artifacts under `Claude Review/` are generated and stale (last built July 11); regenerate them before the review pass. They are validation artifacts, not source truth.
- The new root spec files are not auto-included in the packet; attach this spec to the review explicitly.

Shared cross-output "buried lede" warn check is out of scope here; see `CODEX_SPEC_top_down_purpose_voice.md` item 5 (implement once, in the shared layer, AFTER all three slices are stable).
