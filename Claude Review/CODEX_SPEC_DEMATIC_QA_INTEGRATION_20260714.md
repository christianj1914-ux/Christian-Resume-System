# Codex Implementation Spec: Integrate Generalizable Dematic Q&A into the Prep Bank and Qualifications Generator
## July 14, 2026 - Fold the reusable answer patterns from the Dematic screen into shared generator content, gated by confirmed facts

## Summary

The Dematic recruiter screen (7/14/26, Jennifer Rose) surfaced several strong, reusable answer patterns and one delivery lesson. Christian wants the generalizable ones (not the Dematic-only specifics) folded into the shared interview prep bank and the qualifications-statement generator so every future posting benefits, not just Dematic.

Two generators are in scope:
- `scripts/build_standard_qualifications_statement.py` (deterministic coded answer functions keyed off the application questions and the approved source resume).
- The interview guide and cheat sheet generators (`scripts/build_detailed_interview_guide.py`, `scripts/build_interview_cheat_sheet.py`), which should carry the reusable answer templates and the delivery patterns.

Hard rule: this is a source-and-generator change, so every item must be classified before it ships. Anything not already in confirmed source truth and not already in the approved qualifications output must be gated for Christian's explicit confirmation before it becomes a generator claim. Claude planned this; Codex implements, and routes gated items back to Christian.

## Verified Seams and Corrections (2026-07-14, from a live-code trace)

A code trace corrected two load-bearing assumptions. These override any conflicting detail later in this spec.

**Correction 1 - the qualifications document does NOT delegate to `question_prep`; fix the shadow copy.** `scripts/build_standard_qualifications_statement.py` has its own local answer functions (`software_inventory_answer` line 252, `communication_answer` line 268) and its `answer_prompt` (line 281) calls those locals at lines 296 and 298. `scripts/question_prep.py` has a parallel set (`build_communication_or_implementation_answer` 1233, `software_inventory_answer` 1305, `software_inventory_answer_for_job` 1321, `communication_answer` 1334). Changing only `question_prep.py` would upgrade interview-prep answers but leave the qualifications statement document unchanged. Required fix: de-duplicate by making the qualifications builder delegate to `question_prep`. Concretely: change `answer_prompt` line 296 to call `question_prep.software_inventory_answer_for_job(job_description, resume_text)` (signature-complete, takes exactly those two args). For line 298, delegate to the no-arg wrapper `question_prep.communication_answer()` (line 1334), NOT to `build_communication_or_implementation_answer` directly. The wrapper already derives the PositioningBrief internally (`active_positioning_brief(job_description, resume_text)`) and calls `build_communication_or_implementation_answer(brief, "stakeholder communication")`, so delegating to it avoids making the qualifications builder construct a brief. One robustness note: `communication_answer()` currently reads the job description from `jobs/job_description.txt` rather than taking the caller's in-scope `job_description`. Extend `communication_answer` to accept OPTIONAL `job_description` and `resume_text` params (defaulting to the current file-read / approved-source behavior for existing no-arg callers), and have the qualifications `answer_prompt` pass its in-scope `job_description` and `resume_text` so the qual doc and interview prep use the same context. Put the FRD / confirm-in-writing upgrade content inside `build_communication_or_implementation_answer` (the single engine at line 1233) so both paths inherit it. If full delegation is judged risky, the fallback is to update BOTH copies and add a test asserting they stay in sync; delegation is preferred.

**Correction 2 - the qualifications software answer is not job-aware.** The local `software_inventory_answer(resume_text)` never receives the job description, so it structurally cannot trigger the automation "not PLC / not code" boundary. `job_description` is already in scope inside `answer_prompt`, so delegating to the existing `software_inventory_answer_for_job(job_description, resume_text)` (question_prep 1321) both fixes this and resolves Correction 1. The automation boundary logic itself goes INTO `software_inventory_answer_for_job`.

**Correction 3 - evidence plumbing is required, not optional (Christian confirmed "Both").** Verified: the two active commercial source resumes (`source/Estrada_Resume_Implementation.docx`, `source/Estrada_Resume_PreSales_CSM.docx`) contain none of barcode / scanner / least-privilege / access-control, and both generators read source-resume text via their own `approved_source_resume_text()` (qual builder line 101, `question_prep` line 133). `global_notes.txt` (`config/paths.py:32`, read by `question_prep.py:382`) is read by interview prep but NOT by the qualifications builder. Christian's decision (2026-07-14) is BOTH: add scoped lines for the two confirmed claims to the commercial source resume(s) AND to `source/global_notes.txt`. The resume edit reaches both the qualifications document and interview prep; the `global_notes` line reinforces interview prep. Keep barcode narrow (no conveyor, PLC, or automation-equipment inflation) and least-privilege scoped to access-control design plus incident backtracking. Do not touch the federal JSON source.

