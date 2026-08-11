# CODEX SPEC: LinkedIn, Interview, and Study Updates from CS Hiring Signal

Date: 2026-08-10
Author: Claude (plan pass)
Branch base: `main` at `87eb19d`, suite 493/493
Input: `Linkedin Notes.docx`, a LinkedIn post by a CS hiring leader plus roughly twenty comments, and two appended posts on resume and profile craft

Three workstreams: LinkedIn profile generation, interview preparation logic, and study material. Each is independently committable.

---

# Part 0: Governing constraint, read before anything else

`.context/RULES_FOR_CLAUDE.md` states: **never use LinkedIn page content as source material**, and never invent claims, metrics, tools, responsibilities, or outcomes.

That rule is not in tension with this work, but the boundary has to be explicit because every change below is downstream of a LinkedIn document.

| Use | Allowed? |
|---|---|
| New resume bullet, metric, or evidence anchor sourced from the thread | **No.** Absolutely not, under any framing. |
| New `source/evidence_terms.py` entry justified by the thread | **No.** |
| Vocabulary for describing evidence that already exists in an approved source resume | Yes |
| Anticipating what a CS panel screens for, and preparing answers | Yes |
| Structural changes to LinkedIn profile composition | Yes |
| Study topics and reading direction | Yes |

**Test to apply at every step:** if the change would survive deleting the LinkedIn document and could be justified from the approved source resumes alone, it is in scope. If it needs the document to justify a claim, it is out.

A second caution on evidentiary weight: this is one hiring manager plus an unverified comment section. Treat it as directional market intelligence, not fact. One commenter explicitly pushes back, arguing that expectations are rising faster than compensation, which is a useful counterweight to reading the list as an objective bar.

---

# Part 1: LinkedIn (`scripts/build_linkedin_update.py`)

## 1.1 Current state, measured

The module has six content functions plus orchestration:

| Function | Line | Behavior |
|---|---|---|
| `headline_options()` | 21 | Hardcoded three options per lane, truncated to 119 chars |
| `about_section()` | 58 | One fixed three-paragraph template with `specialty` and `core_problem` interpolation |
| `featured_proof_points()` | 70 | Extracted from resume text |
| `skill_suggestions()` | 86 | Lane-driven |
| `recruiter_keywords()` | 107 | Lane-driven |
| `thought_leadership_themes()` | 111 | Lane-driven |
| `comment_strategy()` | 115 | Lane-driven |

The current About already carries source-supported metrics: 80+ client engagements, five sites and 150+ users, 200+ reporting tools, 60+ workshops and QBRs, and $1M+ in stabilized revenue. **None of those need to change.** They are the asset; only the arrangement is weak.

## 1.2 Gap against the four-part structure in the document

The appended post proposes: years of experience plus roles plus company types, then what you are specifically good at, then measurable examples, then a no-pressure call to action.

Measured gaps in the current `about_section()`:

1. **No years-of-experience opener.** The section starts with a capability claim rather than a credential frame.
2. **No company-type or scale framing.** The worked example in the document establishes context with "startups and global healthtech organizations with 60-2,000+ employees and up to $1.1B in revenue." Christian's equivalent is available from approved sources: manufacturing, enterprise software, and consulting environments, five sites, 150+ users, 80+ international client engagements.
3. **No call to action.** The section ends on an interest statement. The document's model ends with an explicit low-pressure invitation, which is the mechanism that converts a profile view into a conversation.
4. **Prose block rather than scannable proof.** The document's model uses a short bulleted list of career moments. The current version buries five strong metrics inside a single running sentence.

## 1.3 Phrasing risk

The document names specific AI-slop patterns to avoid, including "Transforming complexity into clarity."

The current `about_section()` opens with:

> "I help teams turn complex {specialty} work into usable outcomes"

That is uncomfortably adjacent to the named pattern. It is not identical and it is not dishonest, but it is the weakest sentence in an otherwise concrete section.

**Related finding:** the LinkedIn About text is **not** currently run through `utils.enforce_prose_quality()`. Cover letters, checklist narratives, and interview prose all pass through it. LinkedIn output does not. That is an inconsistency worth closing regardless of this document.

## 1.4 Changes

**1.4.1 Restructure `about_section()` into four labeled segments.**

Keep every existing metric. Change only arrangement and add the two missing segments.

- Segment 1: years of experience, role families, environment types. Derive from approved source resumes only.
- Segment 2: what he is specifically good at, lane-aware, using the existing `specialty` and `core_problem` interpolation.
- Segment 3: three or four measurable career moments as a bulleted list, drawn from the metrics already in the current template.
- Segment 4: a no-pressure call to action.

Implement as separate composable helpers (`about_credential_line()`, `about_capability_line()`, `about_proof_bullets()`, `about_call_to_action()`) so each can be tested independently and reused by lane. Do not build one longer f-string.

