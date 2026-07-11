# Rules for Claude

This file condenses the highest-risk system rules. `AGENTS.md` remains canonical if there is a conflict.

## Absolute Rules

- Create polished Word documents only. Do not create PDFs as final outputs.
- Never use old outputs as source material.
- Never use LinkedIn page content as source material.
- Never invent content, claims, metrics, tools, platforms, responsibilities, company values, culture fit, or outcomes.
- Use one active job posting in `jobs/job_description.txt` at a time.
- Preserve job titles, role order, Education, and Professional Development.
- Keep Christian's LinkedIn URL visible in the resume contact line as plain text only. Do not create an external hyperlink relationship.
- Do not use double dashes anywhere in generated career documents.
- Do not use first-person pronouns anywhere in resumes.

## Source Resume Boundaries

Implementation resume is the default source.

Pre-Sales / CSM resume is used only when the job clearly focuses on demos, discovery, solution consulting, revenue retention, expansion, or account growth.

The KPMG file is the visual formatting base. Generated resumes should match its margins, spacing, font sizing, line density, role spacing, bullet spacing, Core Competencies format, and Education spacing.

## Resume Formatting Rules

- Font: Carlito everywhere.
- Margins: 0.5 inch.
- Body text: 10pt minimum.
- Section headers: at least 10.5pt and at least 0.5pt larger than body text.
- Name: 22pt.
- Final resume must fit exactly two pages.
- Do not allow Word default spacing, 1.15 line spacing, expanded paragraph spacing, or unnecessary whitespace.
- If expansion threatens page fit, improve content selection and condensation before reducing font size.
- Do not set body text below 10pt.
- Federal resume output stays at exactly two pages, and the federal qualifications statement is a separate Word document that should mirror supplemental federal questions or KSAs when they are present.


## Mandatory Reorganization Sentences

The East West Manufacturing summary must always retain:

`Position impacted by company reorganization.`

The Aptean summary must always retain:

`Position impacted by company reorganization.`

Prefer placing the sentence at the end of the role summary.

## Tailoring Process

Before writing, analyze:

- role lane
- employer core problem
- audience
- expected outcomes
- seniority level
- risk areas
- business context
- employer context lens
- story lens
- unsupported requirements

Map requirements as Direct, Adjacent, Transferable, or Unsupported.

Use Direct evidence strongly in the summary, job summaries, first bullets, Core Competencies, and cover letter. Use Adjacent evidence carefully with bridge language. Use Transferable evidence mostly in cover letters or limited summary context. Do not claim Unsupported requirements.
Standard private-sector resumes should follow the same no-assumptions mindset as federal resumes in the top third. Important experience should be explicit, not merely inferable.


## Config File Rules

`scripts/config/language_rules.py` controls shared language guardrails: generic cliche detection, banned AI-writing words, template artifacts, first-person pronouns, duty-only bullet openers, vague soft-skill terms, unsupported job-ad claim language, prompt-leak phrases, and acronym normalization.

`scripts/config/job_profiles.py` controls shared targeting behavior: role-lane classification, bridge evidence areas for fit scoring, unsupported and poor-fit requirement signals, story lenses, employer context positioning, simple Core Competencies additions, and conditional competency removals.

Edit these config files when the reusable rule itself needs to change across resume, cover letter, interview, or audit logic. Do not patch around a config behavior in one script if the same rule should apply system-wide.

After editing either config file, run `scripts/smoke_test.py` and verify all lane detection assertions pass before running a full resume build.

Do not add a new targeting lane to `TARGETING_LANES` without also adding at minimum one entry each in `BRIDGE_EVIDENCE_AREAS` and an interview cheat sheet `questions_to_ask` lane case in `build_interview_cheat_sheet.py`.

## Tracker and Checklist Rules

- `scratch/applications.csv` stores `lane_label` and `fit_status` as separate fields. Do not treat them as interchangeable.
- `DRAFT` is a live commercial output-state suffix for draft-generated files. Keep it documented as a filename/output-state contract, not as a replacement for the main audit enum.
- For tracker and application checklist fit review, prefer the matching tailored resume output when one exists.
- If no tailored resume exists yet, source-resume fallback should be treated as pre-build alignment only, not as a final-output fit audit.
- Safe tracker backfill depends on a matching current or archived job description. Do not infer missing historical fit data without that match.

## Interview Prep Philosophy

