# CODEX SPEC: Worktree Triage, Repository Cleanup, and Interview Engine Decoupling

Date: 2026-08-08
Author: Claude (plan pass)
Predecessor: `CODEX_SPEC_system_audit_bugs_and_redundancy.md`, completed in commits `e3bcdc6` through `97b45ea` on `codex-systemwide-docfixes`
Baseline: HEAD `97b45ea`, smoke suite 488/488, zero undefined names, zero unreachable blocks

Covers everything the previous pass deferred, plus two lint items that pass missed. Nine stages, each independently committed and validated.

**This specification contains no open decisions.** Every branch point has an explicit rule. Codex should not pause to ask which option to take. Where a rule produces a surprising result, the rule still wins, and the deviation goes in the final report rather than into a mid-run question. The only halt conditions are the explicit stop conditions in the Global Rules section, and those halt the run rather than requesting a decision.

---

# Part 1: Measured starting state

Gathered against HEAD `97b45ea`. Items marked **(reproduce locally)** could not be completed in the review sandbox because `git status` and `git diff` exceed 45 seconds on the mounted filesystem. Reproduce them in Stage 0 and use your numbers, not these.

## 1.1 Worktree

| Metric | Value |
|---|---|
| Unstaged tracked changes | 355 (339 modified, 16 deleted) |
| Untracked files | 214 |
| Total status entries | 569 |
| Files git reports needing CRLF to LF conversion | 437+ observed: 392 in `scratch/`, 34 in `jobs/`, 11 in `Claude Review/` **(reproduce locally)** |
| Tracked files under `scratch/` | 751, of which 749 are `scratch/jd_library/` |

**All counts in this section are reference-only and several are superseded.** Stage 0's live report is the sole authority. Codex measured 573 status entries and 22 deletions against the 569 and 16 recorded here.

`.gitattributes` is already correct: `* text=auto`, `*.bat text eol=crlf`, Office and image formats marked binary. The churn is not a configuration bug.

**Correction.** An earlier draft of this section claimed the CRLF warnings were expected to account for the bulk of the modified files. That is wrong and has been struck. Git normalizes working-tree content before comparing, so a file differing only in line endings produces no diff and does not appear as modified. The CRLF warnings describe working-copy state at staging time, not existing diffs. Every modified path therefore has genuine content change, and Stage 1 should be expected to produce a small or empty normalization index.

The real distribution is measured in Stage 2A.1: roughly 86 percent of modified files are `metadata.json` under `scratch/jd_library/`, carrying the data regression documented there.

`scratch/jd_library/` holds 749 archived job descriptions, explicitly whitelisted in `.gitignore` via `!scratch/jd_library/`. They are intentional tracked data. Do not untrack them. **Do not commit them via generic triage either.** Their current worktree state is degraded; see Stage 2A.

## 1.2 `output/` inventory (523 entries)

| Type | Count |
|---|---|
| `.docx` | 323 |
| `.txt` | 131 |
| `.pdf` | 60 |
| `.md` | 11 |
| Other | 2 |

Of the 60 PDFs, **47 have no `.docx` sibling**. They are pre-policy artifacts from before the Word-only rule.

Of the 323 `.docx` files, 221 carry an audit token and 13 end in `DRAFT`.

## 1.3 Output filename grammar

This is the critical input to Stage 6c. It was derived by inspecting the real listing, and it is messier than the naming convention implies.

**Canonical form:**

```
Christian Estrada - <FAMILY> [AUDIT] <DocType> [(Round)] [DRAFT].docx
```

**Token rules, confirmed against real files:**

- `AUDIT` is one of `PASS`, `BRIDGE`, `FAIL`, `POOR`. It appears **before** the document type. It is optional.
- `DRAFT` appears **last**, after both the document type and any round qualifier. It is optional.
- `(Round)` is a parenthesized qualifier such as `(HR Screen)`, `(Hiring Manager)`. It appears after the document type. It is optional.
- `<FAMILY>` is everything between `Christian Estrada - ` and the audit token or document type.

**Why splitting on `" - "` fails.** All of these are real:

| Filename fragment | Problem |
|---|---|
| `Automation Direct ERP Administrator Resume (Revised)` | no second separator; company and role fused; trailing `(Revised)` |
| `BELAY Resume` | company only, no role |
| `Implementation Consultant Resume` | role only, no company |
| `Adobe Solutions Consultant` | no document type at all |
| `QTS - Process Manager` | no document type at all |
| `Guidehouse - Senior Consultant - Organizational Change Management - Healthcare Technology Con` | three separators; role truncated mid-word |
| `Procare Solutions - Implementation Manager - ChildPlus` | two separators, both meaningful |
| `Sourcewell - Senior Solution Consultant Verification DRAFT Cover Letter` | non-standard `Verification` token, and `DRAFT` before the doc type |
| `Interview Review - Example Automation - Solutions Consultant` | company and role come **after** the document type |

The correct approach is **right-to-left stripping**, specified in Stage 6c.

**Document types with counts** (suffix-anchored match on the 323 `.docx`):

| Document type | Count |
|---|---|
| Cover Letter | 89 |
| Resume | 86 |
| Qualifications Statement | 77 |
| Interview Cheat Sheet | 11 |
| Pre-Interview Checklist | 9 |
| Federal Resume | 4 |
| 90 Day Plan One-Pager | 4 |
| Resume (Revised) | 1 |
| **Subtotal** | **281** |

