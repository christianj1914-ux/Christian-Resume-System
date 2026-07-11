# Script Index

This file gives Claude a function-level navigation map. It is not a substitute for the code. Use it to decide which script snippets Claude needs to inspect for a specific task.

## `scripts/build_resume.py`

Core tailored resume generator and final assembly layer. This is still one of the highest-risk scripts.

Main orchestration:

- `build_resume()`: end-to-end resume build, rewrite, validation, output naming, packing, and render check.
- `main()`: command-line entry point.
- `BuildResult`: result metadata for source resume, company, output path, audit status, notes, and structured readiness state.

`build_resume.py` still exposes many imported helpers on the module surface, but the direct definitions for job analysis now live in `scripts/resume_analysis.py` and the direct definitions for summary, rewrite, and competency logic now live in `scripts/resume_content.py`. When Claude needs the implementation, inspect the source file that owns the function rather than only the `build_resume.py` import surface.

Resume assembly and orchestration:

- `validate_inputs()`: verifies required input files and active job description.
- `build_resume()`: orchestrates content staging, provenance render, fit audit, output naming, and final write.
- `role_bullet_budget()`, `select_experience_bullets_for_two_page_resume()`: final bullet-count budgeting and selection.
- `reorder_bullets()`, `natural_top_bullet_score()`: role-relevant bullet ordering before final packing.
- `restore_mandatory_reorg_summaries()`: restores required reorganization lines after downstream edits.

Readiness, fit audit, and validation:

- `keyword_placement_audit()`: identifies whether top JD terms are missing, buried, or absent from early visibility.
- `aggressively_close_supported_keyword_gaps()`: auto-closes only source-supported missing role terms before final audit.
- `resume_readiness_report()`, `resume_readiness_for_output()`: shared downstream blocker contract for cover, checklist, and workflow consumers.
- `resume_gap_blocker_message()`: converts readiness blockers into human-readable workflow output.
- `alignment_score_report()`: pre-build alignment scoring for checklist and command-line audit paths.
- `hiring_manager_skim_issues()`, `final_fit_audit()`: final fit and top-third audit.
- `assert_professional_summary_length()`, `assert_resume_language_rules()`: summary-length and language-rule enforcement.
- `resume_snapshot()`, `validate_resume_integrity()`: preserve roles, summaries, competencies, Education, and Professional Development.

DOCX structure and formatting:

- `unpack_docx()`, `pack_docx()`, `pack_docx_with_page_fit()`: DOCX XML workflow.
- `copy_visual_parts()`, `apply_section_layout()`: KPMG visual base transfer.
- `force_document_font()`, `force_styles_font()`: Carlito enforcement.
- `force_paragraph_single_spacing()`, `force_style_single_spacing()`: spacing enforcement.
- `apply_dense_font_sizing()`, `apply_fit_font_sizing()`: page-fit font profiles.
- `apply_resume_alignment()`, `apply_resume_spacing_rhythm()`, `apply_core_competency_row_spacing()`: layout rhythm.
- `normalize_linkedin_hyperlink_targets()`: LinkedIn target normalization before final plain-text safety.
- `remove_linkedin_hyperlinks()` from `utils.py`: removes LinkedIn hyperlink XML and relationship entries.

## `scripts/resume_analysis.py`

Job-description analysis and targeting helpers that feed the commercial resume workflow.

Input and source selection:

- `choose_resume(job_description)`: selects Implementation vs. Pre-Sales / CSM source.
- `extract_output_name(job_description)`, `extract_company_name(job_description)`, `extract_job_title(job_description)`: derive company/title metadata.
- `clean_company_name()`, `clean_job_title()`, validation helpers: prevent bad output names.

Keyword and job analysis:

- `keyword_set()`, `audit_keywords()`, `keyword_hits()`: ATS/search term extraction and scoring.
- `jd_explicitly_requires_erp()`, `should_deemphasize_erp_for_role()`: ERP emphasis controls.
- `job_problem_profile()`: central role-lane and fit profile.
- `poor_fit_requirements()`, `fit_status()`: fit classification support.

Employer and story lenses:

- `employer_context_matches()`, `primary_employer_context()`: industry/company context.
- `story_lens_matches()`, `primary_story_lens()`: fit narrative selection.
- `visible_role_specialties()`, `visible_company_values()`, `visible_values_phrase()`: only visible role/company context.
- `detect_company_profile()`: company-specific profile detection.
- `is_consulting_job_description()`: consulting-role detection.

## `scripts/resume_content.py`

Commercial resume content generation, rewrite, and competency helpers.

Professional summary and role summaries:

