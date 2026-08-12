# Reconciled Federal Correctness and System Reliability Plan
## August 9, 2026 — final, Claude-verified version. Base: CLAUDE_IMPLEMENTATION_PLAN_federal_hardening_20260809.md, reconciled with the original Codex draft, with both Claude review corrections applied (Phase 2 import rationale, explicit sequencing). Ready for Codex implementation.

## Summary
Implement the complete hardening program using the reviewed Claude plan as the base.
Federal parsing uncertainty will not stop document creation. It will produce filename-marked DRAFT documents with detailed build warnings. Existing hard failures for source-truth violations, unsupported claims, corrupt documents, invalid CLI arguments, or failed rendering remain unchanged.
The active DHS posting will default to GS-11, parse its four GS-11 requirements, and produce DRAFT outputs because its duty header says GS-12 while its qualification blocks stop at GS-11.

## Fixed Product Decisions
- Multi-grade default: highest listed qualification grade.
- Explicit override: `--target-grade GS-XX`.
- Parse uncertainty: generate DRAFT; never hard-stop.
- Parse-only draft marking: filename and build feedback only.
- Question-context draft marking: preserve the existing visible red banner.
- If both draft reasons apply, retain the question-context banner.
- Duty-grade/qualification-grade mismatch always requires DRAFT.
- Old outputs are quarantined recoverably, never deleted.
- Extend `TargetContext`; do not add a sibling `TargetIdentity`.
- Use one federal grade computation.
- Preserve rejected alternatives for Claude review without implementing them.
- Preserve the existing uncommitted agency/grammar fix and regression test.

## Core Data and Interface Changes

### Federal requirement structures
Extend `FederalRequirementSection` with:
```python
grade: str = ""
equivalent_grade: str = ""
equivalence_years: int | None = None
```
Continue using `RequirementElement.grade`; every element receives the grade from its source section.

Add:
```python
@dataclass(frozen=True)
class FederalParseDiagnostic:
    code: str
    message: str
    requires_draft: bool
```

Add:
```python
@dataclass(frozen=True)
class FederalParseResult:
    duty_grade: str
    available_grades: tuple[str, ...]
    selected_grade: str
    equivalent_grade: str
    equivalence_years: int | None
    sections: tuple[FederalRequirementSection, ...]
    requirements: tuple[RequirementElement, ...]
    minimum_competencies: tuple[str, ...]
    assessed_competencies: tuple[str, ...]
    diagnostics: tuple[FederalParseDiagnostic, ...]
    verified: bool
```

Expose:
```python
parse_federal_posting(
    job_description: str,
    target_grade: str = "",
) -> FederalParseResult
```
`FederalParseResult.requirements` contains all parsed grade blocks. `build_target_context()` filters them to the selected grade before populating `TargetContext.requirements`.

### Grade selection
Implement:
```python
select_federal_grade(
    sections: tuple[FederalRequirementSection, ...],
    target_grade: str = "",
) -> tuple[str, tuple[str, ...], tuple[FederalParseDiagnostic, ...]]
```
Rules:
1. Normalize explicit input to `GS-XX`.
2. Select it when the corresponding block exists.
3. Otherwise select the numerically highest available block.
4. If an explicitly requested grade is unavailable, retain it as the target, select no requirements, and require DRAFT.
5. If no grade is parseable, leave the target empty and require DRAFT.
6. Multiple cleanly parsed grades produce an informational diagnostic, not DRAFT by themselves.
7. Duty-grade mismatch, zero requirements, unavailable requested grade, missing selected block, or an unparseable qualification block require DRAFT.

### One grade computation
`parse_federal_requirements()` must stop calling the current global `parse_grade_clause()` regex. It creates each `RequirementElement` from its grade-bearing source section.

`parse_grade_clause()` becomes a compatibility wrapper:
```python
result = parse_federal_posting(job_description)
return result.selected_grade, result.equivalent_grade, result.equivalence_years
```
It must contain no independent grade regex.

### TargetContext consolidation
Extend `TargetContext` using backward-compatible defaults:
```python
agency: str = ""
subagency: str = ""
output_label: str = ""
identity_source: str = "company"  # company | agency | title_fallback
available_grades: tuple[str, ...] = ()
duty_grade: str = ""
parse_diagnostics: tuple[FederalParseDiagnostic, ...] = ()
verified: bool = True
```
Do not add a second role-title field; `TargetContext.official_title` remains canonical.

Extend:
```python
build_target_context(
    job_description: str,
    *,
    workflow: str = "commercial",
    target_grade: str = "",
) -> TargetContext
```
Federal construction calls `parse_federal_posting()` exactly once and derives all singular grade fields, selected requirements, diagnostics, and verification state from it.