Note the checklist is named `Pre-Interview Checklist`, not `Application Checklist`. Do not assume the tasks.py command name matches the output filename.

The remaining 42 files break down as follows.

**Detailed Interview Guide (roughly 17 files).** The doc type is not terminal. Real examples:

```
... FAIL Detailed Interview Guide DRAFT
... Detailed Interview Guide (Hiring Manager)
... FAIL Detailed Interview Guide (HR Screen) DRAFT
```

**Round-specific interview prep (6 files), all family-bearing:**

```
Christian Estrada - Dematic - Solution Consultant Recruiter Screen Prep
Christian Estrada - Dematic - Team Round Prep Addendum
Christian Estrada - Procare Solutions - Implementation Manager - ChildPlus Round 2 Panel Interview Guide
Christian Estrada - Sourcewell - Solution Consultant Panel Master Guide
Christian Estrada - Interview Review - Example Automation - Solutions Consultant
Christian Estrada - Interview Prep Kit
```

**Standalone career and search documents (12 files), no company-role family.** These must never be pruned:

```
Christian Estrada - Career Operating Plan 2026-07-25
Christian Estrada - Career Operating Plan 2026-07-26
Christian Estrada - Career Operating Plan 2026-08-08
Christian Estrada - Daily Prep Plan - Job-Search - 2026-07-25
Christian Estrada - Daily Prep Plan - Job-Search - 2026-07-26
Christian Estrada - Daily Prep Plan - Job-Search - 2026-07-27
Christian Estrada - Daily Prep Plan - On The Job - 2026-07-25
Christian Estrada - Daily Prep Plan - On The Job - 2026-07-26
Christian Estrada - Self-Inventory One-Pager 2026-07-25
Christian Estrada - Self-Inventory One-Pager 2026-07-26
Christian Estrada - Public Speaking Transformation Plan
Question_Bank_Audit_2026-07-27
Question_Bank_Audit_2026-07-28
```

**Non-application debug artifacts (7 files), all removable:**

```
sf_docbuild.docx
bf_docbuild.docx
sf_reg DRAFT.docx
_stage_smoke_all.docx
_stage_smoke_hr (HR Screen).docx
State Farm Direct Regression Guide DRAFT.docx
Sourcewell leakage check guide (HR Screen) DRAFT.docx
```

## 1.4 Root markdown (37 files)

Five are byte-identical to copies already in `Study/Codex_Specs/`:

```
Study/Codex_Specs/CODEX_IMPLEMENTATION_PLAN_top_down_purpose_voice.md
Study/Codex_Specs/CODEX_SPEC_top_down_purpose_voice.md
Study/Codex_Specs/CODEX_SPEC_top_down_voice_cover.md
Study/Codex_Specs/CODEX_SPEC_top_down_voice_interview.md
Study/Codex_Specs/CODEX_SPEC_top_down_voice_resume.md
```

These historical documents are now stored under `Study/Codex_Specs/`; the root copies are archived during Stage 5.

One is unrelated to this system: `Southern_Caribbean_Cruise_Guide.md`, 164 lines, untracked, a personal travel document for a November 2026 cruise. Because it is untracked it exists in no git history, so deletion would be unrecoverable outside the Stage 0 archive. Handling rule is in Stage 5.

## 1.5 Existing cleanup machinery

`scripts/cleanup_output.py` already provides `OUTPUT_MAX_DAYS = 60`, `RENDER_CHECK_MAX_DAYS = 7`, a `--selective` flag, `normalize_company()`, `company_name_from_output_file()`, `protected_company_keys()` (shields companies with an active interview process), `find_stale_output_files()`, `find_stale_render_folders()`, `delete_output_file()`, `delete_render_folder()`. Extend this module. Do not write a parallel script.

## 1.6 Story engine extraction surface

`build_standard_qualifications_statement.py` uses exactly five symbols from `build_interview_cheat_sheet`: `adjusted_profile_for_role`, `supported_story_bank`, `likely_question_story`, `InterviewQuestion`, `spoken_story_answer`.

Those five transitively require twelve more module-level symbols:

```
StoryCard                 expanded_story_bank       story_for_type
assert_full_spoken_answer closest_anchor_story_title contains_all
should_use_cart           signal_score              spoken_caar_answer
spoken_cart_answer        spoken_pyramid_answer     story_by_boost_key
uses_star_answer_framework
```

Sizes: `expanded_story_bank` 352 lines, `likely_question_story` 44, `spoken_story_answer` 16, `story_for_type` 15, `StoryCard` 13, `adjusted_profile_for_role` 7, `supported_story_bank` 3, `InterviewQuestion` 3. Realistic extraction is 500 to 600 lines.

Verify this list by AST analysis before starting. It was derived at HEAD `97b45ea` and may drift.

---

# Part 2: Stages

## Stage 0: Measurement and safety net

No code changes.

