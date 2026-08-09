# CODEX SPEC: System Audit Remediation (Bugs, Dead Code, Redundancy)

Date: 2026-08-07
Author: Claude (review + plan pass)
Scope: full-system static and dynamic audit of `scripts/` and `tasks.py`
Implementation: Codex applies all edits and runs validation. No edits were made during this review.

## Baseline established during review

- `python3 -m pyflakes scripts/ tasks.py`: 39 findings (4 undefined names, 35 unused locals / redefinitions / empty f-strings).
- `python3 -m vulture scripts/ tasks.py --min-confidence 90`: 31 findings, including 2 unreachable-code blocks and 1 unsatisfiable condition.
- `scripts/smoke_test.py`: run in slices covering all 480 registered checks. **477 pass, 3 fail.** All 3 failures share one root cause (Finding 3).
- Two crashes were reproduced directly by executing the functions against synthetic `document.xml` fixtures. They are not theoretical.

Findings are ordered by severity. Each carries the exact file, line, why it matters, the fix, and the regression test to add.

---

# P0 — Confirmed runtime crashes in the live resume build

## Finding 1: `remove_global_low_fit_bullets()` raises `NameError`

**File:** `scripts/resume_content.py:3525`
**Live caller:** `scripts/build_resume.py:7039` — `role_bullets_removed += remove_global_low_fit_bullets(document_xml)`

The function signature is `remove_global_low_fit_bullets(document_xml: Path, max_remove: int = 4)`. It has no `job_description` parameter, but line 3525 calls:

```python
if bullet_deserves_explicit_fit_protection(original_text, job_description):
```

**Reproduced:** building a fixture whose bullet text contains `"applied codex-assisted automation"` raises `NameError: name 'job_description' is not defined`. The crash fires whenever any source bullet matches one of the seven `patterns` entries — several of which are real Aptean/East West bullets ("designed and executed user enablement programs", "advised clients against high-risk or low-value customizations", "negotiated vendor agreements, system enhancement scopes").

**Why it matters:** this aborts `build_resume()` mid-assembly for any job description whose bullet set trips a pattern. Smoke tests never caught it because no registered check drives this function with a matching bullet.

**Fix:** thread the job description through. Change the signature to

```python
def remove_global_low_fit_bullets(document_xml: Path, job_description: str, max_remove: int = 4) -> int:
```

and update the call site at `build_resume.py:7039` to `remove_global_low_fit_bullets(document_xml, job_description)`. Check `scripts/build_federal_resume.py` and `scripts/smoke_test.py` for other call sites before committing.

Do **not** fix by deleting the protection check — `bullet_deserves_explicit_fit_protection()` is the guard that stops a JD-relevant bullet from being removed. Dropping it would silently delete supported evidence.

**Regression test:** add a smoke check that calls `remove_global_low_fit_bullets()` on a fixture containing one pattern-matching bullet that the JD explicitly requires, and assert (a) no exception, (b) the protected bullet survives.

## Finding 2: `merge_low_fit_bullets_before_delete()` raises `NameError`

**File:** `scripts/resume_content.py:3275`
**Live caller:** `scripts/build_resume.py:7036`

Line 3275 calls `audit_keywords(job_description)`, but `audit_keywords` is never imported into `resume_content.py`. The import block at lines 25-45 pulls in `high_value_audit_keywords` and `ats_scan_terms`, not `audit_keywords`.

**Reproduced:** a fixture with an East West role header and a `"designed and executed user enablement programs"` bullet raises `NameError: name 'audit_keywords' is not defined`. The guard at line 3262 restricts this to `CONDENSABLE_BULLET_COMPANIES = ('East West Manufacturing', 'Aptean')`, both of which are in every generated resume.

**Fix:** add `audit_keywords` to the `from resume_analysis import (...)` block in `scripts/resume_content.py`. Confirm `resume_analysis.audit_keywords` is the intended function and not `high_value_audit_keywords` — the surrounding code scores bullets for retention, so the broader `audit_keywords` set is probably correct, but verify against `build_resume.reorder_bullets()`, which uses the same `score(text, keywords)` helper.

**Regression test:** same shape as Finding 1 — drive the function with an East West fixture containing an absorbed pattern and assert the merge completes.

## Finding 3: Stale `Study/` paths break the career plan (3 failing smoke checks)

