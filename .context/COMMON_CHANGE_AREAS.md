# Common Change Areas

Use this file to decide what code Claude must inspect before giving advice. Start with the smallest relevant packet, then run the matching prompt:

- generate the packet with `python tasks.py claude-packet --mode ...`
- run the review prompt with `python tasks.py claude-prompt review --packet-mode ...`
- run the plan prompt with `python tasks.py claude-prompt plan --packet-mode ...`

## Resume Source Selection

Inspect:

- `scripts/build_resume.py`: `validate_inputs()`
- `scripts/resume_analysis.py`: `choose_resume()`, `extract_job_title()`, `extract_company_name()`, `extract_output_name()`
- `.context/RULES_FOR_CLAUDE.md`: source resume boundaries

Common risks:

- selecting Pre-Sales / CSM too broadly
- mixing multiple job postings
- bad company or title extraction
- using old outputs as source truth

## Config File Changes

Inspect:

- `scripts/config/language_rules.py`: language guardrails, prohibited wording, first-person detection, placeholder detection, duty-only openers, soft-skill terms, prompt leaks, and acronym normalization
- `scripts/config/job_profiles.py`: targeting lanes, bridge evidence, unsupported and poor-fit requirement patterns, story lenses, employer contexts, simple competency triggers, and conditional competency removals
- `scripts/build_resume.py`: `validate_config_integrity()`, `assert_resume_language_rules()`
- `scripts/resume_analysis.py`: `job_problem_profile()`
- `scripts/resume_content.py`: `build_problem_first_summary()`, `supported_simple_competencies()`, `irrelevant_competency_items()`
- `scripts/build_interview_cheat_sheet.py`: `questions_to_ask()` when lane detection or new lane behavior is involved
- `scripts/smoke_test.py`: run before giving final advice or before a full resume build

Common risks:

- changing lane detection without updating bridge evidence
- adding a new lane without interview cheat sheet questions-to-ask behavior
- weakening prohibited-language rules across resume, cover letter, and interview outputs
- adding vague soft skills as ATS terms
- adding or removing competency items without trigger/removal logic
- advising on lane detection, prohibited language, or competency item behavior without inspecting both config files

Validation packet:

- Inspect both config files before giving advice on lane detection, prohibited language, or competency item behavior.
- After any config edit, run `scripts/smoke_test.py` and verify all lane detection assertions pass.

## Professional Summary Quality

Inspect:

- `scripts/resume_content.py`: `build_problem_first_summary()`, `summary_positioning_sentence()`, `summary_job_poster_sentence()`, `role_fit_checklist()`, `rewrite_professional_summary_for_role()`
- `scripts/build_resume.py`: `assert_professional_summary_length()`
- `scripts/config/job_profiles.py` if lane/profile behavior is involved

Common risks:

- summary under 75 words or over 140 words
- generic recruiter language without proof
<!-- CLAUDE_REVIEW:COMMON_SUMMARY_RISKS:START -->
<!-- CLAUDE_REVIEW:COMMON_SUMMARY_RISKS:END -->
- prompt-like phrases
- unsupported keywords
- too much ERP emphasis for non-ERP roles
- opening sentence with stacked clauses

## Role Summary Changes

Inspect:

- `scripts/resume_content.py`: `optimized_role_summary()`, `optimize_role_summaries()`, `is_company_context_paragraph()`, `role_detail_paragraphs_after_company()`, `preserve_reorg_sentence_at_end()`
- `scripts/build_resume.py`: `restore_mandatory_reorg_summaries()`

Common risks:

- deleting company context paragraphs
- removing mandatory reorganization sentences
- changing role meaning or scope
- inventing leadership or specialty ownership

## Bullet Rewriting

Inspect:

- `scripts/resume_content.py`: `rewrite_supported_text()`, `apply_supported_rewrites()`, `strengthen_outcome_framing()`, `apply_outcome_framing_rewrites()`, `apply_consulting_story_rewrites()`, `apply_startup_operator_rewrites()`, `apply_value_story_rewrites()`
- `scripts/config/language_rules.py` if prohibited wording is involved