1. Create branch `codex-cleanup-and-decoupling` from `97b45ea`. Do not work on `codex-systemwide-docfixes`.
2. Create `scratch/cleanup_archives/` if absent. Confirm it is gitignored; `scratch/*` is ignored with explicit whitelists, and `cleanup_archives` is not whitelisted, so it is already ignored. Verify rather than assume.
3. Build the recovery archive. **The instruction in the first draft of this specification was "archive the entire working tree excluding `.git/`". That was wrong and produced a runaway multi-gigabyte archive. Use the procedure below instead.**

   **Measured ground truth:** the entire working tree excluding `.git/` is **0.43 GiB across 2,567 files**. `.git/` itself is 0.02 GiB. `render_check/` alone is the largest component at roughly 0.47 GiB across 1,778 files. Any archive materially exceeding ~0.3 GiB compressed is malfunctioning, not slow.

   **Scope rule.** The archive exists to recover what git cannot. Git already holds every committed, unmodified tracked file, and `.git/` is 0.02 GiB sitting in place. Archive only:

   - every path `git status --porcelain` reports as modified (` M`, `MM`, `AM`)
   - every path it reports as untracked (`??`), which is the only content with no other copy
   - every path it reports as deleted (` D`), recovered from HEAD, so the pre-cleanup state is reconstructible

   **Explicit exclusions**, regardless of git status:

   ```
   .git/
   scratch/cleanup_archives/
   render_check*/
   __pycache__/
   .tmp/
   ```

   `render_check/` is excluded because it is reproducible by re-rendering and is the single largest directory in the tree. Stage 6 already treats render folders as reproducible and archive-exempt; Stage 0 must be consistent with that.

   **Self-inclusion guard.** Write the ZIP to a path **outside the directory being walked**, such as the system temp directory. Close it, verify it, then move it into `scratch/cleanup_archives/`. Do not rely on exclusion patterns to prevent self-inclusion; a pattern that fails produces an archive that grows without bound, which is exactly what happened. Writing outside the walked tree makes the failure structurally impossible.

   **Sanity gate before accepting the archive.** All four must hold:

   - the ZIP opens and `testzip()` returns `None`
   - its entry count equals the count of **physically existing** input paths. Deleted paths appear in the manifest but produce no ZIP entry; exclude them from this comparison.
   - its uncompressed size is within 20 percent of the summed size of that file list
   - its on-disk size is **under 50 MiB**

   **Expected size, measured.** The bounded set is dominated by `scratch/jd_library/`, which is **2.7 MiB across 1,165 files** in total, of which only 307 modified plus 169 untracked entries qualify. The other changed directories are small: `jobs/` 0.3 MiB, `Claude Review/` 1.2 MiB, `.context/` 0.1 MiB, `source/` 0.2 MiB, `interview_prep/` 0.1 MiB, and only 13 of `scripts/` 368 files are modified. **A correct bounded archive should land under 10 MiB.** The 50 MiB gate is a ceiling with wide margin, not a target.

   If any check fails, delete the archive and stop. Do not retry with a larger timeout.

   Record the final path, SHA-256, entry count, and uncompressed size.

   **Diagnostic for the failed run.** `scratch/` currently measures **4,122 MiB across 1,523 files**, while `scratch/jd_library/` inside it is **2.7 MiB across 1,165 files**. Essentially the entire 4 GiB is the in-flight archive consuming itself: the ZIP is being written under `scratch/`, and `scratch/` is inside the walked tree. After terminating the worker and deleting the partial ZIP, confirm `scratch/` drops back to roughly 180 MiB. If it does not, another partial archive is still present.
4. Write `scratch/cleanup_archives/stage0_report.txt` containing:
   - full `git status --porcelain`
   - full `git diff --numstat`
   - `git diff --numstat --ignore-cr-at-eol`, filtered to entries with nonzero added or removed counts
   - the set difference between those, which is the line-ending-only set
   - `git ls-files --others --exclude-standard` grouped by top-level directory
5. State four counts explicitly: line-ending-only modifications, genuine content modifications, deletions, untracked files.

Acceptance: report exists, four counts stated, archive passes all four sanity gates. Stage 0 should complete in minutes. If it has run for more than about ten minutes, something is wrong: stop and diagnose rather than waiting.

No commit.

---

## Stage 1: Resolve line-ending churn

Largest and lowest-risk noise reduction. Runs before any content review so Stage 2 reviews real changes.

1. Do not modify `.gitattributes`. It is already correct.
2. Run `git add --renormalize .`.
3. Verify with `git diff --cached --ignore-cr-at-eol --numstat` that **every staged entry reports zero added and zero removed lines**. Any entry with nonzero counts contains real content change: unstage that specific file with `git restore --staged <path>` and record it for Stage 2. Renormalization must not carry content edits.
4. Run `git diff --cached --check`.
5. Commit.

Commit message: `chore: renormalize line endings to repository LF`

Acceptance: `python tasks.py validate` passes 488/488. Report the new `git status` totals and the delta from Stage 0.

---

## Stage 2A: Repair the job-description archive metadata

**This stage did not exist in the first draft of this specification. It was added after measurement showed the `scratch/jd_library/` worktree state is a data regression rather than churn. Run it before committing anything under `scratch/`.**

### 2A.1 What was measured

At HEAD `97b45ea`, scoped `git status` gives this distribution of modified tracked files:

| Path | Modified |
|---|---|
| `scratch/jd_library/` | **307** (306 `metadata.json` + `index.csv`) |
| `scripts/` | 13 |
| root `*.md` | 13 |
| `jobs/` | 5 |
| `Claude Review/` | 5 |
| `.context/` | 2 |
| `interview_prep/` | 2 |
| `source/` | 1 |
| `docs/`, `Study/` | 0 |

`scratch/jd_library/` also holds 169 of the untracked entries, which are new snapshot directories.

So roughly 86 percent of the modified-file count is one directory holding one file type. The genuine review burden outside `scratch/` is about 41 files, not 355. Size the Stage 2 effort accordingly.

