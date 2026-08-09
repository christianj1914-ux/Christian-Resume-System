# Master Plan: Interview Story Generator and Daily Rehearsal System

This is the coordinating document for two related but independent systems. Hand this to Claude or Codex first. `Study/CODEX_SPEC_story_bank_expansion.md` remains the detailed component reference for the generator work.

---

## 1. The two systems, and why they must stay separate

| | Generator | Study rehearsal layer |
| --- | --- | --- |
| Purpose | Select the right stories for one posting | Christian rehearses and memorizes |
| Unit count | 25 `StoryCard` objects | 22 numbered stories |
| Source of truth | `scripts/build_interview_cheat_sheet.py` | `interview_prep/Christian Estrada - Project Delivery Interview Stories.md` |
| Changes per posting | Yes | Never |
| Numbering | None (internal keys) | Stories 1 through 22 |

**The 22 versus 25 distinction is load-bearing.** The generator's 25 cards are the 22 numbered stories plus three unnumbered lane-fit alternates:

- `East West ERP ownership` (alternate framing of Story 11)
- `Aptean lifecycle delivery` (alternate framing of Story 12)
- `Failure lesson and stronger validation` (alternate framing of Story 9)

These three exist so the generator can pick the better-fitting framing per posting. They are deliberate near-duplicates. **They must never receive story numbers or appear in the desk card, flashcards, Daily Companion, Workbook, or rehearsal workbook.** Putting three confusable twins into a set Christian drills by number would recreate the exact selection problem this work exists to fix.

`25` belongs in code, comments, diagnostics, and tests. It must not appear in rehearsal materials.

---

## 2. Why this work exists: two silent-failure defects

Both were found by measurement, not by reading code. Both share a shape worth remembering: **a check passed while the system was broken.**

### Defect A: evidence gating deleted stories from generated guides

Story cards were filtered against the text of the tailored resume for the posting. A card whose exact evidence phrases were absent was dropped with no warning, no log line, and no test failure.

Audited against the actual Procare resume, the interview that prompted this work: **10 of 18 cards dropped**, including four of the five headline stories (EFT/ACH, inventory 78/22, $1M recovery, SMS). Only Amazon Robotics survived from the headline five. Christian prepared from an 8-story guide believing it held 18.

Two root causes, and only one is a bug:

1. **Brittle phrasing.** The concept was on the resume; the exact string was not. `Approved Manufacturer`, `cutover coordination`, `user acceptance`, `200+`, `60+ executive workshops`, `upgrade readiness`, `Service Cloud`. These are defects.
2. **Layout deciding credibility.** The `$1M` and `Truist` stories dropped because those bullets did not fit that resume, not because Christian cannot defend them. A two-page constraint was silently narrowing his interview preparation. This is the architectural error.

### Defect B: workbook parser absorbed non-story sections

The workbook builder split the markdown bank on `## Story N:`. Any section that was not a story got absorbed into the preceding story. Story 22's PREP mode had swallowed 8,698 characters of PREP guidance and lane guides; Story 2's Short mode had swallowed the philosophy-first Bonus. Raw markdown markers rendered into the Word output.

**A page-density scan flagged the anomaly and it was reported as clean anyway.** That is the rule below.

### Standing rule

> Any anomaly, density outlier, unexpected count, or odd page must be investigated before an artifact is reported as clean. A passing scan is not sufficient when it flags something unusual. Chase the odd number.

---

## 3. Generator workstream: four ordered gates

Order is a dependency, not a preference. Gates 1 and 2 exist so that Gate 3's effects are attributable.

### Gate 1: Mechanical stabilization (behavior-preserving)

- Isolate the unrelated uncommitted `smoke_test.py` work (+1,162 lines, 22 resume-subsystem tests). Do not discard it.
- Add `boost_key` and `sensitive_note` to `StoryCard`.
- Migrate every title-string identity lookup: `quantified_story_boost()`, `story_theme_key()`, and **both** lane-keyed dictionaries inside `signature_story_for_checklist()` (`quantified_priority_titles`, `priority_titles`).
- Make `LaneLeadIn` the single source of lane opener, proof, backup order, and checklist priority. `signature_story_for_checklist()` reads from it and carries no separate lane-to-title table. These were the same concept implemented twice and would have drifted.
- Register theme keys for every card, including the two currently returning `"default"`.
- Wire story type `Process Improvement`, currently dead metadata. Add a comment distinguishing it from the targeting lane key `process_improvement`.
- Cap the five unbounded pool consumers: cheat sheet 3668, 3676, 3865, 4045; detailed guide 2020. Compact surfaces at 12, detailed at 15. Existing five- and six-card slices stay.
- Verify ordering invariance against an **explicit fixed 18-card list** and a fixed job description. Do not derive the pool from a posting; Gate 2 changes what is in the pool, and the two tests would contradict.

