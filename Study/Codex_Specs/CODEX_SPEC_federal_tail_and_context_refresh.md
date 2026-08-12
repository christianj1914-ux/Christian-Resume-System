# CODEX SPEC: Federal Tail, Context Refresh, and Remaining Triage

Date: 2026-08-11
Branch: `main` at `54d59ea`, level with `origin/main`
Suite: **522 registered / 524 executed** at `HEAD`, passing from a clean detached worktree

---

# Part 0: Verified state

Independently confirmed:

| Check | Result |
|---|---|
| Three Safe Packet commits present and pushed | `1a1938a`, `da58f94`, `54d59ea`; 0 ahead, 0 behind |
| `HEAD` registered checks | 522 registered / 524 executed, matching the committed baseline |
| Qualifications statements carry body-visible banners | Stratix line 1 `NOT READY FOR SUBMISSION`; Laurel and ketteQ line 1 `REVIEW REQUIRED BEFORE SUBMISSION` |
| Cover letters carry matching banners | All three, first line |
| `document_flow.py` flow controls | 6 `keep_with_next`/widow controls, where the codebase previously had zero anywhere |

The work is correct and shipped. The banner fix in particular closed the defect where a `FAIL` qualifications statement opened with "Christian Estrada" and warned nowhere in the body, while being the document whose answers get copied into web forms.

---

# Part 1: Correction to the outstanding-work picture

I previously described the remaining dirty state as "a second complete workstream sitting uncommitted." **That was wrong, and the real situation is much smaller.**

Every federal function referenced by the uncommitted packet diff is **already committed at `HEAD`**:

```
parse_federal_posting                  COMMITTED
build_target_context                   COMMITTED
select_federal_grade                   COMMITTED
publish_document_set                   COMMITTED
federal_draft_channels                 COMMITTED
validate_staged_federal_documents      COMMITTED
active_application_question_responses  COMMITTED
```

So the federal hardening **implementation shipped**. What remains uncommitted is its supporting tail: packet wiring, an integration-test adjustment, four authored review documents, and documentation drift.

## Remaining dirty inventory

| Area | Count | Nature |
|---|---|---|
| `scripts/` | 2 | `build_claude_review_packet.py` (+24), `integration_test.py` (14 changed) |
| `Claude Review/` | 9 modified + 4 untracked | 5 modified are regenerable bundle copies; 4 untracked are authored |
| `.context/` | 1 | `ARCHITECTURE_MAP.md` |
| root | `SYSTEM_REFERENCE.md` + 2 untracked specs | |
| `jobs/` | 2 | active job context |
| `Study/` | 3 | regenerated artifacts |

Authored federal documents, 660 lines total:

```
447  RECONCILED_IMPLEMENTATION_PLAN_federal_hardening_20260809.md
108  CLAUDE_IMPLEMENTATION_PLAN_federal_hardening_20260809.md
 62  FEDERAL_HARDENING_IMPLEMENTATION_RESULTS_20260809.md
 43  EXTRACT_OUTPUT_NAME_CALLSITE_AUDIT_20260809.md
```

---

# Part 2: The compact context files are stale, and this is the highest-value item

`.context/SCRIPT_INDEX.md` and `.context/ARCHITECTURE_MAP.md` are the function-level navigation map and architecture summary that `CLAUDE.md` directs every Claude session to read first. Measured against `main`:

| Module | In `SCRIPT_INDEX.md` | In `ARCHITECTURE_MAP.md` |
|---|---|---|
| `document_flow.py` | **0** | **0** |
| `top_third_scoring_guard.py` | **0** | **0** |
| `run_commercial_queue.py` | **0** | **0** |
| `interview_story_engine.py` | **0** | **0** |

Four modules shipped to `main` across recent passes and **none appears in either compact context file**. Two of them are shared infrastructure that new code should route through rather than reimplement: `document_flow.py` owns every submission banner and all page-flow control, and `interview_story_engine.py` owns the story model for all interview outputs.

This is the same failure the original audit found, in reverse. Then, `SCRIPT_INDEX.md` described six formatting passes that had stopped running. Now it omits four modules that do run. Either direction produces the same outcome: a reader trusts the map, the map is wrong, and work gets duplicated or misrouted. `document_flow.py` is the acute case, because a future builder that formats its own banner instead of calling the shared helper reintroduces exactly the inconsistency this month's work removed.

## Required updates

**`.context/SCRIPT_INDEX.md`** gains entries for:

