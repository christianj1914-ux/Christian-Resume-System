# Claude Implementation Plan: Federal Correctness and Reliability Hardening
## August 9, 2026 — resolves the Claude review findings against the Codex draft plan of the same date. Adopts the Codex draft's selected defaults everywhere except the grade model and the identity model, both revised below with exact code grounding. Planning only; implementation is for Codex.

## Summary

The active DHS posting (`jobs/federal_job_description.txt`) parses to zero federal requirements today because `parse_federal_requirement_sections()` (requirement_engine.py:287) only matches `"As an ... you will:"` and this posting says `"As a Mission Support Specialist, GS-12 you will perform..."` (line 6), and `parse_grade_clause()` (requirement_engine.py:450) only matches `"Specialized Experience: GS-XX grade level"` while this posting says `"You qualify for the GS-09/GS-11 grade level"` (lines 13, 20). This plan fixes that parsing gap, makes DRAFT the non-blocking outcome for parse uncertainty, and fixes four downstream defects the DHS case exposed: the discarded federal `company_interest` answer, non-atomic document publishing, a stale VA-fixture smoke test reading the live posting, and a slow orphan-test scan. It also corrects two design choices in the prior Codex draft that the code does not support cleanly as originally specified.

## What Changes From the Codex Draft, and Why

**Grade model.** The Codex draft proposed a new `FederalGradeBlock`/`FederalParseResult` model living alongside the existing `TargetContext.target_grade`/`equivalent_grade` singular fields (requirement_engine.py:42-56), populated independently via the existing `parse_grade_clause()` regex. Left as specified, two grade computations would exist for the same posting and could disagree, since `parse_grade_clause()`'s regex will keep returning `""` for this posting's wording even after the new multi-grade parser is added elsewhere. `RequirementElement` already has a `grade` field (requirement_engine.py:29) and `parse_federal_requirements()` already tags every element with one grade computed from a single `parse_grade_clause()` call (requirement_engine.py:395, 409). The fix below extends that existing per-element grade tagging to be block-accurate instead of inventing a parallel model, and makes `parse_grade_clause()` a wrapper over the same parse that feeds `TargetContext`, so there is exactly one federal grade computation.

**Identity model.** The Codex draft proposed a new `TargetIdentity` dataclass in `resume_analysis.py`, separate from `TargetContext` in `requirement_engine.py`, which already carries a `company` field and already branches on `workflow == "federal"` (requirement_engine.py:486-497). A second identity structure recreates the exact class of bug this fix is meant to close: two places holding "who is the target," built by two functions, free to drift. `TargetContext` is extended in place instead.

**Draft marking.** The Codex draft's selected default is filename-only marking for parse-uncertain drafts, but `question_prep.mark_docx_as_draft()` (question_prep.py:1083) already writes a visible red banner into the qualifications statement title, called today whenever `question_context_issues` is non-empty (build_federal_resume.py, `build_federal_resume()`). Left unspecified, the combined draft-status decision in the Codex draft's item 2 could accidentally route parse-only drafts through that same banner call. This plan makes the scoping explicit: the banner stays reserved for `question_context_issues`; parse verification failures affect filename and build feedback only.

Everything else in the Codex draft (no hard stops, highest-grade default with `--target-grade` override, DRAFT-not-fail policy, transactional publishing, fixture decoupling, orphan-scan speedup, quarantine-not-delete) is adopted as written.

## Core Interfaces (Revised)

**`FederalRequirementSection` gains a `grade: str = ""` field** (requirement_engine.py:60-66). `parse_federal_requirement_sections()` (requirement_engine.py:287) is extended to:
- Match duty introductions as `^As an? .+?,?\s*(?:GS-\d+\s+)?you will[:\s]` (covers `"As an X, you will:"` and `"As a X, GS-12 you will perform"`), capturing an inline duty grade into a new `duty_grade` return value.
- Emit one `FederalRequirementSection(kind="specialized_experience", grade=...)` per qualification block, opened by either `"Specialized Experience:? (GS-\d+)"` (existing) or `"You qualify for the (GS-\d+) grade level"` / `"For the (GS-\d+)"` (new), and closed at the next qualification-block opener, `"You will be assessed"`, `"Qualifications"`, or two blank lines.
- Capture the per-block equivalent grade and years from `"Experience: One \(?1\)? years? of specialized experience at the (GS-\d+) grade level or equivalent"` scoped to that block, instead of one document-wide regex.