- `build_problem_first_summary()`: builds the tailored Professional Summary.
- `rewrite_professional_summary_for_role()`: replaces source summary in the DOCX.
- `summary_positioning_sentence()`, `summary_job_poster_sentence()`, `role_fit_checklist()`: summary components.
- `consulting_story_summary()`: consulting-specific summary positioning.
- `optimized_role_summary()`, `optimize_role_summaries()`: role summary tailoring.
- `is_company_context_paragraph()`, `role_detail_paragraphs_after_company()`: preserve company context paragraphs.
- `append_reorg_sentence()`, `preserve_reorg_sentence_at_end()`: protect mandatory reorganization sentences inside rewritten summaries.

Bullet rewriting and selection:

- `rewrite_supported_text()`, `apply_supported_rewrites()`: supported phrase and bullet rewrites.
- `strengthen_outcome_framing()`, `apply_outcome_framing_rewrites()`: convert duty-only wording into outcome wording.
- `apply_consulting_story_rewrites()`, `apply_startup_operator_rewrites()`, `apply_value_story_rewrites()`: lane-specific rewrites.
- `merge_low_fit_bullets_before_delete()`, `clean_merged_role_bullets()`: merge weaker bullets before deletion.
- `bullet_is_condensable()`, `remove_condensable_role_bullets()`, `remove_global_low_fit_bullets()`: space management.

Core Competencies and content guardrails:

- `competency_label_rewrites()`, `rename_core_competency_categories()`: category renaming.
- `supported_simple_competencies()`, `add_simple_core_competencies()`: supported keyword additions.
- `irrelevant_competency_items()`, `remove_irrelevant_core_competencies()`: remove irrelevant items.
- `normalize_core_competency_capitalization()`, `format_core_competency_runs()`: visual and text normalization.
- `scrub_erp_language_for_non_erp_text()`, `assert_no_erp_language_for_non_erp_role()`, `rebalance_professional_summary_erp_mentions()`: prevent ERP overreach.

## `scripts/commercial_resume_model.py`

Provenance-bearing commercial content boundary.

- `build_content_model()`: maps staged summary, role summaries, and selected bullets back to the approved source and same-employer role.
- `with_composed_summaries()`: applies the professional-summary and role-summary composers to the model rather than Word XML.
- `validate_content_model()`: rejects missing or cross-employer provenance.
- `render_content_model()`: performs the authoritative content render before formatting-only passes.
- `write_manifest()`: writes a diagnostic JSON manifest under `scratch/provenance_models/`; the manifest is not source truth.

## `scripts/build_cover_letter.py`

Generates a tailored cover letter after a matching resume exists.

Main orchestration:

- `build_cover_letter()`: reads job description and generated resume, determines output name, builds and validates cover letter.
- `build_document()`: creates the Word document.
- `CoverLetterResult`: result metadata.

Inputs and resume dependency:

- `extract_role_title()`, `clean_role_title()`: role title parsing.
- `find_resume_output()`: locates matching resume in `output/`.
- `visible_resume_text()`, `paragraph_texts()`: reads generated resume evidence.

Evidence and opening logic:

- `evidence_bullets()`, `selected_evidence_items()`, `selected_evidence_items_ordered()`: select proof from generated resume.
- `EvidenceBullet`: cover letter evidence unit.
- `_select_opening_pattern()`: chooses opening style.
- `_situation_opening()`, `_tension_opening()`, `_belief_opening()`, `_direct_opening()`, `_mission_opening()`, `_pyramid_opening()`: opening paragraph variants.
- `opening_method_paragraph()`, `proof_paragraph()`, `learning_paragraph()`, `anticipated_fit_bridge()`, `closing_paragraph()`: body content.

Role/company context:

- `is_consulting_context()`, `is_broad_operator_context()`, `is_early_stage_context()`: lane/context checks.
- `startup_stage_tension()`, `broad_operator_opening()`: startup/operator framing.
- `challenge_forecast_sentence()`, `company_context_sentence()`, `effective_lane_key()`: job-specific bridge language.

Formatting and validation:

- `set_default_style()`, `add_header()`, `add_paragraph()`, `add_run()`, `add_blank_line()`: DOCX formatting.
- `validate_cover_letter_specificity()`, `assert_cover_letter_qc()`, `validate_cover_letter_shape()`, `validate_cover_letter_text()`: quality checks.
- `write_cover_letter_trace()`: trace payload with chosen company fact, role fact, proof bullet, fallback use, and blocker reason.
- `smooth_cover_letter_text()`, `enforce_result_first_ordering()`: language cleanup.

## `scripts/build_interview_cheat_sheet.py`

Generates compact interview prep. It imports resume analysis from `build_resume.py`.

