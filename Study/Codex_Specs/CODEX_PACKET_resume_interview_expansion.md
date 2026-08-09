# Codex Packet: resume-bullet and interview-prep expansion

Covers the system-wide work behind the source-resume expansion and interview-story additions
Claude made this session. Claude did the static, content-side pieces (source bullets and the
authored story/advice docs). Codex owns the generator integration, committing, and validation,
because Claude's sandbox cannot run builds reliably.

## What Claude already did (content side, no generator changes)

- Source resumes (`source/Estrada_Resume_Implementation.docx` and
  `source/Estrada_Resume_PreSales_CSM.docx`), all uncommitted:
  - Degree corrected to "Master of Science, Information Systems".
  - Four overloaded bullets tightened; "technology adoption", "Process Management",
    "Customer Service", and "core training programs" surfaced truthfully.
  - Seven net-new bullets added to both lanes: ERP access governance / least-privilege,
    compliance-audit support, weekly training cadence, inventory + Approved Manufacturer List
    automation carrying the 78/22 metric, structured project-delivery, Aptean pre-sales
    (hundreds of RFP/RFI/SOW, make-to-order and food-and-beverage verticals, ~$80K avg deal),
    and Aptean training cadence. "PMP (in progress)" added to Professional Development.
  - No Six Sigma, Scrum, Salesforce, or AWS certifications claimed (none are completed).
- Interview content authored as static docs in `output/` (all hand-maintained markdown):
  - "Christian Estrada - Project Delivery Interview Stories.md": five core stories (EFT/ACH,
    warehouse + Amazon Robotics, 78/22 automation, $1M at-risk recovery, zero-to-one SMS
    channel) in the system's Hook-Noticing and CART modes with short variants.
  - "Christian Estrada - 10-Minute Pre-Interview Checklist.md": run-before-the-call one-pager
    (anchors, lead-first answer shape, three outcome-first questions, signature story, company
    hypothesis, presence, close).
  - "Christian Estrada - Interview Answer and Question Bank.md": Part A, sixteen common ERP /
    consulting / project-manager questions with lead-first openers and the anchor story/number
    for each; Part B, the questions-to-ask bank ordered outcome/problem first.
  - "Christian Estrada - Daily Confidence and Consultative Delivery Practice.md": added a
    "How to sell your projects (stop underselling)" section, a "Your conversion pattern (from your
    own debriefs)" section, and a morning-sequence pointer to the checklist and bank.
  - A combined printable Word version of the three interview-prep docs was also produced.

## Item A: commit and integrate the source-resume changes

- Commit the two `source/*.docx` files as a focused content commit, separate from the code
  commits already landed.
- Confirm the seven new bullets pass the F3 `BULLET_OVERLOADED` warn rule (they were written
  under the thresholds) and that per-lane budget selection surfaces the right ones per JD.
- Register the newly-real proof anchors so the generator can surface them beyond the resume:
  add the 78/22 automation and the ~$80K / hundreds-of-RFP pre-sales figures to the proof-anchor
  sources used by `question_prep.py` (`brief.top_proof_anchors` / `strongest_direct_proofs`,
  around line 1089) and any evidence/keyword maps that gate cover-letter and interview proof
  selection, so cover letters and interview answers can cite them, not just the resume.

## Item B: interview story bank (the system-wide home for the five stories)

- Audit `expanded_story_bank()` (`scripts/build_interview_cheat_sheet.py:2767`) against the five
  core stories. Add a `StoryCard` for any that is missing (likely the two project-delivery
  stories and the SMS channel; 78/22 and $1M recovery may already exist).
- For each card, set `evidence_terms` so `supported_story_bank(resume_text)` (line 3020, via
  `contains_all(resume_text, card.evidence_terms)`) selects it only when the matching evidence is
  actually in the rendered resume. Tie the terms to the new bullets, for example: EFT/ACH ->
  "EFT/ACH", "Truist"; warehouse -> "Amazon Robotics", "warehouse"; automation -> "78%", "22%",
  "Approved Manufacturer"; recovery -> "$1M", "$6M"; SMS -> "LiveEngage", "SMS".
- Verify each card renders correctly through the existing spoken-story path and the
  `answer_framework_selection` logic (Hook-Noticing default, CART for consulting/senior), so the
  generated cheat sheet and detailed guide match the phrasing in the authored stories doc.

## Item C: bake the "sell don't undersell" advice into the generators

- Move the six selling habits and the reframe from the static daily-prep file into the interview
  generators so they persist across regenerations: `build_general_advice.py` (`build_general_advice`
  at line 170) and/or `build_interview_cheat_sheet.py` and `build_detailed_interview_guide.py`,
  wherever delivery/answer guidance is emitted.
- Decide whether the daily-prep doc should become generated or stay a hand-maintained file. If it
  becomes generated, migrate the new "How to sell your projects" section into the generator and
  keep the existing warm, practical voice. If it stays static, leave it as-is and just ensure the
  same advice appears in the generated guides.
