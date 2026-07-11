# Christian Resume System Changelog

## How To Use This File

When feeding a new improvement prompt to Codex, add the entry to this changelog in the same session so the record stays current. Use the `YYYY-MM-DD` placeholder until Christian fills in the actual completion date.

## Improvement Series

### 2026-06-11 - Hardened explicit-proof tailoring across standard and federal workflows

Files changed: `scripts/build_resume.py`, `scripts/resume_content.py`, `scripts/build_cover_letter.py`, `scripts/build_interview_cheat_sheet.py`, `scripts/build_federal_resume.py`, `scripts/resume_analysis.py`, `scripts/render_checks.py`, `scripts/smoke_test.py`, `Claude Review/CLAUDE.md`, `Claude Review/RESUME_SYSTEM_BRIEF.md`, `Claude Review/RULES_FOR_CLAUDE.md`, `Claude Review/COMMON_CHANGE_AREAS.md`, `CHANGELOG.md`

Why: Standard resume outputs were still leaving too much leadership, implementation, and AI-adjacent fit implicit for higher-level private-sector roles, the Procore path had lingering audit and specificity issues even after the major cover-letter fix, federal AI phrasing still had awkward stitched summary text, and successful builds were printing noisy render stack traces when the local visual-render converter was unavailable.

What changed: Added stronger bridge-hard and explicit-proof logic to standard resume bullet ranking and top-third audit behavior, protected leadership/AI/scoping/testing bullets from low-fit trimming, tightened implementation cover and interview phrasing so core experience areas stay visible without disclaimers, cleaned up low-value audit-keyword noise, refined federal AI summary phrasing while keeping the two-page resume plus separate qualifications statement workflow, softened render-check failure handling into a manual-visual-QA warning, and refreshed the Claude guidance files so future reviews reflect the new explicit-proof private-sector standard and current federal companion-document flow.

Verify: Run `python scripts/smoke_test.py`, `python tasks.py resume`, `python tasks.py cover`, `python tasks.py interview`, `python tasks.py federal-resume`, and `python tasks.py integration-test`, then confirm the smoke suite passes, the Procore standard workflow builds cleanly, the federal workflow outputs both the 2-page resume and 1-page qualifications statement, and render warnings no longer dump the full converter stack trace.

### 2026-06-11 - Made Claude generators write into Claude Review by default

Files changed: `scripts/build_claude_review_packet.py`, `scripts/build_claude_prompt.py`, `Claude Review/UPLOAD_GUIDE.md`, `CHANGELOG.md`

Why: The Claude upload folder existed, but the packet and prompt generators still defaulted to root-level temp files or stdout-only behavior, which meant the folder could drift unless files were copied manually after every refresh.

What changed: Made the review packet generator write mode-specific packet files into `Claude Review` by default, made the prompt generator also write mode-and-kind-specific prompt files there by default while still printing the prompt text, and updated the upload guide so the refresh commands now match the folder workflow directly.

Verify: Run `python tasks.py claude-packet --skip-checks --mode broad`, `python tasks.py claude-packet --skip-checks --mode interview`, `python tasks.py claude-prompt review --packet-mode broad`, and `python tasks.py claude-prompt plan --packet-mode interview`, then confirm the refreshed files land in `Claude Review`.

### 2026-06-11 - Fixed Procore standard-workflow cover-letter routing and duplicate-proof failure

Files changed: `scripts/build_cover_letter.py`, `scripts/smoke_test.py`, `CHANGELOG.md`

Why: The Procore Senior Solutions Architect workflow was misrouting the cover-letter lane because the posting mentioned partnering with Customer Success, which caused the draft to drift away from implementation-delivery framing and then fail QC when it repeated the same workshop/QBR proof twice.

What changed: Kept implementation-heavy solution-architect postings in the implementation-delivery lane when customer-success language appears only as a partner-team mention, added duplicate-proof avoidance so communication examples do not recycle the same accomplishment line, and added a focused Procore smoke test to keep that routing and duplication bug from coming back.

Verify: Run `python scripts/smoke_test.py`, `python scripts/build_resume.py`, and `python scripts/build_cover_letter.py` with the Procore job description active, then confirm the resume is regenerated and the Procore cover letter builds without the previous QC failure.

### 2026-06-11 - Strengthened federal AI tailoring for IT Specialist (AI) resumes

Files changed: `source/Christian_Estrada_Federal_Source.json`, `scripts/build_federal_resume.py`, `scripts/smoke_test.py`, `CHANGELOG.md`

Why: Federal AI-targeted resumes were defaulting to generic implementation and program-management language even when the posting centered on AI-enabled systems, cloud-native modernization, and secure deployment, which buried supported AI workflow evidence already present in the approved commercial source resumes.

What changed: Expanded the approved federal source with supported Claude and AI-workflow skills plus stronger AI-adjacent bullet wording taken from the approved source resumes, added AI-aware federal summary and bullet-selection logic so AI-heavy postings surface supported workflow-automation evidence earlier, and added smoke coverage to confirm AI-focused federal summaries and selected bullets stay visible.