### 2A.2 The regression

The 306 `metadata.json` diffs are not whitespace. A representative diff:

```diff
-  "role": "ERP Implementation Consultant",
+  "role": "Implementation Consultant",
-  "lane": "implementation_delivery",
+  "lane": "",
```

Across the working tree, **460 of 475 `metadata.json` files now carry `"lane": ""`. Only 15 retain a lane.** HEAD still holds correct lanes for the 306 that show as modified, which means the worktree is degraded relative to committed state.

### 2A.3 Why it matters

`.context/RULES_FOR_CLAUDE.md` states that safe tracker backfill depends on a matching current or archived job description, and that missing historical fit data must not be inferred without that match. Three consumers depend on the archive's `lane` field:

- `track_applications.refresh_row_metadata()` backfills tracker lane and fit from archived job descriptions
- `track_applications.row_job_description_text()` resolves a tracker row to its archived posting
- `build_jd_library.pattern_summary()` summarizes lane recurrence across the archive

An empty lane degrades all three silently. Nothing raises; the data simply stops being there.

### 2A.4 Root cause

`scripts/job_context_archive.py:181`

```python
def _safe_lane(job_description_text: str) -> str:
    try:
        return str(resume_analysis.job_problem_profile(job_description_text, "").primary_lane).strip()
    except Exception:
        return ""
```

A bare `except Exception` that writes an empty lane and emits no signal. It is called at lines 239 and 360, both on metadata write paths. Any refresh or rebuild that ran while lane classification was failing silently blanked the field across the archive.

### 2A.5 The data is recoverable

`_safe_lane()` works correctly at HEAD. Sampling five archived job descriptions returns correct lanes for all five, including the Acumatica snapshot whose stored metadata is now empty:

```
_safe_lane='implementation_delivery'  <- 20260623_222036_Acumatica_ERP_Implementation_Consultant_5bb29e84
_safe_lane='implementation_delivery'  <- 20260623_222036_Aptean_Lead_Implementation_...
_safe_lane='customer_success'         <- 20260623_222036_Barracuda_Partner_Success_...
_safe_lane='implementation_delivery'  <- 20260623_222036_BioTouch_Solutions_Imple...
_safe_lane='implementation_delivery'  <- 20260623_222036_BlueCherry_Integrations_...
```

Re-derivation therefore repairs the worktree **and** fixes the roughly 154 snapshots whose lane is already empty in HEAD. Prefer re-derivation over `git restore`, which would only recover the 306 and leave the rest broken.

### 2A.6 Procedure

1. Make `_safe_lane()` fail loudly. Catch only the specific exception types lane classification can legitimately raise, log the snapshot id and exception to stderr on failure, and return `""` only after logging. A silent empty lane must become impossible.
2. Add a `--refresh-metadata` path to `scripts/job_context_archive.py`, or use the existing rebuild path if one covers this, that walks every snapshot, re-derives `lane` from the stored `job_description.txt`, and rewrites `metadata.json` and `index.csv`.
3. **Do not re-derive `role`.** The `role` field also drifted (`ERP Implementation Consultant` became `Implementation Consultant`), and re-deriving it risks a second silent degradation from a different parser. Restore `role` from HEAD where HEAD has a value and the worktree differs. Where HEAD has no value, leave the worktree value.
4. Run the refresh. Report how many snapshots changed from empty to populated, and how many remain empty.
5. Assert the empty-lane count is **zero**.

   This threshold is measured, not estimated. Re-deriving lanes across a random sample of **253 of the 475 snapshots produced zero empty lanes and zero classification errors**. Observed distribution:

   | Lane | Count |
   |---|---|
   | `implementation_delivery` | 121 |
   | `program_delivery` | 33 |
   | `change_enablement` | 23 |
   | `analytics_operations` | 21 |
   | `presales_solution` | 20 |
   | `process_improvement` | 10 |
   | `customer_success` | 10 |
   | `corporate_strategy` | 9 |
   | `product_ownership` | 5 |
   | `technical_support_admin` | 1 |

   Every archived posting in the sample classifies cleanly. A single empty lane after refresh therefore indicates a failure, not an unclassifiable posting. If the count is nonzero, print the snapshot id, the first 200 characters of its `job_description.txt`, and any logged exception for **each** affected snapshot, then stop. Do not commit a partially repaired archive.

   An earlier draft of this specification set this threshold at 15. That was a guess made before measurement and it is wrong: it would let a refresh that silently failed on 3 percent of the archive pass unnoticed.
6. Spot-check ten repaired snapshots against `resume_analysis.job_problem_profile()` run directly on their `job_description.txt`, and confirm the stored lane matches.
7. Commit the repaired archive together with the 169 untracked snapshot directories.
8. Add a smoke check asserting that **every** `metadata.json` under `scratch/jd_library/` has a non-empty `lane`. Do not build in an allowance for unclassifiable postings; the measurement in step 5 shows there are none, and an allowance is exactly what would hide the next silent blanking. If a genuinely unclassifiable posting is archived later, that is the moment to revisit the assertion with evidence.

Commit message: `fix: repair job description archive lane metadata`

Acceptance: `python tasks.py validate` passes. Empty-lane count is zero. `python tasks.py track-report` runs and shows lane breakdowns rather than blanks. Ten spot-checks match `resume_analysis.job_problem_profile()` run directly.

---

## Stage 2: Triage genuine worktree changes

