# Resume System Brief

This system generates tailored career documents for Christian Estrada. The goal is to produce submission-ready or prep-ready Word documents from verified source material.

## Four-Layer Workflow

Every run follows the four-layer workflow from the master appendix:

1. Knowledge Base: `AGENTS.md`, approved source resumes, optional company research, optional interview notes, and approved appendices.
2. User Input: one active job description, target company, target role, requested outputs, and supplied notes.
3. Processing: role-lane analysis, evidence mapping, keyword audit, story lens, employer context lens, unsupported-requirement audit, and output-specific quality checks.
4. Output: polished Word-only documents plus plain-language build feedback.

<!-- CLAUDE_REVIEW:BRIEF_EXPLICIT_STANDARD:START -->
<!-- CLAUDE_REVIEW:BRIEF_EXPLICIT_STANDARD:END -->

## Source Truth

Use only these source resumes from `source/`:

- `Estrada_Resume_Implementation.docx`
- `Estrada_Resume_PreSales_CSM.docx`
- `Christian_Estrada_KPMG_Final_Tightened_EdFix.docx`

Do not use old outputs as source material. Do not use LinkedIn page content as source material. Keep Christian's LinkedIn URL visible as contact text only, with no external hyperlink relationship in generated Word documents.

## Output Rules

The system should create polished Word documents only. Do not create PDFs as final outputs.

Generated documents belong in `output/`. Render-check folders are validation artifacts, not source material.
<!-- CLAUDE_REVIEW:BRIEF_RENDER_NOTE:START -->
<!-- CLAUDE_REVIEW:BRIEF_RENDER_NOTE:END -->

## Active Inputs

Use only one job posting at a time in `jobs/job_description.txt`. If multiple postings are pasted together, separate them and handle one role per run so targeting, keywords, evidence, and output names stay clean.

<!-- CLAUDE_REVIEW:BRIEF_FEDERAL_INPUTS:START -->
<!-- CLAUDE_REVIEW:BRIEF_FEDERAL_INPUTS:END -->

Config inputs:

- `scripts/config/language_rules.py`: shared language guardrails for cliches, banned AI-writing words, placeholders, first-person pronouns, duty-only openers, vague soft skills, unsupported job-ad claim language, prompt leaks, and acronym normalization.
- `scripts/config/job_profiles.py`: shared targeting logic for role lanes, bridge evidence, unsupported and poor-fit signals, story lenses, employer contexts, and competency triggers/removals.

After editing either config file, run `scripts/smoke_test.py` and verify all lane detection assertions pass before running a full resume build.

Optional context files:

- `jobs/company_research.txt`
- `jobs/interview_notes.txt`
- `jobs/debrief_history.txt` when available

Post-interview notes should be captured through `scripts/post_interview_debrief.py`, which appends structured notes to `jobs/debrief_history.txt` and company intelligence to `jobs/company_research.txt`.

Operational context files:

- `scratch/applications.csv`: application tracker data. This is operational metadata, not resume source truth.
- `scratch/jd_library/` and `scratch/jd_library/index.csv`: archived job descriptions used for safe tracker refresh and pattern review.

## Available Outputs

Available as current generated outputs:

- Tailored Resume: `scripts/build_resume.py`
- Federal Tailored Resume: `scripts/build_federal_resume.py`
<!-- CLAUDE_REVIEW:BRIEF_FEDERAL_OUTPUT:START -->
<!-- CLAUDE_REVIEW:BRIEF_FEDERAL_OUTPUT:END -->
- Tailored Cover Letter: `scripts/build_cover_letter.py`
- Application Checklist: `scripts/build_application_checklist.py`
- Standard Interview Cheat Sheet: `scripts/build_interview_cheat_sheet.py`
- Complete Interview Guide: `scripts/build_detailed_interview_guide.py`
- Thank-You Note: `scripts/build_thank_you.py`
- LinkedIn Update Guide: `scripts/build_linkedin_update.py`
- Tell Me About Yourself, question decoding, full answer scripts, five power questions, thank-you strategy: included inside interview outputs
- Customer success and failure/recovery stories: included inside interview story banks when supported
- Career Operating Manual: `scripts/build_general_advice.py`
- Job Search Analytics Report: `scripts/build_search_analytics.py`
- Post-interview debrief capture: `scripts/post_interview_debrief.py`
- Application tracker maintenance: `scripts/track_applications.py`

In-progress outputs exist partially inside scripts but are not standalone unless explicitly implemented. Planned outputs have no current script and should not be described as available.

## Resume Selection

Use the Implementation resume by default.

Use the Pre-Sales / CSM resume only when the job clearly focuses on demos, discovery, solution consulting, revenue retention, expansion, or account growth.

If unsure, use Implementation.

## Fit Classification

Before final output, classify fit as:

- Strong Fit
- Adjacent Fit
- Stretch Fit
- Poor Fit

Base the classification on direct evidence, adjacent evidence, unsupported requirements, seniority, leadership expectations, and specialty depth.

Unsupported requirements must not be claimed. When tailoring needs human review, generated resume filenames may include `FAIL`. When the role appears strategically weak, filenames may include `POOR`.

For application checklist and tracker reviews, prefer the matching tailored resume output when one exists. If no tailored output exists yet, source-resume fallback should be treated as advisory pre-build alignment rather than a final-output fit audit.