Main orchestration:

- `build_interview_cheat_sheet()`: end-to-end cheat sheet generation.
- `build_document()`: writes the DOCX.
- `CheatSheetResult`, `StoryCard`, `InterviewQuestion`, `PreparedAnswer`: core output structures.

Inputs and notes:

- `paragraph_texts()`: reads resume output.
- `note_lines()`, `supplied_company_background_lines()`, `supplied_smart_questions()`: user-supplied context extraction.
- `scrub_document_for_job_language()`: prevents non-role ERP spillover.

Company and role positioning:

- `adjusted_profile_for_role()`, `fit_label()`: fit and role profile.
- `interview_pitch_parts()`, `human_motivation_sentence()`, `pitch_variants()`: shared interview pitch and human-layer reuse from cover-letter logic.
- `pitch_for_profile()`, `sixty_second_pitch()`, `ninety_second_pitch()`, `why_role()`: spoken pitch ladder and role bridge.
- `company_context_lines()`, `company_background_lines()`, `personal_fit_lines()`: company/fit sections.
- `human_layer_reference_lines()`, `role_challenge_forecast()`, `first_90_day_approach()`: human-layer reminders and role strategy.
- `qualification_test_lines()`, `recruiter_three_stage_audit()`: gap and qualification checks.

Panel and format-specific prep:

- `detect_panel_context()`, `panel_composition_type()`, `panel_composition_strategy()`: panel detection.
- `add_panel_interview_section()`, `add_virtual_panel_adaptation_table()`: panel prep sections.

Stories and answers:

- `expanded_story_bank()`, `supported_story_bank()`, `hero_stories()`: story selection.
- `story_for_type()`, `story_theme_key()`, `story_specific_bridge()`, `story_human_connection_line()`: story matching and human-connection mapping.
- `caar_answer()`, `pyramid_answer()`, `uses_star_answer_framework()`: answer format.
- `common_interview_answers()`, `keyword_ready_answers()`, `behavioral_answer_scripts()`: prepared answers.
- `questions_to_ask()`, `closing_language()`, `thank_you_email_template_lines()`: interviewer questions and follow-up.

Validation:

- `assert_cheat_sheet_qc()`, `validate_text()`: document quality and prohibited-language checks.
- warn-only prose checks now run on pitch and story-answer sections through `utils.enforce_prose_quality()`.

## `scripts/build_detailed_interview_guide.py`

Generates the full interview guide. It builds on `build_resume.py` and `build_interview_cheat_sheet.py`.

Main orchestration:

- `build_detailed_interview_guide()`: end-to-end detailed guide generation.
- `build_document()`: writes the full guide.
- `DetailedGuideResult`, `PrepInsights`: result and insight structures.

Company research and notes:

- `relevant_company_research()`, `context_mentions_company()`: filter company research.
- `notes_context()`, `verified_company_research_points()`: user-supplied notes.
- `build_prep_insights()`, `add_insight_brief()`, `add_pushback_section()`, `add_anticipated_question_section()`: deeper preparation logic.

Answer and story depth:

- `company_story_positioning()`, `detailed_pitch()`, `why_company_answer()`, `role_challenge_answer()`: deeper narrative sections.
- `human_pivot_paragraph()`, `build_extended_tmay_sections()`, `add_extended_tmay_section()`: extended TMAY and human-element structure.
- `story_quality_audit()`, `story_selection_decision_table()`: story evaluation.
- `important_resume_keywords()`, `best_story_for_keyword()`, `keyword_sample_answer()`, `add_keyword_question_bank()`: keyword-to-answer mapping.
- `story_sample_answer()`, `behavioral_sample_answers()`, `add_story_page()`: full answer scripts with human-layer phrasing.

Advanced prep sections:

- `add_company_fit_answer_bank()`, `add_reflection_prompt_bank()`: answer bank and prompts.
- `add_final_round_strategy_section()`, `value_validation_project_ideas()`: final-round strategy.
- `add_hidden_assessment_section()`, `add_general_answer_operating_system()`: interviewer evaluation lens.
- `add_thank_you_strategy_section()`: follow-up strategy.

Validation and formatting:

- `set_default_style()`, `add_title()`, `add_section()`, `add_subsection()`, `add_body()`, `add_bullet()`: DOCX structure.
- `validate_text()`, `scrub_document_for_job_language()`: text checks.
- warn-only prose checks now run on pitch and story-answer sections through `utils.enforce_prose_quality()`.

## `scripts/run_resume_workflow.py`

Runs the generation workflow with recovery and DOCX repair.