- `document_flow.py`: shared submission-status banners and Word page-flow control. Note the three states (`PASS` no banner, `BRIDGE`/`DRAFT` review required, `FAIL`/`POOR` not ready) and that the banner is inserted as first body content by design, not as filename or footer metadata.
- `top_third_scoring_guard.py`: corpus comparison and promotion guard. **State explicitly that semantic top-third matching is not enabled and that this guard shipped ahead of it.**
- `run_commercial_queue.py`: sequential multi-posting queue, `execution_status` versus `submission_readiness`, per-stage timings.
- `interview_story_engine.py`: neutral story model shared by the cheat sheet and qualifications statement; note that `build_interview_cheat_sheet` re-exports its symbols for compatibility.

**`.context/ARCHITECTURE_MAP.md`** gains the queue in the data-flow section and `document_flow.py` in the shared-helpers list.

**Do not reuse the uncommitted `.context/ARCHITECTURE_MAP.md` diff.** Review it first; those edits describe federal work and may not cover the four modules above.

---

# Part 3: Federal tail commit

## 3.1 `scripts/build_claude_review_packet.py` (+24)

Registers packet excerpts for the already-shipped federal functions and adds federal review scope notes. Because the implementation is committed and this is not, **federal review packets currently omit the functions a reviewer most needs to see.** That is a live gap in the review loop, not cosmetic.

Verify each registered `fx(...)` target resolves against committed code, then stage.

## 3.2 `scripts/integration_test.py`

Establish intent before staging. If it exercises federal grade selection or the transactional publisher, it belongs with 3.1. If unrelated, leave it and record why.

## 3.3 The four authored federal documents

These are authored analysis, not generated output, and should not be discarded with the regenerable bundle copies. Move to `Study/Codex_Specs/` alongside the other completed specs, or commit in place under `Claude Review/` if that directory is intended to retain authored records. Pick one and apply it consistently; do not split the four.

Commit: `docs: register federal review excerpts and archive hardening records`

## 3.4 Regenerable bundle copies

The five modified files under `Claude Review/` (`ARCHITECTURE_MAP.md`, `CLAUDE.md`, `COMMON_CHANGE_AREAS.md`, `RULES_FOR_CLAUDE.md`, `SCRIPT_INDEX.md`) are bundle copies of `.context/` files. Per the standing rule, discard them and regenerate after Part 2 lands so the bundle reflects the corrected context files rather than the stale ones.

---

# Part 4: Archive completed specs

Root holds two implemented specs:

- `CODEX_SPEC_resume_performance_and_queue.md`
- `CODEX_SPEC_safe_packet_commit.md`

Both are done. `git mv` to `Study/Codex_Specs/` after grepping for references. This specification joins them once its work completes.

---

# Part 5: Remaining triage

- `jobs/` (2 files): active job context is legitimate working state. Commit.
- `Study/` (3 files): regenerated artifacts. Commit with the work that produced them if identifiable; otherwise commit as `docs:`.
- `SYSTEM_REFERENCE.md`: review whether the edits describe federal work or the new modules, and route accordingly.

---

# Part 6: Additions worth making

**Install vulture, or record that the gate is unavailable.** The dead-code scan has now been skipped across three consecutive passes for want of one package. Either `pip install vulture` and run it once, or add a line to `CONTRIBUTING.md` stating the gate is optional and locally unavailable, so it stops being silently assumed.

**Consider a `packet` mode covering the new shared modules.** Packet modes exist for `broad`, `tracker`, `checklist`, `resume`, `cover`, `interview`, and `workflow`. There is no mode that surfaces `document_flow.py` or the queue, so a review of packet-safety behavior currently has no compact packet. Low priority, but it is the kind of gap that makes the next review start from a worse position.

**The Aptean historical finding remains open and is not a code task.** Both Aptean ERP Consultant artifacts moved from Stretch and Adjacent Fit to Strong Fit at 100/115 once parsing worked. That is information about a submitted application. Nothing in this plan resolves it and nothing should.

---

# Validation

- `python tasks.py validate --commit HEAD --expected-count <baseline>` after each commit, against the committed tree rather than the workspace. No new checks are expected from Parts 2 through 5, so the count should remain 522 unless 3.2 adds coverage.
- Confirm `git status --porcelain -- source/ output/` is empty before every commit.
- After Part 2, regenerate the Claude bundle and confirm `tasks.py claude-packet --mode broad` succeeds with no new self-audit warnings.
- Fetch `origin/main` before pushing; if it advanced, stop rather than rebasing or merging.

**Stop conditions.** A failing clean validation, a check count other than the recorded baseline plus approved additions, a diff whose intent cannot be established, or a rejected push.
