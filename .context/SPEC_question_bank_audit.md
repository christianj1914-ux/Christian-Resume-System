# Spec: Question Bank Audit and Prep Mapping (final, as built)

Authoritative record of the question-bank audit and prep-mapping feature as implemented and verified on 2026-07-27. This supersedes the working plan-pass file `CODEX_SPEC_question_bank_audit.md`, which can be archived. Written as a maintenance reference: what the system does, where it lives, and the invariants that must not regress.

## Purpose

1. Every application-bank prompt gets a real, evidence-backed answer instead of a generic bridge.
2. A read-only, warn-only audit reports application-bank health honestly, separate from general interview-prep material.
3. Question themes map to the existing Study tracks, surface as coverage in the detailed interview guide, and drive a full, ranked question checklist in daily prep.

## Invariants (must not regress)

- No invented claims, metrics, tools, or authority. Answers may use only anchors already supported in `question_prep.py`: 80+ international client engagements, 200+ reporting tools, 60+ executive workshops and QBRs, five-site / 150+ user ERP ownership, the Aptean Intuitive to Epicor Kinetic migration, and the warehouse / Amazon Robotics launch.
- Every generated answer passes `assert_no_application_banned_phrases`: no `--`, and no sentence beginning with the word "That".
- The audit never edits, reorders, deletes, or rewrites any source bank. It groups and warns only.
- `question_category()` is the single source of truth for prompt-to-answer routing. The audit and the live build must call the same classifier so they never disagree.
- Run `scripts/smoke_test.py` after any change here. Current baseline: 420 checks passing.

---

## 1. Answer categories and builders (`scripts/question_prep.py`)

Two categories were added so the newest behavioral prompts route to real answers instead of `generic_bridge`:

- `parallel_project_governance` for "ran multiple complex technical projects in parallel ... milestones, dependencies, and stakeholders".
- `executive_reporting_trust` for "built trust with an executive stakeholder group through your reporting and communication".

Routing (`question_category()`): both guards are multi-token and sit above the looser `prioritization` and `communication` checks so they win. Verified: none of the other 18 bank prompts trip either guard.

- `parallel_project_governance`: requires `parallel` plus (`multiple` or `several`) plus (`milestones` or `dependencies`).
- `executive_reporting_trust`: requires `executive` plus `trust` plus (`reporting` or `communication`).

Answer builders: `parallel_project_governance_answer()` and `executive_reporting_trust_answer()`. Both wrap `finalize_candidate_answer(..., claim_first=True)`. The parallel answer deliberately leads with the cross-project / portfolio angle (one combined milestone view, an explicit cross-project dependency map, a shared stakeholder cadence) so it does not re-tell the single-program launch story already used by `ambiguity_delivery_answer` and `complex_project_leadership_answer`. The executive-trust answer stays on making risk and tradeoffs visible so executives could decide; it does not claim people leadership, executive relationship ownership, or strategy ownership.

Wiring: both categories are added to the `answer_prompt()` dispatch and to the `claim_first_categories` set so they receive the same claim-first validation as the other behavioral answers.

Verified output: the reusable bank has 20 prompts and 0 `generic_bridge` prompts; the two samples map to the new categories.

---

## 2. Question-bank audit (`scripts/question_bank_audit.py`, `scripts/build_question_bank_audit.py`)

Read-only module plus a Word report builder. The audit separates two populations, because conflating them produced a misleading headline in the first build.

### Two source classes

Class A, application-answer sources. `question_category`, category-collision grouping, and the unmapped `generic_bridge` alarm apply here only:

- `jobs/application_questions_bank.txt` (reusable bank).
- `jobs/application_questions.txt` (active file; currently empty, so the loader falls back to a single default).
- Optional embedded `Application Questions:` section in `job_description.txt`, included via guarded import if that parser exists.

Class B, interview-question corpus (reference only). `question_category` only knows the ~20 application prompts, so every Class B item is expected to be `generic_bridge`; it must never feed the unmapped alarm or collision grouping:

- `interview_prep/*.md`.
- Generated `business_context.business_interview_questions(...)` when a JD is present.

Class B markdown extraction keeps only genuine questions: a line ending in `?` with an interrogative or behavioral lead (What, How, Why, Tell, Describe, Give, Walk, Do, Does, Are, Is, Can, Could, When, Where, Who), or an enumerated interview prompt such as `2. How do you handle scope creep?` or `13. Tell me about yourself.`. It rejects headings, coaching prose, bracket-fill instructions, quoted closing lines, lowercase fragments, and mid-sentence fragments. This strict allowlist is Class B only and must not be reused for Class A parsing.

### Signals

- Exact duplicate: identical `normalize_question`, computed within each class. Same logical prompt arriving from two Class A sources is merged into one row carrying both source labels (shared provenance), not flagged as a redundancy to remove. Only same-source repeated text is a possible cleanup finding.
- Category collision (Class A only): two application prompts sharing a `question_category` produce the same answer, so this is the functional-redundancy signal.
- Near-duplicate hints: token overlap (Jaccard over content words, threshold ~0.6), run within Class A `generic_bridge` and, separately, within Class B. Reported in distinct sections.
- Unmapped flag (Class A only): any Class A prompt whose category is `generic_bridge`. This is the actionable signal, since it means the qualifications build would emit a warn-level generic answer.
- Synthetic prompts from `question_prep.element_probe_responses()` are excluded from both classes.