### Gate 2: Evidence architecture

- Eligibility gates on `question_prep.approved_source_resume_text()`, the union of both approved source resumes. This is the honest test of what Christian can defend.
- Generated tailored resume text becomes a **ranking boost only**. It must never remove a source-supported story.
- Do not build Implementation-versus-Pre-Sales eligibility machinery. Measured: both produce identical results (16/18).
- Reuse `source/evidence_terms.py` for concepts, variants, anchors, provenance, and strength. It already models what the story bank was failing to do with raw substrings.
- Phrase-aware or word-boundary matching everywhere. Naive substring matching means `ACH` matches "approach".
- Report source-unsupported cards separately from source-supported cards merely absent from the tailored resume.

#### Evidence-term policy: one class, no short aliases

The two-class model (registered short aliases versus raw fallback terms) was proposed to resolve an apparent contradiction: `QBR`, `UAT`, and `80+` are under five characters yet appeared in the repair table. **That machinery turns out to be unnecessary, and building it would be solving a problem created by the architecture this plan is replacing.**

Short aliases were only ever needed because the old gate ran against the *generated* resume, where long forms get cut for space. Against the approved source union, the long forms survive. Measured:

| Short alias | Long-form replacement | Length | In source union |
| --- | --- | --- | --- |
| `UAT` | `user acceptance` | 15 | Present |
| `QBR` | `executive business review` | 25 | Present |
| `80+` | `client engagements` | 18 | Present |
| `150` | `150+ users` | 10 | Present |
| `$1M` | `at-risk annual revenue` | 22 | Present |
| `$6M` | `book of business` | 16 | Present |
| `SMS` | `text messaging` / `liveengage` | 14 / 10 | Present |
| `78%`, `22%` | `inventory adjustment` | 20 | Present |
| `KPI` | `dashboard` / `power bi` | 9 / 8 | Present |

**The rule is therefore singular.** Every evidence term on every card must:

- be at least five characters;
- be matched as a complete phrase or word-boundary-safe token, never a bare substring;
- be verified present in `question_prep.approved_source_resume_text()`.

No alias registry, no concept-resolution path, no two-tier match, no boundary rules for tokens ending in `+` or `%`. One rule, one test.

`source/evidence_terms.py` remains the provenance and documentation ledger and should still be consulted when choosing terms, but the generator does not need an alias-resolution code path against it.

**Verified:** a full single-class term set for all 18 current cards passes the source union 18/18 with zero terms under five characters. The mapping is in the repair table below.

**Note for Codex on why this matters beyond simplicity.** The seven short terms already on existing cards (`$1M`, `$6M`, `150`, `SMS`, `78%`, `22%`, `KPI`) were not mentioned in any prior plan. Under the two-class model's own test they would have failed immediately on first run, the same red-test-on-arrival as the `Process Improvement` dead metadata. The single-class rule disposes of all seven with verified replacements instead.

**Verified brittle-term repairs.** All replacements confirmed present across both source resumes and the generated outputs tested:

Full single-class term set for all 18 current cards. Verified 18/18 against the approved source union, zero terms under five characters.

| Card | Evidence terms |
| --- | --- |
| EFT/ACH payment integration replacement | `payment`, `integration` |
| High-volume inventory automation | `inventory adjustment` |
| Aptean rapid product learning | `concurrent`, `client engagements` |
| $1M+ account stabilization | `at-risk annual revenue` |
| 200+ dashboards and decision visibility | `dashboard`, `power bi` |
| 60+ workshops and QBRs | `executive business review` |
| East West ERP ownership | `five sites`, `enterprise system` |
| East West Salesforce visibility | `salesforce` |
| Salesforce backlog and release coordination | `salesforce`, `marketing cloud` |
| Zero-to-one SMS support channel | `liveengage`, `text messaging` |
| Aptean lifecycle delivery | `requirements`, `implementation` |
| Operations versus finance alignment | `finance`, `engineering` |
| Failure lesson and stronger validation | `validation` |
| Customer loss and proactive success lesson | `at-risk annual revenue` |
| 13-month modernization complexity | `implementation`, `go-live` |
| UAT defect catch before go-live | `user acceptance`, `go-live` |
| CEO hardware scoping conversation | `hardware`, `infrastructure` |
| New warehouse and Amazon Robotics systems launch | `amazon robotics`, `warehouse` |