Verify: Run `python scripts/smoke_test.py` and `python tasks.py federal-resume`, then confirm the federal output summary and selected bullets now surface supported AI workflow evidence such as Claude-assisted documentation, AI-assisted analysis, and LivePerson chatbot workflow configuration.

### 2026-06-10 - Refreshed Claude interview review packet for the new pitch system

Files changed: `CLAUDE.md`, `.context/CLAUDE_REVIEW_TEMPLATE.md`, `.context/CODE_REVIEW_PACKET_GUIDE.md`, `.context/SCRIPT_INDEX.md`, `.context/COMMON_CHANGE_AREAS.md`, `scripts/build_claude_review_packet.py`, `CHANGELOG.md`

Why: The Claude handoff layer still described the older interview review surface and did not expose the new shared elevator-speech, human-motivation, and extended TMAY logic that now drives the cheat sheet and detailed guide.

What changed: Updated the `interview` Claude review packet mode to include the shared pitch-builder, human-layer, and long-answer assembly excerpts; tightened the interview review questions around cover-letter-to-interview drift and story-to-human mapping; and refreshed the compact Claude docs so packet guidance, script references, and common risk areas all point to the new interview architecture.

Verify: Run `python tasks.py claude-packet --skip-checks --mode interview` and confirm the generated packet now includes `cover_letter_pitch_parts()`, `human_motivation_sentence()`, `pitch_variants()`, `story_human_connection_line()`, `build_extended_tmay_sections()`, and `story_sample_answer()`.

### 2026-06-10 - Upgraded Claude packet workflow and closed workflow test blockers

Files changed: `CLAUDE.md`, `ARCHITECTURE_MAP.md`, `.context/ARCHITECTURE_MAP.md`, `.context/COMMON_CHANGE_AREAS.md`, `.context/SCRIPT_INDEX.md`, `.context/CODE_REVIEW_PACKET_GUIDE.md`, `.context/CLAUDE_REVIEW_TEMPLATE.md`, `.context/CLAUDE_TASK_TEMPLATE.md`, `scripts/build_claude_review_packet.py`, `scripts/build_claude_prompt.py`, `tasks.py`, `scripts/track_applications.py`, `scripts/post_interview_debrief.py`, `scripts/run_resume_workflow.py`, `scripts/build_search_analytics.py`, `scripts/build_resume.py`, `scripts/build_cover_letter.py`, `scripts/build_interview_cheat_sheet.py`, `scripts/smoke_test.py`, `CHANGELOG.md`

Why: The Claude handoff layer needed a stricter two-pass review-to-plan workflow, and end-to-end testing surfaced live tracker, debrief, workflow, cover-letter, and interview-prep blockers that prevented representative jobs from completing the full workflow cleanly.

What changed: Added mode-based Claude packet generation and strict review/plan prompt generation, aligned compact Claude docs with the new command surface, added smoke coverage for packets/prompts plus tracker and workflow edge cases, added tracker audit flags and JD refresh warnings, made debrief outcome handling explicit, moved workflow auto-tracking ahead of optional steps, hardened alignment-score tuple handling, surfaced flagged outputs in analytics, removed interview placeholder and cliche leaks, and fixed company-specific cover-opening context so AppFolio, BioTouch, and Braven all complete dry run, full workflow, and checklist passes.

Verify: Run `python tasks.py validate`, `python tasks.py integration-test`, `python tasks.py claude-packet --skip-checks --mode broad`, `python tasks.py claude-prompt review --packet-mode tracker`, `python tasks.py claude-prompt plan --packet-mode tracker --focus "debrief and workflow sync"`, `python tasks.py track-report`, `python tasks.py analytics`, and rerun the AppFolio, BioTouch, and Braven dry-run/resume/checklist workflow batch.

### 2026-06-10 - Corrected tracker and checklist fit analysis

Files changed: `scripts/track_applications.py`, `scripts/build_application_checklist.py`, `scripts/build_search_analytics.py`, `scripts/build_general_advice.py`, `scripts/smoke_test.py`, `tasks.py`, `scratch/applications.csv`

Why: Tracker rows and application checklist snapshots could grade against source resumes or stale metadata instead of the matching tailored output, which made fit reporting drift from the real generated documents.

What changed: Split tracker `lane_label` and `fit_status`, added `track-refresh`, made tracker rows and checklist analysis prefer the newest matching tailored resume, kept source-resume fallback on pre-build alignment only, and routed downstream tracker consumers through shared tracker helper functions.

Verify: Run `python tasks.py validate`, `python tasks.py integration-test`, `python tasks.py track`, `python tasks.py track-refresh`, `python tasks.py track-list`, `python tasks.py track-report`, and `python tasks.py checklist`.

### 2026-06-10 - Refreshed compact Claude context and minimal review packet docs