- Keep it consistent with the existing anchors ("I am not selling myself, I am diagnosing their
  problem") and the hedge-count drill, so it reinforces rather than duplicates.

## Item D: replace the canned, context-stripped story opener (this is the main interview undersell)

Finding, from reading the generated Dematic cheat sheet and Guidehouse detailed guide: the
ownership voice is already strong (61 active "I <verb>" constructions, 0 passive in one guide),
and some answers sell judgment well ("I named the problem directly to leadership instead of
softening it"). The underselling comes from the opener. The spoken story hook repeats
"There was a project where the challenge was ..." (21 times in one guide), cycling through
"there was a moment where" / "there was a stretch where" variants. That formula sounds scripted,
strips the company out, and buries the number in a separate anchor field instead of the hook.

Locations:
- Opener clause variants: `scripts/build_interview_cheat_sheet.py:266-277`
  (`f"{company_clause}there was a project where"` and siblings).
- Story hooks: the `hook=` fields on each `StoryCard` in `expanded_story_bank()`
  (`scripts/build_interview_cheat_sheet.py:2772-2980`), currently phrased "The challenge was ..."
  and abstracted to generic "ERP" / "enterprise systems".

Fix:
- Lead each hook with the anchor number and the concrete stakes, and name the company. Prefer a
  concrete "At {company}, {stakes}" opener over the generic "there was a project where" formula.
  Example: replace "The challenge was standing up an entirely new warehouse facility in the
  enterprise systems" with "At East West, we stood up a new warehouse and Amazon Robotics program
  that had to be production-ready by go-live."
- Make sure `company_clause` is actually populated so the company is named, not dropped.
- Align the rewritten hooks with the five authored stories in
  `output/Christian Estrada - Project Delivery Interview Stories.md` so the guide and the
  rehearsal doc say the same thing.
- Cut the opener-variant cycling; concreteness reads as natural, rotating "there was a ... where"
  phrasings does not.

Tests: assert generated story openers name a company and include the story's number when it has
one, and that no more than a small threshold of openers per guide use the generic
"there was a ... where" template.

## Item E: make the recurring delivery pattern a standing part of every guide

Finding, from analyzing the owner's actual debrief history (`jobs/debrief_history.txt`,
`jobs/interview_debriefs/`): the losses are delivery, not content. Interviewers consistently rate
him "qualified, relevant, worth advancing" and praise the resume and experience, then decline on
delivery: "too long, loose, and reactive rather than crisp and consultative," "you didn't lead
with the simplest answer," "answers buried the point," "adjacent examples before the closest
direct proof," "questions too tactical," and no question asked when invited. Every "better
version" in the debrief was shorter than what he said. This is the conversion gap and it is
stable across interviews, so it should be a standing feature of the guides, not just per-debrief
coaching from `build_debrief_analysis.py`.

Encode into `build_interview_cheat_sheet.py` and `build_detailed_interview_guide.py`:
- A standing "Delivery watch-list" block on every guide, derived from the recurring debrief
  coaching signals: lead first (answer in sentence one), one closest example then stop (trim 30 to
  40 percent), name ownership explicitly, cut filler and restarts, be declarative.
- Enforce lead-first in generated model answers: sentence one states the answer and the ownership
  line, then one example, then the outcome, then stop. This makes the existing debrief "answer
  strategy" a generation constraint, not just printed advice. Add a soft length cap per model
  answer so answers do not sprawl.
- A curated "High-impact questions to ask them" bank surfaced on every guide, ordered so outcome
  and role-success questions come first (what does success look like in the first few months,
  where does this role most often struggle, who are the stakeholders and what do they care about)
  and tactical/tooling questions come last or move to follow-up email. This directly fixes the
  "no questions" and "questions too tactical" debrief signals.
- Feed the recurring pattern forward: have `build_debrief_analysis.py` aggregate repeated coaching
  signals across debriefs into a persistent "known delivery pattern" that the guide builders read,
  so the same lesson is not re-learned each interview.

Tests: assert every generated guide includes the delivery watch-list and the ordered
questions-to-ask bank, and that generated model answers put the answer/ownership line in the first
sentence.

## Item F: interview-prep artifacts and answer-to-story mapping

Turn the static prep docs into generated, per-role artifacts so they stay tailored and current.

- Generate a per-role one-page pre-interview checklist (mirror
  `output/Christian Estrada - 10-Minute Pre-Interview Checklist.md`) as a `.docx`: the two anchors,
  the lead-first answer shape, three outcome-first questions, one signature story chosen for the
  role's lane, a company-hypothesis line drawn from the JD or company notes, presence reminders,
  and a deliberate close. Wire it into the interview build path (`build_interview_cheat_sheet.py` /
  `build_detailed_interview_guide.py` or a small new builder).
- Map common questions to the closest anchor story so generated model answers stop reaching for an
  adjacent example (the debrief "wrong example first" signal). Codify the Part A mapping from the
  Answer Bank: walk-me-through -> Aptean Encompix full lifecycle; scope creep -> SOW/FRD scope
  control; data or go-live risk -> EFT/ACH plus validation discipline; failure -> the
  "resolved every technical issue but still lost the account" story; ambiguity -> structured
  discovery-to-go-live; largest project -> EFT/ACH or warehouse launch; why-the-role-ended ->
  reorganization stated in three sentences, no ramble.
- Add a "company hypothesis" prompt to each guide: one line from the JD or `jobs/company_notes` /
  `jobs/company_research.txt` that the candidate states early ("From the posting, your main
  challenge looks like X, is that close?"), with a safe fallback.
- Source the questions-to-ask block from the authored bank's Part B (outcome and problem first,
  stakeholder and bar next, tactical/tooling last or moved to follow-up email).

Tests: assert the per-role checklist artifact is produced, that each common-question model answer
uses its mapped anchor story, and that a company-hypothesis line appears in the guide.

## Item G: remaining refinements after the first implementation (found in testing)

Testing the committed generators (Randstad cheat sheet and per-role checklist) confirmed Items A-F
largely landed: the generic "there was a ... where" opener is gone (0 occurrences), the delivery
watch-list, consultative reframe, company hypothesis, outcome-first questions, and the per-role
`.docx` checklist all render, and the five flagship StoryCards exist with correct evidence terms
and concrete hooks. Two refinements remain.

- G1, finish the hook rewrite. The five new flagship cards (EFT/ACH, 78/22, $1M, SMS, warehouse)
  now open concretely, but the roughly thirteen older StoryCards still open with "The challenge
  was ..." (8 such hooks appeared in the Randstad guide, and the checklist signature story
  inherited one). Rewrite the remaining `hook=` fields in `expanded_story_bank()`
  (`scripts/build_interview_cheat_sheet.py`) to lead with the company and the number or operational
  stake, matching the five new cards. Test: assert no story hook starts with "The challenge was",
  and each names a company or leads with a number.