Only the Stage 1 residue reaches here. Classification is rule-driven, not judgment-driven.

### 2.1 Modified tracked files

Apply these rules in order. First match wins.

| Condition | Action |
|---|---|
| Path is under `scratch/jd_library/` | **Do not commit. Go to Stage 2A first.** These files carry a data regression; committing them destroys lane history. |
| Path is `scratch/applications.csv` | **Commit.** Live tracker state. |
| Path is under `jobs/` | **Commit.** Active job context is legitimate working state. |
| Path is under `Claude Review/` | **Discard** with `git restore`. Regenerable via `tasks.py claude-packet`. |
| Path is under `output/` or `render_check*/` | **Leave untouched.** Handled in Stage 6. |
| Path is under `scripts/`, `.context/`, `docs/`, or root, and the diff is only comments, docstrings, or formatting | **Commit** grouped as `docs:` or `style:`. |
| Path is under `scripts/` and the diff changes executable logic | **Commit** individually with a descriptive message, one commit per coherent change. Run `python tasks.py validate` before each. |
| Anything else | **Commit** with a descriptive message. |

Never batch unrelated `scripts/` logic changes into one commit. If a single file contains two unrelated logic changes, commit it once with a message naming both rather than attempting hunk surgery.

### 2.2 Deleted files (16 reported)

For each deletion, run `git log --oneline -3 -- <path>` and `git show HEAD:<path> | head -20`.

| Condition | Action |
|---|---|
| File is a generated output, render artifact, log, or `__pycache__` entry | **Stage the deletion.** |
| File is referenced by any file under `scripts/`, `tasks.py`, or `.context/` | **Restore it** with `git restore`. A referenced file deleted from the worktree is an accident. |
| File is a `.md` under root or `Study/` | **Stage the deletion**; it is covered by the Stage 0 archive. |
| Anything else | **Restore it.** Default to keeping. |

Record every restore in the final report.

### 2.3 Untracked files (214 reported)

| Condition | Action |
|---|---|
| Under `output/`, `render_check*/`, `.tmp/`, `backup/`, `backups/`, `__pycache__/` | **Leave.** Already ignored or handled in Stage 6. |
| Matches `debug-*.log`, `err.txt`, `err_c`, `err_tmp` | **Delete.** Already gitignored patterns. |
| Under `scripts/` with a `.py` extension | **Commit.** A new untracked script is real work. |
| Under `.context/` or `Study/` | **Commit.** |
| Is a `.docx`, `.pdf`, `.xlsx`, or `.pptx` outside `output/` and `source/` | **Leave and add a `.gitignore` entry** for its directory. Generated binaries do not belong in history. |
| Anything else | **Commit.** Default to preserving. |

Commits: as many as the content warrants, each narrowly scoped.

Acceptance: `python tasks.py validate` passes after each commit. Final `git status` is empty except `output/`, `render_check*/`, and directories newly added to `.gitignore`. Report the disposition count for each rule row.

---

## Stage 3: Close residual lint and source hygiene

### 3.1 Remove the duplicate `fail()`

`scripts/build_cover_letter.py:99` defines `fail()`, shadowing the `fail` imported from `utils` at line 52. They differ:

```python
# utils.py:24
def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)

# build_cover_letter.py:99
def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(message)
```

`SystemExit` with a string argument makes CPython print that string to stderr and exit 1. The exit code matches, but the message is emitted twice. Delete lines 99 through 101 and rely on the import.

Verify `run_resume_workflow.failure_kind()` does not depend on the duplicated line. It matches on `"not found:"`, `"traceback"`, and renderer text, none of which depend on repetition, so removal is safe. Confirm rather than assume.

### 3.2 Resolve the `signal_hits` shadow

`scripts/build_resume.py:102` imports `signal_hits` from `resume_analysis`. Line 990 rebinds it as a local.

Rule: grep the module for `signal_hits`. If every occurrence is inside the function at line 990, remove `signal_hits` from the import list at line 102. If any occurrence outside that function uses the imported symbol, rename the **local** to `signal_word_hits`. Never rename the imported symbol.

### 3.3 Strip the BOM

`scripts/build_cover_letter.py` is the only remaining file with a UTF-8 BOM. It breaks `ast.parse()` on the decoded source, so every AST-based lint and codemod silently skips the largest cover-letter module. This is why the original audit could not statically analyze that file.

Rewrite with `encoding="utf-8"` and no BOM.

### 3.4 Normalize intra-file line endings

`build_cover_letter.py`, `build_detailed_interview_guide.py`, `build_general_advice.py`, and `build_resume.py` all mix CRLF and LF internally. Convert each to pure LF.

### 3.5 Add a pre-commit hygiene hook

Add to `.pre-commit-config.yaml` a fast local hook rejecting UTF-8 BOMs and mixed line endings in `*.py` and `*.md`. Implement as a small Python script under `scripts/` so it needs no network install.

### 3.6 Restore the static analysis gate

Run `pip install pyflakes vulture` first. Neither was available last pass, so the final static-analysis acceptance criterion went unverified. It must not be skipped twice.

Commit message: `chore: close residual lint and source encoding hygiene`

Acceptance:

- `python tasks.py validate` passes 488/488
- `python -m pyflakes scripts/ tasks.py` reports zero undefined names and zero redefinitions
- `python -m vulture scripts/ tasks.py --min-confidence 90` reports zero unreachable blocks and zero unsatisfiable conditions
- `ast.parse()` succeeds on every file under `scripts/`. Assert this explicitly with a loop; it is the thing the BOM was silently breaking.