Files changed: `CLAUDE.md`, `ARCHITECTURE_MAP.md`, `.context/ARCHITECTURE_MAP.md`, `.context/RESUME_SYSTEM_BRIEF.md`, `.context/RULES_FOR_CLAUDE.md`, `.context/SCRIPT_INDEX.md`, `.context/COMMON_CHANGE_AREAS.md`, `.context/CODE_REVIEW_PACKET_GUIDE.md`, `.context/CLAUDE_REVIEW_TEMPLATE.md`, `.context/CLAUDE_TASK_TEMPLATE.md`, `CHANGELOG.md`

Why: Claude handoff docs had drifted from the live checklist and tracker architecture and did not clearly show the smallest useful upload packet for newer review tasks.

What changed: Added compact guidance for tracker, checklist, and search-ops reviews, documented the separated tracker schema and archived-JD backfill flow, corrected the compact Professional Summary rule to `70` to `110` words, and clarified the smallest useful Claude packets instead of broad repo uploads.

Verify: Read `CLAUDE.md` and the `.context/` files together and confirm they now cover application checklist logic, tracker/search analytics flows, `track-refresh`, tailored-resume analysis basis, and minimal upload packets without requiring whole-repo context.

### 2026-06-10 - Added live Claude review packet generator

Files changed: `scripts/build_claude_review_packet.py`, `tasks.py`, `TEMP_FOR_REVIEW.md`, `CLAUDE.md`, `ARCHITECTURE_MAP.md`, `.context/ARCHITECTURE_MAP.md`, `.context/SCRIPT_INDEX.md`, `.context/CODE_REVIEW_PACKET_GUIDE.md`, `CHANGELOG.md`

Why: A hand-maintained `TEMP_FOR_REVIEW.md` can drift quickly, which defeats the goal of lean but current Claude uploads.

What changed: Added `python tasks.py claude-packet` to rebuild `TEMP_FOR_REVIEW.md` from the live codebase, current validation output, tracker summary, job-description excerpt, and curated high-risk code excerpts.

Verify: Run `python tasks.py claude-packet` and confirm `TEMP_FOR_REVIEW.md` is regenerated with current `validate`, `integration-test`, and `track-report` output plus live code excerpts from resume, cover-letter, checklist, tracker, workflow, and debrief logic.

### 2026-05-27 - Added business-context targeting and interview-question layer

Files changed: `scripts/business_context.py`, `scripts/resume_analysis.py`, `scripts/resume_content.py`, `scripts/build_resume.py`, `scripts/build_cover_letter.py`, `scripts/build_thank_you.py`, `scripts/build_interview_cheat_sheet.py`, `scripts/build_detailed_interview_guide.py`, `scripts/build_post_round.py`, `scripts/build_application_checklist.py`, `tasks.py`, `scripts/smoke_test.py`, `ARCHITECTURE_MAP.md`

Why: Recent resume guidance emphasized that landing interviews depends on communicating objective business context, customer/product scope, operating complexity, measurable outcomes, and business impact rather than matching job-ad buzzwords or relying on ATS myths.

What changed: Added shared business-context extraction, a `business-context-check` command, resume and cover-letter context audits, business-aware resume summary and bullet scoring, concrete thank-you note business details, business-context interview questions, post-round business question refinement, question-quality warnings, and application checklist readiness prompts.

Verify: Run `python tasks.py business-context-check`, `python tasks.py validate`, `python tasks.py integration-test`, and rebuild resume, cover letter, thank-you note, interview cheat sheet, detailed guide, post-round prep, and application checklist for the active job.

### YYYY-MM-DD - Fixed cover letter bullet-character validation

Files changed: `scripts/build_cover_letter.py`, `scripts/smoke_test.py`

Why: The cover letter validator incorrectly treated question marks as bullet points, which could fail valid prose while missing real bullet characters.

Verify: Run `scripts/smoke_test.py` and confirm cover letter validation flags lines starting with bullet characters such as `*`, `-`, or symbol bullets only when they are actual list markers.

### YYYY-MM-DD - Removed fragile State Farm module lookup

Files changed: `scripts/build_detailed_interview_guide.py`

Why: `story_sample_answer` accessed the State Farm playbook through `sys.modules`, which was fragile and unclear compared with a direct import.

Verify: Build the detailed interview guide for a State Farm job and confirm State Farm story sample answers still render without import or module lookup errors.

### YYYY-MM-DD - Made render cleanup compatible across Python versions

Files changed: `scripts/cleanup_render_checks.py`

Why: `shutil.rmtree(..., onexc=...)` only exists in Python 3.12+, so cleanup could fail on older Python versions.

Verify: Run `scripts/cleanup_render_checks.py --delete --hours 24` on Python below 3.12 and Python 3.12+ and confirm folder deletion works in both environments.

### YYYY-MM-DD - Stabilized `rewrite_supported_text` replacement order

Files changed: `scripts/build_resume.py`

Why: Earlier replacements could create text that later cleanup patterns re-matched, making some intended cleanup patterns unreachable or order-dependent.

Verify: Run `scripts/smoke_test.py` and inspect `rewrite_supported_text` outputs for transactional, operational, reporting, analytics, and dashboard phrasing to confirm cleanup happens once in the intended sequence.