Common risks:

- changing factual meaning
- adding unsupported metrics
- duty-only bullets surviving
- adding job-ad subjective claims as proof
- using forbidden AI-writing words

## Bullet Selection and Two-Page Fit

Inspect:

- `scripts/build_resume.py`: `role_bullet_budget()`, `select_experience_bullets_for_two_page_resume()`, `pack_docx_with_page_fit()`, `apply_fit_font_sizing()`
- `scripts/resume_content.py`: `bullet_is_condensable()`, `remove_condensable_role_bullets()`, `merge_low_fit_bullets_before_delete()`, `remove_global_low_fit_bullets()`

Common risks:

- deleting too much from a role
- losing strongest role-relevant evidence
<!-- CLAUDE_REVIEW:COMMON_BULLET_RISKS:START -->
<!-- CLAUDE_REVIEW:COMMON_BULLET_RISKS:END -->
- breaking the two-page rule
- shrinking body text below 10pt
- preserving irrelevant bullets while removing useful ones

<!-- CLAUDE_REVIEW:COMMON_FEDERAL_BLOCK:START -->
<!-- CLAUDE_REVIEW:COMMON_FEDERAL_BLOCK:END -->

## Core Competencies

Inspect:

- `scripts/resume_content.py`: `competency_label_rewrites()`, `rename_core_competency_categories()`, `supported_simple_competencies()`, `add_simple_core_competencies()`, `irrelevant_competency_items()`, `remove_irrelevant_core_competencies()`, `format_core_competency_runs()`
- `scripts/build_resume.py`: `assert_core_competency_run_format()`
- `scripts/config/job_profiles.py` if new lane terminology is needed

Common risks:

- adding unsupported skills
- removing relevant competencies
- over-capitalizing ordinary phrases
- breaking Core Competencies formatting

## ERP and Non-ERP Guardrails

Inspect:

- `scripts/resume_analysis.py`: `jd_explicitly_requires_erp()`, `should_deemphasize_erp_for_role()`
- `scripts/resume_content.py`: `scrub_erp_language_for_non_erp_text()`, `assert_no_erp_language_for_non_erp_role()`, `rebalance_professional_summary_erp_mentions()`
- `scripts/build_cover_letter.py`: places that call resume ERP guards
- interview scripts: `scrub_document_for_job_language()`

Common risks:

- making non-ERP roles sound ERP-heavy
- removing legitimate ERP proof for ERP roles
- attaching Aptean Intuitive to the wrong employer
- framing Epicor Kinetic as the primary owned ERP at East West

## Employer Context and Story Lens

Inspect:

- `scripts/resume_analysis.py`: `employer_context_matches()`, `primary_employer_context()`, `story_lens_matches()`, `primary_story_lens()`, `visible_role_specialties()`, `visible_company_values()`, `detect_company_profile()`, `employer_context_sentence()`
- `scripts/build_cover_letter.py`: `_select_opening_pattern()`, opening paragraph functions, `company_context_sentence()`, `challenge_forecast_sentence()`

Common risks:

- inventing company values or culture
- overfitting to a company name without visible JD support
- producing keyword matching instead of a fit narrative
- using company context where only job context is visible

## Fit Audit and FAIL/POOR Output Naming

Inspect:

- `scripts/resume_analysis.py`: `poor_fit_requirements()`, `job_problem_profile()`
- `scripts/build_resume.py`: `hiring_manager_skim_issues()`, `final_fit_audit()`, `build_resume()`
- `scripts/build_cover_letter.py`: `build_cover_letter()` if cover letter output naming follows resume audit status

Common risks:

- claiming unsupported requirements instead of flagging them
- missing formal leadership or specialty-depth gaps
- inconsistent `FAIL` or `POOR` naming across resume and cover letter

## DOCX Formatting and Visual Base

Inspect:

- `scripts/build_resume.py`: `copy_visual_parts()`, `apply_section_layout()`, `force_document_font()`, `force_styles_font()`, `apply_dense_font_sizing()`, `apply_fit_font_sizing()`, `apply_resume_spacing_rhythm()`, `apply_core_competency_row_spacing()`, `assert_document_font()`
- `scripts/render_checks.py`: `render_docx()`

Common risks:

- losing Carlito
- Word default spacing returning
- three-page resume output
- broken Core Competencies row spacing
- altered KPMG visual rhythm
<!-- CLAUDE_REVIEW:COMMON_RENDER_FALLBACK:START -->
<!-- CLAUDE_REVIEW:COMMON_RENDER_FALLBACK:END -->

## LinkedIn and DOCX Open-Error Repair

Inspect:

- `scripts/utils.py`: `remove_linkedin_hyperlinks()`
- `scripts/build_resume.py`: `normalize_linkedin_hyperlink_targets()` and the call to `remove_linkedin_hyperlinks()`
- `scripts/run_resume_workflow.py`: `repair_docx_open_issues()`, `repair_generated_docx_outputs()`

Common risks:

- reintroducing external LinkedIn hyperlink relationships
- Word file-format open errors
- changing visible contact text

## Cover Letter Content

Inspect:

- `scripts/build_cover_letter.py`: `selected_evidence_items()`, `selected_evidence_items_ordered()`, `_select_opening_pattern()`, `opening_method_paragraph()`, `proof_paragraph()`, `learning_paragraph()`, `anticipated_fit_bridge()`, `closing_paragraph()`, `validate_cover_letter_text()`
- `scripts/build_resume.py`: `resume_readiness_report()`, `resume_readiness_for_output()`, `resume_gap_blocker_message()`
- `scripts/resume_analysis.py`: `job_problem_profile()`, `primary_story_lens()`, `visible_role_specialties()`, `visible_values_phrase()`
- `scripts/utils.py`: `enforce_prose_quality()`
- `scripts/writing_eval.py`: artifact-specific prompt-leak, weak-close, list-density, and fallback-clause checks

Common risks:

- using cover letter to claim unsupported experience
- not matching the generated resume
- overly generic opening
- invented company culture or values
- cover letter generated before resume exists
<!-- CLAUDE_REVIEW:COMMON_COVER_RISKS:START -->
<!-- CLAUDE_REVIEW:COMMON_COVER_RISKS:END -->
- downstream sendable docs building even though the tailored resume still has role-defining blockers
- brittle fallback sentences stitching raw JD fragments into connector clauses

## Shared Writing Quality and Downstream Gating

Inspect:

- `scripts/utils.py`: `assert_no_template_leakage()`, `prose_quality_report()`, `enforce_prose_quality()`
- `scripts/writing_eval.py`: `ARTIFACT_CHOICES`, `evaluate_text()`, artifact-specific issue rules
- `scripts/build_resume.py`: `aggressively_close_supported_keyword_gaps()`, `resume_readiness_report()`, `resume_gap_summary_line()`
- sendable-doc builders: `scripts/build_cover_letter.py`, `scripts/build_thank_you.py`, `scripts/build_followup_email.py`, `scripts/build_interview_followup.py`, `scripts/build_post_round.py`
- warn-only prep builders: `scripts/build_interview_cheat_sheet.py`, `scripts/build_detailed_interview_guide.py`, `scripts/build_application_checklist.py`

Common risks:

- adding a new wording rule to only one output family
- treating prep warnings like blockers or letting sendable email copy silently pass with stale bridge phrasing
- global regexes becoming so broad they flag normal prose
- forcing unsupported finance, budget, EAC, or ETC language into downstream documents

## Application Checklist

Inspect:

- `scripts/build_application_checklist.py`: `analysis_resume_path()`, `analysis_basis_label()`, `fit_snapshot_status()`, `fit_classification()`, `top_keywords()`, `keyword_status()`, `lead_story_line()`, `add_previous_round_intelligence()`
- `scripts/build_resume.py`: `alignment_score_report()`, `final_fit_audit()`
- `scripts/resume_analysis.py`: `job_problem_profile()`