---

## Stage 4: Deduplicate the architecture map

1. Diff root `ARCHITECTURE_MAP.md` (84 lines) against `.context/ARCHITECTURE_MAP.md` (81 lines).
2. Merge into `.context/ARCHITECTURE_MAP.md` as canonical. `CLAUDE.md` already directs readers there and `.context/` is the documented compact-context entry point.
3. **Merge rule for conflicts:** where the two files describe the same subsystem differently, verify against the live code and keep whichever is accurate. Where both are accurate but differently worded, keep the `.context/` phrasing. Where only one file covers a topic, keep that content.
4. Delete the root copy. Do not leave a pointer stub; that is another file to keep in sync.
5. Grep for `ARCHITECTURE_MAP` across `AGENTS.md`, `CLAUDE.md`, `SYSTEM_REFERENCE.md`, `CONTRIBUTING.md`, `.github/`, `.codex/`, `.cursor/`, `.agents/`, `scripts/build_claude_review_packet.py`, and `scripts/claude_review_bundle.py`. Repoint every reference.
6. Confirm the normative font contract added last pass still lives only in `.context/RULES_FOR_CLAUDE.md`, and that the merged map references rather than restates it.

Commit message: `docs: consolidate architecture map into .context`

Acceptance: exactly one `ARCHITECTURE_MAP.md` exists. `python tasks.py claude-packet --mode broad` succeeds with no new self-audit warnings. `python tasks.py validate` passes.

---

## Stage 5: Relocate completed root specifications

Root holds 37 markdown files. Target is 12.

### 5.1 Delete confirmed duplicates

Re-verify each hash immediately before deleting; do not trust this document's hashes. Delete the root copy only where the hash matches `Study/Codex_Specs/` exactly. If any hash differs, treat that file as unique and move it in 5.2 instead.

### 5.2 Move completed work to `Study/Codex_Specs/`

Use `git mv` so history follows. Move every root `.md` matching `CODEX_SPEC_*`, `CODEX_PACKET_*`, `CODEX_IMPLEMENTATION_PLAN_*`, `CLAUDE_PLAN_*`, `ANALYSIS_*`, plus `ATS_HEADING_REVIEW.md` and `KEYWORD_COVERAGE_FINDINGS_AND_PLAN.md`, **except** those listed in 5.3.

Before each move, grep the repository for the filename. `scripts/build_claude_review_packet.py`, `scripts/claude_review_bundle.py`, and `.context/` files may cite specs by path. Update any reference found.

### 5.3 Keep at root

```
AGENTS.md
CLAUDE.md
SYSTEM_REFERENCE.md
CHANGELOG.md
CONTRIBUTING.md
QUEUED_WORK_PLAN.md
CODEX_NEXT_WORK_post_remediation.md
ARCHITECTURE_MAP.md          (deleted in Stage 4; listed here so it is not re-created)
CODEX_SPEC_system_audit_bugs_and_redundancy.md
CODEX_SPEC_worktree_cleanup_and_decoupling.md
```

The last two move to `Study/Codex_Specs/` in Stage 9, after their work is complete.

### 5.4 `Southern_Caribbean_Cruise_Guide.md`

Rule, no exceptions: create `personal/` at repository root, add `personal/` to `.gitignore`, and `mv` the file into it. Do not `git mv`; the file is untracked, so a plain move is correct.

This preserves the file, removes it from untracked-file noise, and keeps personal content out of a repository that gets packaged into Claude review bundles. Do not delete it. Do not move it outside the repository, since that would place it somewhere the user did not choose.

### 5.5 Debug log

Archive `debug-9b3920.log` (395 KB) into the Stage 0 archive location as a separate entry, then delete it. It is already gitignored.

Commit message: `docs: archive completed specifications to Study/Codex_Specs`

Acceptance: root markdown count is 10 or fewer plus the two active specs. Every moved file resolves at its new path. No script or context file references a moved path. `python tasks.py validate` and `claude-packet --mode broad` both pass.

---

## Stage 6: Clean `output/` in three reversible phases

**Archive protocol, applies to all three phases.** Before any deletion, write every scheduled file into `scratch/cleanup_archives/output_cleanup_<UTC timestamp>.zip` with a sibling JSON manifest recording original path, size, SHA-256, mtime, and removal reason. Confirm the ZIP opens and its entry count equals the deletion list length. Only then delete. Report the archive path and SHA-256.

### Phase 6a: Non-application debug artifacts

Delete these seven exactly:

```
sf_docbuild.docx
bf_docbuild.docx
sf_reg DRAFT.docx
_stage_smoke_all.docx
_stage_smoke_hr (HR Screen).docx
State Farm Direct Regression Guide DRAFT.docx
Sourcewell leakage check guide (HR Screen) DRAFT.docx
```

Also delete any file matching `_stage_smoke*`, `*_docbuild*`, or `sf_reg*`.

**Then fix the generator.** Grep `scripts/` and `scripts/smoke_test.py` for the strings `_stage_smoke`, `docbuild`, and `sf_reg`. Any test or helper writing into `OUTPUT_DIR` is the actual defect; tests belong in `TemporaryDirectory()`. Redirect them. Without this, the folder refills on the next suite run and this phase repeats forever.

Commit message: `chore: remove non-application debug artifacts from output`