### YYYY-MM-DD - Improved page-fit profile search feedback and early exit

Files changed: `scripts/build_resume.py`

Why: `pack_docx_with_page_fit` tried every fit profile even after finding a usable fallback, making long render runs slower and less transparent.

Verify: Run a resume build and confirm each render prints elapsed time and remaining profiles, with the most likely two-page profiles tried first.

### YYYY-MM-DD - Consolidated LinkedIn hyperlink removal

Files changed: `scripts/utils.py`, `scripts/build_resume.py`, `scripts/run_resume_workflow.py`

Why: Resume generation and workflow recovery had duplicate LinkedIn hyperlink cleanup logic, which increased drift risk and made Word repair behavior harder to maintain.

Verify: Generate a resume through both direct and workflow paths, then confirm visible LinkedIn text remains while external hyperlink relationships are removed from `document.xml` and `document.xml.rels`.

### YYYY-MM-DD - Cleaned AGENTS.md encoding and formatting

Files changed: `AGENTS.md`

Why: Mojibake, escaped Markdown characters, and Windows-style paths made the instruction file harder to read and less cross-platform.

Verify: Open `AGENTS.md` in a UTF-8 editor and confirm there are no replacement characters, corrupted punctuation, escaped file-name examples, or backslash-only path references.

### YYYY-MM-DD - Corrected the output menu

Files changed: `AGENTS.md`

Why: Some output menu items were marked as standalone outputs even though they were only sections inside generated documents, while planned items were mixed into active output guidance.

Verify: Compare the `## COMPLETE OUTPUT MENU` section with `scripts/` and confirm available, in-progress, and roadmap items match current script behavior.

### YYYY-MM-DD - Added config file governance

Files changed: `AGENTS.md`

Why: The system needed explicit rules for what `config/language_rules.py` and `config/job_profiles.py` control and how to validate changes to them.

Verify: Confirm `AGENTS.md` includes the `## CONFIG FILE GOVERNANCE` section and states that `scripts/smoke_test.py` must pass after either config file changes.

### YYYY-MM-DD - Synced compact context files

Files changed: `.context/RULES_FOR_CLAUDE.md`, `.context/ARCHITECTURE_MAP.md`, `.context/SCRIPT_INDEX.md`, `.context/COMMON_CHANGE_AREAS.md`

Why: The compact handoff files needed to reflect the new config governance, smoke test, and config file roles so future sessions start from accurate context.

Verify: Inspect the four compact context files and confirm they mention the smoke test, config file rules, script index entries, and config-change workflow.

### YYYY-MM-DD - Extracted State Farm prep insights into the playbook

Files changed: `scripts/build_detailed_interview_guide.py`, `scripts/modules/employer_playbooks/state_farm.py`

Why: State Farm-specific prep logic lived inside the general detailed guide builder instead of the State Farm playbook module.

Verify: Build a detailed guide for a State Farm posting and confirm `build_prep_insights` returns the State Farm `PrepInsights` content through `state_farm_prep_insights()`.

### YYYY-MM-DD - Added import-time config validation

Files changed: `config/job_profiles.py`, `config/language_rules.py`, `scripts/smoke_test.py`

Why: Empty or malformed config structures could load silently and break lane detection, language checks, or competency behavior later in the workflow.

Verify: Run `scripts/smoke_test.py` and confirm both config modules import cleanly before the rest of the smoke checks run.

### YYYY-MM-DD - Cleaned ERP mention rebalancing counter logic

Files changed: `scripts/build_resume.py`, `scripts/smoke_test.py`

Why: `rebalance_professional_summary_erp_mentions` used a function attribute as a mutable counter and had a final case-sensitive ERP replacement pass.

Verify: Run `scripts/smoke_test.py` and confirm summaries with three ERP mentions are reduced to two while summaries with one ERP mention remain unchanged.

### YYYY-MM-DD - Replaced broad cover letter colon smoothing

Files changed: `scripts/build_cover_letter.py`, `scripts/smoke_test.py`

Why: A catch-all colon replacement could corrupt legitimate text such as time expressions, ratios, and natural sentence constructions.

Verify: Run `scripts/smoke_test.py` and confirm `smooth_cover_letter_text` preserves `9:00 AM` while still smoothing label-style colons.

### YYYY-MM-DD - Filled lane coverage gaps

Files changed: `scripts/build_cover_letter.py`, `scripts/build_interview_cheat_sheet.py`, `scripts/build_detailed_interview_guide.py`

Why: Some role lanes had specific handling in one output but fell through to generic language in others.

Verify: Generate cover letter, cheat sheet, and detailed guide outputs for implementation delivery, process improvement, and corporate strategy roles and confirm lane-specific sections appear.

### YYYY-MM-DD - Added workflow dry-run mode

Files changed: `scripts/run_resume_workflow.py`, `run_resume.bat`

Why: The workflow needed a no-write validation mode to confirm inputs, source files, resume selection, lane detection, keyword audit, and downstream readiness before generating documents.

