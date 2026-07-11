# Architecture Map

This is a local Python-based document generation system, not a web app.

## Important Folders

- `source/`: approved source Word documents and visual formatting base.
- `jobs/`: current job description, company research, interview notes, and debrief history.
- `scripts/`: Python scripts that generate documents and perform validation.
- `output/`: generated Word documents. Not source truth.
- `render_check*/`: visual QA artifacts. Not source truth.
- `backup/` and `backups/`: historical snapshots and old generated material. Not source truth.
- `scratch/` and `.tmp/`: temporary logs and working files. `scratch/applications.csv` and `scratch/jd_library/` are operational context, not source resumes.
- `.context/`: compact Claude-readable project context.

## Main Data Flow

1. User places one complete job posting in `jobs/job_description.txt`.
2. Processing logic also reads `scripts/config/language_rules.py` for shared language guardrails and `scripts/config/job_profiles.py` for lane detection, bridge evidence, story lenses, employer contexts, and competency triggers.
3. Resume builder reads the job description and selects the appropriate source resume.
4. `resume_analysis.py` classifies the job and evidence map, `resume_content.py` composes summary and bullet-level tailoring, then `commercial_resume_model.py` records approved-source provenance for the summary, role summaries, and selected/reordered bullets and renders those surfaces once before formatting-only passes.
5. Resume builder writes a Word document to `output/`.
6. Checklist, cover letter, and interview builders read the job description and the matching generated resume output when available.
7. Shared prose-quality validation runs through `scripts/writing_eval.py` and `utils.enforce_prose_quality()` so sendable outputs can hard-fail while prep outputs only warn.
8. Resume readiness and downstream gating come from `build_resume.resume_readiness_report()` and related helpers so cover letters and workflow runners do not guess from human-readable notes.
9. `track_applications.py` records the active job in `scratch/applications.csv`, while `build_jd_library.py` can archive job descriptions for later tracker refresh and pattern review.
10. Search-ops outputs such as search analytics and general advice read tracker helper functions rather than raw tracker columns.
11. Render checks create page images for visual QA.

## Main Scripts

- `scripts/build_resume.py`: core tailored resume generator. It handles resume selection, keyword audit, role-lane analysis, employer/story lenses, aggressive supported keyword-gap closure, structured readiness reporting, fit audit, Word XML manipulation, formatting, and render check.
- `scripts/resume_analysis.py`: direct definitions for job-description parsing, resume selection, keyword extraction, role-lane profiling, employer-context lenses, story lenses, and fit-signal helpers that `build_resume.py` re-exports at runtime.
- `scripts/resume_content.py`: direct definitions for professional-summary composition, role-summary rewrites, supported bullet rewrites, competency reshaping, and bullet-condensation helpers that `build_resume.py` imports into the live resume build.
- `scripts/commercial_resume_model.py`: provenance-bearing commercial content model and single-render boundary for summary, role summaries, and bullets; manifests are diagnostic scratch artifacts, not claim sources.
- `scripts/build_application_checklist.py`: one-page readiness document. It prefers the newest matching tailored resume for fit snapshot, keyword coverage, and risk review, with a source-resume fallback only when no tailored output exists.
- `scripts/build_cover_letter.py`: tailored cover letter generator. It depends on a matching generated resume output for the active company and stops when structured resume gap blockers remain.
- `scripts/build_interview_cheat_sheet.py`: compact interview prep document.
- `scripts/build_detailed_interview_guide.py`: full interview guide with deeper answer strategy and story logic.
- `scripts/track_applications.py`: tracker owner for `scratch/applications.csv`, including row creation, lane/fit refresh, and list/report helpers.
- `scripts/build_jd_library.py`: archives job descriptions into `scratch/jd_library/` for later lookup.
- `scripts/build_search_analytics.py`: builds a tracker-based job-search analytics report.
- `scripts/build_general_advice.py`: includes active-job and tracker-performance context in the operating manual.
- `scripts/build_claude_review_packet.py`: rebuilds `TEMP_FOR_REVIEW.md` from current code and command output with packet modes for broad or subsystem-focused Claude review.
- `scripts/build_claude_prompt.py`: prints the strict review-pass or plan-pass prompt that matches a packet mode.
- `scripts/run_resume_workflow.py`: workflow runner with basic recovery, generated DOCX repair for LinkedIn hyperlink issues, and automatic tracker row updates after successful runs.
- `scripts/post_interview_debrief.py`: structured post-interview note capture that can also update the matching tracker row.
- `scripts/render_checks.py`: renders generated DOCX files for visual QA.
- `scripts/smoke_test.py`: Validation-only script that checks imports, lane detection, and language rule integrity without reading a live job description. Run this after any config change or script modification.
- `scripts/utils.py`: shared text helpers, template-leakage guards, and prose-quality enforcement.
- `scripts/writing_eval.py`: shared sentence-level writing evaluator used across cover letters, email bodies, checklist narratives, and interview-prep prose.
- `scripts/config/language_rules.py`: prohibited or risky wording patterns used by processing and validation.
- `scripts/config/job_profiles.py`: job profile, lane, bridge evidence, story lens, employer context, and competency configuration.
- `scripts/modules/employer_playbooks/`: employer-specific interview logic.

## File Dependency Notes

`build_cover_letter.py` expects a matching resume output to already exist. If no matching resume exists, run `build_resume.py` first.

`build_application_checklist.py` prefers a matching tailored resume output. If no output exists yet, it can still build from the selected source resume, but that fallback is advisory pre-build alignment rather than a final-output fit audit.

Commercial output naming also recognizes a live `DRAFT` suffix state when filename parsing sees draft output. Keep that documented as an output-state contract rather than folding it into the PASS/BRIDGE/FAIL/POOR audit enum.

Interview scripts use the generated resume and optional job context files. Company research and interview notes should be treated as user-supplied context, not independently verified facts unless the user says they are verified.

`output/` may contain older generated documents and even legacy PDFs. These are not source material. New final documents should be Word-only.

## Validation Priorities

High-risk changes should preserve:

- source-truth boundaries
- no invented content
- Word-only output
- two-page resume fit
- Carlito font and dense KPMG formatting
- mandatory company reorganization sentences
- role order, job titles, Education, and Professional Development
- no LinkedIn external hyperlink relationship
- tracker lane and fit data staying separate and current
- Claude packet and prompt docs staying aligned with the live command surface