Common risks:

- grading the checklist against the source resume when a matching tailored output exists
- using final-output audit rules against a source-resume fallback
- stale keyword coverage or risks because the wrong resume text was analyzed
- carrying forward debrief context for the wrong company
- presenting old output as current evidence

## Application Tracker and Search Analytics

Inspect:

- `scripts/track_applications.py`: `latest_resume()`, `row_job_description_text()`, `row_for_active_job()`, `active_job_fit_status()`, `refresh_row_metadata()`, `tracker_lane_label()`, `tracker_fit_status()`, `upsert_application()`
- `scripts/build_jd_library.py`: `archive_current()`
- `scripts/build_search_analytics.py`: `build_report()`
- `scripts/build_general_advice.py`: `add_current_search_performance()`

Common risks:

- mixing `lane_label` and `fit_status`
- scoring fit from the source resume instead of the tailored output
- refreshing historical rows without a matching current or archived job description
- updating output paths while leaving tracker metadata stale
- analytics code reading raw tracker columns instead of tracker helper functions

## Interview Cheat Sheet

Inspect:

- `scripts/build_interview_cheat_sheet.py`: `build_document()`, `adjusted_profile_for_role()`, `interview_pitch_parts()`, `human_motivation_sentence()`, `pitch_variants()`, `pitch_for_profile()`, `sixty_second_pitch()`, `ninety_second_pitch()`, `story_human_connection_line()`, `role_challenge_forecast()`, `expanded_story_bank()`, `supported_story_bank()`, `hero_stories()`, `behavioral_answer_scripts()`, `questions_to_ask()`, `closing_language()`, `thank_you_email_template_lines()`
- `scripts/resume_analysis.py`: profile and employer/story lens functions

Common risks:

- interview prep making stronger claims than the resume supports
- shared cover-letter and interview pitch logic drifting apart
- invented human motivation or culture-fit language that is not grounded in notes or supported patterns
- stories selected without source support
- generic answers that do not map to the active role
- wrong story-to-human-layer mapping that makes longer answers feel canned or mismatched
- missing company/interview notes context

## Detailed Interview Guide

Inspect:

- `scripts/build_detailed_interview_guide.py`: `build_prep_insights()`, `verified_company_research_points()`, `company_story_positioning()`, `why_company_answer()`, `role_challenge_answer()`, `human_pivot_paragraph()`, `build_extended_tmay_sections()`, `add_extended_tmay_section()`, `story_quality_audit()`, `add_keyword_question_bank()`, `story_sample_answer()`, `add_final_round_strategy_section()`, `add_thank_you_strategy_section()`
- `scripts/build_interview_cheat_sheet.py`: shared story and answer logic

Common risks:

- treating unverified company research as fact
- overlong or repetitive prep docs
- extended TMAY sections drifting from the shorter pitch ladder or repeating the same proof with different wording
- human-element language landing too late in long answers to feel natural
- weak story-to-keyword mapping
- missing thank-you or closing strategy

## Employer-Specific Playbooks

Inspect:

- `scripts/modules/employer_playbooks/state_farm.py`
- `scripts/build_detailed_interview_guide.py` where playbooks are imported or called

Common risks:

- playbook firing for the wrong employer
- employer-specific language leaking into generic guides
- violating the same source-truth rules as general interview outputs

## Post-Interview Debrief

Inspect:

- `scripts/post_interview_debrief.py`: `collect_debrief()`, `build_debrief_entry()`, `build_company_research_note()`, `append_text()`

Common risks:

- overwriting rather than appending notes
- losing chronological debrief history
- adding company intelligence without `POST-INTERVIEW NOTE [date]:`

## Workflow Runner

Inspect:

- `scripts/run_resume_workflow.py`: `run_with_recovery()`, `failure_kind()`, `explain_unresolved()`, `repair_generated_docx_outputs()`

Common risks:

- hiding a generation failure
- failing to rebuild resume before cover letter
- missing user-friendly recovery guidance
- failing to repair generated DOCX files