**`parse_federal_requirements()` (requirement_engine.py:394)** stops calling `parse_grade_clause()` for a single global grade (line 395) and instead tags each `RequirementElement.grade` from its own section's `grade`, so GS-09 and GS-11 requirements stay in separate evidence groups as the Codex draft intended, without a second model.

**New `select_federal_grade(sections, target_grade="") -> tuple[str, tuple[str, ...], tuple[str, ...]]`** in requirement_engine.py returns `(selected_grade, available_grades, diagnostics)`: explicit `target_grade` if it appears among parsed blocks; otherwise the highest parsed block; if `target_grade` was requested but not found, return it anyway with a diagnostic (unverified path); if no blocks parsed, return `("", (), diagnostic)`.

**New `parse_federal_posting(job_description: str, target_grade: str = "") -> FederalParseResult`** in requirement_engine.py, where `FederalParseResult` is a thin aggregate, not a new grade representation:
```
duty_grade: str
available_grades: tuple[str, ...]
selected_grade: str
equivalent_grade: str
equivalence_years: int | None
requirements: tuple[RequirementElement, ...]   # already grade-tagged; caller filters to selected_grade
minimum_competencies: tuple[str, ...]
assessed_competencies: tuple[str, ...]
diagnostics: tuple[str, ...]
verified: bool
```
`verified` is `False` when: zero sections parsed; the selected grade has no requirement block; `duty_grade` is set and conflicts with `selected_grade`; a requested `target_grade` was not found among `available_grades`; or a qualification marker was found but yielded zero requirement lines.

**`parse_grade_clause()` (requirement_engine.py:450) becomes a compatibility wrapper**: `target, equivalent, years = parse_federal_posting(jd).selected_grade, .equivalent_grade, .equivalence_years`. No independent regex remains, closing the drift path described above.

**`TargetContext` (requirement_engine.py:42) gains fields** instead of a sibling `TargetIdentity`: `agency: str = ""`, `subagency: str = ""`, `role_title: str = ""`, `output_label: str = ""`, `identity_source: str = "company"` (one of `"company" | "agency" | "title_fallback"`, closing the silent-fallback gap in `extract_output_name()`, resume_analysis.py:1152), `available_grades: tuple[str, ...] = ()`, `duty_grade: str = ""`, `parse_diagnostics: tuple[str, ...] = ()`, `verified: bool = True` (commercial workflow and previously-verified federal postings keep the default).

**`build_target_context()` (requirement_engine.py:479)** for `workflow == "federal"` calls `parse_federal_posting(job_description, target_grade=target_grade)` exactly once and derives `target_grade`, `equivalent_grade`, `equivalence_years`, `requirements` (filtered to `selected_grade`), `minimum_competencies`, `assessed_competencies`, `available_grades`, `duty_grade`, `parse_diagnostics`, and `verified` from that single result. `company`/`agency`/`subagency`/`role_title`/`output_label` are populated by moving `extract_federal_agency_name()` and the role-title half of `extract_federal_output_name()` (build_federal_resume.py:1062, 1103) into this function, re-exported from `build_federal_resume.py` for compatibility. Commercial workflow is unchanged except for the new defaulted fields.

**`extract_output_name()` (resume_analysis.py:1152) and `extract_federal_output_name()` (build_federal_resume.py:1103) remain as compatibility wrappers** over `TargetContext.output_label`, preserving all ~24 existing call sites (`company_name`/`company`/`current_company` assignments across build_cover_letter.py, build_resume.py, run_resume_workflow.py, track_applications.py, and 20 others) without a rename pass. New consumers (cover letter, debrief, tracker, question-prep) that need the organization specifically should read `TargetContext.agency or TargetContext.company` rather than the filename-fallback wrapper.

## Implementation Phases

**Phase 1 — Federal structural parsing.** Implement the `FederalRequirementSection.grade` extension, the new duty-grade and qualification-block regexes, `select_federal_grade()`, `parse_federal_posting()`, and the `parse_grade_clause()`/`parse_federal_requirements()` rewrites above, all in requirement_engine.py. Validate against the DHS fixture directly (no test file changes yet): `available_grades == ("GS-09", "GS-11")`, `duty_grade == "GS-12"`, `selected_grade == "GS-11"` by default, four requirement elements tagged `grade="GS-11"`, `verified is False` (duty/qualification grade mismatch diagnostic present).

**Phase 2 — TargetContext extension and identity consolidation.** Extend `TargetContext` and `build_target_context()` as specified above. Move `extract_federal_agency_name()`/`extract_federal_output_name()` federal-specific logic into `build_target_context()`; keep both original functions as wrappers. Add `--target-grade GS-XX` to `tasks.py federal-resume`, `federal-dry-run`, `run_resume_workflow.py`, and `build_federal_resume.py`'s arg parser, threaded into `build_target_context(..., target_grade=...)`.