The seven new and reframed cards in Gate 3 must follow the same rule. Candidate terms already verified present: `training`, `adoption`, `migration`, `validation`, `go-live`, `cross-site`, `five sites`, `client engagements`.

`stakeholder` was rejected because it passes at source but is absent from the generated Advantive resume. Source presence is necessary but not sufficient.

**Preserve genuine absence.** SMS stays unavailable where no messaging evidence exists. Do not force it into an ERP guide.

**Measured acceptance targets** (all verified, not estimated):

| Checkpoint | Target |
| --- | --- |
| Procare generated-resume gate (the defect) | 8/18 |
| Approved source union, current terms | 16/18 |
| Approved source union, after repairs | 18/18 |
| After expansion | 25/25 |

**Fixture** (already committed):

```
scripts/fixtures/interview/procare_generated_resume.txt
```

Resolve as `Path(__file__).resolve().parent / "fixtures" / "interview" / "procare_generated_resume.txt"`. Never from the working directory, never from `output/`, which is not source truth and can be cleaned. The fixture self-validates: old gating logic against it reproduces 8 of 18 exactly.

### Gate 3: Card expansion

Add five confirmed stories (Mexico cross-site, parallel-workstream prioritization, churn redirect, migration setback, communication feedback) and two reframes (East West end-to-end, both-sides breadth). Register stable key, theme key, bridge, ledger-backed evidence, signals, and story types together in one commit.

Selection behavior:

- `story_for_type()` becomes profile-aware for failure selection. Implementation and delivery gets the migration setback; customer success gets the customer-loss lesson; fallback is stronger-validation. Keep a profile-free fallback for utility callers.
- Preserve the five-card hero budget.
- Guarantee one `Challenge and Failure` and one `Persuasion` or `Opposing Views` in the hero set.
- Mutual exclusion: never both Robotics cards, never both East West cards.

### Gate 4: Rendering

- Compact cheat sheet: active lane lead-in in full, other documented lanes as a one-line index.
- Detailed guide: active lane in full, others compact, above the story pages.
- `sensitive_note` (the layoff line) renders only on the detailed East West story page.
- Confirm checklist priority and lead-in priority read the same `LaneLeadIn` records.

---

## 4. Study rehearsal workstream

Independent of generator behavior by design. This is the insurance: even if the generator work slips, Christian cannot walk into an interview with half his material missing.

### Current state, all complete and verified

| Artifact | State |
| --- | --- |
| `interview_prep/...Project Delivery Interview Stories.md` | 22 stories, four modes each, lane lead-in guide |
| `Study/Daily_Interview_Rehearsal_Workbook.docx` | 55 pages, generated from the bank |
| `Study/Interview_Story_Card.docx` | Two-sided desk card with lane selector |
| `Study/Interview_Story_Bank_Improvement_Plan.md` | Corrected diagnosis, measured Procare audit |
| `Study/Interview_Gap_Stories_Drafts.md` | Superseded header, mapped to Stories 6 to 10 |
| `Study/Interview_Story_Tightening.md` | Coaching preserved, numbering reconciled |
| `Study/Daily_Companion.md` | Deck list, rotation drill, lane instruction |
| `Study/Personal_Operating_Workbook.docx` | Deck list, interview deck line |
| `Study/IT_Flashcards_InterviewStories.txt` | 62 cards |
| `Study/IT_Flashcards_ALL.txt` | 865 by exact concatenation |
| `Study/IT_Flashcards.apkg` | 17 decks, original deck and model IDs preserved |

### Workbook structure

Seven-item Daily Core (spine, differentiator, umbrella pitch, method sentence, layoff line, philosophy-first project method, compress rule and five tells). Eleven-day rotation, two stories daily, each day pairing one hard-evidence story with one human story. Per-story pages carrying covered-page recall, competencies tested, anchor facts, all four modes ordered PREP to CART, follow-up probes, a rep-scoring table, and ruled notes. Lane mock loops. Competency coverage map against the eleven-item `COMPETENCY_TAXONOMY`. Rep log.

