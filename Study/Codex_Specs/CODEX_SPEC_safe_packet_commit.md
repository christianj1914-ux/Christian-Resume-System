# CODEX SPEC: Commit the Safe Packet Outputs Work

Date: 2026-08-11
Branch: `main`, level with `origin/main` (0 ahead, 0 behind)
Suite: 522 registered + 2 bootstrap = **524 executed**, passing in the working tree

The Safe Packet Outputs work is complete and verified but **exists only in the working tree**. This plan commits it, validates the committed artifact, and pushes.

---

# Part 0: Verified state

Independently confirmed against the current tree:

| Check | Result |
|---|---|
| Qualifications statements carry body-visible banners | **Yes.** Stratix line 1 is `NOT READY FOR SUBMISSION`; Laurel and ketteQ line 1 is `REVIEW REQUIRED BEFORE SUBMISSION` |
| Cover letters carry matching banners | Yes, all three, first line |
| `document_flow.py` exists with real flow control | Yes, 4,862 bytes, **6** `keep_with_next`/widow controls where the codebase previously had **zero anywhere** |
| `top_third_scoring_guard.py` exists | Yes, 3,304 bytes |
| Registered checks | 522 registered, 524 executed |

The banner fix closes the defect where all three qualifications statements opened with "Christian Estrada" and carried no warning anywhere in the body, while being the exact document whose answers get copied into web application forms.

## Dirty set

**Safe Packet work, ~346 insertions across 8 files plus 2 new modules:**

```
?? scripts/document_flow.py                              (new)
?? scripts/top_third_scoring_guard.py                    (new)
 M scripts/build_standard_qualifications_statement.py    +71
 M scripts/run_commercial_queue.py                       +115
 M scripts/smoke_test.py                                 +92
 M scripts/render_checks.py                              +30
 M scripts/build_cover_letter.py                         +17
 M scripts/resume_format.py                              +2
```

**Intent not established, do not stage without checking:**

```
 M scripts/build_claude_review_packet.py                 +24
 M scripts/integration_test.py                           14 changed
```

**Other dirty areas:** `jobs/` 2 files, `Study/` 3 files, `Claude Review/` 9 files plus 2 untracked, `.context/ARCHITECTURE_MAP.md`, `SYSTEM_REFERENCE.md`, and untracked `CODEX_SPEC_resume_performance_and_queue.md`.

---

# Part 1: Establish intent on the two ambiguous files

Before staging anything.

**`scripts/build_claude_review_packet.py` (+24).** Read the diff. If it is packet-mode support for the new modules, it belongs with this work. If it is unrelated federal or excerpt-registry work, leave it unstaged and record why.

**`scripts/integration_test.py` (14 changed, mixed).** Same question. If it exercises the new banner or readiness fields, stage it with the matching commit. If not, leave it.

Do not stage a diff whose intent cannot be established. That rule has caught real problems in this repository twice.

---

# Part 2: Three commits

Split at the natural seams. The whole set is only ~346 lines, but the seams are real and each part is independently revertible.

## 2.1 Safety and layout

```
scripts/document_flow.py                            (new)
scripts/build_standard_qualifications_statement.py
scripts/build_cover_letter.py
scripts/resume_format.py
scripts/render_checks.py
+ matching smoke_test.py hunks
```

Covers the shared status formatter, the three banner states, `keep_with_next` and widow control, the compact reflow profile, and sparse-terminal-page detection.

`feat: add visible submission status banners and shared page flow`

## 2.2 Queue readiness reporting

```
scripts/run_commercial_queue.py
+ matching smoke_test.py hunks
```

Covers `execution_status` versus `submission_readiness`, audit state and blocker reason, per-stage timings, per-job artifact filtering, and repeated-opening detection.

`feat: separate queue execution from submission readiness`

## 2.3 Scoring guard

```
scripts/top_third_scoring_guard.py                  (new)
+ matching smoke_test.py hunks
```

