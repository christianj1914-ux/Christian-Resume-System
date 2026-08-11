# CODEX SPEC: Portability Fixes and CS Upgrade Commit

Date: 2026-08-10
Author: Claude (review and plan pass)
Branch: `main` at `87eb19d`, level with `origin/main`
Context: the CS hiring-signal upgrade is implemented but **uncommitted**. Independent full-suite verification is complete.

Small, three-part closeout. Two defects found during independent verification, then the commit that is currently missing.

---

# Part 0: Verification already completed

Recorded so it is not repeated.

I ran the full suite in parallel slices covering **all 510 registered checks: zero failures**, 577 observed passes across overlapping slices. This satisfies the gate that the 64-second command window prevented Codex from completing. It does **not** replace a single clean local run, which Codex should still produce once Part 1 lands.

Also verified independently:

- `source/` untouched, so no LinkedIn-derived claim reached evidence
- `config/paths.py` defines `STUDY_GUIDES_DIR`, `DAILY_INTERVIEW_REHEARSAL_WORKBOOK`, `INTERVIEW_STORY_CARD`, `PERSONAL_OPERATING_WORKBOOK`
- `build_daily_interview_rehearsal_workbook.py:32` uses the constant rather than rebuilding the path
- `verify_rehearsal_workbook.py:51` actively asserts no root duplicate exists
- No root duplicate present
- `commercial_acumen_answer()` at `build_interview_cheat_sheet.py:138` leads with the honest boundary and contains zero forbidden quota, NRR, GRR, or closed-expansion language

---

# Part 1: Restore Python 3.10 compatibility

**Severity: high for anyone not on 3.11+. Zero impact if every interpreter that touches this repo is 3.11 or newer.**

## 1.1 The defect

`scripts/cleanup_output.py:8`

```python
from datetime import UTC, datetime, timedelta
```

`datetime.UTC` was added in **Python 3.11**. On 3.10 this raises `ImportError: cannot import name 'UTC' from 'datetime'`.

Because `cleanup_output` is in `MAJOR_SCRIPTS`, the failure lands in `import_major_scripts()` at bootstrap check 2, so **the entire 510-check suite aborts before check 3**. Nothing downstream runs.

Used at two sites:

```python
165:    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
286:    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
```

## 1.2 Why it matters despite CI passing

`.github/workflows` pins `python-version: "3.11"`, so CI is green and will stay green. The repo is otherwise pure standard library plus `python-docx==1.2.0`, and it previously carried bytecode for CPython 3.10, 3.12, and 3.14, meaning more than one interpreter has run this code. One line silently raised the floor to 3.11 without that being a deliberate decision or being recorded anywhere.

## 1.3 Fix

```python
from datetime import datetime, timedelta, timezone
```

and at both use sites:

```python
stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
```

`timezone.utc` is available in every Python 3 version and is exactly what `datetime.UTC` aliases. Behavior is identical, including the `Z` suffix in the formatted stamp.

## 1.4 Decide and record the floor

Pick one and write it down; do not leave it implicit:

- **Option A, recommended.** Support 3.10+. Apply the fix above. Add a `python_requires`-style note to `requirements.txt` stating the minimum version, since there is no `pyproject.toml` or `setup.cfg` to carry it.
- **Option B.** Declare 3.11+ deliberately. Keep `datetime.UTC`, record the floor in `requirements.txt` and `CONTRIBUTING.md`, and add a runtime guard in `_bootstrap.py` that fails with a clear message on older interpreters rather than an opaque `ImportError` from an unrelated module.

Option A is cheaper and keeps the dependency surface as small as the rest of the codebase.

## 1.5 Guard

Add a smoke check asserting no module under `scripts/` imports a symbol newer than the declared floor. A narrow, effective version: scan for `from datetime import` lines containing `UTC` and fail. Broader version-shim detection is not worth the complexity.

Commit: `fix: restore Python 3.10 compatibility in cleanup_output`

---

# Part 2: Stop bootstrap failures from masking their own error

**Severity: medium. It does not cause failures; it hides them.**

## 2.1 The defect

`scripts/smoke_test.py`

```
18795:        full_total = len(registered_checks) + 2      # inside the try block
18820:        print(f"Smoke test FAILED: ... ({full_total} total registered).")
18826:    print(f"Smoke test PASSED: ... ({full_total} total registered).")
```

`full_total` is assigned only after `import_major_scripts()` succeeds. When a bootstrap check fails, line 18820 raises:

```
UnboundLocalError: local variable 'full_total' referenced before assignment
```

