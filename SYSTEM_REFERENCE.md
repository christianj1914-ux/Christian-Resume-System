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

See [ARCHITECTURE_MAP.md](ARCHITECTURE_MAP.md) for script ownership and pipeline boundaries.