- `run_step()`, `run_with_recovery()`: execute generation scripts.
- `failure_kind()`, `explain_unresolved()`, `print_failure_summary()`: readable recovery messages.
- dry-run readiness now reports structured resume gap blockers when an existing tailored resume would stop the cover-letter step.
- `generated_docx_paths()`: finds generated documents from script output.
- `repair_docx_open_issues()`, `repair_generated_docx_outputs()`: post-process generated DOCX files with `utils.remove_linkedin_hyperlinks()` to avoid LinkedIn hyperlink relationship issues.
- auto-tracker call near the end of `main()`: records the active job in `scratch/applications.csv` after a successful workflow run.
- `write_log()`: stores run logs in `scratch/run_logs`.

## `scripts/build_application_checklist.py`

Builds a one-page application-readiness document for the active job.

Main orchestration:

- `build_application_checklist()`: validates inputs, resolves the analysis resume, builds the document, and writes the checklist DOCX.

Resume basis and fit snapshot:

- `latest_tailored_resume()`: finds the newest matching generated resume output.
- `analysis_resume_path()`: prefers the matching tailored resume output, with source-resume fallback only when needed.
- `analysis_basis_label()`: labels whether the checklist is reading a tailored output or a source-resume fallback.
- checklist narrative sections use warn-only prose checks, and tailored-output reads can show structured resume gap blockers.
- `fit_classification()`: runs final-output fit audit against a tailored resume output.
- `fit_snapshot_status()`: uses final-output fit audit for tailored outputs and pre-build alignment grade for source-resume fallback.

Checklist content:

- `top_keywords()`, `keyword_status()`: checklist keyword coverage.
- `lead_story_line()`: selects the strongest interview story lead.
- `add_business_context_readiness()`: business model, risk, and question prompts.
- `find_debrief_entries_for_company()`, `add_previous_round_intelligence()`: carries forward prior debrief context when available.

## `scripts/track_applications.py`

Maintains `scratch/applications.csv` and tracker-derived status views.

Tracker model and matching:

- `COLUMNS`: canonical tracker schema, including separate `lane_label` and `fit_status` fields.
- `latest_resume()`: finds the newest matching generated resume output for the active job.
- `row_job_description_text()`: resolves the matching current or archived job description for a tracker row.
- `canonicalize_row()`, `tracker_lane_label()`, `tracker_fit_status()`: normalize and safely read tracker rows.

Row creation and refresh:

- `row_for_active_job()`: builds the active-job tracker row and prefers the tailored resume output for fit analysis when available.
- `active_job_fit_status()`: derives fit grade from the resume text used for tracker analysis.
- `refresh_row_metadata()`, `refresh_metadata()`: backfill lane and fit safely from current or archived job descriptions.
- `upsert_application()`, `add_row()`, `update_row()`: create or update tracker rows.

Views:

- `list_rows()`: prints row-level tracker view.
- `report_rows()`: prints status, lane, and fit breakdowns.

## `scripts/build_jd_library.py`

Archives job descriptions for later tracker refresh and pattern review.

- `archive_current()`: stores the active job description in `scratch/jd_library/`.
- `pattern_summary()`: summarizes lane and keyword recurrence across archived job descriptions.

## `scripts/build_search_analytics.py`

Builds a tracker-based job-search analytics report.

- `build_report()`: reads tracker rows, uses `track_applications.tracker_lane_label()` and `track_applications.tracker_fit_status()`, and writes the analytics DOCX.

## `scripts/build_general_advice.py`

Builds the standing career operating manual with active-job and tracker context.

- `add_active_job_context()`: summarizes active-job lane, problem, keywords, and lead story.
- `add_current_search_performance()`: summarizes tracker counts and uses tracker lane helpers rather than raw CSV assumptions.

## `scripts/build_claude_review_packet.py`

Builds a ready-to-upload broad Claude review packet from the live codebase.

- `build_packet()`: assembles review scope, current command output, tracker/JD summaries, packet self-audit warnings, and curated code excerpts into `TEMP_FOR_REVIEW.md`.
- packet mode registry: chooses between broad, tracker, checklist, resume, cover, interview, and workflow excerpt sets.
- `extract_function_source()`, `trim_source()`, `excerpt_block()`: keep packet excerpts aligned with current live functions instead of stale pasted snippets.
- `command_section()`: captures current `validate`, `integration-test`, and `track-report` summaries for the packet.

## `scripts/build_claude_prompt.py`

Builds the prompt text that pairs with a Claude packet mode.

- `build_prompt()`: loads the correct prompt template, fills in packet-mode placeholders, and prints a ready-to-paste Claude prompt.
- `read_prompt_template()`: extracts the prompt block from the template markdown file.
- `parse_args()`: supports the `review` and `plan` prompt modes plus optional focus text.