**Lane mock loops: five lanes, four documented lead-ins.** The builder carries five loops (Implementation and Delivery, Customer Success and Account Management, Analytics and Operations, Solutions Consulting and Pre-Sales, Change Enablement and Process Improvement). The story bank documents exact first lines for only four lanes, and Analytics and Operations is not one of them. Do not invent a first line for it; label it as having no documented lead-in and point to the nearest documented lane.

A loop is a rehearsal of an interview, not a playlist of stories. Each must carry: the lane's exact first line where one is documented, the ordered story sequence, a six-question interview run (tell me about yourself, walk me through your most relevant project, a failure, a disagreement, why this role and your first 90 days, your questions for me), and after-loop self-review prompts. A story sequence plus a one-line lens is not a mock loop.

### Memorization method

Built for a top-down, pattern-driven, non-linear thinker for whom rote sequencing is a documented friction point. Memorize **one spine and 22 hooks**, not 22 scripts. The only rote content is numbers and nouns. Attach meaning before chronology. Claim-first is permission to skip the narrative order. Work modes shortest to longest so the hook forms first. Rehearse alone, out loud, and stop when it starts draining.

The philosophy-first project-method answer is a generalized Daily Core item, not a numbered story.

### Workbook builder rules

Terminate each story at the **next heading of any kind**, not only the next `## Story N:`. The bank contains non-story `##` sections and they will otherwise be absorbed into the preceding story.

---

## 5. Validation

```
python scripts/smoke_test.py
python tasks.py validate
python tasks.py claude-packet --mode interview
```

Then build Procare, implementation, and customer-success guides and render them.

### Generator tests

No card returns `"default"` from `story_theme_key()`. No unknown story types and no unused ones. Unique non-empty boost keys. Fixed-list ordering invariance against an explicit card list. Source-union eligibility at 25/25. Procare fixture retains all source-supported cards. Generated presence affects ranking but not eligibility. Hero behavioral coverage. Mutual exclusion. Lane lead-in completeness with resolvable card keys. Bounded output surfaces.

Evidence-term tests specifically:

- **No evidence term on any card is under five characters.** One assertion, no exemption list, no alias registry to consult.
- No evidence term terminates in a non-word character such as `+` or `%`.
- Every term matches as a complete phrase or word-boundary-safe token. Assert that a term cannot be satisfied by a substring of a longer word.
- Regression for the known trap: assert `ACH` cannot satisfy a card by matching "approach".
- Every term is present in `approved_source_resume_text()`.

### Workbook tests

No raw markdown headings, emphasis markers, or rules in rendered text. Exactly 22 numbered stories. No generator-only alternate present. Rotation covers 1 through 22 exactly once. Four modes on every story. 22 scoring tables, 22 note blocks, 22 follow-up sets. Four lane loops. Philosophy-first answer in the Daily Core. No unexplained page-density anomaly.

Render every page and inspect. Fix, then render and inspect again.

---

## 6. Out of scope

- No resume or cover-letter generation changes.
- No new targeting lanes.
- No PDF outputs unless separately requested; Word is the deliverable.
- No unsupported metrics, ownership, tools, or outcomes. Every claim traces to documented anchor facts.
- No propagating `25` into rehearsal materials.
- No rewriting completed Study artifacts. If one appears to need editing, that is evidence of drift; diagnose first.


---

## Appendix A: Story-to-competency mapping (workbook)

Verified against `interview_intelligence.COMPETENCY_TAXONOMY`: all 22 stories mapped, no unknown competency names, no taxonomy entry left without a story. Use this directly in the workbook builder rather than re-deriving it, and reject any competency name not in the taxonomy.