`test: guard against unapproved fit state promotions`

**Before committing, add a module docstring stating plainly that semantic top-third matching was deliberately not enabled, and that this guard exists so the change cannot ship later without a corpus diff.** Right now the module is a tripwire for a change that has not been made. Without that note, the next reader will reasonably assume semantic matching shipped and this is its safety net, which inverts the intent.

## Staging discipline

`smoke_test.py` spans all three commits. Use `git add -p` and keep each test hunk with the implementation it exercises. Run `git diff --cached` and `git diff --cached --check` before each commit.

Confirm `git status --porcelain -- source/ output/` is empty before every commit.

---

# Part 3: Validate the committed artifact

**Not the workspace.** This is the failure mode that produced the 500-versus-512 divergence, where a green suite reflected the working tree while `HEAD` was a different, smaller thing.

```
python tasks.py validate --commit HEAD --expected-count 522
```

Expect 522 registered, 524 executed, zero failures, and no untracked dependencies.

If it fails:

- Do not push.
- Identify the missing or accidentally staged hunk from the detached candidate result. The most likely cause is a `smoke_test.py` hunk separated from the implementation it tests.
- Amend with the scoped hunk and rerun.
- If the split cannot be made to validate, squash the three into one commit rather than weakening the gate or rebaselining the expected count.

---

# Part 4: Push

1. `git fetch origin`
2. If `origin/main` advanced, **stop**. Do not rebase, reset, or merge unknown remote work. Report and wait.
3. Otherwise push `main`.
4. Confirm `origin/main` resolves to the final commit.

---

# Part 5: Documentation drift, separate commit

Handle after the code lands, never mixed into it.

- `.context/ARCHITECTURE_MAP.md` and `SYSTEM_REFERENCE.md` are modified. Review whether the changes describe the new modules. If yes, extend them to cover `document_flow.py`, `top_third_scoring_guard.py`, and the queue readiness fields, then commit as `docs:`. If the changes are unrelated drift, leave them.
- `Claude Review/` has 9 modified files. Per the established rule these are regenerable via `tasks.py claude-packet` and should be discarded rather than committed. **Exception:** the two untracked files, `CLAUDE_IMPLEMENTATION_PLAN_federal_hardening_20260809.md` and `EXTRACT_OUTPUT_NAME_CALLSITE_AUDIT_20260809.md`, are authored work rather than generated output. Decide whether they belong in `Study/Codex_Specs/` and move them there, or leave them untracked deliberately.
- `CODEX_SPEC_resume_performance_and_queue.md` at root is implemented. Archive it to `Study/Codex_Specs/` with the other completed specs.
- `jobs/` and `Study/` dirty files: triage per the standing rules. Active job context in `jobs/` is legitimate working state and commits; regenerated `Study/` artifacts commit with the work that produced them.

---

# Part 6: Remaining open items

Not blocking this commit.

**Vulture is not installed in the project environment.** The undefined-name and source-structure gates passed, and those are the ones wired into the suite. Either install vulture and run the dead-code scan once, or record explicitly that the dead-code gate is unavailable locally so it is not silently assumed to have passed.

**Semantic top-third matching remains unimplemented by choice.** The guard is in place. The change itself should not ship without the before/after corpus diff, an explicit count of how many `BRIDGE` and `FAIL` artifacts would become `PASS`, and individual review of every state change. If that count is large, the change is loosening the gate rather than sharpening it.

**The Aptean historical finding is still open for your decision.** Both Aptean ERP Consultant artifacts moved from Stretch and Adjacent Fit to Strong Fit at 100/115 once parsing worked. That is application information, not a build defect, and nothing in this plan resolves it.

---

# Global gates

- `python tasks.py validate --commit HEAD --expected-count 522` after the final commit, against the committed tree.
- `source/` and `output/` unstaged throughout.
- Stop rather than work around: a failing clean validation, a check count other than 522 registered, a diff whose intent cannot be established, or a push rejected because the remote advanced.
