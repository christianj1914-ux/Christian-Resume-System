# CODEX SPEC: Final Closeout

Date: 2026-08-10
Author: Claude (review and plan pass)
Branch: `main` at `707501e`, level with `origin/main`
Suite: 512 registered, independently verified green

Four outstanding items. One is larger than it looks, one has just met its deferral trigger, and two are small.

---

# Part 0: Verification already completed

I covered all 512 checks in parallel slices: **668 passes, zero real failures.** Three checks failed in my sandbox only:

| Check | Cause |
|---|---|
| `federal resume import stays isolated from commercial builders` | subprocess hits the new 3.11 guard on my 3.10 interpreter; the error text is literally `Python 3.11+ is required; found Python 3.10.` In-process check confirms zero leaked builders. |
| `bootstrap configure fresh pycache avoids stale timestamp bytecode` | same cause, spawns `/usr/bin/python3` |
| `smoke selector preserves failing federal check` | my slice runner intercepted the synthetic registry the test injects; my bug, fixed mid-run |

Also confirmed: five commits pushed and level with `origin/main`; `cleanup_output.py:8` now imports `timezone` with `timezone.utc` at lines 165 and 286; pyflakes clean on the gate criteria (zero undefined names, zero redefinitions).

**Note for the record:** with only the version guard spoofed, the entire suite runs on real Python 3.10. The 3.11 floor is now deliberate policy rather than a technical requirement, since `timezone.utc` removed the last actual dependency. That is a good position, but it should be understood as a choice.

---

# Part 1: Triage 35 uncommitted files in `scripts/`

**This is the largest item and it has been carried, untouched, across three separate passes.**

## 1.1 Measured state

`scripts/` has **35 modified files** plus one untracked directory. `Study/`, `source/`, and `output/` are clean.

```
application_status.py                    build_interview_review.py
build_application_checklist.py           build_interview_validation_set.py
build_claude_review_packet.py            build_networking_outreach.py
build_cover_letter.py                    build_post_round.py
build_debrief_analysis.py                build_resume.py
build_detailed_interview_guide.py        build_salary_guide.py
build_federal_cover_letter.py            build_standard_qualifications_statement.py
build_federal_detailed_interview_guide.py build_thank_you.py
build_federal_interview_cheat_sheet.py   build_weekly_tracker.py
build_federal_resume.py                  federal_supporting_docs.py
build_followup_email.py                  integration_test.py
build_internal_interview.py              post_interview_debrief.py
build_interview_cheat_sheet.py           question_prep.py
build_interview_companions.py            requirement_engine.py
build_interview_followup.py              resume_analysis.py
                                         run_federal_resume_workflow.py
                                         smoke_test.py
                                         track_applications.py
                                         workflow_step_runner.py
?? test_fixtures/
```

This is not a small residue. It touches the resume builder, the cover-letter builder, both interview builders, the entire federal family, the requirement engine, `resume_analysis.py`, and the smoke suite.

## 1.2 Why it matters

The suite passes at 512 **with these changes present in the working tree**. So the green result reflects the uncommitted state, not `HEAD`. Anyone who clones `main` and runs the suite is testing something different from what was verified. That gap widens the longer it sits.

`test_fixtures/` being untracked is the sharper risk: if any of the 35 modified files or any smoke check references a path under it, `HEAD` is already broken for a fresh clone and nobody would know, because every local run has the directory present.

## 1.3 Procedure

1. **Check `test_fixtures/` first.** Grep `scripts/` and `tasks.py` for `test_fixtures`. If anything references it, it must be committed before anything else, and this becomes the highest-priority item in the entire plan. If nothing references it, decide whether it is intended repository content or scratch, and either commit it or add a `.gitignore` entry.

2. **Verify `HEAD` independently of the working tree.** Clone or `git worktree add` a clean copy at `707501e`, run the suite there, and record the result. This is the only way to know whether `main` is actually green. Do not skip this; it is the question the current state cannot answer.

3. **Group the 35 by theme** and commit in coherent slices, not one commit:
   - federal family: the five `build_federal_*` files plus `federal_supporting_docs.py`, `run_federal_resume_workflow.py`
   - interview family: cheat sheet, detailed guide, companions, followup, review, validation set, `question_prep.py`
   - commercial core: `build_resume.py`, `build_cover_letter.py`, `resume_analysis.py`, `requirement_engine.py`
   - tracker and workflow: `track_applications.py`, `workflow_step_runner.py`, `application_status.py`, `post_interview_debrief.py`
   - remaining single-purpose builders
   - `smoke_test.py` hunks belong with whichever slice they test

4. **Run `python tasks.py validate` before each commit**, not just at the end. A green suite after all 35 land tells you the aggregate works; it does not tell you which slice broke something if a later regression appears.

5. If a diff cannot be explained, **do not commit it**. Record it and leave it uncommitted rather than guessing at intent.

Commits: as many as the grouping warrants.

---

# Part 2: Validation performance, trigger now met