## Implementation Phases

### Phase 1 — Parse modern federal structures
Update federal parsing to recognize:
- `As a ... you will`
- `As an ... you will`
- Optional inline duty grades such as `GS-12`
- `You qualify for the GS-XX grade level`
- `For the GS-XX`
- Existing `Specialized Experience: GS-XX` variants
- `Experience: One (1) year of specialized experience at the GS-XX grade level or equivalent`
- Semicolon- and line-delimited requirement lists

Use structural headers rather than blank-line counts because the normalized federal line reader removes blank lines.

A qualification block ends at:
- The next grade opener
- A competency-assessment header
- Qualifications, education, questionnaire, required-document, or application-process headers
- End of input

The experience lead establishes equivalent grade and years but is not itself emitted as a capability requirement. Subsequent duty lines become separate grade-tagged sections and requirement elements.

Validate directly against the live DHS text before changing fixtures:
- Duty grade: GS-12
- Available grades: GS-09 and GS-11
- Default selection: GS-11
- Equivalent grade: GS-09
- Four selected GS-11 requirements
- Duty-grade mismatch requiring DRAFT
- Nonzero structured requirements

### Phase 2 — Consolidate organization identity in TargetContext
Keep lightweight extraction helpers in `resume_analysis.py`. Add helpers for:
- Semantic organization and identity source
- Federal agency
- Federal subagency
- Official title
- Filename-oriented output label

`build_target_context()` calls those helpers and stores their results. Federal-specific helpers currently owned by the federal builder become compatibility wrappers.

Keep `extract_output_name()` lightweight rather than routing it through `build_target_context()`. Deferred bidirectional imports already work safely in this codebase; the reason is performance and responsibility separation: callers needing only a filename should not trigger complete job-description and requirement parsing.

Audit all 31 files calling `extract_output_name()`:
- Filename and output-lookup uses may retain it.
- Company-, agency-, tracker-, research-, debrief-, or prose-semantic uses migrate to the semantic organization helper or an existing `TargetContext`.
- Classify each call site as `filename` or `semantic`.
- Add a regression check preventing new semantic assignments such as `company_name = extract_output_name(...)`.
- Preserve `identity_source="title_fallback"` whenever a role substitutes for an unavailable organization.

Federal output labels use agency, official title, and selected grade when known. Subagency is available for document context but omitted from filenames.

### Phase 3 — Thread grade selection through the command surface
Add `--target-grade GS-XX` to:
- Federal workflow runner
- Federal dry-run
- Direct federal builder
- Federal supporting-document builders

Validate syntax through argparse. Malformed CLI input remains a normal command error rather than a parsing DRAFT.

Extend workflow steps to accept child-script argument tuples. Pass the chosen grade consistently to resume, qualifications, cover, interview, and guide builders.

Update federal supporting-document resolution so an explicit GS-09 resume cannot be paired with automatically selected GS-11 materials.

### Phase 4 — Implement reason-scoped DRAFT behavior
Compute independent draft channels:
```python
question_draft_reasons = question_context_issues
parse_draft_reasons = tuple(
    diagnostic.message
    for diagnostic in target_context.parse_diagnostics
    if diagnostic.requires_draft
)
is_draft = bool(question_draft_reasons or parse_draft_reasons)
```
Rules:
- Add `DRAFT` to both federal filenames when `is_draft`.
- Call `mark_docx_as_draft()` only when `question_context_issues` is nonempty.
- Parse-only drafts never receive the visible red banner.
- When both channels apply, preserve the question-context banner.
- Print every parse diagnostic with its stable code.
- Print duty grade, selected grade, available grades, selected requirement count, and verification state.
- Return success after producing a valid DRAFT set.
- Supporting documents inherit DRAFT status.
- DRAFT artifacts cannot satisfy final-output lookup.
- Do not implement parser hard-stop, `--strict-parse`, or a final-output override.

### Phase 5 — Eliminate discarded federal answers
Extend:
```python
active_application_question_responses(
    job_description,
    question_path=...,
    *,
    require_prompts=False,
    excluded_categories: tuple[str, ...] = (),
)
```
Filter excluded prompts before:
- Selecting a resume snapshot
- Loading company context
- Constructing a positioning brief
- Generating or validating answers

Federal qualification generation passes:
```python
excluded_categories=("company_interest",)
```
Delete the current post-generation filter.