| Story | Competencies |
| --- | --- |
| 1 | Implementation and integration, Stakeholder alignment, Project delivery |
| 2 | Project delivery, Implementation and integration, Stakeholder alignment |
| 3 | Process improvement, Data and analytics |
| 4 | Customer relationship building, Stakeholder alignment |
| 5 | AI adoption, Process improvement, Adaptability / fast ramp |
| 6 | Stakeholder alignment, Customer relationship building, Implementation and integration |
| 7 | Project delivery, Requirements translation |
| 8 | Customer relationship building, Discovery, Stakeholder alignment |
| 9 | Implementation and integration, Project delivery, Data and analytics |
| 10 | Adaptability / fast ramp, Stakeholder alignment |
| 11 | Implementation and integration, Project delivery, Requirements translation, Stakeholder alignment |
| 12 | Adaptability / fast ramp, Implementation and integration, Customer relationship building |
| 13 | Data and analytics, Requirements translation, Discovery |
| 14 | Stakeholder alignment, Customer relationship building, Requirements translation |
| 15 | Discovery, Stakeholder alignment, Project delivery |
| 16 | Project delivery, Implementation and integration |
| 17 | Discovery, Stakeholder alignment, Technical fluency gap |
| 18 | Customer relationship building, Discovery |
| 19 | Process improvement, Data and analytics, Adaptability / fast ramp |
| 20 | Requirements translation, Project delivery, Process improvement |
| 21 | Stakeholder alignment, Discovery |
| 22 | Adaptability / fast ramp, Discovery, Implementation and integration |

## Appendix B: Per-story rep-scoring rubric (workbook)

The rubric is **the five tells**, not a separate positive-criteria list:

| Tell | Meaning |
| --- | --- |
| Buried outcome | The result did not arrive by sentence two |
| Stream of consciousness | Narrated the timeline instead of leading with the claim |
| Hedging | "I guess", "kind of", "just" |
| Warm-up wandering | Setup before the point |
| Volunteering salary | Raised compensation unprompted |

This must stay the five tells because it is already the tracked rubric in three other artifacts, verified: `Daily_Companion.md` (5 of 5), `Interview_Story_Card.docx` (5 of 5), and `IT_Flashcards_InterviewStories.txt` (5 of 5). Introducing a second five-item rubric in the workbook would leave Christian tracking two different scales, and the plan correctly forbids editing those three artifacts to match. Score each rep by tallying tells, plus time and a clean-pass box.


---

## Decision Log

Locked decisions with their rationale. Recorded here so they survive a lost chat session and do not get re-litigated.

### D1. Lane mock loop set: keep the current five (LOCKED)

**Decision:** Implementation and Delivery, Customer Success and Account Management, Analytics and Operations, Solutions Consulting and Pre-Sales, Change Enablement and Process Improvement.

**Rejected:** the proposal to swap Change Enablement out for Program Management in order to align all five loops with the four documented bank openers.

**Rationale, from `scratch/applications.csv`, 138 classified applications:**

| Lane | Applications |
| --- | --- |
| Implementation and Delivery | 67 |
| Change Enablement and Adoption | 21 |
| Pre-Sales and Solution Consulting | 15 |
| Analytics and Operations | 15 |
| Customer Success and Retention | 12 |
| Corporate Strategy and Consulting | 6 |
| Program and Delivery Management | 2 |

The current five cover 130 of 138 applications (94 percent). The proposed swap covers 111 of 138 (80 percent) and would drop the second-most-applied lane (21 applications) to add the least-applied one (2 applications).

**The principle:** loop selection follows where Christian actually interviews, not where the bank happens to have openers written. Optimizing the loop set to match existing documentation is letting the artifact drive the strategy.

### D2. Two lanes needed openers (CLOSED)

The real gap D1 exposed was not which loops to keep. It was that **26 percent of application volume sat in lanes with no documented opener**: Change Enablement and Adoption (21 applications) and Analytics and Operations (15).

**Resolved.** Both openers are now written into `interview_prep/Christian Estrada - Project Delivery Interview Stories.md` under "Role-tailored lead-ins by lane", assembled from existing story claims rather than invented:

- `Change enablement and process improvement`: opens on Story 6 (went live ready, not just installed), proves with Story 3 (78 and 22 percent). Backups 19, 20, 10, 11, 21.
- `Analytics and operations`: opens on Story 13 (decision before data), proves with Story 3. Backups 19, 9, 20, 21, 14.

The bank now documents **six lanes**, and every one of the five workbook loops maps to a documented opener. Nothing needs to be invented or marked as missing.

Both carry an explicit `Avoid` guardrail, because both lanes invite overreach. Change enablement must not claim change management certification, culture or values work, operating model transformation, or people leadership. Analytics must not imply data science, statistical modeling, or machine learning ownership; the supported ground is SQL, Crystal Reports, Power BI, KPI and operational reporting, and ERP data extraction and validation.

### D3. Program and Delivery Management keeps its bank opener, gets no loop

Two applications does not justify a rehearsal loop. The documented opener stays in the bank so it is available if that lane picks up.
