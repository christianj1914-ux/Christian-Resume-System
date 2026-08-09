# Codex Next Work: Deferred Follow-Up

The reliability, federal parsing, alignment, archive, output-cleanup, story-engine, and federal-isolation work is complete. The latest full validation passed **493/493** on August 8, 2026. Output cleanup removed 60 legacy PDFs and reduced `output/` from 523 to 431 entries; the 475-record job-description archive has zero empty lanes.

## Deferred: search-term semantics

`contains_search_term` remains intentionally duplicated. The two implementations differ in opposite plural directions, so consolidation can change alignment scores, gap suppression, bullet selection, and competency selection. Take it as a dedicated change: choose its intended semantics, run `keyword_reliability_corpus.py` before and after, and review score and output diffs before merging.

## Deferred: federal program-delivery defaults

`program_delivery` remains absent from `FEDERAL_DEFAULT_CLUSTERS_BY_LANE`. The active federal fixture relies on the current fallback tie-break; any lane-map change requires a before/after cluster comparison and deliberate fixture re-pinning.

## Follow-Up: validation performance

Do not change validation behavior as part of this completed reliability batch. Profile the full suite separately using the per-check elapsed output. The latest run identified the orphan-function scan, Claude packet self-audits, and Claude bundle refresh as the largest visible contributors. Establish a clean local baseline before optimizing, then preserve the focused selector behavior and the 475-or-higher full-suite gate.

## Verified Stable

- Federal workflow steps now share the ten-minute timeout, process-group termination, output quarantine, and return-code-124 behavior with the commercial workflow.
- The active federal fixture remains pinned at 12 specialized duties, 4 minimum and 14 assessed competencies, and the reviewed cluster weights and keyword tail.
- The 45-to-70-word summary range is the resolved product contract.
- The neutral interview story engine is the sole implementation of shared story selection and spoken-answer logic; the cheat-sheet module retains compatibility re-exports only.
- `build_federal_resume` imports neither `build_interview_cheat_sheet` nor `build_cover_letter` in a clean interpreter.
- The smoke suite now enforces pyflakes undefined-name and redefinition diagnostics alongside its existing runtime checks.