Verify: Run `scripts/run_resume_workflow.py --dry-run` or choose the dry-run option in `run_resume.bat` and confirm it exits without writing files.

### YYYY-MM-DD - Added Big Four and consulting playbook support

Files changed: `scripts/modules/employer_playbooks/consulting_bigfour.py`, `scripts/build_detailed_interview_guide.py`, `scripts/build_cover_letter.py`

Why: Consulting and Bain-style logic needed to live in a dedicated playbook instead of inline cover letter logic, with reusable detection and prep insight behavior.

Verify: Use a job description containing KPMG, Deloitte, PwC, EY, Bain, McKinsey, BCG, Accenture, or consulting signals and confirm the consulting playbook activates.

### YYYY-MM-DD - Converted value story rewrites to key-phrase matching

Files changed: `scripts/build_resume.py`

Why: Long exact-prefix bullet matching could silently stop working when source bullets changed by a word or punctuation mark.

Verify: Run `scripts/smoke_test.py` and confirm value story rewrites still fire when their distinctive key phrases are present.

### YYYY-MM-DD - Converted consulting story rewrites to key-phrase matching

Files changed: `scripts/build_resume.py`

Why: Consulting rewrites depended on long bullet prefixes and failed silently when the source resume wording drifted.

Verify: Run a consulting-context resume build and confirm consulting story bullets rewrite when all expected short key phrases appear, with a stderr warning if none match.

### YYYY-MM-DD - Converted startup operator rewrites to key-phrase matching

Files changed: `scripts/build_resume.py`

Why: Startup operator rewrites had the same fragile prefix-matching behavior as the consulting and value story rewrite passes.

Verify: Run a startup-operator-context resume build and confirm Aptean Intuitive and inventory adjustment rewrites fire by key phrase rather than exact prefix.

### YYYY-MM-DD - Completed process improvement cover letter handling

Files changed: `scripts/build_cover_letter.py`

Why: Process improvement cover letters still fell back to generic language in some proof, close, and bridge paths.

Verify: Run a process improvement dry run or cover letter build and confirm the letter mentions root cause, measurable improvement, adoption, cost-benefit, service quality, and practical process bridge language.

### YYYY-MM-DD - Centralized contact information constants

Files changed: `scripts/build_resume.py`, `scripts/build_cover_letter.py`, `scripts/smoke_test.py`

Why: Christian's email address and LinkedIn URL fragments were hardcoded in multiple places, making future contact updates error-prone.

Verify: Run `scripts/smoke_test.py` and confirm `CONTACT_EMAIL` and `LINKEDIN_URL` are non-empty and used by both resume and cover letter code paths.

### YYYY-MM-DD - Fixed role-heading false positives

Files changed: `scripts/build_resume.py`, `scripts/smoke_test.py`

Why: `is_role_heading` treated any month-year text as a role heading, which could misclassify bullets that mentioned dates and corrupt role parsing.

Verify: Run `scripts/smoke_test.py` and confirm a real role heading returns true while sentence-style and start-of-line month-year references return false.

### YYYY-MM-DD - Refactored cover letter specificity warnings

Files changed: `scripts/build_cover_letter.py`, `scripts/run_resume_workflow.py`, `AGENTS.md`

Why: Specificity issues were printed to stderr and could disappear inside long build output instead of reaching the user as structured post-build warnings.

Verify: Build a cover letter with low company-name density, missing specialty terms, or generic closing language and confirm `SPECIFICITY WARNING:` lines appear after the output filename and in the workflow summary.

### YYYY-MM-DD - Standardized Professional Experience alignment

Files changed: `scripts/build_resume.py`, `scripts/smoke_test.py`, `CHANGELOG.md`

Why: Professional Experience paragraphs inherited alignment from different source resumes, which could mix left-aligned and justified bullets within the same generated resume.

Verify: Run `scripts/smoke_test.py`, then build resumes from both the Implementation and Pre-Sales sources and confirm role headings, company lines, summaries, bullets, and in-section blank separators are explicitly left-aligned in the render checks.

### YYYY-MM-DD - Added fast pre-flight check command

Files changed: `tasks.py`, `CHANGELOG.md`

Why: Christian needed a quick way to inspect resume selection, lane detection, keyword coverage, evidence matches, fit risks, and story framing without running the full DOCX build or render pipeline.

Verify: Run `python tasks.py check` and confirm it completes in under five seconds while printing resume selection, role lane, keyword coverage, match lists, poor-fit warnings, story lens, and elapsed time without creating files.

### YYYY-MM-DD - Made summary domain sentence job-aware

Files changed: `scripts/build_resume.py`, `scripts/smoke_test.py`, `CHANGELOG.md`

Why: `build_problem_first_summary` used the same hardcoded domain list for every job, causing healthcare, SaaS, retail, and manufacturing roles to receive identical domain framing.

Verify: Run `scripts/smoke_test.py` and confirm healthcare, SaaS customer success, and manufacturing ERP summary tests all pass with the expected domain terms in the `Experience spans ... environments` sentence.