**Scope split.** The answer-shaping and evidence work above is Phase 3 (this spec). The output-pattern and debrief-overlay work (company snapshot, TMAY ladder in hr_screen, story-anchor table, First-90-Days glance block, debrief-to-prep overlay, cheat-sheet expansion) moves to Phase 4 (`CODEX_SPEC_PHASE4_PREP_PATTERNS_20260714.md`) so Phase 3 stays tight and shippable.

## Sequencing note

The qualifications-generator changes are independent and can proceed now. The interview-guide changes should layer on the scripted-answer model from `CODEX_SPEC_SCRIPTED_INTERVIEW_GUIDE_20260713.md` (Phase 1); do those after Phase 1 is merged so the reusable templates slot into `StoryAnswerParts` and the general-answer operating system rather than the old flat model.

## Item-by-item audit

Legend: **In-source** = already in confirmed source or the current qualifications output, safe to reuse. **Add** = generalizable and consistent with confirmed facts, integrate now. **Gate** = candidate-provided in the interview but not in confirmed source truth; requires Christian's explicit confirmation before it becomes a generator claim.

| # | Q&A pattern from the screen | Generalizable? | Target | Status |
|---|---|---|---|---|
| 1 | Software categorization opener: lead with category (business analytics + ERP configuration), list tools (Power BI, SQL, system config), state plainly "not PLC programming or code writing" | Yes | `software_inventory_answer` (line 252) | In-source (tools) + Add (the "categorize first, name the non-skills" framing) |
| 2 | FRD / confirm-in-writing practice: after live meetings, confirm scope in writing, widen the email chain to all stakeholders, request follow-up meetings | Yes | `communication_answer` (268) and a new stakeholder-alignment answer | In-source (present in current qual output) + Add (make it the lead proof for relationship/alignment questions) |
| 3 | "How do you build productive relationships with customers and internal stakeholders?" answered via the CEO-escalation ownership story | Yes | interview guide behavioral bank; qual "relevant experience" / communication | Add (anchor to confirmed client-recovery story) |
| 4 | "How do you get alignment when perspectives differ?" via map-current-process, replication documents, assess "consistently achievable", bring people in | Yes | interview guide behavioral bank | Add (must anchor to a concrete story, not stay abstract; this was the weak, methodology-only answer in the screen) |
| 5 | 30/60/90 template, answered first then validated ("Does that match what the team expects?") | Yes | interview guide general-answer operating system + a reusable first-90-days answer | Add |
| 6 | Experience-gap bridge: acknowledge the gap plainly, bridge to the East West fast-ramp story, then ask about onboarding | Yes (any "do you have experience with X" gap) | interview guide: a reusable gap-handling answer template | Add |
| 7 | Discovery-that-surfaced-a-hidden-risk story (infrastructure too outdated, "Windows 95 era") | Yes | hero-story bank | In-source (maps to the confirmed 13-month modernization; "Windows 95 era" is acceptable color) |
| 8 | Redirecting a client off an unattainable ask via SOW/FRD scoping | Yes | hero-story bank / behavioral | In-source (consistent with confirmed Aptean vendor-side work and the existing qual "expectation gap" answer) |
| 9 | Fast-ramp / "thrown into the fire" at East West on an unfamiliar Aptean config, then trained global teams | Yes | hero-story bank (ramp/adaptability) | In-source (consistent with confirmed Amazon Robotics certification ownership) |
| 10 | Compensation anchor "$105 to 115K base" | No, keep flexible | salary guide generator | **Resolved 2026-07-14: KEEP FLEXIBLE.** Do not hardcode a default range; salary answers stay general and decided per role. |
| 11 | Least-privilege security design at East West (restricting who can access which functions/screens after incidents caused losses; backtracked incidents and improved controls) | Yes | source truth (East West evidence) then qual/guide | **Resolved 2026-07-14: CONFIRMED by Christian. Add** as an authorized East West claim (access-control design + incident backtracking to improve controls). |
| 12 | Barcode-scanner hardware exposure (limited, tied to ensuring scanned items were reflected correctly in the software) | Yes | source truth + interview gap answer | **Resolved 2026-07-14: CONFIRMED as a resume claim.** Encode as limited barcode-scanner / hardware-adjacent exposure only; do NOT extend to conveyors, PLC, or automation equipment. |

## Implementation Changes

### A. Qualifications generator (`build_standard_qualifications_statement.py`)