## `scripts/post_interview_debrief.py`

Captures post-interview intelligence without AI generation.

- `collect_debrief()`: prompts for structured debrief fields.
- `build_debrief_entry()`: formats chronological history entry.
- `build_company_research_note()`: formats company-specific note.
- `append_text()`: appends to jobs context files.
- `update_tracker_from_debrief()`: updates the matching tracker row from debrief status and round details when possible.
- `main()`: writes `jobs/debrief_history.txt` and optionally `jobs/company_research.txt`.

## `scripts/render_checks.py`

Visual QA helper for DOCX output.

- `render_docx()`: renders a DOCX into page images.
- `latest_output_docx()`: selects recent output documents.
- `find_render_docx_script()`: locates renderer.

## `scripts/smoke_test.py`

Validation-only script. It is safe to run without a live job description in `jobs/job_description.txt`.

- `import_major_scripts()`: imports major scripts without executing their command-line entry points.
- `test_validate_inputs()`: exercises `build_resume.validate_inputs()` with a known-good dummy job description string.
- `test_choose_resume()`: verifies Pre-Sales and Implementation source-resume selection.
- `test_lane_profiles_and_summaries()`: checks every targeting lane, summary length, first-person rules, double-dash rules, and banned AI-writing-word rules.
- tracker and checklist regression tests: verify tailored-resume preference, source-fallback grading, and tracker metadata refresh behavior.
- `main()`: prints a pass/fail summary and exits nonzero on failures.

Run this after any config change or script modification, especially after changes to lane detection, prohibited language, or competency item behavior.

## `scripts/config/language_rules.py`

Stores prohibited or risky language patterns used by validation logic. Inspect this when changing forbidden wording, subjective-claim rules, first-person rules, prompt-leak detection, duty-only opener handling, vague soft-skill behavior, or AI-writing-word checks.

- `CLICHE_PATTERNS`: detects generic cliches in resume text.
- `AI_WRITING_PATTERNS`: detects banned AI-writing words.
- `PLACEHOLDER_PATTERNS`: detects template artifacts.
- `FIRST_PERSON_PATTERNS`: detects first-person pronouns.
- `DUTY_ONLY_OPENERS`: detects bullets that start like responsibilities.
- `GENERIC_SOFT_KEYWORDS`: lists soft-skill terms too vague for ATS.
- `SUBJECTIVE_JOB_AD_PATTERNS`: detects claim language copied from job ads without proof.
- `PROMPT_LEAK_PATTERNS`: detects tailoring signposting phrases.
- `ACRONYM_TEXT_REPLACEMENTS`: maps known acronym variants to canonical form.

After editing this file, run `scripts/smoke_test.py` and verify all lane detection assertions pass before running a full resume build.

## `scripts/config/job_profiles.py`

Stores role-lane and job-profile configuration. Inspect this when changing role detection, lane names, bridge evidence, recurring competencies, competency removals, cover-letter lessons, story lenses, employer contexts, or employer/problem profiles.

- `TARGETING_LANES`: list of role lanes the system can classify into.
- `BRIDGE_EVIDENCE_AREAS`: maps job-description signals to resume evidence areas for fit scoring.
- `UNSUPPORTED_REQUIREMENT_PATTERNS`: flags requirements the resume cannot support.
- `POOR_FIT_REQUIREMENT_AREAS`: flags structural poor-fit signals.
- `STORY_LENSES`: maps industry or mission context to narrative framing.
- `EMPLOYER_CONTEXTS`: maps company type signals to positioning language.
- `SIMPLE_COMPETENCY_KEYWORDS`: skills to add to Core Competencies when triggered.
- `CONDITIONAL_COMPETENCY_ITEMS`: competency items to remove when their triggering job signals are absent.

After editing this file, run `scripts/smoke_test.py` and verify all lane detection assertions pass before running a full resume build.

Do not add a new targeting lane to `TARGETING_LANES` without also adding at minimum one entry each in `BRIDGE_EVIDENCE_AREAS` and an interview cheat sheet `questions_to_ask` lane case in `build_interview_cheat_sheet.py`.

## `scripts/modules/employer_playbooks/state_farm.py`

State Farm-specific detailed interview workbook logic.

Key areas:

- State Farm context detection and workbook eligibility.
- State Farm role deconstruction, positioning, story workbook, data exercise, panel prep, video prep, mock dialogue, questions bank, and practice plan.
- `add_state_farm_full_workbook()`: main employer-specific workbook insertion.
- `validate_state_farm_workbook_text()`: State Farm-specific validation.
