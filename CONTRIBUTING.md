# Contributing To The Resume System

This is the authoritative guide for extending the resume system with new targeting lanes, employer playbooks, or story bank entries. Keep changes narrow, supported by source-resume evidence, and validated before using them in a live build.

## Adding A New Targeting Lane

Touch files in this order so lane detection, resume quality checks, cover letters, and interview prep stay aligned:

1. Add the lane entry to `TARGETING_LANES` in `config/job_profiles.py`. The entry must include every required key: `key`, `label`, `problem`, `audience`, `outcomes`, and `signals`.
2. Add at least one matching entry to `BRIDGE_EVIDENCE_AREAS` in `config/job_profiles.py` so the new lane maps job terms to resume evidence terms.
3. Add lane-specific role terms to `hiring_manager_skim_issues` in `scripts/build_resume.py` so the Professional Summary skim check knows what language proves the lane.
4. Add a `career_through_line` entry for the lane in `scripts/build_interview_cheat_sheet.py`.
5. Add a `pitch_for_profile` proof sentence for the lane in `scripts/build_interview_cheat_sheet.py`.
6. Add lane-specific branches for interview and cover-letter positioning: `role_challenge_forecast` in `scripts/build_interview_cheat_sheet.py`, cover-letter role positioning logic in `scripts/build_cover_letter.py`, `closing_paragraph` in `scripts/build_cover_letter.py`, and the `lane_closes` dictionary inside that close.
7. Run `python scripts/smoke_test.py` and verify all lane detection assertions pass.
8. Run `python tasks.py check` against a sample job description for the new lane and verify the detected lane matches.

## Adding An Employer Playbook

Use `scripts/modules/employer_playbooks/state_farm.py` as the structural template. A playbook should keep employer-specific content out of the general resume, cover letter, and guide builders.

Required functions:

1. `is_<employer>_active(company_name, role_title, job_description, company_research="", interview_notes="") -> bool` for activation.
2. `<employer>_prep_insights() -> PrepInsights` when the employer needs custom situation reads, scorecard items, selling angles, pushbacks, anticipated questions, smart questions, or brevity rules.
3. `<employer>_story_bridge(card)` when story cards need employer-specific framing.
4. `<employer>_calibration_question(card)` when story cards need employer-specific follow-up questions.
5. `add_<employer>_...` document-section functions when the detailed guide needs custom workbook or prep sections.

Integration points:

1. In `scripts/build_detailed_interview_guide.py`, import the playbook and add it to the prep-insights dispatch path, plus any story bridge, calibration, or document-section calls needed for that employer.
2. In `scripts/build_cover_letter.py`, import the detector and any cover opening helper, then register it in `FIRM_PROFILE_REGISTRY` or the relevant firm-profile branch.
3. In `scripts/build_interview_cheat_sheet.py`, add company-specific callouts, questions, or role-strategy branches only when the cheat sheet needs employer-specific guidance separate from the detailed guide.

## Adding A Story Bank Entry

Story entries live as `StoryCard` objects in `scripts/build_interview_cheat_sheet.py`. Each card must include:

1. `title`: short story name used in interview prep sections.
2. `story_types`: one or more story categories, such as leadership, teamwork, resilience, influence, failure, or individual achievement.
3. `hook`: the concise situation or problem setup.
4. `takeaways`: exactly three takeaways the interviewer should remember.
5. `evidence`: the resume-supported proof behind the story.
6. `level3_trait`: the deeper operating trait the story demonstrates.
7. `result`: the measurable or observable result.
8. `outcome`: why the result mattered to the business, customer, workflow, or team.
9. `evidence_terms`: resume text gates for inclusion.
10. `signals`: job-description signals that make the story relevant to a lane or role context.

The `evidence_terms` requirement is strict: each term must appear in the generated resume text for the card to be included. This prevents interview prep from surfacing a story that the submitted resume does not support. Use terms that are stable in the generated resume, not fragile full-sentence matches.

The `signals` tuple drives role relevance. Add signals that match the job-description language likely to trigger the story for different lanes, such as implementation, customer success, discovery, adoption, analytics, reporting, process improvement, operations, consulting, or strategy.

## Validation Checklist

Application checklist intelligence now includes prior debrief entries when `jobs/debrief_history.txt` contains matching company history. Preserve the `POST-INTERVIEW DEBRIEF CAPTURED` delimiter and field labels written by `python tasks.py debrief`; the checklist parser depends on that capture format to identify company names, rounds, outcomes, follow-up stories, unexpected questions, and interviewer role language.

Use `python tasks.py reset-jobs --clear` when starting a new application so the active job description is archived and cleared without losing accumulated company research, interview notes, or debrief history. Use `python tasks.py reset-jobs --full-clear` only when starting an entirely new job search campaign where all four job context files should be archived and cleared.

Run these commands in order after any change:

1. `python scripts/smoke_test.py`
2. `python tasks.py integration-test`
3. `python tasks.py check`
4. `python tasks.py checklist`
5. `python tasks.py dry-run`
6. `python tasks.py resume`

Run both `python tasks.py validate` and `python tasks.py integration-test` before committing changes to any core script.

Use the checklist as the recommended first document step for a new job description because it summarizes lane detection, keyword coverage, evidence areas, lead story, cover approach, and fit risks before a full build. After the full resume build, review the render check output before using the generated document. Confirm the lane detection, source resume selection, keyword coverage, fit risks, page count, and visual formatting all match the intended role.