**Phase 3 — DRAFT policy, not hard-stop.** In `build_federal_resume()` (build_federal_resume.py, ~3067): compute `target_context = requirement_engine.build_target_context(job_description, workflow="federal", target_grade=args.target_grade)`. Draft-filename decision becomes `draft_reasons = question_context_issues + target_context.parse_diagnostics` (tuple concatenation); both `output_docx` and `qualifications_docx` filenames get `" DRAFT"` inserted when `draft_reasons` is non-empty (today only the qualifications filename does, at build_federal_resume.py:3078). The `mark_docx_as_draft()` banner call stays gated on `question_context_issues` only, per the resolution above; parse diagnostics are printed as `FEDERAL PARSE WARNING: ...` lines and included in dry-run/build feedback alongside `selected_grade`, `available_grades`, and requirement count. No `fail()` path is added for parse uncertainty anywhere in this phase.

**Phase 4 — Stop generating discarded federal answers.** Add `excluded_categories: tuple[str, ...] = ()` to `question_prep.active_application_question_responses()` (question_prep.py:1961), filtering by `question_category(prompt)` before `selected_resume_snapshot()` and answer generation. In `additional_application_question_responses()` (build_federal_resume.py:2596), call it with `excluded_categories=("company_interest",)` instead of the current post-hoc filter (build_federal_resume.py:2603-2610), removing the wasted generation pass and its `PositioningBrief` cross-contamination risk. Precompute one `FederalQualificationsContent` used by every qualifications layout, as in the Codex draft.

**Phase 5 — Transactional publishing (resume and qualifications both).** `build_federal_resume()` currently `shutil.copy2`s the resume into `OUTPUT_DIR` (build_federal_resume.py:3106) before the qualifications document is even built, and both files sit under final `output/` filenames before ATS validation, `assert_final_federal_coverage`, and page-count checks run (build_federal_resume.py:~3115-3122) — wider exposure than the Codex draft's "qualifications only" framing. Rework so both documents are built and saved only into `temp_root`, all checks (ATS, coverage, page count, render) run against the staged copies, and `shutil.copy2` into `OUTPUT_DIR` happens once, after every check passes, for both files together. On any check failure, nothing changes in `OUTPUT_DIR`. Extend `run_resume_workflow.py` recovery to quarantine and restore changed DOCX files after any failed process step, not only timeouts.

**Phase 6 — Fixture decoupling and validation speed.** Move the VA GS-14 case out of `test_active_federal_structural_requirement_fixture` (smoke_test.py:1147), which currently reads `jobs/federal_job_description.txt` directly and asserts `("GS-14", "GS-13", 1)` — values that no longer match the live DHS posting — into an immutable fixture file (e.g. `scripts/fixtures/federal_va_gs14.txt`). Add an immutable DHS multi-grade fixture with the expected Phase 1 results. Add a guard test asserting no smoke test reads `jobs/federal_job_description.txt` or `jobs/job_description.txt`, matching the documented contract (ARCHITECTURE_MAP.md:49). Replace the per-name `re.findall` re-scan in `orphaned_test_function_names()` (smoke_test.py:378-390) — which already does one `ast.parse()` to collect `test_` names, then re-scans the full 18,380-line source once per name — with a single `ast.walk()` pass that collects both the definitions and every `Name`/`Attribute` reference in one traversal.

**Phase 7 — Regenerate and quarantine.** Rebuild the DHS resume and qualifications statement under the new pipeline; confirm `DRAFT` filenames (duty/qualification grade mismatch keeps `verified=False` even after parsing succeeds, by design). Move the current DHS resume and qualifications statement (built under the old zero-requirement false-clean parse) into a timestamped `scratch/review_quarantine/` folder with a note recording why they were superseded. Leave `jobs/federal_job_description.txt` and all approved source files untouched.

## Public Interfaces and Compatibility

New: `requirement_engine.parse_federal_posting(job_description, target_grade="") -> FederalParseResult`; `requirement_engine.select_federal_grade(sections, target_grade="")`; `python tasks.py federal-resume --target-grade GS-11`; `python tasks.py federal-dry-run --target-grade GS-11`; `question_prep.active_application_question_responses(..., excluded_categories=())`.

Unchanged signatures, revised internals: `requirement_engine.parse_grade_clause()`, `requirement_engine.build_target_context()`, `resume_analysis.extract_output_name()`, `build_federal_resume.extract_federal_agency_name()`, `build_federal_resume.extract_federal_output_name()`. No caller of these needs to change.