- `software_inventory_answer` (252): restructure so the answer leads with the category summary, then the tool list, then an explicit boundary line naming what Christian does not do (for example PLC programming or code writing) when the posting is in an automation or engineering context. Keep the tool list sourced from the approved resume, not hardcoded per company.
- `communication_answer` (268): make the FRD confirm-in-writing practice the lead proof point (live meeting, written confirmation, widen the stakeholder email chain, proactive follow-up meetings), since it is Christian's clearest differentiator and generalizes to any stakeholder question.
- Add a reusable stakeholder-relationship / alignment answer that anchors to the confirmed client-recovery (CEO escalation) story rather than staying at the methodology level, and reuse it for both "build productive relationships" and "get alignment when perspectives differ" prompts.
- Leave `public_agency_experience_answer` (214) as is; the honest "0 years, but adjacent structured delivery" pattern already matches the screen.
- Least-privilege (item 11) is CONFIRMED (2026-07-14) and enters through the evidence step (scoped lines added to the source resume(s) and global_notes.txt), not as a hardcoded sentence in this function; the qualifications answer will surface it naturally once it is in the source resume text. Salary (item 10) stays FLEXIBLE: do not hardcode a range anywhere.

### B. Interview guide and cheat sheet generators

- Add three reusable answer templates that obey the Bumbling-to-Boardroom principles and slot into the scripted-answer model from the Phase 1 spec:
  1. First-90-days answer: state the 30/60/90 hypothesis first, then a one-line validate-with-the-team question. Never render it as a question back to the interviewer without the hypothesis first.
  2. Experience-gap bridge: acknowledge the gap in one sentence, bridge to the confirmed fast-ramp story, then a forward-looking onboarding question. Parameterize the gap so it works for hardware, a new platform, a new domain, and so on.
  3. Technical-framing opener (the software categorization): lead with the category, then tools, then the explicit boundary of what he does not do, for use whenever an interviewer's framing of "technical" is ambiguous.
- Ensure the four anchor stories (items 7 to 9 plus the CEO escalation) are present in the hero-story bank with meat-first cores and pushback branches per the Phase 1 spec. They already map to confirmed stories; this item is about coverage, not new claims.
- Reinforce BLUF in the general-answer operating system (already added by the Phase 1 spec): every answer opens with the direct answer, evidence after.

### C. Confirmation gate (RESOLVED 2026-07-14)

Christian confirmed the gated items:
- **Least-privilege security at East West: CONFIRMED.** Encode as an authorized East West claim: designed/tightened least-privilege access controls (who can access which functions and screens) after processing incidents caused losses, and backtracked incidents to improve controls. Keep wording to that scope.
- **Salary range: KEEP FLEXIBLE.** Do not hardcode a default range in the salary guide; keep salary answers general and per-role.
- **Barcode-scanner hardware: CONFIRMED as a resume claim,** but scoped to limited barcode-scanner / hardware-adjacent exposure tied to the software. Do NOT extend to conveyors, PLC, or physical automation equipment.

These update the authorized evidence set. Everything else in this spec proceeds. Any future claim beyond these still requires fresh confirmation.

## Guardrails

- No item may introduce a metric, dollar figure, named system, or responsibility beyond confirmed evidence ([[evidence-confirmations-2026-07-02]], [[story-confirmations-2026-07-08]]). Reuse the existing validation surface.
- Company-specific phrasing (Dematic, KION, Dematic iQ, AutoStore, conveyors, warehouse automation) stays out of the shared generators; only the generalizable structure is integrated. The generators must continue to produce role-specific equivalents from the current posting, not hardcode Dematic.
- All reused answers obey the Bumbling-to-Boardroom principles.

## Test and Acceptance Plan

1. Render the qualifications statement for a non-automation posting and confirm `software_inventory_answer` still reads cleanly without the "not PLC/code" boundary when it is not relevant, and includes it when the posting is automation or engineering.
2. Render for the current posting and confirm the communication answer leads with the FRD practice.
3. Confirm no Dematic-specific term appears in any shared generator output for a different company.
4. Confirm the two confirmed claims render correctly once the evidence step lands: least-privilege appears scoped to access-control design plus incident backtracking, barcode appears scoped to limited barcode-scanner exposure and NEVER extends to conveyor/PLC/automation equipment, and salary output stays flexible with no hardcoded range.
5. Guardrail: injecting an unconfirmed claim into a reused answer fails validation.
6. Regression: existing qualifications and interview outputs for State Farm / Big Four still build.

## Assumptions

- The qualifications generator remains deterministic and source-driven; these changes refine existing answer functions and add reusable ones, they do not switch it to free-form generation.
- The interview-guide reuse layers on the Phase 1 scripted-answer model and should be done after that merges.
- The two previously gated items (least-privilege, barcode) are CONFIRMED as of 2026-07-14 and enter through the evidence step (source resume(s) plus global_notes.txt); salary stays flexible. Any claim beyond these two still requires fresh confirmation from Christian.