### Report and command

`python tasks.py question-bank-audit` builds `output/Question_Bank_Audit_<date>.docx` and prints a two-part console summary, Class A first. Registered in `tasks.py` with `needs_job_description=False`, maturity Experimental; not in `COMMERCIAL_AUTO_ARCHIVE_COMMANDS` (diagnostic, not a per-application artifact).

Word report sections: Application Bank Health (counts, category collisions, unmapped prompts, internal duplicate defects, application near-duplicate hints), Application Bank Prompt Table (provenance and theme/track refs), and Interview Question Corpus (Class B near-duplicate pairs only, labeled reference, with a note that `generic_bridge` is expected there and is not a defect).

Verified output (2026-07-27): Application bank 20 prompts, 0 unmapped, 0 category collisions, 0 internal duplicate defects, 0 near-duplicate hints; Interview corpus 43 questions, 2 near-duplicate pairs; no junk fragments remain.

---

## 3. Theme-to-track mapping (`scripts/interview_intelligence.py`)

`QUESTION_THEME_TRACKS` maps answer category to entries in the existing `STUDY_TRACK_REFERENCES`, exposed via `question_theme_tracks(category)`. Only categories with a real prep gap are mapped: project-governance themes to PMP, AI themes to the AI and AI-adoption tracks, executive-reporting and implementation-success themes to Data Analytics/BI and Business Architecture. Every referenced file is a real `STUDY_TRACK_REFERENCES` entry. Career-target alignment (Implementation Consultant, Solutions Consultant, Business Systems Analyst, Technical Program Manager, Business Architect / AI Evangelist) is encoded implicitly through those track choices.

---

## 4. Detailed guide coverage (`scripts/build_detailed_interview_guide.py`)

A Question Bank Coverage section renders each application-question cluster with the canonical prompt, the best story anchor, the answer shape, and the Study track refs. Application-question prompts show full sample answers (reusing `answer_prompt` output), not only coaching notes. Verified: the section renders both new prompts with correct category, anchor, and Study refs.

---

## 5. Daily prep checklist (`scripts/interview_intelligence.py` + `scripts/build_daily_prep_plan.py`)

`DailyPrepPlan` carries a `question_bank_checklist` field, populated in `build_daily_prep_plan()` and rendered as a Question Bank Checklist section.

Rules: include every applicable bank prompt (all ~20), never truncated. "Applicable" drops only prompts the audit flags as stale for the active JD via `question_prep.application_question_context_issues` (for example the public-agency prompt on a non-public-sector role). Ranking: Study-track-mapped, career-target-aligned categories first; then unmapped `generic_bridge` prompts (weakest-prepared, worth drilling most); then remaining bank order, stable-sorted. Exact duplicates collapse to one line; category collisions stay separate so each distinct prompt is rehearsable. Each line names the theme and its Study track ref.

Verified output: 19 of 20 prompts render (public-agency prompt correctly filtered for the GoodShip JD), Study-track categories ranked on top.

---

## 6. Tests (`scripts/smoke_test.py`)

Coverage added and passing (420 total):

- Category lock: each of the 20 bank prompts maps to its intended category; the two new prompts map to the new categories and no longer hit `generic_bridge`.
- Both new answers pass the banned-phrase and claim-first checks.
- Audit: exact-duplicate grouping, Class A category collisions, application near-duplicates via controlled fixture rows; `element_probe_responses` prompts excluded.
- Class separation: with the live bank plus `interview_prep/*.md`, Class A has 0 unmapped and 0 collisions, no Class B markdown prompt appears in Class A unmapped, and Class B rows exist separately.
- Provenance: repeating a bank prompt from a second Class A source yields one row with both labels and is not a duplicate-removal defect.
- Extractor fixtures: rejects `are automatic. Fill any bracketed blanks with your real specifics.` and `How to sell your projects (stop underselling)`; keeps `How do you handle scope creep or changing requirements?` and `13. Tell me about yourself.`.
- Audit command is read-only (bank bytes unchanged) and Word-only.
- Detailed guide renders coverage; daily prep renders the ranked checklist.

Validation commands: `python scripts/smoke_test.py`, `python tasks.py commands`, `python tasks.py question-bank-audit`, `python tasks.py qualifications`, `python tasks.py guide`, `python tasks.py daily-prep`, `python scripts/integration_test.py`.

## Open housekeeping

- `scripts/question_bank_audit.py` and `scripts/build_question_bank_audit.py` are untracked in git and should be committed so the audit subsystem is captured.
- `jobs/application_questions.txt` is empty in the current baseline; seed it (or point tests at the bank) whenever exercising the real qualifications path end to end.

## Assumptions

- Warn and group only; never auto-delete or rewrite banks.
- Cross-class duplicates (a prompt in both the bank and a markdown file) are expected and not defects.
- Class B is reference-only, so a strict extractor may drop some legitimate statement-style interview prompts without affecting application-answer quality.
- The embedded `Application Questions:` parser remains part of the separate commercial-questions plan; this feature treats it as an optional, guarded audit source.