**1.4.2 Replace the opening sentence.** Lead with the credential frame from segment 1 rather than the capability claim. Keeps the concrete material first and sidesteps the flagged pattern.

**1.4.3 Route LinkedIn text through `utils.enforce_prose_quality()` in warn-only mode**, matching how checklist narratives are handled. Warn-only, not hard-fail: LinkedIn copy is user-edited before posting, so a hard gate is the wrong severity.

**1.4.4 Add a Time, Money, Team, Scope checklist section to the generated guide.** Not generated copy: a verification prompt listing each featured proof point with a checkbox for whether it states duration, financial or volume value, team size, and organizational scope. The framework in the document is a good match for the bullet rules the resume builder already enforces, and surfacing it in the LinkedIn guide makes the standard visible where it is currently implicit.

**1.4.5 Leave `headline_options()` alone for now.** The three `customer_success` headlines are source-supported and specific. There is an argument for adding a Builder-flavored variant, but headline space is 119 characters and the existing options already lead with concrete proof. Revisit only if a real posting makes the current set feel wrong.

**Validation:** `python tasks.py validate` at 493 or higher. Generate a LinkedIn guide against the active posting and confirm the About section contains all four segments, retains every metric present before the change, and produces no new prose-quality warnings beyond those already accepted.

Commit: `feat: restructure LinkedIn about section and add scope checklist`

---

# Part 2: Interview

## 2.1 Current state, measured

`build_interview_cheat_sheet.py` has substantial `customer_success` lane coverage already: a `LaneLeadIn` at line 115, `questions_to_ask` at 504, a business-impact translation line at 530, pitch and bridge language at 636 through 718, and lane-specific summary framing at 1449 through 1670.

`interview_story_engine.py` supports these story types:

```
Individual Achievement    Managing and Leading    Persuasion
Analysis and Decision     Challenge and Failure   Teamwork
Rapid Learning            Ambiguous Problem       Customer Disagreement
Process Improvement
```

## 2.2 Gap: there is no Builder story type

The post's second criterion is the one Christian can evidence most strongly, and the story engine has no slot for it.

"Can they turn a one-off solution into something repeatable" maps directly onto approved source material: core training programs, user enablement programs, workflow documentation, 200+ reporting tools, and process standardization across five sites. `Process Improvement` is the nearest existing type but it is not the same claim; process improvement is about making a thing better, builder is about making a thing reusable.

**Change:** add a `Repeatable Systems` story type to `interview_story_engine.py`. Map it to existing supported stories rather than authoring new ones. Add it to the `story_types` tuples of the stories that already carry enablement, training-program, documentation, or tooling evidence.

Do not write a new story. Retype existing ones.

## 2.3 Gap: no prepared answer for the commercial-acumen question

This is the highest-value item in this entire specification.

Commercial acumen is the most-repeated addition across the comment thread. Multiple commenters state they want to be walked through the retention number, the expansion identified, and the risk caught before churn.

`.context/RULES_FOR_CLAUDE.md` states that for CSM roles Christian may be framed as commercially aware and post-sale revenue-adjacent, but that direct quota ownership, exact NRR attainment, GRR attainment, and closed expansion dollars **must not be invented**.

So the single most-probed competency is the one where he has the least quantified proof. He will be asked. There must be a prepared, honest, non-apologetic answer, and it must be generated rather than improvised.

**Change:** add a commercial-acumen bridge answer to the `customer_success` lane in `behavioral_answer_scripts()`, built from supported evidence only:

- at-risk account recovery and churn-risk mitigation at Aptean, which the rules explicitly support
- $1M+ in stabilized annual revenue, already used in LinkedIn copy and therefore already source-backed
- executive business reviews and QBRs
- expansion **discovery** and account growth **conversations**, which the rules support, as distinct from closed expansion dollars

Structure the answer claim-first per the existing interview philosophy: what he owned, the proof, then an honest boundary on what he did not own. The boundary sentence is the point. A candidate who states plainly that they did not carry a quota, and then describes the retention work they did own, reads as more credible than one who blurs it.

**Add a golden test** asserting the generated answer contains no invented quota, NRR, GRR, or closed-dollar language. Reuse the existing unsupported-claim patterns in `config/language_rules.py` where they apply.

## 2.4 Add a competency decoder section

The document's most transferable insight is structural: behavioral questions are not asking for the most complete story, they are asking for the clearest evidence of one capability. A candidate can tell a complete, well-organized story and still fail, because the interviewer never heard the competency they were scoring.

**Change:** add a decoder section to the cheat sheet for `customer_success` and `presales_solution` lanes. For each common question, state the likely competency being scored and the one sentence that must appear for the evidence to land.

Seed it from the thread's named competencies, all of which are framing rather than evidence and therefore in scope:

| Competency | What it is scoring |
|---|---|
| Owner | Brought a recommendation without being asked |
| Builder | Turned one fix into something reusable |
| Executive presence | Pushed back on a senior stakeholder and kept the relationship |
| Signal literacy | Read the data before the customer reported the problem |
| Diagnostic judgment | Separated symptom from root cause and named what was in their control |
| Commercial acumen | Connected the work to retention or expansion |

Render as a short table in the generated document, not as prose.

## 2.5 Anticipated-question additions

Add to the `customer_success` question bank, phrased as the thread phrases them, since these are close to how they will actually be asked:

- "Tell me about a time you caught a problem before the customer raised it. How did you catch it?"
- "Walk me through a one-off save you turned into something repeatable."
- "Describe a time you disagreed with a VP or executive stakeholder."
- "How do you separate a symptom from a root cause when the outcome depends on teams you do not manage?"
- "Walk me through your book: retention, expansion, and risk."

The last one routes to the 2.3 bridge answer.

**Validation:** regenerate the cheat sheet and detailed guide against the active posting. Confirm the story diversity warning does not fire, the decoder table renders, and the commercial-acumen answer passes the golden test. Suite at 493 or higher.

Commit: `feat: add builder story type and CS competency decoder`

---

# Part 3: Study guides

## 3.1 Current state

```
Study/Guides/          Daily_Interview_Rehearsal_Workbook.docx, Job_Search_Playbook.docx,
                       Personal_Operating_Workbook.docx, Interview_Story_Card.docx,
                       IT_Cheat_Sheets.docx, IT_Learning_Path_and_Schedule.docx
Study/Notes/           Job_Search_Playbook.md, How_I_Think_and_Communicate.md,
                       Daily_Companion.md, People_and_Lanes_to_Follow.md, and others
Study/Interview_Story_System/
                       MASTER_PLAN_interview_story_system.md,
                       Interview_Story_Bank_Improvement_Plan.md,
                       Interview_Gap_Stories_Drafts.md, Interview_Story_Tightening.md
Study/Flashcards/      IT_Flashcards_InterviewStories.txt, _Communication.txt,
                       _DataAnalyticsBI.txt, _AIAdoption.txt, and others
```

## 3.2 Changes

**3.2.1 New note: `Study/Notes/CS_Hiring_Signal_2026.md`.**

Capture the thread's substance with an explicit provenance header stating that it is external opinion from one hiring manager and an unverified comment section, that it is **not** evidence, and that nothing in it may become a resume claim. That header is the thing that stops a future reader from mining it six months from now.

Include the counterweight comment about compensation. A digest that records only the demands reads as an objective bar, which it is not.

**3.2.2 Update `Study/Interview_Story_System/MASTER_PLAN_interview_story_system.md`** with the Builder story gap from 2.2 and the commercial-acumen bridge from 2.3. That file is the existing home for story-bank direction; do not start a parallel plan.

**3.2.3 Extend `Study/Flashcards/IT_Flashcards_InterviewStories.txt`** with the six competencies from the 2.4 decoder, one card each, framed as "question shape on the front, competency being scored on the back." This is drill material for the pattern the document identifies, and it costs nothing.

**3.2.4 Do not create a new study track.** The thread names data analysis, prompt engineering, and change management as valuable, and all three already have flashcard decks (`_DataAnalyticsBI`, `_AIAdoption`, `_AIEngineeringMLOps`, and change material inside `_MethodsAndFluency`). Adding a track would duplicate existing coverage.

**3.2.5 Verify every new Study path resolves.** `interview_intelligence.STUDY_TRACK_REFERENCES` and `QUESTION_THEME_TRACKS` are now path-verified with a smoke assertion. If any new file is referenced from code, it must exist, or the suite fails. That guard was added after all ten references broke silently.

Commit: `docs: add CS hiring signal digest and story system updates`

---

# Part 4: Sequencing and validation

1. **Part 2 first.** The interview work is the only piece with a live deadline attached to it, since it changes what he can answer in a real screen. It is also where the source-truth risk concentrates, so it deserves attention while fresh.
2. **Part 1 second.** LinkedIn is a standing asset, not time-critical.
3. **Part 3 last.** Study material documents decisions made in the first two.

**Global gates:**

- `python tasks.py validate` after every commit, never below **493**
- No change to `source/`, `source/evidence_terms.py`, or any resume evidence anchor in this specification. If a change appears to require one, stop: it means a LinkedIn-sourced claim has leaked into evidence.
- Regenerate the affected document after each commit and read it, rather than trusting the suite alone. Every quality problem in this area is one the tests were never written to catch.
- Run pyflakes, vulture, and the AST gate after any source-hygiene-adjacent edit.

**Explicitly out of scope:**

- Any new resume bullet, metric, or evidence term
- Changes to the 45 to 70 word summary contract
- Headline rewrites without a real posting to test against
- A new study track duplicating existing flashcard coverage