Not implemented in this pass, per the no-new-parallel-model resolution above: `resume_analysis.TargetIdentity`, `resume_analysis.parse_target_identity()`. If a future need arises for an identity object usable without pulling in `requirement_engine`'s federal parsing dependency, revisit as a read-only projection built from `TargetContext`, not an independent parser.

## Test and Acceptance Plan

1. Phase 1 unit assertions against the live DHS text (grades, duty/qualification mismatch, four GS-11 elements) before any test-file changes, so the parser is proven against the real posting first.
2. `python tasks.py validate --quick` (new: imports, parser, `build_target_context`, prompt routing, publishing safety) after Phases 1-2.
3. Question-routing test: `additional_application_question_responses()` output contains no `company_interest`-category response for a federal job description that has one queued (Phase 4).
4. Draft/filename tests: both filenames carry `DRAFT` when `parse_diagnostics` is non-empty and `question_context_issues` is empty; banner appears only when `question_context_issues` is non-empty (Phase 3).
5. Publishing failure-injection test: force an ATS or page-count failure and assert `OUTPUT_DIR` is unchanged (Phase 5).
6. `python tasks.py validate --federal`, then full `python tasks.py validate`, then `python tasks.py integration-test`.
7. `python tasks.py commands`, confirm `--target-grade` documented.
8. Federal dry runs: DHS with no flag (expect GS-11, DRAFT), DHS with `--target-grade GS-09` (expect GS-09 block only, DRAFT), DHS with `--target-grade GS-13` (expect unavailable-grade diagnostic, DRAFT).
9. Rebuild DHS documents; render every page at 100% zoom; visual inspection for clipping/overlap.
10. Confirm zero smoke tests read `jobs/federal_job_description.txt` or `jobs/job_description.txt` (guard test from Phase 6); confirm `test_active_federal_structural_requirement_fixture`-equivalent now runs against the immutable VA fixture and passes with the original `("GS-14", "GS-13", 1)` values.
11. Confirm the orphan-scan timing drop (Phase 6) directly: total smoke suite wall time before/after.

Acceptance mirrors the Codex draft's list; the two additions are: `TargetContext.identity_source` is `"agency"` or `"title_fallback"` for every federal build (never silently blank), and no test anywhere reads a mutable active job file.

## Sequencing and Gates

Phase 1 gates Phases 2-5 (nothing downstream can trust `TargetContext` grade fields until the parser is correct). Phase 3's DRAFT policy gates Phase 7 (do not regenerate DHS documents as final until DRAFT routing is proven). Phase 6 can run in parallel with Phases 2-5 since it only touches test infrastructure, but must land before Phase 7's rebuild is treated as regression-proven. Phase 4 is independent and can land any time after Phase 1.

## Options Preserved for Claude Review

Unchanged from the Codex draft: hard stop (rejected, not implemented), user-controlled strict/override mode (analyze only), highest-evidence-supported-grade selection (rejected in favor of highest-listed), banner-plus-filename or banner-only-in-qualifications draft marking (rejected in favor of the reason-scoped split above), builder-only or workflow-only publishing transactions (rejected in favor of both), splitting `smoke_test.py` into subsystem modules or adopting a new test framework (rejected in favor of optimizing the existing module first).

Revised in this document, kept open for a future pass if requirements change: dedicated `TargetIdentity` model (superseded by extending `TargetContext`) and a parallel `FederalGradeBlock` model (superseded by extending `RequirementElement.grade` and `FederalRequirementSection.grade`, which already existed as scaffolding for exactly this).

## Assumptions

- "No hard stops" applies to federal parsing and grade ambiguity only; source-truth, unsupported-claim, corruption, and render-safety failures still hard-stop, unchanged.
- Duty-grade/qualification-grade mismatch always forces `verified=False`, even when the selected grade parses cleanly, since the DHS posting's own internal inconsistency (GS-12 duties, GS-09/GS-11 qualification ceiling) is real signal a human should see before submission.
- The existing `mark_docx_as_draft()` banner behavior for `question_context_issues` is intentional prior product behavior and is preserved unchanged, not extended to the new parse-diagnostics draft reason.
- Old DHS outputs are quarantined, never deleted, consistent with `.context/ARCHITECTURE_MAP.md`'s "not source truth" framing of `output/`.
- No source resume, federal source JSON, approved essay JSON, Education, job title, role order, or Professional Development content is altered by this plan.
