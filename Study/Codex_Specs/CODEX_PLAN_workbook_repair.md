# Codex Plan: Repair the Daily Interview Rehearsal Workbook

Scope: `scripts/build_daily_interview_rehearsal_workbook.py` and the regenerated `Study/Daily_Interview_Rehearsal_Workbook.docx`. Nothing else. The generator workstream and the other Study artifacts are out of scope.

This plan is written so that **running it produces the completion report**. Every claim in the final report must come from a check that printed a number, not from a summary written by hand. The reason is specific: the previous rebuild was reported as complete and verified while it had silently dropped five required elements, because the verification list only covered what had been added.

---

## 1. Pre-flight: record the before-state

Capture these before touching anything. They are measured, not estimated.

| Metric | Baseline value |
| --- | --- |
| File size | 77,851 bytes |
| Modified | Aug 2, 19:25 |
| Rendered pages | 55 |
| Paragraphs | 982 |
| Tables | 2 |
| Story headings (`^Story N:`) | 44 |
| `PREP mode` occurrences | 12 |
| `Short mode` / `Full mode` / `CART mode` | 22 / 22 / 22 |
| `Q.` lines | 67 |
| `A.` lines | 67 |
| Lane-variant lines | 113 |
| Bookmarks | 27 |
| Internal anchors | 46 |

### Two baseline numbers that look wrong and are not

Do not "fix" these:

- **Story headings is 44, not 22.** Part 2 has 22 story sections and Part 4 has 22 more in the clean reference. 44 is correct. A check asserting 22 will fail spuriously.
- **Lane-variant lines is 113, not 110.** Three of the five lane labels appear 23 times rather than 22 because Part 3's mock-loop section reuses the same lane names. 113 is correct.

Both are recorded here so the harness does not raise on them and, more importantly, so nobody silences a real check to make them pass.

---

## 2. Implementation changes

### 2a. Parsing and recall-first ordering

- Parse the separate `# PREP lines for Stories 1 through 11` section and merge each entry into the matching story. Keep inline PREP for Stories 12 through 22.
- **Raise a build error if any of the 22 stories has an empty PREP mode after parsing.** This is the guard that would have caught the regression at build time.
- In Part 2, order each story section: heading and index link, covered-page recall prompt, then answer content below it.
- Part 4 stays answer-first and instruction-free.

### 2b. Per-story elements (all 22 Part 2 sections)

- Competencies line, taken from Appendix A of `Study/MASTER_PLAN_interview_story_system.md` verbatim. Validate every name against `interview_intelligence.COMPETENCY_TAXONOMY` and reject unknowns.
- All four modes.
- Follow-up questions with example answers.
- Lane variations.
- A rep-scoring table using **exactly the five tells** from Appendix B: buried outcome, stream of consciousness, hedging, warm-up wandering, volunteering salary. Plus a time field and a clean-pass box. No second positive-criteria rubric.
- A ruled notes block.

### 2c. Workbook-level sections

- Competency coverage map built from Appendix A. Preserve the intentionally thin coverage: `AI adoption` maps only to Story 5 and `Technical fluency gap` only to Story 17. Do not pad these to look balanced.
- Rep log with blank fields for date, stories practiced, lane, time, tell count, clean pass, notes.
- Preserve the clickable index, 67 follow-up answers, lane variations, and the clean 22-story reference.

### 2d. Rebuild the lane mock loops (they are currently playlists, not loops)

Keep five lanes. Do **not** preserve the current loop content as-is. Measured against the live workbook, each loop holds only a story sequence, a one-line lens, and a `Close:` line that is byte-identical across all five. The following are absent from the entire document:

| Missing | Status |
| --- | --- |
| CSM exact first line | Absent |
| Program and project management exact first line | Absent |
| Solutions consulting and pre-sales exact first line | Absent |
| "Tell me about yourself" | Absent |
| "Tell me about a failure" | Absent |
| "Tell me about a disagreement" | Absent |
| "What questions do you have for me" | Absent |

The exact lane first lines are the single highest-value rehearsal asset in the system, because selection under pressure is the failure this work exists to fix. Three of the four documented lines are gone.

Each loop must carry:

1. The lane's **exact first line, verbatim from the story bank**. All five loops now have one.
2. The ordered story sequence (keep the existing sequences).
3. A six-question interview run: tell me about yourself, walk me through your most relevant project, a failure, a disagreement, why this role and your first 90 days, your questions for me.
4. After-loop self-review prompts: did you lead with the claim every time, did you exceed two full-mode answers, how many tells on playback, did you close with a question that made them think.
5. A lane-specific close, not the same sentence five times.

**The bank now documents six lanes, not four.** Openers for `Change enablement and process improvement` and `Analytics and operations` were written from existing story material and added under "Role-tailored lead-ins by lane". The full set is now: Implementation and delivery consultant, Customer Success and account management, Program and project management, Solutions consulting and pre-sales, Change enablement and process improvement, Analytics and operations.

This closes the gap that made Analytics a documentation-free loop. **Every one of the five workbook loops now maps to a documented opener**, and no opener needs to be invented or omitted. Program and project management has an opener in the bank but no loop, by decision D3 in the master plan (two applications does not justify one).

