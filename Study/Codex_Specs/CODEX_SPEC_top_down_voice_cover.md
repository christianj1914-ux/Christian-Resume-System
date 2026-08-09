# CODEX_SPEC: Top-Down and Purpose Voice — Cover Letter (slice 2 of 3)

## Intent (bottom line up front)
Bias the cover letter to **open with the point (BLUF) or the mission (purpose)** and to **order proof result-first**, for Christian's primary lanes, while preserving opening variety. Reinforcement only. Build only after a matching resume exists.

## Already implemented (do NOT duplicate)
- `scripts/build_cover_letter.py`: `_pyramid_opening()` (BLUF), `_mission_opening()` (purpose), `enforce_result_first_ordering()`, `smooth_cover_letter_text()`, `selected_evidence_items_ordered()`.

## Changes

### C1. (Medium) Raise pyramid/mission priority in the ordered opening selection
- Inspect: `_select_opening_pattern()` and the opening variants (`_situation_opening()`, `_tension_opening()`, `_belief_opening()`, `_direct_opening()`, `_mission_opening()`, `_pyramid_opening()`).
- Change: NOTE the current selection is **deterministic ordered rules, not a weighted or random table**. Implement this as adjusting the ordered rule priority and the lane-to-opening mappings so `_pyramid_opening()` and `_mission_opening()` are preferred for Christian's core lanes, while keeping the other patterns reachable so openings do not become formulaic. Do not introduce randomness or a weight table.
- Guardrail: no invented company values or culture; keep `validate_cover_letter_specificity()` and `company_context_sentence()` grounded in visible JD/company signals only.
- Validate: `writing_eval.py` cover checks; `scripts/smoke_test.py`.

### C3. (Low, style) Fix spaced-hyphen separators in the pyramid opening
- Inspect: `_pyramid_opening()`.
- Change: it currently uses spaced hyphens as separators. Replace them with cleaner punctuation (comma or colon). This is separate from the double-dash rule, but the project is intentionally strict about artificial-looking punctuation, so include it in the implementation checklist.
- Validate: `validate_cover_letter_text()`; visual read of a generated letter.

### C2. (Medium) Confirm result-first proof and a purpose thread in the body
- Inspect: `selected_evidence_items()`, `selected_evidence_items_ordered()`, `proof_paragraph()`, `opening_method_paragraph()`, `closing_paragraph()`, `enforce_result_first_ordering()`.
- Change: ensure each proof point leads with the result or stakes, and that the capability-plus-purpose thread appears once near the top and again lightly at the close.
- Guardrail: cover must match the generated resume (`find_resume_output()`), make no claims beyond it, and never run before the resume exists (`resume_readiness_for_output()`); avoid brittle fallback clauses stitched from raw JD fragments.
- Validate: `validate_cover_letter_specificity()`, `assert_cover_letter_qc()`, `validate_cover_letter_shape()`, `validate_cover_letter_text()`, `write_cover_letter_trace()`; `scripts/smoke_test.py`.

## Guardrails that must hold
Source truth only; match the resume; no invented company values; no double-dashes or banned AI-writing words; keep the downstream gating (do not build sendable docs if the resume has role-defining blockers). Keep edits in `build_cover_letter.py` per `.context/SCRIPT_INDEX.md`.

## Order and validation
Do C1, then C2. After each: run `scripts/smoke_test.py`, generate a cover letter against a freshly built resume, and read for a BLUF or mission opening, result-first proof, and no unsupported or invented company claims.

## Claude review workflow (before Codex applies)
`python tasks.py claude-packet --mode cover` then `python tasks.py claude-prompt review --packet-mode cover`; feed findings back for a plan pass. Shared "buried lede" warn check: see `CODEX_SPEC_top_down_purpose_voice.md` item 5 (implement once, in the shared layer).
