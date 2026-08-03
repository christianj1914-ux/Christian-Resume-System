# Codex Spec: Per-JD Interview Scorecard and BLUF Answer Generation

## Purpose
Christian's interviews fail on execution, not substance: he does not pre-map the competencies a
role scores him on, and he answers in unstructured paragraphs. The resume system already
extracts a JD's competencies and keywords (commercial `audit_keywords` / evidence ledger;
federal competency extraction). Reuse that machinery to make the interview-prep generators
produce, per JD: the scored-competency scorecard, the frameworks/keywords to say out loud, a
story mapped to each competency, BLUF model answers, honest gap-pivots, and a 30/60/90. This
turns the existing guides from generic into JD-targeted.

Truthfulness is non-negotiable: gap-pivots admit real gaps and bridge to real ramp stories;
never fabricate a certification, belt, or experience Christian lacks. See
`interview_prep/Interview Repair Kit and Dematic Mock.md` for the target output quality and the
five anchor stories.

## Where (reuse, do not rebuild)
Interview generators exist: `scripts/question_prep.py` (story bank, question categorization,
answer builders), `scripts/build_interview_cheat_sheet.py`,
`scripts/build_detailed_interview_guide.py`, `scripts/interview_context.py`. Competency/keyword
extraction exists in `scripts/resume_analysis.py` (`audit_keywords`, `high_value_audit_keywords`,
evidence ledger) and the federal competency parser in `scripts/build_federal_resume.py`. Build
the scorecard layer on top of these; do not create a parallel extractor.

## Key changes

### 1. JD competency scorecard
- Add a `jd_competency_scorecard(job_description)` that returns the 4-8 competencies an
  interviewer will score, derived from the JD's responsibilities/requirements using the existing
  keyword/competency extraction plus a curated `COMPETENCY_TAXONOMY` (below). Examples for a
  Solutions Consultant: discovery, requirements translation, stakeholder alignment, structured
  problem solving, customer communication, adaptability.
- Each scorecard entry carries: competency name, the JD phrases that triggered it, and its
  framework/keyword cheat.

### 2. Framework/keyword cheat map (curated data)
- Add `COMPETENCY_FRAMEWORKS`, a truthful map from competency to the frameworks and terms to
  name out loud. Seed it:
  - process improvement -> DMAIC, PDCA, 5 Whys, root-cause analysis, value stream mapping, Lean
    Six Sigma
  - project/program delivery -> Agile, Scrum, sprint, backlog, milestone, risk register, change
    control
  - discovery/requirements -> current-state mapping, requirements elicitation, FRD, SOW, gap
    analysis
  - data/analytics -> KPI, dashboard, data quality, ETL validation, Power BI, SQL
  - stakeholder alignment -> RACI, executive readouts, written confirmation, escalation path
  - implementation/integration -> data migration, UAT, cutover, ODBC/API integration, hypercare
- This is the piece that fixes the State Farm Lean Six Sigma miss: the scorecard surfaces "name
  a framework" for any competency he is thin on.

### 3. Story-to-competency matrix
- Ensure the five anchor stories are in the story bank (`question_prep` StoryCards / story bank),
  sourced from the evidence ledger so they stay truthful: (1) Windows-95 discovery, (2) CEO
  escalation, (3) East West fast ramp, (4) EFT/ACH cross-functional, (5) inventory automation /
  DMAIC. Each StoryCard tagged with the competencies it proves.
- Add `map_stories_to_scorecard(scorecard, story_bank)` so each scored competency gets at least
  one mapped story; flag any competency with no supporting story as a gap.

### 4. BLUF model answers
- For the likely questions per competency (reuse existing question categorization), generate the
  answer in strict BLUF shape: Answer -> Example (one mapped story) -> Result (with a number when
  the ledger has one) -> Relevance (one sentence tying to this JD). Enforce the shape; reject
  answers that bury the point or chain three half-stories.
- Include the standard high-stakes prompts every time: why this role, walk me through your last
  role (lead with the software/skill category), build relationships, alignment under conflict,
  your biggest gap, 30/60/90.

### 5. Gap-pivots (honest)
- For any scorecard competency with weak/no story support, generate an admit-bridge-ask pivot:
  name the gap plainly, bridge to a truthful ramp story (default: East West fast-ramp), end with
  a smart question. Never assert a credential or experience not in the source. A "formal Lean Six
  Sigma belt" gap pivots to the DMAIC-in-practice story, not to a claimed belt.

### 6. 30/60/90 and questions to ask
- Generate a role-appropriate 30/60/90 hypothesis (learn portfolio + shadow -> lead portions ->
  run independently) and 2-3 consultative questions to ask the interviewer, per JD.

## Render
- Extend `build_interview_cheat_sheet.py` (the fast, night-before/day-of view) to lead with the
  one-page scorecard: competency, framework words to say, mapped story, in a scannable table.
- Extend `build_detailed_interview_guide.py` with the full BLUF model answers, gap-pivots, and
  30/60/90.
- Keep the existing daily-practice guide; add a "scorecard rep" drill (build a scorecard from a
  live JD in five minutes).

## Tests
- `jd_competency_scorecard` returns 4-8 competencies for a Solutions Consultant JD and includes
  discovery and stakeholder alignment.
- A process-improvement JD surfaces DMAIC / Lean Six Sigma in the framework cheat.
- Every scorecard competency maps to a story or is flagged as a gap with a pivot.
- Model answers follow BLUF (assert structure: first sentence is the answer; a result/number
  appears; a relevance sentence ties to the JD).
- Gap-pivots never emit an unsupported credential (no "Six Sigma certified" unless in source).
- Run: `python scripts\smoke_test.py`, `python tasks.py validate`, `python tasks.py source-lint`.

## Verification
- Generate the cheat sheet and detailed guide against a saved Solutions Consultant / discovery
  JD (e.g., a Dematic-style posting). Confirm the scorecard lists the right competencies, each
  has framework words and a mapped real story, the model answers are BLUF, and the hardware/Six
  Sigma-style gaps produce honest pivots.
- Christian reads the output; nothing claims experience or credentials he does not have.

## Guardrails
- Truthful only; gap-pivots for real gaps; stories sourced from the evidence ledger.
- Reuse existing extraction and generators; one focused feature, phased if large (scorecard +
  cheat map first, then answers/pivots, then render).
- Do not stage generated outputs, active jobs/ files, or spec docs.