**File:** `scripts/interview_intelligence.py:31-42` (`STUDY_TRACK_REFERENCES`) and `:43+` (`QUESTION_THEME_TRACKS`)

All ten `STUDY_TRACK_REFERENCES` entries point at flat paths like `Study/IT_Flashcards_PMP.txt` and `Study/IT_Learning_Path_and_Schedule.docx`. Every one of them returns `False` from `Path.exists()`. The files were reorganized into subfolders:

- `Study/IT_Flashcards_*.txt` → `Study/Flashcards/IT_Flashcards_*.txt`
- `Study/IT_Learning_Path_and_Schedule.docx` → `Study/Guides/IT_Learning_Path_and_Schedule.docx`

`_existing_study_references()` therefore returns an empty tuple, and `build_career_plan()` raises `ValueError("no Study references were found for the career operating plan")` unconditionally. **`python tasks.py career-plan` is completely broken.**

**Failing smoke checks:**

- `career plan roles modes and safe gaps`
- `career plan Study tracks are real`
- `career operating plan command builds Word plan`

**Scope:** 36 string literals across `scripts/` still use the old flat `Study/...` prefix, 32 of them in `interview_intelligence.py`. `QUESTION_THEME_TRACKS` has the same problem, and it degrades silently — theme tracks resolve to nothing and study references vanish from interview outputs without an error.

**Fix:**

1. Repoint every `Study/IT_Flashcards_*.txt` literal to `Study/Flashcards/...` and `Study/IT_Learning_Path_and_Schedule.docx` to `Study/Guides/...`.
2. Note that `Study/IT_Flashcards_SecurityPlus.txt` and `Study/IT_Flashcards_AWS.txt` need verifying against the actual `Study/Flashcards/` listing before repointing — confirm each target exists rather than assuming the rename pattern holds for all ten.
3. Prefer defining a single `STUDY_ROOT` / `STUDY_FLASHCARDS_DIR` constant and building paths from it, so the next reorganization is a one-line change.

**Regression test:** the existing `career plan Study tracks are real` check already covers this. Additionally assert that every value in `QUESTION_THEME_TRACKS` resolves to an existing file, so silent degradation becomes a hard failure.

---

# P1 — Silent logic defects (no crash, wrong or missing behavior)

## Finding 4: Story-diversity guard is unreachable

**File:** `scripts/build_interview_cheat_sheet.py:4704` and `:4867-4872`

`behavioral_answer_scripts()` does `return [` at line 4704 and closes the list at 4867. Lines 4868-4872 are dead:

```python
4867:    ]
4868:    story_diversity_warning(
4869:        question_labels=[answer.prompt for answer in answers],
4870:        assigned_stories=[achievement, leadership, persuasion, analysis, failure, teamwork, rapid],
4871:    )
4872:    return answers
```

Confirmed by vulture (`unreachable code after 'return'`, 100% confidence) and pyflakes (`undefined name 'answers'`).

**Why it matters:** `story_diversity_warning()` exists to warn when one story is assigned to 3+ behavioral questions. It has never executed. Cheat sheets and detailed guides can silently reuse the same story across most of the behavioral bank — exactly the failure mode the function was written to catch.

**Fix:** bind the list, then warn, then return.

```python
    answers = [
        ... (unchanged list body, lines 4705-4866) ...
    ]
    story_diversity_warning(
        question_labels=[answer.prompt for answer in answers],
        assigned_stories=[achievement, leadership, persuasion, analysis, failure, teamwork, rapid],
    )
    return answers
```

Note `question_labels` is accepted but unused inside `story_diversity_warning()` (pyflakes/vulture both flag it). Either use it in the warning message — which would be more useful, since it would name which questions collide — or drop the parameter. Prefer using it.

**Regression test:** call `behavioral_answer_scripts()` with a single `StoryCard` so every slot falls back to the same story, capture stdout, and assert `STORY DIVERSITY WARNING` is emitted. The existing `behavioral answer scripts empty story guard` check does not cover this.

## Finding 5: Unreachable fallback in `summary_fit_close_sentence()`

**File:** `scripts/resume_content.py:1542-1545` (function `summary_fit_close_sentence`, lines 1442-1598)