- G2, surface the flagship number-led stories. For the Randstad JD the top-five cards were
  200+ dashboards, Aptean lifecycle, 13-month modernization, 60+ workshops, and the warehouse,
  which pushed the EFT/ACH and $1M+ stories out of the top five even though the rendered resume
  supports both, and the checklist signature story defaulted to 200+ dashboards. Tune the story
  ranking so strongly quantified, differentiated stories (78/22, $1M+, EFT/ACH) compete for the
  top five on relevant lanes, and prefer a quantified story for the checklist signature slot.
  Test: for an analytics/process/delivery JD, at least one of 78/22 or $1M+ appears in the top-five
  cards and as the checklist signature story.
- G3, resolve the 78/22 coupling. The 78/22 story is filtered out for Randstad because its resume
  bullet (the inventory and Approved Manufacturer List automation bullet carrying "78%"/"22%") is
  not selected into the rendered Randstad resume, and `supported_story_bank` requires the evidence
  on the rendered resume. Decide between prioritizing that automation bullet in resume selection
  for analytics/process lanes (keeps resume-story integrity, recommended) or letting the story's
  evidence be satisfied by the registered proof anchor even when that bullet is not rendered.

## Related packets (the full plan is these three together)

- `CODEX_PACKET_prose_nested_list.md`: PROSE_NESTED_LIST repair convergence (build-breaker;
  underlying fix still queued behind the East West content stopgap).
- `CODEX_PACKET_systemwide_docfixes.md`: F0-F5 (degree guard, cover opener hook, qualifications
  generator, F3 bullet warn rule, F4 summaries, F5 cover-letter quality). F0-F3 landed; F4/F5
  remain, warn/golden-first then promote to fail with builder tightening in the same change.
- This packet (Items A-F): resume-bullet expansion plus interview story bank, selling advice,
  opener fix, standing delivery pattern, and per-role prep artifacts.

Recommended global order: finish the nested-list convergence and F4/F5 first (they touch shared
prose/cover/summary code), then land this packet's Items A-F.

## Guardrails

- Word (.docx) output only; no PDF-generation behavior.
- No invented experience: every claim traces to what the owner confirmed this session (certs are
  in-progress or knowledge only; keep them out unless completed, except "PMP (in progress)").
- Preserve the dirty tree and unrelated edits.
- Claude's sandbox reads are advisory; Codex's local smoke and builds are authoritative.

## Verification

- `python scripts/smoke_test.py` and `python tasks.py validate` stay green, with new coverage:
  the five story cards are selected when their evidence is present, and the new proof anchors are
  citable.
- Run `python tasks.py resume`, `python tasks.py cover`, and an interview build; confirm the new
  bullets render per lane, the 78/22 and pre-sales figures can appear in cover/interview outputs,
  the five stories surface in the interview guide in the right framework, and the selling advice
  appears.
- Confirm no PDF behavior was introduced.