### YYYY-MM-DD - Guarded summary condensation and ERP rebalance passes

Files changed: `scripts/build_resume.py`, `scripts/smoke_test.py`, `CHANGELOG.md`

Why: Summary condensation ran even when the Professional Summary was already within target length, and ERP rebalancing scanned the full document even when the summary already met the ERP mention limit.

Verify: Run `scripts/smoke_test.py` and confirm short-enough summaries keep longer phrasing such as "more than ten years" while ERP rebalance still reduces summaries with too many ERP mentions.

### YYYY-MM-DD - Made interview story and guidance sections context-aware

Files changed: `scripts/build_interview_cheat_sheet.py`, `scripts/build_detailed_interview_guide.py`, `scripts/smoke_test.py`, `CHANGELOG.md`

Why: The six-story section could silently omit uncovered story types, and process-engineering advice appeared in interview guidance even when the job description had no process engineering signals.

Verify: Run `scripts/smoke_test.py` and confirm six story slots always render with missing-story fallbacks while process-engineering advice appears only for matching process or manufacturing engineering postings.

### YYYY-MM-DD - Added CI and pre-commit smoke-test gates

Files changed: `.github/workflows/smoke_test.yml`, `.pre-commit-config.yaml`, `tasks.py`, `CHANGELOG.md`

Why: The resume system needed a repeatable validation gate in GitHub Actions and an optional local pre-commit hook so lane detection, config validation, and language-rule checks fail early before changes are merged or committed.

Verify: Run `python tasks.py validate` locally and confirm the smoke test passes before pushing; the GitHub Actions workflow and pre-commit hook both run the same `python scripts/smoke_test.py` check, so local smoke failures will also fail CI and block commits when the hook is installed.

### YYYY-MM-DD - Preserved DOCX run formatting during ERP scrubs

Files changed: `scripts/build_cover_letter.py`, `scripts/build_interview_cheat_sheet.py`, `scripts/build_detailed_interview_guide.py`, `scripts/smoke_test.py`, `CHANGELOG.md`

Why: ERP scrub passes assigned to `paragraph.text`, which flattened python-docx paragraph runs and could strip formatting such as header font size, color, bold, and italic.

Verify: Run `scripts/smoke_test.py` and confirm the run-level ERP scrub formatting test passes, proving text can be scrubbed while bold and font color remain unchanged.

### YYYY-MM-DD - Precomputed cover letter bridge context flags

Files changed: `scripts/build_cover_letter.py`, `CHANGELOG.md`

Why: `anticipated_fit_bridge` repeated the same secondary regex checks across branch conditions, making the selection logic noisier and less efficient than necessary.

Verify: Capture `anticipated_fit_bridge` output for a representative job before and after the refactor, confirm the strings match exactly, then run `python tasks.py check` and `scripts/smoke_test.py`.

### YYYY-MM-DD - Moved detailed guide keyword bank to the back

Files changed: `scripts/build_detailed_interview_guide.py`, `scripts/build_interview_cheat_sheet.py`, `CHANGELOG.md`

Why: Dense keyword overlap could generate a long keyword-question bank in the middle of the detailed guide, burying the primary story bank and behavioral answer scripts.

Verify: Build a full detailed interview guide and confirm the order reads story bank, behavioral answers, likely questions, answer mechanics, closing strategy, thank-you strategy, keyword answer reference, then appendix when supplied notes exist.

### YYYY-MM-DD - Tightened Professional Summary fit checklist

Files changed: `scripts/build_resume.py`, `scripts/smoke_test.py`, `CHANGELOG.md`

Why: `build_problem_first_summary` used the full six-item role checklist in the closing sentence, which made the summary read like a list dump instead of precise fit positioning.

  Verify: Run `scripts/smoke_test.py` and confirm each main lane summary stays between 70 and 110 words, avoids "That" openings, and has no sentence with more than four comma-separated items.

### YYYY-MM-DD - Detected late-stage interview signals from job descriptions

Files changed: `scripts/build_interview_cheat_sheet.py`, `scripts/smoke_test.py`, `CHANGELOG.md`

Why: `detect_late_stage_context` ignored the job description, so compensation, total rewards, or salary transparency language in postings did not trigger the negotiation preparation section.

Verify: Run `scripts/smoke_test.py` and confirm job descriptions with total compensation signals trigger late-stage detection while empty inputs do not.

### YYYY-MM-DD - Added contribution guide for system extensions

Files changed: `CONTRIBUTING.md`, `CHANGELOG.md`

Why: Extending the system with new lanes, employer playbooks, or story cards requires coordinated edits across config, resume, cover letter, and interview scripts; the repo needed one authoritative extension checklist.

Verify: Open `CONTRIBUTING.md` and confirm it documents the lane, playbook, story-bank, and validation workflows in the requested order.

### YYYY-MM-DD - Clarified why-company placeholders and negotiation lever order

Files changed: `scripts/build_interview_cheat_sheet.py`, `scripts/smoke_test.py`, `CHANGELOG.md`

