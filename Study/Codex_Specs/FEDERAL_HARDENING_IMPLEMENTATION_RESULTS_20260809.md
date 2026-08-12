# Federal Hardening Implementation Results — 2026-08-09

## Implemented decisions

- Federal parse uncertainty generates valid filename-marked DRAFT documents and never becomes a parser hard stop.
- The highest listed qualification grade is selected by default; `--target-grade GS-XX` is available across the workflow, dry run, direct builder, cover letter, interview cheat sheet, and detailed guide.
- `TargetContext` is the single identity and selected-grade model. `parse_federal_posting()` is the single grade computation; `parse_grade_clause()` is only a compatibility projection.
- Parse-only drafts use filename and build feedback only. Question-context drafts retain the existing visible red banner. Combined reasons retain that banner.
- Federal resume and qualifications files remain staged through ATS, coverage, unsupported-claim, page-count, and render checks. The set publishes transactionally with prior-file rollback and partial-output quarantine.
- Federal company-interest questions are excluded before resume selection, company context, positioning-brief work, or answer generation.
- Smoke fixtures are immutable and do not read either active posting. The orphan detector uses one AST traversal, and explicit `SmokeCheck` metadata powers focused validation.

## Rejected alternatives retained for review only

- Parser hard stop.
- User-controlled strict parsing or final-output override.
- Require explicit grade selection or select by evidence strength.
- Parse-diagnostic red banner.
- Separate `TargetIdentity`.
- Parallel `FederalGradeBlock` representation.
- Builder-only publication or workflow-only recovery.
- Smoke-module split or another test framework.

## Live DHS before and after

Before: the DHS posting parsed zero requirements and produced apparently final filenames.

After:

- Duty grade: GS-12.
- Available qualification grades: GS-09, GS-11.
- Default selected grade: GS-11.
- Equivalent grade: GS-09.
- Selected GS-11 requirements: 4.
- Verification: false because `duty_qualification_grade_mismatch` requires DRAFT.
- Output: two-page GS-11 DRAFT federal resume plus two-page GS-11 DRAFT qualifications statement.
- Parse-only DRAFT banner check: no visible DRAFT text or red banner in the qualifications document.
- Excluded-answer check: no company-interest response was generated or rendered.

Dry-run matrix:

- No flag: GS-11, four selected requirements, DRAFT.
- `--target-grade GS-09`: GS-09, four selected requirements, DRAFT.
- `--target-grade GS-13`: unavailable-grade diagnostics, zero GS-13 requirements, DRAFT, successful dry run.

## Publication and recovery evidence

Failure injection covers ATS failure, coverage failure, page-count failure, first destination replacement failure, and second destination failure after the first succeeds. Every case preserves prior output bytes. Successful final and DRAFT set publication are both covered. Workflow recovery now snapshots, quarantines, and restores changed DOCX files after every nonzero child result, not only timeouts.

## Validation evidence

- `python tasks.py validate --quick`: 16/16, 23.1 seconds (under the 60-second target).
- `python tasks.py validate --federal`: 41/41.
- `python tasks.py validate`: 505/505 in 481.1 seconds.
- `python tasks.py integration-test`: passed.
- `python tasks.py commands`: passed and lists the live command targets.
- DHS default build: passed staged ATS, final coverage, two-page validation, render validation, and transactional publication.
- Visual QA: all four rendered pages inspected at original resolution; no clipping, overlap, or margin overflow.

## Quarantine

The two earlier false-clean DHS documents were moved recoverably to `scratch/run_logs/quarantine/20260809_150545_superseded_dhs/`. Its manifest records original, quarantine, and replacement paths plus the zero-requirement-parser reason. The active posting and approved source files were not changed by quarantine.