Indentation bug. Line 1537 opens `if leadership_emphasis and is_education_assessment_context(job_description):` at indent 8. Its `return` at 1538 is at indent 12. The next `return` at 1542 is **also at indent 12**, so it sits inside the same `if` body and can never run.

Compare the sibling structure at 1518-1526, where the analogous fallback `return` is correctly placed at the outer level.

**Why it matters:** the analytics/reporting lane loses its close-sentence fallback. When none of the preceding conditions match, execution falls past line 1545 to whatever follows instead of returning "Best used where reporting depth and operating judgment improve decision speed…". This changes generated Professional Summary content for that lane.

**Fix:** dedent lines 1542-1545 from indent 12 to indent 8.

**Regression test:** assert `summary_fit_close_sentence()` returns the "decision speed, workflow clarity" sentence for an analytics-lane JD that matches none of the earlier branches.

## Finding 6: Six documented formatting enforcers are imported but never called

**File:** `scripts/build_resume.py:242-267` (import block from `resume_format`)

These are imported into `build_resume.py` and referenced nowhere in the repository:

| Function | Documented responsibility |
|---|---|
| `force_document_font` | Carlito on direct run-level `rPr` in `document.xml` |
| `apply_dense_font_sizing` | dense KPMG font profile |
| `force_paragraph_single_spacing` | paragraph-level single spacing |
| `apply_resume_spacing_rhythm` | role and bullet spacing rhythm |
| `apply_core_competency_row_spacing` | Core Competencies row spacing |
| `normalize_linkedin_hyperlink_targets` | LinkedIn target normalization |

Only `force_styles_font()` and `force_style_single_spacing()` run (`build_resume.py:7024-7027`), and both operate on `styles.xml`. `apply_fit_font_sizing()` runs inside `resume_format.pack_docx_with_page_fit()` at `resume_format.py:232`.

**Why it matters:** `.context/SCRIPT_INDEX.md` and `.context/ARCHITECTURE_MAP.md` both describe these as part of the live formatting pipeline, and `.context/RULES_FOR_CLAUDE.md` states "Font: Carlito everywhere" and "Do not allow Word default spacing, 1.15 line spacing, expanded paragraph spacing." Style-level enforcement alone does not override direct run-level or paragraph-level formatting carried in from the source DOCX. Today the KPMG source is style-driven so output is probably still correct, which is why nothing has caught this — but the defensive enforcement the rules assume is not wired in.

**This one needs a decision, not a blind fix.** Codex should:

1. Render a current output DOCX and inspect `word/document.xml` for direct `rFonts`/`sz`/`spacing` attributes that deviate from Carlito / 10pt / single. Use `python tasks.py ats-check` plus a direct XML grep.
2. If deviations exist → wire the calls into `assemble_variant()` after line 7027 in source order, then confirm two-page fit still holds.
3. If no deviations exist → remove the six unused imports and correct `.context/SCRIPT_INDEX.md` and `.context/ARCHITECTURE_MAP.md` so the docs stop describing a pipeline that does not run.

Either way, the docs and the code must end up agreeing.

`normalize_linkedin_hyperlink_targets` is safe to drop regardless: the LinkedIn rule is genuinely enforced by `remove_linkedin_hyperlinks(work_dir)` at `build_resume.py:7170`.

## Finding 7: `Iterable` used without import

**File:** `scripts/build_resume.py:3195` (`keyword_placement_audit`, `early_bullets: Iterable[str] | None = None`)

`Iterable` is never imported. This does not raise today only because `build_resume.py` has `from __future__ import annotations`, so annotations stay strings. It becomes a hard `NameError` the moment anything calls `typing.get_type_hints()` on the module, or if the `__future__` import is ever removed.

**Fix:** add `Iterable` to the `typing` (or `collections.abc`) import at the top of `build_resume.py`.

---

# P2 — Robustness and divergence

## Finding 8: Tracker CSV write is non-atomic

**File:** `scripts/track_applications.py:93-99`

```python
with TRACKER.open("w", newline="", encoding="utf-8") as handle:
```

`open("w")` truncates `scratch/applications.csv` immediately. If the process is interrupted mid-write — Ctrl-C, the workflow runner's ten-minute step timeout, or a Windows file lock from an open Excel window — the tracker is left truncated or empty with no backup.

This is the system's only persistent operational dataset, and it is not reconstructible from `output/` because `lane_label` and `fit_status` are derived at write time.

