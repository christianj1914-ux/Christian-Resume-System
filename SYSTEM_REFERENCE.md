# Christian Resume System Reference

This file holds the fuller command and output inventory so `AGENTS.md` can stay compact and cheap to load.

## Command Surface

Use `python tasks.py` as the canonical entrypoint.

Production-safe commands:

- `resume`
- `federal-resume`
- `cover`
- `qualifications`
- `checklist`
- `thank-you`
- `interview`
- `guide`
- `linkedin`
- `advice`
- `debrief`
- `validate`
- `integration-test`
- `jd-check`
- `business-context-check`
- `align`
- `application-status`
- `track`
- `track-list`
- `track-report`
- `reset-jobs`
- `list-archives`
- `debrief-patterns`
- `clean-renders`
- `keyword-corpus --corpus recent|legacy20|outputs`
- `fresh-keyword-corpus --corpus recent|legacy20 --batch-dir <isolated-path>`
- `balanced-promotion-report --recent-csv <path> --legacy-csv <path> --output-dir <path>`

Review-heavy commands:

- `cover-long`
- `followup`
- `interview-followup`
- `post-round`
- `linkedin-calendar`
- `outreach`
- `plan`
- `salary-guide`
- `internal-interview`
- `monthly-review`
- `skills-gap`
- `weekly-plan`
- `assess`
- `trajectory`
- `story-audit`
- `interview-review`
- `self-inventory`
- `daily-prep`
- `career-plan`

Run `python tasks.py commands` for the live inventory, maturity labels, and script targets.

Commercial resume keyword policy:

- `--keyword-policy balanced` is the production default; it blocks supported-but-unwritten core
  terms and warns on breadth.
- `--keyword-policy advisory` reports all supported misses without blocking dependent documents.
- `--keyword-policy exhaustive` blocks supported core and breadth misses.
- Fit status and Tailoring status are separate. Tailoring never appears in filenames; the existing
  `BRIDGE`, `FAIL`, and `POOR` Fit suffix contract remains unchanged.
- Use `python tasks.py keyword-corpus --corpus recent` and `--corpus legacy20` for classifier
  calibration. Add `--ownership-only` for the lightweight corrected skim-zone measurement; use
  `--corpus outputs --ownership-only` to audit all commercial resume outputs.
- Core coverage admits only validated requirement concepts. Validated competencies and domain terms
  remain visible in breadth but cannot block balanced policy.
- Role-noun classification distinguishes assigned roles from counterpart roles. Explicit OR-lists
  are scored as one requirement family, with a separate assigned occurrence taking precedence.
- Balanced blocking requires an assigned, validated requirement with direct approved evidence;
  adjacent evidence, domain terms, and unsupported gaps remain non-blocking Fit diagnostics.
- The final packaged DOCX is the audit authority. Resume Notes are written only after the saved
  document is re-read and its Fit, Tailoring, coverage, alignment, ownership, gap, prose, and policy
  snapshot matches the assembled state.
- Ownership auditing reads only the Professional Summary and first visible role opening (role
  summary plus first two bullets). PASS/REVIEW/FAIL are separate; only ownership FAIL lowers Fit.
- The authoritative corrected 2026-07-30 fresh-corpus run rebuilt 35/35 fixtures under pipeline
  fingerprint `5d77e61e5cb630bf039db37e82433c13bd192e36b64baf695da9c02af90af481`.
  All 35 packaged resumes passed audit equality and rendered at exactly two pages. Balanced-policy
  safety passed with zero false/non-requirement blockers. Three builds (8.6%) have genuine supported
  core blockers: Fisher Phillips `operational transformation`, Pragmatike `project management`, and
  Delta `digital transformation`. Advisory remains the centralized default pending a separately
  approved placement pass and/or policy change.
- The archived figure of 47 supported core misses is a historical upper bound only. Default-policy
  decisions must use an isolated fresh manifest, never archived output files.

## Output Families

Resume and application outputs:

- Tailored commercial resume
- Federal tailored resume
- Standard qualifications statement
- Federal qualifications statement
- Application checklist
- Resume audit notes for FAIL and POOR outputs
- LinkedIn update guide

Cover and communication outputs:

- concise cover letter
- long cover letter
- thank-you note
- follow-up email
- interview follow-up email

Interview outputs:

- standard interview cheat sheet
- per-JD interview scorecard inside the cheat sheet
- detailed interview guide
- provisional self-inventory one-pager
- daily prep plan with optional scratch progress log
- career operating plan linking target roles, safe gaps, Study tracks, daily prep, and review checkpoints
- post-round follow-up and next-round prep
- internal interview guide
- dedicated interview review document

Career strategy outputs:

- Career Operating Manual
- career operating plan
- first 90 days plan
- LinkedIn calendar
- networking outreach templates
- salary guide
- weekly plan
- monthly review
- skills-gap analysis
- assessment and trajectory templates

## Debrief Storage Model

Interview intelligence lives in three layers:

1. structured round records in `jobs/interview_debriefs/`
2. human-readable company dossiers in `jobs/company_notes/`
3. legacy compatibility text in `jobs/debrief_history.txt` and `jobs/company_research.txt`

Structured round records should store compact parsed sections and file references. Large imported reviews should live in appendices, not inline in the default JSON body.

## Debrief Workflow

Use `scripts/post_interview_debrief.py` to:

- capture a new round
- prepare a company dossier
- repair legacy debrief files into structured records
- list or search prior debriefs

After capture, the debrief feedback loop writes advisory `scratch/prep_focus.json`
and `scratch/inventory_candidates.json`. These files bias the next daily prep
plan and queue possible self-inventory updates for human review only; capture
must never auto-edit `source/self_inventory.json`.

Normal next step after a debrief:

- rebuild the interview review, daily prep plan, cheat sheet, or guide for the same company

## Architecture Pointers

See [.context/ARCHITECTURE_MAP.md](.context/ARCHITECTURE_MAP.md) for script ownership and pipeline boundaries.