Why: The interview cheat sheet could show an unbracketed company-research placeholder and used the same negotiation lever order for every role lane.

Verify: Run `scripts/smoke_test.py` and confirm why-company answers use supplied company context or an explicit research reminder, while pre-sales and customer success lanes prioritize performance bonus and equity levers.

### YYYY-MM-DD - Kept why-company research reminder out of placeholder validation

Files changed: `scripts/build_interview_cheat_sheet.py`, `scripts/smoke_test.py`, `CHANGELOG.md`

Why: The bracketed why-company research reminder was intentional coaching text, but the interview cheat sheet validator treats all bracketed text as unsafe placeholders and stopped the build.

Verify: Run `scripts/smoke_test.py` and then `scripts/build_interview_cheat_sheet.py`; confirm the why-company answer uses plain research-reminder language and the placeholder validator passes.

### YYYY-MM-DD - Made communication audit guidance interview-format aware

Files changed: `scripts/build_interview_cheat_sheet.py`, `scripts/smoke_test.py`, `CHANGELOG.md`

Why: Communication audit guidance treated video, on-demand, and in-person interviews the same, which made eye-contact and answer-length coaching less useful.

Verify: Run `scripts/smoke_test.py` and confirm video or on-demand interview signals change the eye-contact and answer-length audit lines while default guidance remains unchanged.

### YYYY-MM-DD - Added story-type-specific detailed guide audit checks

Files changed: `scripts/build_detailed_interview_guide.py`, `scripts/smoke_test.py`, `CHANGELOG.md`

Why: Detailed guide story audits used the same checklist for every story type, reducing usefulness for failure, persuasion, leadership, rapid-learning, and teamwork rehearsal.

Verify: Run `scripts/smoke_test.py` and confirm story cards receive relevant type-specific audit checks while total audit lines stay capped at eight.

### YYYY-MM-DD - Guarded startup interview guidance against enterprise false positives

Files changed: `scripts/build_interview_cheat_sheet.py`, `scripts/smoke_test.py`, `CHANGELOG.md`

Why: Large employers can use startup-adjacent language such as ownership or fast-paced without being startups, which could trigger inaccurate startup-specific interview advice.

Verify: Run `scripts/smoke_test.py` and confirm a Fortune 500 posting with only a single startup-adjacent phrase does not trigger startup guidance, while true early-stage signals still do.

### YYYY-MM-DD - Added job-specific application checklist builder

Files changed: `scripts/build_application_checklist.py`, `tasks.py`, `scripts/smoke_test.py`, `CONTRIBUTING.md`, `CHANGELOG.md`

Why: The system needed a compact pre-build document that summarizes lane detection, fit status, keyword coverage, evidence areas, lead story, cover approach, and fit risks for the current job.

Verify: Run `python tasks.py checklist` and confirm `output/Christian Estrada - [Company Name] Application Checklist.docx` is created with the expected one-page sections.

### YYYY-MM-DD - Connected debrief history to the application checklist

Files changed: `scripts/build_application_checklist.py`, `scripts/smoke_test.py`, `CONTRIBUTING.md`, `CHANGELOG.md`

Why: Prior interview intelligence captured by the debrief tool should surface in the job-specific checklist instead of staying buried in raw text files.

Verify: Run `python tasks.py checklist` for a company with entries in `jobs/debrief_history.txt` and confirm the checklist includes Previous Round Intelligence and reports how many debrief entries were incorporated.

### YYYY-MM-DD - Added active job context to the Career Operating Manual

Files changed: `scripts/build_general_advice.py`, `scripts/smoke_test.py`, `CHANGELOG.md`

Why: The general advice document could not reflect the current job description, selected resume, lane, keywords, lead story, or lane-specific coaching when an active posting was present.

Verify: Run `python tasks.py advice` with and without `jobs/job_description.txt` populated and confirm the document either includes Active Job Context or the note explaining how to add it.

### YYYY-MM-DD - Added safe job-context reset utility

Files changed: `scripts/reset_jobs.py`, `tasks.py`, `scripts/smoke_test.py`, `CONTRIBUTING.md`, `CHANGELOG.md`

Why: Switching between active job searches needed an archive-first workflow that can clear only the current job description while preserving accumulated research, interview notes, and debrief history.

Verify: Run `python tasks.py list-archives` to inspect archives, and use `python tasks.py reset-jobs --archive-only` or `--clear` to confirm non-empty job files are copied to `scratch/jobs_archive/` before anything is cleared.

### YYYY-MM-DD - Added job description quality checks

Files changed: `scripts/build_resume.py`, `tasks.py`, `CHANGELOG.md`

Why: Short postings, missing company names, multiple pasted postings, and LinkedIn UI snippets could weaken lane detection and keyword coverage without giving the user an early warning.

Verify: Run `python tasks.py jd-check` and confirm it reports any job-description quality warnings without generating files.

### YYYY-MM-DD - Consolidated Great Eight outcome detection

Files changed: `scripts/utils.py`, `scripts/build_resume.py`, `scripts/build_interview_cheat_sheet.py`, `scripts/smoke_test.py`, `CHANGELOG.md`