So the operator sees an `UnboundLocalError` from the reporting code instead of the actual failure. That is what happened with Part 1: the real cause was a one-line `ImportError`, and the suite reported a variable-scope error in its own summary printer.

This is the same shape as the defects this codebase has produced repeatedly. A failure path that obscures rather than reports.

## 2.2 Fix

Initialize `full_total = 0` alongside `passed` and `executed_checks` before the try block, and have the failure branch print the registered total only when it is known:

```python
registered_label = f"{full_total} total registered" if full_total else "registration incomplete"
```

Verify by temporarily breaking an import in a scratch copy and confirming the suite prints the underlying traceback and a clear bootstrap-failure message, then discard the scratch change.

## 2.3 Guard

Add a smoke check that calls `main()` with a monkeypatched `import_major_scripts` raising `SmokeFailure`, and asserts the process reports the failure text rather than raising `UnboundLocalError`. This is cheap and it is exactly the path that just cost a debugging cycle.

Commit: `fix: report bootstrap failures instead of masking them`

---

# Part 3: Commit the CS hiring-signal upgrade

**This is the largest outstanding item. The work exists only in the working tree.**

## 3.1 Measured state

| Path | Modified files |
|---|---|
| `scripts/` | **42** |
| `Study/` | **8** |
| `output/` | 0 |
| `source/` | 0 |

`git log -S "commercial_acumen_answer"` returns nothing, confirming none of it is committed. HEAD is `87eb19d`, level with `origin/main`.

## 3.2 Commit split

Split along the three workstreams the spec itself defined. Do not create a second `f66729c`; that one is documented as an intentional exception, not a precedent.

1. **Interview system.** `interview_story_engine.py`, `build_interview_cheat_sheet.py`, `build_detailed_interview_guide.py`, `question_prep.py` if touched, plus their smoke checks. Covers `Repeatable Systems`, Builder routing, the decoder table, expanded `likely_questions()`, and `commercial_acumen_answer()`.

   `feat: add builder story routing and CS competency decoder`

2. **LinkedIn.** `build_linkedin_update.py` and its smoke checks. Covers the four-segment About refactor, true Word bullets, CTA, warn-only prose enforcement, and the Time/Money/Team/Scope table.

   `feat: restructure LinkedIn about section and add scope checklist`

3. **Paths and study material.** `config/paths.py`, `build_daily_interview_rehearsal_workbook.py`, `verify_rehearsal_workbook.py`, the regenerated `Study/Guides/` documents, `Study/Notes/`, `Study/Flashcards/`, and `Study/Interview_Story_System/`.

   `fix: centralize study guide paths and propagate builder drill`

If a file spans two workstreams, put it in the earlier commit and note the overlap in the message rather than splitting hunks.

## 3.3 Before committing

- Confirm `git status --porcelain -- source/` is empty. If anything appears there, stop: a LinkedIn-derived claim has reached evidence.
- Confirm `git status --porcelain -- output/` is empty or contains only regenerated artifacts you intend to leave uncommitted. Generated output is not commit content.
- Run `git diff --cached --check` before each commit.

## 3.4 Validation

- Full `python tasks.py validate` after each of the three commits, requiring **510** registered checks and zero failures. Parts 1 and 2 add checks, so the final count will be higher than 510; assert the delta rather than an absolute number, using the approach adopted previously: record the starting count, add the approved number of new tests, assert equality.
- Rebuild and verify the rehearsal workbook: `python scripts/build_daily_interview_rehearsal_workbook.py` then `python scripts/verify_rehearsal_workbook.py`. Require 24/24 structural checks and the 22-story invariant.
- Run pyflakes, vulture, and the AST gate.

---

# Part 4: Sequencing and closeout

1. **Part 1 first.** Until it lands, the suite cannot run to completion on any 3.10 interpreter, which makes every other verification conditional on interpreter version.
2. **Part 2 second.** Small, and it improves diagnostics for everything after it.
3. **Part 3 last**, as three commits.
4. Push `main` to `origin`. If the push is rejected because the remote advanced, fetch and stop for review rather than merging unknown remote work.
5. Add a short `CHANGELOG.md` entry covering the CS hiring-signal upgrade and both portability fixes.

**Stop conditions.** Halt rather than work around:

- `source/` shows any modification
- The suite reports fewer checks than the recorded baseline plus approved additions
- The rehearsal workbook verifier drops below 24/24 or the 22-story invariant breaks
- A push is rejected because `origin/main` advanced

**Out of scope.** No resume evidence changes, no headline rewrites, no new study track, no PDF deliverables, and no changes to the 45 to 70 word summary contract.
