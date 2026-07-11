# Christian Resume System Architecture Map

## Entry Point

- `tasks.py` is the canonical command surface. Use it to discover the live inventory, maturity labels, and script targets.
- Stable commands are intended for normal production use.
- Experimental and Template-only commands can still be valuable, but they require closer human review before Christian uses the output externally.

## Core Resume Pipeline

- `scripts/build_resume.py` is the orchestration layer. It validates inputs, selects the source resume, applies the build pipeline, runs integrity checks, names the output, and reports build results.
- `scripts/resume_format.py` owns low-level DOCX and WordprocessingML formatting. It handles unpacking and packing DOCX files, visual style copying, font and spacing passes, section layout, LinkedIn hyperlink normalization, and page-fit attempts.
- `scripts/resume_analysis.py` owns job-description analysis and targeting. It handles lane detection, keyword audit helpers, fit signals, unsupported requirement checks, company and role extraction, employer context, story lens selection, and company profile lookup.
- `scripts/resume_content.py` owns resume content shaping. It builds and rewrites the professional summary, role summaries, role-relevant bullets, the commercial skills section (internally still modeled as core competencies), ERP language cleanup, and content-specific condensation.
- `scripts/commercial_resume_model.py` is the authoritative commercial content boundary for the professional summary, role summaries, and selected/reordered bullets. It records same-employer approved-source provenance, writes inspection manifests to `scratch/provenance_models/`, and performs the single content render before formatting-only passes.

## Search Operations Layer

- `scripts/build_application_checklist.py` builds a one-page job-specific readiness sheet. It prefers the newest matching tailored resume output for fit snapshot, keyword coverage, evidence mapping, risks, and story selection. If no tailored resume exists, it falls back to the selected source resume for pre-build alignment only.
- `scripts/track_applications.py` owns `scratch/applications.csv`, keeps `lane_label` and `fit_status` as separate fields, auto-adds rows from the workflow, refreshes metadata from the current or archived job description, and powers list/report summaries.
- Commercial filename parsing also recognizes a live `DRAFT` suffix state for draft outputs. Keep that documented as a separate output-state contract instead of merging it into the main audit enum.
- `scripts/build_jd_library.py` archives job descriptions into `scratch/jd_library/` so tracker backfill and cross-JD pattern analysis can use older postings without reading the whole repo.
- `scripts/build_search_analytics.py` and `scripts/build_general_advice.py` read tracker lane/fit helpers instead of parsing raw tracker columns directly.
- `scripts/build_claude_review_packet.py` rebuilds `TEMP_FOR_REVIEW.md` from the live codebase with packet modes such as broad, tracker, checklist, resume, cover, interview, and workflow.
- `scripts/build_claude_prompt.py` generates the strict review and implementation-plan prompts that pair with the packet modes so Claude review threads stay consistent.

## Shared Guidance Layer

- `scripts/business_context.py` extracts business model, customer type, product or service context, operational complexity, technical stack, compliance signals, and role-success outcomes.
- `scripts/interview_context.py` scopes company research and interview notes so later outputs only use context that belongs to the active company.
- `scripts/job_search_guidance.py` is the shared advice layer for generalized career guidance, recruiter-screen prep, follow-up timing, concise email rules, salary research basics, remote or hybrid screening, LinkedIn findability, informational interviews, and follow-up sequences.

## Output Families

- Resume and cover letter: `build_resume.py`, `build_federal_resume.py`, `build_cover_letter.py`, `build_application_checklist.py`
- Interview prep: `build_interview_cheat_sheet.py`, `build_detailed_interview_guide.py`, `build_thank_you.py`, `build_interview_followup.py`, `build_post_round.py`, `build_internal_interview.py`
- Career and job-search guidance: `build_general_advice.py`, `build_linkedin_update.py`, `build_linkedin_calendar.py`, `build_networking_outreach.py`, `build_first_90_days.py`, `build_salary_guide.py`, `build_monthly_review.py`, `build_skills_gap.py`
- Debrief and search operations: `post_interview_debrief.py`, `build_debrief_analysis.py`, `track_applications.py`, `application_status.py`, `build_search_analytics.py`, `reset_jobs.py`, `backup.py`

## Governance Rules

- `AGENTS.md` is the compact operating contract. Keep it limited to always-needed rules.
- `SYSTEM_REFERENCE.md` holds the fuller command and output inventory. Keep it aligned with the real script surface and maturity labels.
- `CLAUDE.md` and the `.context/` files are the compact external-review system. Keep them aligned with live script behavior, packet modes, prompt commands, and tracker/checklist/workflow changes.
- LinkedIn content must never be used as resume source material.
- One active job description belongs in `jobs/job_description.txt` at a time.
- Word documents are the only final document artifact format. Do not create PDFs.
- Christian-specific evidence rules outrank generic career advice. Shared advice can support the workflow, but it must not weaken unsupported-claim boundaries, ERP guardrails, or one-job-at-a-time targeting.

## Validation Expectations

- Run `python tasks.py validate` after script or config changes.
- For guidance or interview changes, build at least one interview or advice document and inspect the DOCX output.
- For command-surface or governance changes, run `python tasks.py commands` and verify the printed inventory matches the intended maturity labels.
- For Claude workflow changes, run `python tasks.py claude-packet --skip-checks --mode broad` and `python tasks.py claude-prompt review --packet-mode broad` to confirm the packet and prompt layers still match the docs.
- When editing `config/language_rules.py` or `config/job_profiles.py`, confirm the smoke test still passes all lane-detection assertions before generating new outputs.