Why: Resume bullet audits and interview story audits duplicated the same Great Eight outcome model, increasing drift risk between resume quality checks and story quality checks.

Verify: Run `scripts/smoke_test.py` and confirm the shared utility detects outcome language while rejecting task-only workflow text.

### YYYY-MM-DD - Consolidated cover letter evidence selection mechanics

Files changed: `scripts/build_cover_letter.py`, `CHANGELOG.md`

Why: `evidence_bullets` and `selected_evidence_items` duplicated the same support filtering and signal-scoring mechanics, making future matching fixes easy to apply in only one path by accident.

Verify: Run `scripts/smoke_test.py` and confirm cover-letter imports and supporting checks still pass; compare generated cover-letter text against a prior run when a matching resume output is available.

### YYYY-MM-DD - Refactored cover opening pattern selection

Files changed: `scripts/build_cover_letter.py`, `CHANGELOG.md`

Why: `_select_opening_pattern` used a long embedded conditional chain, making priority order and future pattern additions harder to audit.

Verify: Run `scripts/smoke_test.py` and compare opening paragraph output for consulting, pre-sales, and implementation job descriptions against the pre-refactor selection behavior.

### YYYY-MM-DD - Added cover letter structure preview command

Files changed: `scripts/build_cover_letter.py`, `tasks.py`, `CHANGELOG.md`

Why: The system needed a fast way to inspect cover-letter opening pattern, evidence selection, bridge, closing lane, length, and specificity warnings without generating a DOCX.

Verify: Run `python tasks.py cover-check` after a matching resume exists in `output/` and confirm it prints the cover structure preview without writing a file.

### YYYY-MM-DD - Added Professional Summary preview tooling

Files changed: `scripts/build_resume.py`, `scripts/preview_summary.py`, `tasks.py`, `CHANGELOG.md`

Why: The Professional Summary generator needed lightweight debug output and a fast preview command so lane, domain, checklist, word count, ERP density, story lens, and employer context can be checked before a full build.

Verify: Run `python tasks.py preview-summary` and confirm it prints summary debug lines, the generated summary, diagnostics, and elapsed time without writing files.

### YYYY-MM-DD - Added proactive bullet-budget minimum guard

Files changed: `scripts/build_resume.py`, `scripts/smoke_test.py`, `CHANGELOG.md`

Why: Bullet trimming could remove role bullets below the configured minimum and leave the later integrity check to fail after many unrelated transformations had already run.

Verify: Run `scripts/smoke_test.py` and confirm each known company role budget is at least its configured minimum.

### YYYY-MM-DD - Centralized core company-name constants

Files changed: `scripts/build_resume.py`, `scripts/build_interview_cheat_sheet.py`, `scripts/build_detailed_interview_guide.py`, `scripts/smoke_test.py`, `CHANGELOG.md`

Why: Core employer names were repeated across role budgets, integrity rules, summaries, and interview text, making future name changes easy to miss.

Verify: Run `scripts/smoke_test.py` and confirm the company-constant assertions pass along with the existing resume and interview checks.

### YYYY-MM-DD - Moved AI workflow evidence matching into config

Files changed: `scripts/build_resume.py`, `scripts/smoke_test.py`, `CHANGELOG.md`

Why: `job_problem_profile` had a hardcoded AI-assisted workflow match outside the standard bridge-evidence loop, making AI evidence invisible to config validation and harder to maintain.

Verify: Run `scripts/smoke_test.py` and confirm AI job/resume signals produce an `AI-Assisted Workflow Improvement` direct match through `BRIDGE_EVIDENCE_AREAS`.

### YYYY-MM-DD - Consolidated resume XML font and layout passes

Files changed: `scripts/build_resume.py`, `CHANGELOG.md`

Why: The main resume build parsed and wrote `document.xml` multiple times for font, sizing, spacing, row rhythm, and alignment updates that could be grouped into fewer passes without changing final behavior.

Verify: Run `scripts/smoke_test.py`, then run a full resume build and confirm the new `[pass] font and size pass starting` and `[pass] spacing and layout pass starting` log lines appear while final render and formatting checks still pass. The individual XML helper functions remain available for direct use.

### YYYY-MM-DD - Added project changelog

Files changed: `CHANGELOG.md`

Why: The improvement series needed a durable record so future Codex sessions can see what was completed, why it mattered, and how to verify it.

Verify: Open `CHANGELOG.md` and confirm every improvement prompt has a dated placeholder entry with summary, files changed, why, and verify lines.

## Known Limitations

* `detect_company_profile(company_name, job_description)` is intentionally a stub and always returns `None`; registered firms should use `_registered_firm_profile` in `scripts/build_cover_letter.py`.
* Render verification depends on a specific Codex document-rendering plugin path and may fail outside the configured Codex desktop/runtime environment.
* Items listed under the `## ROADMAP` section of `AGENTS.md` have no current implementation and should not be generated unless Christian explicitly asks for a new feature build.