**Fix:** write to a sibling temp file in the same directory, `flush()` + `os.fsync()`, then `os.replace()` onto the target. Keep one rotating `.bak` alongside it. `os.replace()` is atomic on Windows for same-volume renames.

**Regression test:** simulate a mid-write failure (patch `csv.DictWriter.writerow` to raise on the third row) and assert the original tracker file is intact afterward.

## Finding 9: `failure_kind()` misclassifies by substring order

**File:** `scripts/run_resume_workflow.py:311-331`

Classification is a sequence of `in` checks against lowercased stdout+stderr. Two problems:

- `"not found:"` (line 321) is broad and is tested *before* `"traceback"` (line 329). Any Python traceback containing `FileNotFoundError: ... not found: ...` is reported as `missing_required_file`, and the user is told to check inputs rather than shown a real crash.
- `"render_docx"` (line 327) matches the *script name* as well as a render failure, so a step that merely mentions the renderer in its log is classified as `render_failure` and gets the retry-once path.

**Why it matters:** `run_with_recovery()` branches on `failure_kind()`. A misclassification means either a pointless retry of a deterministic failure, or a real traceback presented as a missing-file problem.

**Fix:** check `"traceback"` first and return `unexpected_traceback` immediately — a traceback is never a clean validation stop. Then tighten the remaining patterns: anchor `"not found:"` to the known `require_file()` message prefix, and match render failures on the renderer's actual error text rather than the bare script name.

**Regression test:** feed `failure_kind()` a synthetic `StepResult` whose output is a traceback containing `not found:` and assert `unexpected_traceback`.

## Finding 10: Divergent duplicate readers give different text to different builders

Three helpers are copy-pasted with **behavioral differences**, not just duplication:

**`read_text` — 10 definitions**

| Location | Strips? | Missing file | Encoding fallback |
|---|---|---|---|
| `utils.py:56` | yes | raises | UTF-16 fallback |
| `job_context_archive.py:75` | yes | returns `""` | none |
| `analyze_job.py:20`, `build_followup_email.py:25`, `build_interview_followup.py:30`, `build_linkedin_update.py:26`, `build_post_round.py:26`, `build_thank_you.py:34` | no | returns `""` | none |
| `build_claude_review_packet.py:468`, `claude_review_bundle.py:54` | no | raises | none |

Only `utils.read_text()` has the UTF-16 fallback. Every other reader hard-fails on a job description saved as UTF-16 — a realistic outcome when pasting from Word or Notepad on Windows.

**`docx_visible_text` — 5 definitions** (`analyze_job.py:24`, `build_linkedin_update.py:30`, `build_skills_gap.py:35`, `integration_test.py:64`, `preview_summary.py:20`). Three keep empty paragraphs as blank lines; two drop them. Two do not collapse internal whitespace.

**`paragraph_texts` — 3 definitions** (`build_cover_letter.py:3945`, `build_interview_cheat_sheet.py:1198`, `compare_resumes.py:29`). The cover-letter version collapses internal whitespace with `re.sub(r"\s+", " ", ...)`; the cheat-sheet version only calls `.strip()`.

**Why the last one matters most:** `build_cover_letter.py` and `build_interview_cheat_sheet.py` read the *same generated resume* to extract evidence, using differently-normalized text. A resume bullet containing a double space or a line break inside a run yields a different string in each, so keyword matching and evidence selection can legitimately disagree between the cover letter and the interview prep for the same job.

**Fix:** promote one canonical implementation of each into `scripts/utils.py` (or `resume_format.py` for the DOCX readers), delete the copies, and import. Use the strictest existing behavior as canonical: strip, collapse internal whitespace, drop empty paragraphs, UTF-16 fallback, return `""` for missing files.

Sequence this carefully — consolidating `read_text` changes whether callers get stripped text and whether a missing file raises. Do it one helper at a time with a full smoke run between each.

**Regression test:** assert `build_cover_letter.paragraph_texts()` and `build_interview_cheat_sheet.paragraph_texts()` return identical output for a fixture DOCX containing a paragraph with a double space and an empty paragraph.

## Finding 11: `paragraph_text`, `is_bullet`, and `W` are defined twice

`scripts/build_resume.py` imports `W`, `paragraph_text`, and `is_bullet` from `resume_format` (line 242 block), then **redefines all three** at lines 365, 1262, and 1346. The redefinitions shadow the imports.