Add one immutable `FederalQualificationsContent` carrying:
- Federal application questions
- Standard essays
- Included active question responses
- Recent interview preparation
- Question-context issues
- Parse diagnostics

Create it once before layout selection. Every qualifications layout formats the same object without rereading active files or regenerating answers.

Validate included sendable content before performing layout renders. The excluded company-interest path must never call `build_why_company_answer()`.

### Phase 6 — Stage, validate, render, and publish transactionally
Keep both documents in `temp_root` through:
- DOCX construction
- Plain-text ATS validation
- Final federal coverage validation
- Unsupported-claim validation
- Page-count validation
- Render generation
- Structural render checks

Publish only after the complete set passes.

Add a shared document-set publisher that:
1. Accepts staged-to-final path mappings.
2. Backs up existing destinations.
3. Uses same-volume temporary files and `os.replace()`.
4. Restores all prior files if any replacement fails.
5. Quarantines partial replacements.
6. Removes backups only after the complete set commits.

The existing scratch and output trees share the same project volume, so `os.replace()` follows existing repository conventions and provides atomic per-file replacement. The surrounding rollback makes the multi-file set transactional.

Extend workflow recovery to compare output snapshots after every nonzero process result, not only timeouts.

Failure-injection tests must cover:
- ATS failure after both staged documents exist
- Coverage failure
- Page-count failure
- First destination replacement failure
- Second replacement failure after the first succeeds
- Successful DRAFT publication
- Successful final publication

`OUTPUT_DIR` must remain byte-for-byte unchanged after every injected failure.

### Phase 7 — Decouple and accelerate smoke validation
Create immutable fixtures under `scripts/test_fixtures/federal/` for:
- Previous VA GS-14 posting
- DHS multi-grade posting
- Verified single-grade posting
- Existing specialized-experience marker style
- `As a` and `As an` openings
- Requested grade available
- Requested grade unavailable
- Qualification marker with no duties
- Duty/qualification mismatch
- Compact questionnaire

Replace the stale active-posting test with fixture assertions. Add a guard that `smoke_test.py` does not read either mutable active job-description file.

Optimize the orphan detector precisely:
- Retain one `ast.parse()`.
- Replace per-name full-source `re.findall()` scans with one `ast.walk()`.
- Collect definitions and every `Name`/`Attribute` reference in that traversal.
- Preserve the synthetic-orphan regression.

Replace label-derived tags with explicit `SmokeCheck` metadata.

Add:
```text
python tasks.py validate --quick
```
Quick validation covers imports, federal parsing, TargetContext construction, question routing, and transactional publishing safety without document rendering. Target runtime: under 60 seconds.

Keep focused federal/alignment validation and the full CI suite. Do not parallelize stateful tests during this pass.

### Phase 8 — Rebuild and quarantine DHS artifacts
After all gates pass:
1. Run DHS dry-run without a grade flag.
2. Confirm GS-11 and DRAFT.
3. Run with `--target-grade GS-09`.
4. Confirm only GS-09 requirements are selected.
5. Run with unavailable `--target-grade GS-13`.
6. Confirm a diagnostic DRAFT with no fabricated GS-13 requirements.
7. Rebuild the default DHS document set.
8. Render and inspect every page at 100% zoom.
9. Confirm both filenames contain DRAFT.
10. Confirm parse-only DRAFT does not contain the red banner.
11. Move the earlier false-clean DHS outputs to `scratch/run_logs/quarantine/<timestamp>_superseded_dhs/`.
12. Write a manifest containing original paths, replacement paths, timestamp, and the zero-requirement-parser reason.
13. Leave the active posting and approved sources untouched.

## Sequencing and Independent Work
Strict dependency chain:
```text
Phase 1 parser
  → Phase 2 TargetContext
  → Phase 3 CLI propagation
  → Phase 4 DRAFT routing
  → Phase 8 regeneration
```
Additional dependencies:
- Phase 5 can be developed after Phase 1 and must merge before regeneration.
- Phase 6 is independent of grade parsing but must merge before regeneration.
- Phase 7's test-infrastructure work can be developed independently; fixture expectations depending on new parser behavior land after Phase 1.
- Merge and validate boundaries sequentially even when implementation work is prepared independently, following the repository's narrow-upstream-first rule.

## Compatibility Requirements
- Commercial parsing and filenames remain unchanged.
- `parse_grade_clause()` retains its three-item return tuple.
- Existing federal agency/output helpers remain importable.
- Existing `TargetContext` construction remains valid through defaulted fields.
- `extract_output_name()` remains a lightweight filename fallback.
- Existing question-context banners remain unchanged.
- Parse uncertainty adds no failure exit.
- DRAFT outputs never masquerade as final dependencies.
- Old outputs remain recoverable.
- New outputs remain Word-only.

