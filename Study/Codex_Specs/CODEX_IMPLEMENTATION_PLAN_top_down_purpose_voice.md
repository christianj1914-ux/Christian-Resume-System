# Purpose-Driven Resume System Implementation Plan
## Summary
Implement in order: resume, cover, interview, then one shared warn-only buried-lede check. Before each implementation slice, refresh the relevant Claude packet and prompt, use Claude's review-and-plan output as the final checkpoint, then apply only the scoped changes. For each slice's review, attach the exact functions being changed to the Claude context and regenerate stale packet artifacts first, since packets are review artifacts, not source truth. Function-level detail per slice lives in `CODEX_SPEC_top_down_voice_resume.md`, `CODEX_SPEC_top_down_voice_cover.md`, and `CODEX_SPEC_top_down_voice_interview.md`.
## Key Changes
- Resume: keep Professional Summary at the live `45-70` word contract, add lane-sharpened purpose language through existing summary builders, and add conservative result-first bullet reordering only when an existing supported outcome is already present. For the review pass, attach `strengthen_outcome_framing()` and `apply_outcome_framing_rewrites()` because the current `resume` packet omits them.
- Cover: build only after a matching clean resume exists; adjust deterministic opening priority so BLUF/purpose openings are preferred for core lanes; keep proof result-first; remove artificial spaced-hyphen separators in `_pyramid_opening()`.
- Interview: edit shared `pitch_variants()` first so pitch wrappers stay aligned; make behavioral and detailed-guide story answers lead with the point and surface the human/purpose line earlier.
- Shared check: add one warn-only buried-lede rule in `writing_eval.py` / `utils.py`; keep it narrow and non-blocking.
## Public Interfaces
- No new user-facing commands required.
- No summary length contract change.
- No output format change: Word-only documents, two-page commercial resume, existing packet modes preserved.
- Any added warning must remain advisory and must not block document generation.
## Test Plan
- After each slice: run `python scripts/smoke_test.py`.
- After resume changes: run `python tasks.py validate`, build the resume, render/check it, and confirm exactly two pages.
- After cover changes: build the matching resume first, then build the cover and run existing cover QC.
- After interview changes: build the cheat sheet and detailed guide; manually verify answer-first structure and source-supported stories.
- For buried-lede: add smoke coverage proving it warns without failing builds.
## Assumptions
- Live validators override stale spec text.
- Claude packets and prompts are generated review artifacts, not source truth.
- Implementation pauses after each packet/prompt review until the matching Claude plan pass is available.
