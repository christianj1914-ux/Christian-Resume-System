# Codex Next Work: Deferred Follow-Up

## Release B prerequisite baseline

The output-equivalence harness is frozen against Release A behavior SHA `a14fb43d58a8cc8f3817fd3ac7665fc913bb22f4`; its permanent planted-change certification is commit `210380f9eafeed18f5922cacdee9ab5d510a3203`. Two independent full captures produced 17/17 canonically identical fixtures with zero unexplained differences in 927.508 and 953.696 seconds using LibreOffice `7.6.5.2 38d5f62f85355c192ef5f1dd47c5c0c0c6d6598b` and Poppler `26.05.0`. The baseline covers all nine live commercial lanes, PASS/BRIDGE/FAIL/DRAFT states, federal standard/AI and grade paths, publication recovery, companion documents, readiness, archive refresh, tracker isolation, and the two-posting queue. No baseline archive posting triggered the canonical POOR detector, so POOR remains an explicit coverage gap.

Release B itself remains blocked. Release A has not yet completed the required real application cycle or one-week regression-free observation period, and no approval has been given for Phase B1 through B7.

### Equivalence recertification history

The first full comparison on August 12, 2026 reported `companion_bridge.processes` as unexplained with no visible-text difference. Report schema v1 retained only the difference hash, so the original nested value could not be recovered. The result did not reproduce in two independent Release A process captures or a fresh baseline-versus-candidate capture. Report schema v2 now retains canonical nested before/after evidence, and certification requires two consecutive full green comparisons at one candidate SHA.

The same run exposed a category error in queue comparison: `pipeline_fingerprint` hashes the complete Python tree, so it identifies the candidate rather than behavior and necessarily changes when harness Python changes. Queue fingerprints and derived completion keys are now validated for internal consistency before being projected out of cross-version comparison; posting identity, decisions, states, blockers, artifacts, output, and exit behavior remain authoritative.

On August 13, 2026, comparison run `bc70b23b4b3a490089846686d5cab125` tested candidate `6475add50a3024fa6c60ff6646f176171a46c7e2` and exposed two additional projection gaps. The three companion fixtures retained the raw cover-letter build date, and the system fixture retained the transient queue run directory inside its artifact and log paths. Schema-v2 preserved the complete nested evidence, proving that neither was a behavior change. Projection v3 normalizes both categories symmetrically. The report was persisted before the invocation reached its external 30-minute ceiling; later recertification commands receive 45 minutes externally without changing repository renderer, workflow, or retry limits. The frozen companion hashes change under v3; the frozen system hash correctly remains stable because that record already stores its queue paths as `<WORKSPACE>/...`.

Format normalization is inherently reactive because it recognizes volatile forms after they surface. A frozen clock in Release B's `RunContext` is the preferred long-term design because it eliminates wall-clock variation at generation time. That future work is not authorized by this repair.

The BRIDGE detailed-guide fixture records a 119-page render. That is captured Release A behavior, explicitly **not a minimum, target, or quality requirement**. A future product change should retain the full answer library while emitting stage-aware working subsets. Its reviewed page-count reduction is expected to trip equivalence and must not be rejected merely for becoming shorter. That product work is separate from Release B architecture.

The reliability, federal parsing, alignment, archive, output-cleanup, story-engine, and federal-isolation work is complete and integrated into `main`. The post-merge full validation passed **493/493** on August 9, 2026 in 2m54s. Output cleanup removed 60 legacy PDFs and reduced `output/` from 523 to 431 entries; the 475-record job-description archive has zero empty lanes.

## Resolved evidence boundary: Randstad training

The approved Implementation source resume supports building and maintaining **core training programs**, onboarding, and release communications that reduce resistance to system change. It does not support **policy training**, **strategic delivery**, or **delivery-based** language. Use the confirmed training evidence only where a live posting calls for it; do not generalize the claim or add new source language.

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