### Phase 6b: PDFs

Delete all 60 `.pdf` files in `output/`. No exceptions.

`.context/RULES_FOR_CLAUDE.md` states final outputs are Word only. 47 of the 60 have no `.docx` sibling, so an orphan-based exception would spare 78 percent of them and defeat the purpose. They are pre-policy artifacts, and the archive is the safety net.

Commit message: `chore: remove PDF outputs per Word-only policy`

### Phase 6c: Newest-per-role pruning

The phase most likely to remove something wanted. Extend `scripts/cleanup_output.py`; reuse `normalize_company()`, `company_name_from_output_file()`, and `protected_company_keys()`.

**Family key algorithm.** Right-to-left stripping, in this exact order:

1. Strip the file extension.
2. If the stem matches an entry in the standalone list (Part 1.3) or matches `Career Operating Plan*`, `Daily Prep Plan*`, `Self-Inventory One-Pager*`, `Question_Bank_Audit*`, `Interview Prep Kit`, or `Public Speaking Transformation Plan`, return `None`. **A `None` family is never pruned.**
3. If the stem does not begin with `Christian Estrada - `, return `None`. This catches `Question_Bank_Audit_*` and any future non-conforming name. Never prune what you cannot parse.
4. Remove the `Christian Estrada - ` prefix.
5. Strip a trailing ` DRAFT` if present.
6. Strip a trailing parenthesized round qualifier matching `\s*\([^)]+\)$`, but **only if** what precedes it ends in a known document type. This preserves `(Platform & Data)` and `(Mid-Market)`, which are part of role names, while removing `(HR Screen)` and `(Hiring Manager)`. Apply this check before step 7 and re-test after.
7. Strip a trailing known document type. Match longest-first against this list:

```
Complete Interview Guide      Detailed Interview Guide
Round 2 Panel Interview Guide Panel Master Guide
Recruiter Screen Prep         Team Round Prep Addendum
Qualifications Statement      Pre-Interview Checklist
Application Checklist         Interview Cheat Sheet
90 Day Plan One-Pager         LinkedIn Update
Thank You Note                Thank-You Note
Cover Letter                  Federal Resume
Resume (Revised)              Resume
```

8. Strip a trailing audit token matching `\s+(PASS|BRIDGE|FAIL|POOR)$`. Repeat steps 5 through 8 until no further change, since `DRAFT` sometimes precedes the doc type.
9. If nothing was stripped in steps 5 through 8, the file has no document type. Return `None`.
10. Normalize the remainder: lowercase, collapse whitespace, strip punctuation except `&`, strip a trailing ` - ` fragment. The result is the family key.

**Special case:** `Interview Review - <company> - <role>` places the family after the doc type. Detect the literal prefix `Interview Review - ` after step 4 and take the remainder as the family key directly.

**Validation the algorithm must pass before any deletion.** These are assertions in code, not a review request:

- Every one of the 323 `.docx` files produces either a family key or `None`. No exceptions raised.
- The family count is **between 60 and 150**. A naive parse produced 411 from 523 files, which is definitionally wrong since it implies almost no file shares a family. If the count falls outside this band, the algorithm is broken: **abort the phase, write the computed families to the report, and stop.** Do not delete.
- Every file in the standalone list maps to `None`.
- `Christian Estrada - Rippling - Implementation Consultant (Platform & Data) FAIL Resume` and `... (Platform & Data) FAIL Detailed Interview Guide DRAFT` produce the **same** family key.
- `Christian Estrada - Dematic - Solution Consultant FAIL Detailed Interview Guide (HR Screen) DRAFT` and `... (Hiring Manager)` produce the same family key.
- No family key is the empty string.

**Retention rule.** Within each family, find the newest `Resume` or `Federal Resume` by mtime. Retain every file in that family whose mtime is greater than or equal to that resume's mtime minus 24 hours. This keeps the whole bundle together even when a cover letter is regenerated later than its resume. Delete the rest of the family.

If a family contains no resume, retain the entire family. Never prune a bundle you cannot anchor.

**Protections, applied before deletion:**

- Skip any family whose company matches `protected_company_keys()`.
- Skip any family with fewer than three files. Pruning a two-file family saves nothing and risks the wrong one.
- Skip any file modified within the last 14 days regardless of family.

**Interface.** Add `--prune-bundles`, which previews by default and prints, per family, the retained variant and the full removal list. Deletion requires the additional explicit flag `--prune-bundles-execute`. Write the preview to `scratch/cleanup_archives/prune_preview_<timestamp>.txt` and include its path in the report.

Also delete stale `render_check*/` folders via the existing seven-day retention. Reproducible; no archive needed.

Commit message: `feat: add newest-per-role output bundle pruning`

Acceptance: all assertions above pass. `python tasks.py validate` passes after each phase. `python tasks.py checklist` and `python tasks.py cover` still resolve their matching resume from the pruned `output/`, which is the real functional risk. Report exact archived, deleted, and retained counts.

---

## Stage 7: Extract `interview_story_engine.py`

Highest regression risk in this plan. It changes code feeding every interview document, for an architectural reason rather than a correctness one.