Verified byte-identical today, so there is no live defect — but `resume_content.py` and `commercial_resume_model.py` use the `resume_format` versions while `build_resume.py` uses its own. Any future edit to one copy silently diverges the XML parsing between the content model and the assembly layer.

**Fix:** delete the three redefinitions in `build_resume.py` and rely on the imports. Confirm no local variable named `W` or `score` collides in the intervening scope.

---

# P3 — Redundancy removal and hygiene

These are the "remove redundant code" items. None change behavior; all reduce surface area.

## Finding 12: 286 lines of dead code in `smoke_test.main()`

**File:** `scripts/smoke_test.py:17274-17559`

`main()` opens with `checks = (...)`, a 286-line tuple of `(label, None)` pairs. It is never read. The live registry is `registered_checks` at line 17627. Flagged by pyflakes as `local variable 'checks' is assigned to but never used`.

This is an obsolete registry left behind by a refactor. It is actively harmful: it looks authoritative, and anyone adding a check may add it here and wonder why it never runs.

**Fix:** delete lines 17274-17559 outright.

## Finding 13: Unused imports and locals

From vulture at 90%+ confidence and pyflakes. Remove after confirming each is not an intentional re-export (`build_resume.py` deliberately re-exports helpers per `.context/SCRIPT_INDEX.md`, so treat its import block with care — cross-check against Finding 6 first).

Unused imports: `build_career_operating_plan.py:11` (`WD_CELL_VERTICAL_ALIGNMENT`), `build_cover_letter.py:32` (`WD_TAB_ALIGNMENT`), `build_daily_interview_rehearsal_workbook.py:19,21`, `build_detailed_interview_guide.py:46` (`validate_state_farm_workbook_text` — verify; the State Farm playbook may expect it to be re-exported), `build_resume.py:101` (five `story_lens_*` / `employer_context_sentence`), `build_resume.py:192` (three summary helpers), `resume_content.py:25` (three `story_lens_*`).

Unused locals: `application_status.py:82`, `build_application_checklist.py:269`, `build_cover_letter.py:3270,6071,6971`, `build_detailed_interview_guide.py:818,3159`, `build_federal_resume.py:1729,1730`, `build_interview_cheat_sheet.py:358,3754`, `build_resume.py:5671,6525`, `interview_context.py:639`, `run_resume_workflow.py:492`, `smoke_test.py:6516,17593,17594`, `verify_rehearsal_workbook.py:185`, `tasks.py:375,868`, `build_daily_interview_rehearsal_workbook.py:488`, `cleanup_render_checks.py:92`, `resume_analysis.py:298`.

Empty f-strings (`f"..."` with no placeholder): `build_cover_letter.py:5324`, `build_interview_cheat_sheet.py:1754,1839,3980,5032`, `text_safety.py:111`.

Redundant redefinition: `build_cover_letter.py:99` redefines `fail` from line 52.

## Finding 14: `detect_company_profile` is a permanent stub behind `if False`

**File:** `scripts/build_cover_letter.py:7108`

```python
# stub: implement detect_company_profile in build_resume.py before enabling this block.
firm_profile = build_resume.detect_company_profile(company_name, job_description) if False else None
```

`resume_analysis.detect_company_profile()` exists at line 3005, and `scripts/smoke_test.py:13188` asserts it "should remain a no-op stub until implemented" — so the stub is deliberate and consistent. But the `if False` makes the `elif firm_profile:` branch at 7115-7118 permanently dead, and `build_cover_letter.py:4486` and `build_interview_cheat_sheet.py:5260` call the same stub live, burning a call to get `None`.

**Fix (choose one, do not leave it as is):** either implement the profile lookup and delete the `if False`, or delete the dead branch and its two live no-op call sites and record the intent in `.context/COMMON_CHANGE_AREAS.md`. The `if False` guard is the worst of both — it reads as working code.

## Finding 15: Import chain couples unrelated builders

`build_federal_resume` → `build_standard_qualifications_statement` → `build_interview_cheat_sheet` → `build_cover_letter` → `build_resume` → `commercial_resume_model` → `resume_analysis`.