- Build a rehearsed foundation, not brittle word-for-word delivery.
- Prefer full spoken practice answers plus anchor facts and adaptation drills over framework-only fragments.
- Keep Tell Me About Yourself, pitch variants, and story answers claim-first: answer first, proof second, bridge third.
- When updating interview outputs, change the shared answer logic rather than patching only one generated guide.

## Professional Summary Rules

The Professional Summary must:

- be 70 to 110 words
- be recruiter-friendly
- usually use three sentences
- prioritize the job's core problems first
- include relevant keywords naturally when supported
- show concrete outcomes, measurable scope, or proof of change
- answer "What happened because Christian was there?"
- avoid prompt-like phrases such as "relevant to this role," "tailored to this role," "target role," or "this job description"
- not start any sentence with "That"
- avoid stale endings such as "not just activity"
- make higher-level private-sector leadership, ownership, executive audience, and decision-making scope explicit when the source supports them


The opening sentence should use one clean problem clause and read like direct human positioning for the target lane, such as implementation consultant, solutions consultant, customer success consultant, analytics consultant, or change adoption consultant.

## Bullet Rules

Bullets should answer "What happened because Christian was there?"

Prefer concrete outcomes, measurable impact, supported proof, and business context over duty descriptions. When a bullet starts like a responsibility, revise toward what Christian delivered, improved, reduced, stabilized, enabled, accelerated, protected, built, or launched.

Keep the factual meaning, outcome, scope, metric, employer, and role intact. Reorder and select bullets as needed for relevance and two-page fit.
Protect bridge-hard bullets that carry explicit AI usage, technical scoping, testing, delivery ownership, executive advisory, or leadership scope when the target role depends on those areas.


## Supported Experience Boundaries

Home Depot supports LivePerson LiveEngage online chat and text messaging workflows, automated greeting and closing scripts, SMS pilot support, customer interaction trend monitoring, conversational AI, chatbot configuration, and NLP-based messaging workflow language when the job description calls for those areas.

East West Manufacturing supports Aptean Intuitive ownership as the primary mission-critical ERP platform across five sites and 150+ users, Aptean Intuitive administration and continuous improvement, Aptean Intuitive to Epicor Kinetic ERP migration support through final cutover, ETL and data transformation, SQL-based validation, ERP/database extraction, querying, updating, cutover coordination, technical program ownership, and cross-functional ERP leadership. Do not frame Epicor Kinetic as the primary owned ERP at East West.

Aptean supports Encompix implementation, configuration, data migration, integration, testing, go-live, post-go-live support, pre-sales discovery, requirements definition, SOWs, functional requirements documents, portfolio ownership, account health, adoption, executive business reviews, QBRs, renewal risk management, churn-risk mitigation, expansion discovery, account growth conversations, value realization, customer enablement, and at-risk account recovery. Do not tie Aptean Intuitive to the Aptean Customer Success role.

For Customer Success Manager roles, Christian may be framed as commercially aware and post-sale revenue-adjacent. Do not invent direct quota ownership, exact NRR attainment, GRR attainment, or closed expansion dollars.

## Forbidden Language and Claims

Avoid generic cliches such as:

- dedicated
- results-driven
- detail-oriented
- self-starter
- hard-working
- team player

Avoid unsupported subjective claims as standalone proof, such as:

- strong in strategy
- excellent communication
- creative problem-solver
- resourceful
- proactive
- highly organized
- excels in ambiguity

Avoid AI-writing words such as:

- spearheaded
- pioneered
- championed
- meticulously
- robust
- leveraged extensively

Do not claim ownership of culture transformation, values activation, People strategy, enterprise AI strategy, operating model transformation, leadership transitions, direct people leadership, advanced API authentication, endpoint configuration, JWT/tokens, HR policy ownership, legal compliance ownership, DEI governance, or enterprise AI ethics ownership unless the source resume is explicitly updated to support the exact claim.

## Claude Output Rules

Claude should keep outputs concise and implementation-ready.

When planning, provide logic maps, affected files, data flow, validation checks, and edge cases.

When reviewing, do not rewrite whole files. Provide exact issues, why each issue matters, affected lines or functions, and precise replacement snippets or instructions for Codex.

If document-render warnings appear, separate content or logic defects from environmental render limitations. Missing local DOCX-to-image tooling should not be treated as a resume-writing failure.

If you recommend a new status, command, enum, packet mode, or public contract that does not exist today, label it as a proposal and name the consumers that would need propagation before treating it as live behavior.