1. **Capture the behavioral baseline first.** From the current active job description, build a cheat sheet, a detailed interview guide, and a qualifications statement. Extract full visible text from each `.docx` and save to `scratch/cleanup_archives/story_engine_baseline/`. Record SHA-256 for each.
2. Create `scripts/interview_story_engine.py` with the five imported symbols plus the twelve transitive dependencies from Part 1.6. Re-derive that list by AST analysis first.
3. The new module must import **neither** `build_interview_cheat_sheet` nor `build_cover_letter`. If a moved symbol reaches back into either, that symbol moves too, or the dependency inverts. Do not paper over it with a function-local import; that hides the cycle from the Stage 8 isolation check while leaving it in place.
4. Re-export every moved symbol from `build_interview_cheat_sheet` so existing imports keep working.
5. Point `build_standard_qualifications_statement.py` at the new module directly.
6. Move the corresponding smoke checks to the new module, retaining at least one check against the cheat-sheet re-export so the compatibility surface stays covered.

Commit message: `refactor: extract shared interview story engine`

Acceptance, in priority order:

- Regenerate all three documents from the same job description. Visible text must be **byte-identical** to the baseline. Any difference stops the stage.
- `python tasks.py validate` passes at full count.
- `python -c "import build_standard_qualifications_statement"` succeeds.
- The new module's import graph contains no builder module.

**If the text diff is not clean, revert the stage.** Do not adjust the baseline to match. A refactor that changes output is not a refactor. Record the diff in the report and continue to Stage 8 with Stage 7 reverted.

---

## Stage 8: Decouple and verify the federal import chain

1. Confirm the chain: `build_federal_resume` imports `build_standard_qualifications_statement`, which after Stage 7 imports `interview_story_engine` rather than `build_interview_cheat_sheet`.
2. Trace anything else pulling `build_interview_cheat_sheet` or `build_cover_letter` into the federal path. Resolve each identically: move the shared symbol to a neutral module, or invert the dependency.
3. Add a smoke check importing `build_federal_resume` in a clean interpreter and asserting neither `build_interview_cheat_sheet` nor `build_cover_letter` appears in `sys.modules`. This is the guard that stops the chain reforming.
4. Measure import time for `build_federal_resume` before and after. **Set `PYTHONPYCACHEPREFIX` to a local directory when measuring.** On a slow or networked filesystem, bytecode writes dominate: the original audit's 30-second figure was 12 seconds of `importlib._write_atomic` and was an environment artifact, not a finding. Report both numbers and the cache prefix used.

If Stage 7 was reverted, skip steps 1 and 2, and still add the isolation check from step 3 as a currently-failing expected-failure test marked with the reason. This preserves the finding.

Commit message: `refactor: decouple federal resume from commercial builders`

Acceptance: isolation check passes. `python tasks.py federal-resume` and `python tasks.py resume` both complete. Full suite passes.

---

## Stage 9: Archive these specifications

Move `CODEX_SPEC_system_audit_bugs_and_redundancy.md` and `CODEX_SPEC_worktree_cleanup_and_decoupling.md` to `Study/Codex_Specs/` with `git mv`. Append a summary to `CHANGELOG.md` covering both passes: the 16 audit findings and the nine cleanup stages.

Commit message: `docs: archive completed audit and cleanup specifications`

---

# Part 3: Global rules

**Branch.** All stages land on `codex-cleanup-and-decoupling`, branched from `97b45ea`.

**Staging.** Stage only hunks belonging to the current stage. Run `git diff --cached` and `git diff --cached --check` before every commit. Stages 1 and 2 are exceptions in scale, not in discipline.

**Validation cadence.** `python tasks.py validate` after every commit, full suite, never a subset. The count must remain at or above 488 and must never drop.

**Deletion discipline.** Nothing is deleted before being archived to `scratch/cleanup_archives/` with a manifest, except `render_check*/`, `__pycache__/`, and the gitignored log patterns in Stage 2.3, all of which are reproducible. Confirm each archive opens before the corresponding delete runs.

**No mid-run questions.** Every decision in this specification is pre-made. Where a rule yields an unexpected result, follow the rule and record the deviation. The only interruptions are the stop conditions below.

**Stop conditions.** Halt the entire run and report:

- Stage 1 renormalization stages a file with genuine content changes that cannot be cleanly unstaged
- Stage 3 leaves any undefined name, unreachable block, or `ast.parse()` failure
- Stage 2A leaves any snapshot with an empty lane after refresh (measured expectation is zero; see 2A.6 step 5)
- Stage 6c family count falls outside 60 to 150, or any listed assertion fails
- The smoke count drops below 488 at any point
- Any archive ZIP fails to open or its manifest count mismatches

Stage 7 failing its byte-identical gate is **not** a stop condition. Revert that stage and continue.

**Final report.** Every commit with its message. The four Stage 0 counts against final values. Every archive path with SHA-256. Stage 2 disposition counts per rule row. Exact `output/` deleted and retained counts plus family count. Stage 7 diff result. Stage 8 import measurements with cache prefix. Complete remaining worktree state.

---

# Part 4: Sequencing rationale

Stages 1 and 2 come first because every later stage is harder to review against a 569-entry status, and because deleting files while hundreds of unrelated changes sit uncommitted is how work gets lost.

Stage 3 precedes the documentation and file-move work because the BOM currently blocks AST tooling on the largest cover-letter module, and Stage 5 greps the codebase for filename references.

Stage 6 precedes Stage 7 so the story-engine baseline is captured against an already-clean `output/`, removing ambiguity about which resume a regenerated document matched.

Stages 7 and 8 come last because they carry the only real regression risk. Everything before them is recoverable from an archive. A subtly wrong story engine is not, because it produces documents that look correct.