The deferral condition I wrote was: **defer unless full-suite duration begins preventing routine full-suite validation.** That condition is now met. Codex has been unable to complete a full run across three separate sessions, hitting 60 to 64 second command limits each time, and has repeatedly shipped on partial evidence as a result.

## 2.1 Measured profile

Slowest checks observed during my full-coverage run:

| Seconds | Check |
|---|---|
| 23.2 | daily prep plans cover rep types and modes |
| 19.7 | tracker row prefers tailored resume for fit |
| 17.6 | explicit stale questions still flagged |
| 16.5 | S7 lane expansion routes and specializes content |
| 16.4 | system-wide top-third quality followups |
| 13.9 | long cover mode |
| 13.4 | ollie cover acceptance |
| 11.3 | ATS keyword mirroring and coverage |
| 11.1 | daily prep command builds Word plan |
| 10.9 | S3 supported keyword weave targets priority summaries |
| 10.3 | Python runtime guard and datetime UTC import policy |
| 9.6 | import major scripts |

Roughly **170 seconds concentrated in twelve checks**, against a suite that takes about six minutes. Twelve of 512 checks are consuming close to half the runtime.

Note that `Python runtime guard and datetime UTC import policy` at 10.3s and the pyflakes gate, which I measured between 13.9s and 22.3s across runs, are both **checks added in the last two passes**. Two of the most expensive checks in the suite are ones recently introduced, including one I recommended.

## 2.2 Approach

1. **Profile properly first.** Set `PYTHONPYCACHEPREFIX` to local disk before measuring. Bytecode writes on a slow filesystem dominate otherwise; that effect is what made an early reading of "30 second imports" an environment artifact rather than a finding.
2. **Characterize, do not optimize yet.** For each of the twelve, determine whether it is slow because it builds a full Word document, spawns a subprocess, or scans the whole source tree. Those have different remedies.
3. **Likely wins, in order of expected value:**
   - The pyflakes and runtime-guard checks each re-scan `scripts/` independently. Running one scan and sharing the result across both would recover most of their combined cost.
   - Checks that build a complete document to assert one string could assert against the composed text before rendering.
   - Subprocess-spawning checks pay full interpreter startup plus the import chain each time.
4. **Preserve coverage absolutely.** No check may be deleted, merged, or moved behind a flag. The target is the same 512 checks running faster, not fewer checks. If a change reduces the registered count, it is wrong.
5. **Set a concrete goal:** full suite under three minutes on a warm cache. That is enough to make routine full-suite validation practical again, which is the entire point.

Commit: `perf: reduce smoke suite runtime without changing coverage`

---

# Part 3: Small items

## 3.1 Archive two spec files

Root currently holds eight markdown files, two of which are completed specs:

- `CODEX_SPEC_cs_signal_linkedin_interview_study.md`
- `CODEX_SPEC_portability_and_cs_commit.md`

Both are implemented. `git mv` them to `Study/Codex_Specs/` and grep for references before moving. Root should return to six.

## 3.2 Visually verify three regenerated Word documents

LibreOffice was unavailable locally, so `Daily_Interview_Rehearsal_Workbook.docx`, `Interview_Story_Card.docx`, and `Personal_Operating_Workbook.docx` have not been rendered or inspected by anyone.

These are study materials Christian reads himself rather than employer-facing deliverables, so the risk is low. Opening each once in Word and checking the Builder drill section, the revised lane loops, and the commercial-boundary line renders correctly is sufficient. No PNG pipeline needed. If a layout defect appears, fix it locally and regenerate.

---

# Part 4: Still deferred

Both retain their original entry conditions and neither has been met.

**`contains_search_term` consolidation.** Two implementations differ in opposite plural directions. Entry condition: an output that reports an obviously supported term as a gap, or the reverse. Then choose the semantics explicitly, run `keyword_reliability_corpus.py` before and after, and diff alignment scores, suppressed gaps, selected bullets, and selected competencies separately.

**Federal `program_delivery` cluster mapping.** Absent from `FEDERAL_DEFAULT_CLUSTERS_BY_LANE`; the active federal fixture depends on the current fallback tie-break. Entry condition: a real federal posting in that lane. `program_delivery` is a live commercial lane with 33 archived postings, so the gap is real, but re-pinning a fixture against a hypothetical posting is worse than waiting.

---

# Part 5: Sequencing

1. **Part 1**, and within it the `test_fixtures/` check and the clean-clone verification first. Until `HEAD` is verified independently of the working tree, every other result is provisional.
2. **Part 3.1**, trivial, do it alongside.
3. **Part 2**, once the tree is committed and there is a stable baseline to measure against. Profiling a dirty tree measures something you are about to change.
4. **Part 3.2** whenever convenient.

**Global gates.** `python tasks.py validate` after every commit at 512 or higher, never fewer. `source/` untouched. Stop rather than work around a check count that drops, a clean-clone run that fails, or a diff whose intent cannot be established.
