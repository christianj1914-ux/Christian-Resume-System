# Christian Estrada Resume Automation

This project generates Christian Estrada's tailored resume, cover letter, interview, and debrief outputs.

## Core Contract

Every run follows the same four layers:

1. Knowledge Base: `AGENTS.md`, approved source resumes, approved federal source JSON, approved appendices, and any user-supplied notes allowed by the workflow.
2. User Input: one active target posting, one target company, one target role, requested outputs, and any active application questions in `jobs/application_questions.txt`.
3. Processing: lane detection, evidence mapping, keyword audit, employer-context lens, unsupported-claim audit, and output-specific quality checks.
4. Output: polished Word-only documents plus plain-language build feedback saved to `/output`.

Use `python tasks.py` as the canonical command surface. For the live command inventory and architecture references, use [SYSTEM_REFERENCE.md](SYSTEM_REFERENCE.md) and [ARCHITECTURE_MAP.md](ARCHITECTURE_MAP.md).

## Invariant Rules

- Create polished Word documents only. Do not create PDFs.
- Use only one active commercial posting in `jobs/job_description.txt` at a time.
- Use only one active federal posting or questionnaire set in `jobs/federal_job_description.txt` at a time.
- Never use LinkedIn page content as source material.
- Never use old outputs as source material.
- Never invent content, placeholder content, unsupported metrics, or unsupported ownership.
- Keep Christian's LinkedIn URL visible in the contact line as plain text only. Do not add an external Word hyperlink relationship for it.
- For multi-file coding changes, start with the narrowest safe upstream dependency, prefer reuse and deletion over new layers, validate each boundary before moving downstream, and choose the lowest-token path that preserves correctness.

## Source Of Truth

Commercial resume workflow may use only:

- `source/Estrada_Resume_Implementation.docx`
- `source/Estrada_Resume_PreSales_CSM.docx`
- `source/Christian_Estrada_KPMG_Final_Tightened_EdFix.docx`

Federal workflow may use only:

- `source/Christian_Estrada_Federal_Source.json`
- `source/Christian_Estrada_Federal_Standard_Essays.json`

The commercial source resumes are evidence banks, not submission-ready resumes. They should stay longer than the final two-page output and preserve supported depth, including company context paragraphs, the broader Core Competencies inventory, bridge evidence, and roughly 8-10 bullets per role where supported.

## Resume Selection

- Use the Implementation resume by default.
- Use the Pre-Sales resume only when the posting clearly centers on demos, discovery, solution consulting, revenue retention, expansion, or account growth.
- If unclear, use the Implementation resume.

## Formatting Contract

Use `source/Christian_Estrada_KPMG_Final_Tightened_EdFix.docx` as the visual formatting base.

Generated commercial resumes must match that file's margins, spacing, font sizing, line density, role spacing, bullet spacing, Skills format, and Education spacing.

Commercial resumes must fit exactly two pages. Do not allow Word default spacing, 1.15 line spacing, expanded paragraph spacing, or avoidable whitespace to push the file beyond two pages.

## Company Context Rule

If a source role includes a company context paragraph immediately after the company line and before the role summary:

- preserve it in the generated resume
- do not merge it into the role summary
- do not overwrite it during tailoring
- do not remove it unless Christian explicitly asks

## Tailoring Boundaries

Before writing, determine:

- target lane
- employer type and business context
- core problem being solved
- expected audience and success measures
- direct, adjacent, transferable, and unsupported evidence

Use direct evidence most strongly in the Professional Summary, strongest role summaries, first 1-2 bullets under the best-matching roles, Skills section, and cover-letter proof.

Reserve adjacent or transferable evidence for truthful bridge language. Do not claim unsupported requirements; allow normal `FAIL` or `POOR` handling instead of stretching the record.

Strictly preserve:

- job titles
- role order
- Education
- Professional Development

Allowed tailoring moves:

- reorder bullets
- select the strongest role-relevant bullets
- rename Core Competencies categories without changing the underlying truth
- add supported simple competencies when the JD triggers them
- remove clearly irrelevant competencies
- rewrite summaries and bullets for ATS fit without changing factual meaning

## Summary And Top Third

The Professional Summary must:

- stay between 50 and 110 words
- default to 3 recruiter-friendly sentences
- read like supported proof, not a generic brand statement
- surface scale, scope, business context, metrics, or outcomes quickly
- sound natural and human
- answer what changed because Christian was there

The top third must pass a six-second skim:

- clear role lane
- proof of similar work
- scale or scope
- business problem
- measurable or concrete outcome

Use the strongest truthful ownership verb the source supports. Prefer `owned`, `led`, `was responsible for`, `coordinated`, then `supported`. Do not inflate authority.

## Validation

After editing `scripts/config/language_rules.py` or `scripts/config/job_profiles.py`:

- run `python scripts/smoke_test.py`
- confirm lane detection still passes before generating new outputs

After meaningful script changes:

- run the smoke suite

When changing command surfaces, command docs, or maturity labels:

- run `python tasks.py commands`
- confirm the live inventory matches the docs

When changing resume or interview logic:

- run `python tasks.py validate`
- run at least the most relevant output builder for the changed area

Use `scripts/post_interview_debrief.py` after interview updates so new interview intelligence flows into later prep.

## Final Reminder

The system should make Christian look more clearly qualified, more clearly ownership-forward, and more clearly matched to the employer's problem while staying source-truth-bound.

Use a rehearsed-foundation study method for interview prep: repeat the opening, core stories, and close until the structure is automatic, but do not memorize answers word-for-word.