## Test and Acceptance Plan
Run in order:
1. Live DHS parser assertions
2. Parser fixture tests
3. TargetContext and identity-source tests
4. Question pre-filter tests
5. Draft-reason/banner matrix
6. Grade-propagation tests across all federal outputs
7. Publishing failure-injection tests
8. `python tasks.py validate --quick`
9. `python tasks.py validate --federal`
10. Full `python tasks.py validate`
11. `python tasks.py integration-test`
12. `python tasks.py commands`
13. Federal dry-run matrix
14. End-to-end DHS build
15. Full visual inspection

Acceptance requires:
- DHS produces four GS-11 requirements instead of zero.
- Logistics, procurement, administrative analysis, guideline application, and process-reengineering requirements receive evidence statuses.
- Unsupported and adjacent requirements remain visible.
- GS-12/GS-11 mismatch forces DRAFT without stopping output.
- Parse-only drafts have filename marking but no banner.
- Question-context drafts retain the banner.
- No federal company-interest answer is generated and discarded.
- `TargetContext` and `parse_grade_clause()` agree.
- All 31 `extract_output_name()` call sites are classified and semantic misuse is removed.
- Both documents publish together or neither changes.
- No smoke check reads the active posting.
- Orphan detection performs no per-name whole-file regex scans.
- Quick validation completes within 60 seconds.
- Every delivered page passes render inspection.

## Claude Review Options
Preserve these alternatives in the saved implementation plan and review packets:
- Parse uncertainty:
  - Hard stop — rejected; analysis only.
  - Automatic DRAFT — selected.
  - User-controlled strict mode — analysis only.
- Grade selection:
  - Highest listed — selected.
  - Require explicit selection.
  - Highest evidence-supported.
- Draft marking:
  - Filename only for parse uncertainty — selected.
  - Filename plus banner.
  - Qualifications-only banner.
- Identity:
  - Extend TargetContext — selected.
  - Separate TargetIdentity.
  - Independent string extractors.
- Grade representation:
  - Existing grade-bearing sections/elements plus aggregate result — selected.
  - Parallel FederalGradeBlock model.
  - Document-wide singular regex.
- Publishing:
  - Builder transaction plus workflow rollback — selected.
  - Builder-only transaction.
  - Workflow-only recovery.
- Validation:
  - Optimize the current smoke module with explicit metadata — selected.
  - Split subsystem modules.
  - Adopt another test framework.

Before implementation review:
```text
python tasks.py claude-prompt plan --packet-mode federal
```
After implementation:
```text
python tasks.py claude-packet --mode federal
python tasks.py claude-packet --mode broad
```
Packets must include selected decisions, rejected alternatives, parser diagnostics, grade behavior, banner matrix, atomic-publishing results, validation timing, and DHS before/after evidence.

## Assumptions
- "No hard stops" applies to federal parsing and grade ambiguity.
- Existing source-truth, unsupported-claim, corruption, CLI, and render-safety protections remain.
- Highest listed grade is the automatic default.
- Explicit unavailable grades produce diagnostic DRAFT outputs without fabricated requirements.
- Duty-grade mismatch always requires DRAFT.
- Parse diagnostics alone never trigger the visible banner.
- `TargetContext.official_title` remains the canonical role title.
- Deferred bidirectional imports are already supported; lightweight extraction remains separate for performance and responsibility boundaries.
- No approved source, Education, job title, role order, Professional Development, or active posting content is altered.

## Claude Verification Notes (August 9, 2026)
Confirmed against live code before sign-off:
- `os.replace()` (Phase 6) matches existing repository convention (fresh_corpus_rebuild.py:166, track_applications.py:119), not a new pattern.
- `OUTPUT_DIR` and the scratch tree both resolve under `PROJECT_ROOT` (confirmed across build_*.py modules), so same-volume atomicity for `os.replace()` holds.
- `run_resume_workflow.py`'s recovery is confirmed timeout-only today (`kind == "outer_timeout"` gates the quarantine path at run_resume_workflow.py:313, 359); Phase 6's extension to all nonzero process results is a real, needed change.
- The Phase 2 import rationale is now accurate: `resume_analysis.py` already lazily imports from `requirement_engine` in four places (lines 1376, 1674, 2029, 2194) and `requirement_engine.build_target_context()` already lazily imports `resume_analysis` (line 481); this bidirectional deferred-import pattern is already proven safe in this codebase.
This plan is implementation-ready.