The federal resume builder transitively imports the commercial cover-letter and interview-cheat-sheet modules. Anything imported for the federal path pays for all of it, and a syntax error in the cheat sheet breaks the federal resume.

**Fix (low priority, do not bundle with the P0 fixes):** identify what `build_standard_qualifications_statement` actually needs from `build_interview_cheat_sheet` and lift those helpers into a shared module. This is a multi-step refactor and should be its own change with its own smoke run.

## Finding 16: Repository hygiene

- **`output/` holds 523 files, 60 of them PDFs.** `.context/RULES_FOR_CLAUDE.md` says "Create polished Word documents only. Do not create PDFs as final outputs." `scripts/cleanup_output.py` and `python tasks.py cleanup` exist but are evidently not being run. Run cleanup; if the PDFs are legacy artifacts the rule intends to exclude, confirm the retention policy covers them.
- **37 markdown files at the repository root**, mostly historical `CODEX_SPEC_*`, `CODEX_PACKET_*`, and `ANALYSIS_*` handoffs. `Study/Codex_Specs/` already exists as a home for these. Move completed specs there and keep only active ones at root.
- **`debug-9b3920.log` (395 KB) at root.** Gitignored, but present. Delete.
- **`ARCHITECTURE_MAP.md` exists twice** — root (84 lines) and `.context/` (81 lines) — and they have **diverged**. `CLAUDE.md` directs readers to the `.context/` copy. Delete the root copy or make it a pointer, so there is one source of truth.
- **`scripts/build_cover_letter.py` has a UTF-8 BOM and mixed CRLF/LF line endings.** The BOM breaks `ast.parse()` on the decoded source, so any AST-based lint or codemod silently skips the largest cover-letter module. `build_detailed_interview_guide.py`, `build_general_advice.py`, and `build_resume.py` also have mixed line endings. Normalize to no BOM and consistent endings, and add the rule to `.pre-commit-config.yaml`.

---

# Recommended fix order

Each numbered stage is one commit with a full `python tasks.py validate` before moving on.

1. **Findings 1, 2, 3** — the crashes and the broken `career-plan` command. Finding 3 should take all 480 smoke checks to green.
2. **Findings 4, 5, 7** — unreachable code and the missing `Iterable` import. Small, isolated, each with a new regression test.
3. **Finding 12** — delete the dead `checks` tuple. Do this before any other `smoke_test.py` work so new tests land in the right registry.
4. **Finding 6** — investigate the formatting enforcers, then either wire them in or remove them and correct the `.context/` docs. Requires a rendered-output check, not just a smoke run.
5. **Findings 8, 9** — atomic tracker write and failure classification.
6. **Finding 10** — consolidate `read_text`, `docx_visible_text`, `paragraph_texts`. One helper per commit, full smoke run between each.
7. **Findings 11, 13, 14, 16** — redundancy and hygiene cleanup.
8. **Finding 15** — import decoupling, as a standalone change.

# Validation requirements

- `python tasks.py validate` must reach 480/480 after stage 1. It is currently 477/480.
- After stage 1, build a real resume end to end against a JD whose bullets trip the `remove_global_low_fit_bullets` patterns — the smoke suite does not exercise that path today, which is why both crashes shipped.
- After stage 4, render the output and confirm two-page fit, Carlito throughout, and 10pt minimum body text.
- After stage 6, diff a generated cover letter and interview cheat sheet built from the same resume before and after consolidation; evidence selection should not change.
- Re-run `python -m pyflakes scripts/ tasks.py` and `python -m vulture scripts/ tasks.py --min-confidence 90` at the end. Both should be materially cleaner, and no new undefined names or unreachable blocks should appear.

# Notes on scope

Two things were investigated and are **not** defects:

- **Import time.** `import_major_scripts()` takes ~30s in a sandboxed Linux mount, but profiling attributes 12 of those 16 seconds to `importlib._write_atomic` writing `.pyc` files to a slow network mount. With `PYTHONPYCACHEPREFIX` on local disk the same imports take 4.5s. This is an artifact of the review environment, not a problem on the user's machine.
- **Missing `encoding=` arguments.** An initial AST sweep flagged 66 `read_text` / `open` calls without an explicit encoding. Nearly all resolve to a module-local `read_text()` helper that does specify `utf-8-sig`. The real issue is the duplication and divergence of those helpers, captured as Finding 10, not a bare encoding bug.
