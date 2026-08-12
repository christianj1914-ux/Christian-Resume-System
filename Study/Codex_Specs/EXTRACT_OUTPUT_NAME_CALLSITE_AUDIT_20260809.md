# extract_output_name Call-Site Audit — 2026-08-09

The reviewed plan described 31 callers. The immutable `HEAD` baseline contains 35 textual Python occurrences across 25 files, including the function definition and four internal filename-fallback uses. Every external use was classified by responsibility.

## Filename uses retained

- `tasks.py`: output candidate lookup.
- `scripts/run_resume_workflow.py`: workflow output-name lookup.
- `scripts/resume_analysis.py`: the function definition, output-target fallback, output-name candidates, and matching-output fallback.

These uses are intentionally filename-oriented and remain lightweight.

## Semantic uses migrated

The following consumers now call `extract_semantic_organization()` (directly or through the `build_resume` re-export) instead of treating a filename fallback as an employer identity:

- `tasks.py`
- `scripts/application_status.py`
- `scripts/build_application_checklist.py`
- `scripts/build_cover_letter.py`
- `scripts/build_debrief_analysis.py`
- `scripts/build_detailed_interview_guide.py`
- `scripts/build_followup_email.py`
- `scripts/build_internal_interview.py`
- `scripts/build_interview_cheat_sheet.py`
- `scripts/build_interview_companions.py`
- `scripts/build_interview_followup.py`
- `scripts/build_interview_review.py`
- `scripts/build_interview_validation_set.py`
- `scripts/build_networking_outreach.py`
- `scripts/build_post_round.py`
- `scripts/build_resume.py`
- `scripts/build_salary_guide.py`
- `scripts/build_standard_qualifications_statement.py`
- `scripts/build_thank_you.py`
- `scripts/build_weekly_tracker.py`
- `scripts/post_interview_debrief.py`
- `scripts/question_prep.py`
- `scripts/track_applications.py`

## Regression guard

`smoke_test.py` walks assignment syntax and fails if `extract_output_name()` is newly assigned directly to `company`, `company_name`, `current_company`, `agency`, `employer`, or `organization`. The helper still preserves `identity_source="title_fallback"` through `TargetContext` when no organization can be identified.