Copy all five openers character for character. Do not paraphrase.

---

## 3. Verification harness

Write `scripts/verify_rehearsal_workbook.py`. It takes the DOCX, checks every criterion, prints a table of expected versus actual, and **exits nonzero on any failure**. The completion report is its stdout.

### Design rule: assert per story, not in aggregate

This is the most important line in the plan. The previous regression survived because aggregate counts looked plausible. `PREP mode` appearing 12 times reads as "PREP is present." Only splitting the document into 22 story sections and checking each one individually reveals that Stories 1 through 11 have none.

The harness must therefore parse the document into per-story sections and, for each of the 22, assert the presence of: a recall prompt, a competency line, four non-empty modes, at least one follow-up question with a paired answer, five lane variants, a five-tell scoring table, and a notes block. Report failures as a list of story numbers, never as a total.

### Checks and expected values

| # | Check | Expected |
| --- | --- | --- |
| 1 | File mtime and size changed from baseline | Both differ from 77,851 / 19:25 |
| 2 | Rendered page count | Greater than 55 |
| 3 | Part 2 story sections | Exactly 22 |
| 4 | Part 4 reference sections | Exactly 22 |
| 5 | Stories with non-empty PREP | 22 of 22, list any missing |
| 6 | Stories with Short, Full, CART | 22 each, list any missing |
| 7 | Stories with a recall prompt above answer content | 22 of 22 |
| 8 | Stories with a competency line | 22 of 22 |
| 9 | Competency names valid against taxonomy | 0 unknown |
| 10 | Stories with a five-tell scoring table | 22 of 22 |
| 11 | Scoring tables containing any non-tell criterion | 0 |
| 12 | Stories with a notes block | 22 of 22 |
| 13 | Stories with five lane variants | 22 of 22 |
| 14 | Follow-up questions and answers | 67 and 67, paired |
| 15 | Competency coverage map present, all 11 taxonomy entries listed | 11 of 11 |
| 16 | `AI adoption` maps to Story 5 only; `Technical fluency gap` to Story 17 only | True |
| 17 | Rep log present with all seven fields | True |
| 18 | Lane mock loops | 5 |
| 18a | Loops carrying a verbatim bank opener | 5 of 5 |
| 18b | Six-question interview run per loop | 5 of 5 |
| 18c | After-loop self-review prompts per loop | 5 of 5 |
| 18d | Identical close text repeated across loops | 0 |
| 18e | Opener text matching the bank character for character | 5 of 5 |
| 19 | Bookmarks | 27 or more |
| 20 | Internal anchors | 46 or more |
| 21 | Raw markdown (`**`, `##`, `---`) in rendered text | 0 |
| 22 | Generator-only alternates present | 0 |
| 23 | Part 4 contains no practice instructions | True |
| 24 | Terms per page density outliers | None unexplained |

### Expected deltas

| Metric | Before | After |
| --- | --- | --- |
| Tables | 2 | 2 + 22 scoring + 22 notes + 1 coverage + 1 rep log, so roughly 48 |
| Pages | 55 | Well above 55; a return of 55 is a failure signal, not a coincidence |
| Bookmarks | 27 | 27 or more |
| Q / A | 67 / 67 | 67 / 67 unchanged |
| Lane variants | 113 | 113 unchanged |

---

## 4. Completion report

The report is the harness output plus rendered-page inspection. It must contain:

1. The expected-versus-actual table for all 24 checks, with actual values printed.
2. Before and after file size, mtime, and page count.
3. For any check reporting a count below expected, the explicit list of which story numbers failed.
4. Confirmation that the pages listed in section 5 were rendered and viewed.
5. A statement of any anomaly found and what it turned out to be.

**Do not report the workbook clean while any check has an unexplained result.** If page count comes back at 55, or table count is not near 48, or any per-story list is non-empty, that is a failure to investigate before reporting, not a rounding difference.

---

## 5. Pages to render and inspect visually

Machine checks do not catch layout problems. Render and view: the clickable index, Story 1, Story 2, Story 11, Story 12, one table-heavy story page, the competency coverage map, the rep log, and both the first and last page of Part 4.

Story 11 and Story 12 are named specifically because they sit on the boundary of the PREP parsing fix. Story 11 draws from the separate PREP section and Story 12 from an inline one. If the merge is wrong, that is where it shows.

---

## 6. Validation commands

```
python scripts/build_daily_interview_rehearsal_workbook.py
python scripts/verify_rehearsal_workbook.py
python tasks.py validate
```

`tasks.py validate` is included because the builder imports `interview_intelligence`. It should be unaffected, and confirming that is the point.

---

## 7. Assumptions and boundaries

- Appendix A of the master plan is the sole story-to-competency source.
- Appendix B is the sole scoring rubric. The five tells stay consistent with `Daily_Companion.md`, `Interview_Story_Card.docx`, and `IT_Flashcards_InterviewStories.txt`.
- The story bank markdown is the content source. The current DOCX is not source truth.
- No hard maximum page count.
- Only the workbook builder, the new verification harness, and the regenerated workbook change.
- Do not renumber stories, add generator-only alternates, or propagate the count 25 into Study materials.
