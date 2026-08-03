# Claude Review: Reliability and Reporting Remediation Plan

Review pass only. No source files were modified. Findings are ranked by severity and reference live code verified against the working tree on 2026-08-02.

Verification method: read the affected functions directly and executed the federal parsers against the active `jobs/federal_job_description.txt`.

---

## Verdict

The plan is directionally correct on all five workstreams, and every defect it names is real. It is not safe to hand to Codex as written, because of one wrong diagnosis (F1), two behavioral conflicts the plan does not resolve (C1, C2), and several missing scope items that would leave the stated verification steps passing while the underlying problem remains.

---

## CRITICAL

### C1. Timeout will be silently retried, doubling the limit and defeating the stated stop condition

`scripts/run_resume_workflow.py:311` classifies any output containing `"timed out"` as `render_or_timeout`, and `run_with_recovery()` at line 364 retries that kind exactly once. The plan requires that a timeout "return a nonzero result, and stop downstream steps/tracker updates," but under current control flow a timed-out step is retried automatically, so the real ceiling is two times the limit and the run continues.

Also note `run_with_recovery()` recurses: a `missing_resume_output` recovery calls `run_with_recovery("Building resume", ...)` at line 356, so a pathological case can chain three timed-out step executions.

Required plan additions:

- State explicitly whether a timeout is retryable. Recommended: not retryable. Add a distinct `failure_kind` value (for example `step_timeout`) rather than reusing `render_or_timeout`, and exclude it from the retry branch at line 364.
- If the timeout message is allowed to contain the literal string `timed out`, the new classifier branch must be ordered before the existing `render_or_timeout` check.

### C2. Five minutes is likely below the real cost of a resume step

`scripts/render_checks.py:111` already applies a 180-second subprocess timeout to a single render, and `scripts/resume_format.py:1202` applies 120 seconds. `build_resume.py` performs render checks inside the step. A 300-second step budget therefore leaves roughly two minutes for the entire content build, XML manipulation, audit, and packing on a cold Word/LibreOffice start.

The plan asserts five minutes as a fact under Assumptions with no measurement. Required change:

- Measure actual wall-clock duration of each commercial and federal step on this machine before fixing the constant.
- Set the limit to a measured p95 plus generous headroom, and make it overridable by environment variable so a slow cold start does not turn a correctness fail-safe into a false failure.
- The limit must in all cases exceed the sum of the nested `render_checks` and `resume_format` timeouts, or the outer timeout will preempt the inner ones and destroy their diagnostic messages.

### C3. Workspace health check runs before the dry-run branch, so `federal-dry-run` can write files

`scripts/run_federal_resume_workflow.py:333` calls `ensure_workspace_health_or_exit()` before `if args.dry_run` on line 334. `ensure_workspace_health_or_exit()` currently calls `attempt_question_prep_recovery()`, which can execute `git restore -- scripts/question_prep.py` (`workspace_health.py`, git-restore branch) and can copy backup files over `scripts/question_prep.py`.

That means `python tasks.py federal-dry-run`, which prints "no files will be written" at line 172, can in fact discard uncommitted work. Same ordering exists at `run_resume_workflow.py:577`.

The plan's read-only change does fix this, but the plan does not name it, so the fix could be implemented in a way that preserves the ordering bug (for example by leaving a recovery call in a preflight helper). Add an explicit requirement: no health-check code path invoked by a dry run may write to the working tree, and add a regression test asserting `dry-run` and `federal-dry-run` leave `git status --porcelain` unchanged.

### C4. Silent destruction of uncommitted edits is the actual severity of the recovery bug, and the plan understates it

The plan frames read-only health checks as a safety improvement. The concrete failure is worse: `git restore -- scripts/question_prep.py` runs whenever `question_prep_health()` returns anything other than `healthy`, which includes `parse-failed`. A user mid-edit with a syntax error in `question_prep.py` who runs `python tasks.py resume` loses that work with no prompt and no backup, because the backup-preservation step only exists on the backup-copy branch, not the git-restore branch.

This should be recorded as the primary justification, and the recovery guidance text the plan wants must tell the user their file is unchanged, so they do not assume the workflow already reverted it.

### C5. `requirement_engine.parse_federal_requirements()` returns zero requirements on the active posting, and the plan does not cover it

There are two independent federal requirement parsers. The plan targets only one.

Executed against `jobs/federal_job_description.txt`:

```
requirement_engine.parse_federal_requirements(jd)  ->  0 elements
requirement_engine.parse_grade_clause(jd)          ->  ('', 'GS-13', 1)   # target grade empty
requirement_engine.parse_federal_competencies(jd)  ->  0 minimum, 14 assessed
```

Root cause: `requirement_engine.py:276` anchors on `r"Specialized Experience\s+GS-\d+\s+Level:.*?includes:\s*"` and line 272 on `r"Specialized Experience\s+(GS-\d+)\s+Level"`. The posting reads `Specialized Experience: GS-14 grade level:`. The `\s+` cannot match `: `, and `Level` does not match `grade level`, so both regexes fail and `_federal_block()` returns an empty string.

Consequences:

- `TargetContext.requirements` is empty for federal, so `sections` at line 361 is a single empty section, `requirement_text` is empty, and `_display_title()` degrades.
- `parse_federal_competencies()` minimum list is empty because its anchor `following nine competencies:` also does not match this posting.
- `TargetContext.target_grade` is empty even though the posting is unambiguously GS-14.

`build_federal_resume.py:1652` builds this context during `federal_requirement_audit()`, so the federal audit is currently running against a fully empty requirement set from this parser while separately using its own bucket parser.

The plan must either bring `requirement_engine.parse_federal_requirements()` into scope or explicitly declare it out of scope and record the empty-result behavior as a known defect. Silently leaving it will make the plan's federal fixtures pass while half the federal requirement surface stays broken.

---

## HIGH

### H1. The plan's federal diagnosis is right for the bucket parser; confirm the fixture asserts against the correct function

Executed `build_federal_resume.parse_requirement_buckets(jd, 'implementation')` against the active posting, producing 6 buckets. The plan's described symptoms are confirmed:

| # | kind | priority | problem |
|---|------|----------|---------|
| 1 | `core_experience` | 69 | Text is only the job title and agency header. Not a requirement at all. |
| 2 | `specialized_experience` | 96 | Pure boilerplate: "is experience that has equipped the applicant with the particular knowledge, skills, and abilities/competencies..." |
| 3 | `specialized_experience` | 96 | Genuine duties, but all bullets merged into one bucket |
| 4 | `gs_level` | 86 | Competency-standard preamble |
| 5 | `specialized_experience` | 96 | Grade eligibility boilerplate: "one year of specialized experience (equivalent to the gs-13 grade level...)" |
| 6 | `specialized_experience` | 96 | 1611 characters. Contains the genuine duty list **plus** the `OR` alternate route (`applicants may also` present), **plus** evaluation language (`you will be assessed on the following Competencies`) |

`HIGH_PRIORITY_BUCKET_THRESHOLD` is 80 (`build_federal_resume.py:70`), so buckets 2 and 5, pure boilerplate at priority 96, clear the gate at line 1638 and can each emit "is not well supported by the current federal source" warnings. The same threshold gates a second consumer at line 2073. That is the mechanism behind the noisy dry-run report.

Plan gap: it does not mention bucket 1 (`core_experience` built from the posting header) or the `gs_level` preamble bucket. Add both to the scope and to the fixture assertions.

### H2. The plan omits the largest alignment component from the CLI display

`tasks.py:810-814` prints five components. It does not print `requirement_coverage`, which is worth 40 of the 115 points, the single largest term. The plan says only to correct the stale maxima labels, so a literal implementation would still hide 35 percent of the score.

Additional precision: the plan lists the stale labels as `/30`, `/25`, and `/20`. There are two separate `/25` labels, at line 811 (lane fit) and line 813 (business context). Only `Specialty fit: /15` at line 812 is currently accurate.

Worth recording as context for Codex: the current labels sum to `30+25+15+25+20 = 115`, which is why the total has looked internally consistent. They are the maxima of a superseded weighting; the 40-point `requirement_coverage` term was added and the per-component caps were reduced to 15, but the display was never updated.

Add to the plan: print a `Requirement coverage: {score}/40 (required=, direct=, adjacent=, unsupported=)` line, and add a smoke assertion that every key in the report with a `score` field has a corresponding printed line.

### H3. "Align the keyword-gap display with the scoring rule" is not achievable by relabeling, because the two use different predicates

The plan states exact phrase coverage is the only thing earning score credit, and that the gap display should be aligned to it. These are two different functions today:

- Scoring: `alignment_score_report()` calls `contains_search_term()`. Because `build_resume.py:1926` redefines `contains_search_term` **after** the `from resume_analysis import (...)` at line 101, the local definition shadows the import. That local version tolerates plural and singular variants (`ies`/`y`, trailing `s`) and treats `and`/`&` as an interword connector.
- Display: `tasks.py:512 coverage_status()` calls `term_occurrences()` at line 502, which is a strict literal `re.escape` match with no morphological variants.

So a keyword such as `delivery capabilities` can score as covered while the CLI reports it `MISSING`, and the two will still disagree after the labels are corrected.

Required plan change: name the single predicate that both paths must use. Recommended: have `tasks.py` import and call `build_resume.contains_search_term()` for `COVERED`, and keep `term_occurrences()` only for the frequency-based sort key. Add a fixture asserting that for a fixed JD/resume pair, the set of keywords scored as covered by `alignment_score_report()` equals the set the CLI labels `COVERED`.

Also flag the shadowing itself as a latent trap: two functions with the same name and different semantics in the same import graph. It is out of scope to fix, but Codex should be told which one wins so the fix targets the right one.

### H4. Making `read_index()` pure removes the only reconciliation between the index and disk

`job_context_archive.read_index()` at line 514 calls `sync_legacy_archives()` (line 582), which at line 590 does `if raw_rows != disk_rows: _write_index(disk_rows)`. That is the only place index/disk drift is repaired. The plan removes it from the read path and offers `--sync-legacy` as the replacement, but `--sync-legacy` is scoped in the plan as "a one-time maintenance operation" for legacy import.

Consequences to resolve in the plan:

- Rows whose snapshot directory was deleted will persist in `index.csv`. `job_description_text_for_row()` (line 487) returns `""` for them, and `track_applications.py:146` consumes `read_index()`, so tracker backfill silently loses matches instead of reporting them. `RULES_FOR_CLAUDE.md` explicitly says safe backfill depends on a matching current or archived job description, so silent loss violates a stated rule.
- Legacy rows (`filename` set, `snapshot_id` empty) will never normalize, and `find_snapshot_id_for_active_context()` at line 497 will not match them.

Recommended plan addition: `read_index()` stays pure but detects drift and emits a one-line warning naming the remediation command. `--sync-legacy` is then documented as repeatable reconciliation, not strictly one-time.

Precision note for the writeup: `_SYNC_COMPLETE` at line 46 is a module-level one-shot, so the current behavior is "the first read in each process mutates," not every read. The plan should say so, otherwise the severity reads as higher than it is and the fixture may be written to assert the wrong thing.

---

## MEDIUM

### M1. Snapshot dedup infrastructure already exists; the plan reads as if it must be built

`archive_texts()` already accepts `dedupe_by_content: bool = False` and `_existing_snapshot_by_hash()` already matches on both hashes. The actual defect is narrow: `archive_active_context()` at line 428 does not accept or forward the flag, and `tasks.py:885 archive_environment_for_command()` (the automatic path for the 20 commands in `COMMERCIAL_AUTO_ARCHIVE_COMMANDS` at line 300) therefore always creates a new snapshot.

Reframe the plan item as: add a `dedupe_by_content` parameter to `archive_active_context()`, pass `True` from `tasks.py:885`, and leave `build_jd_library.archive_current()` at `False`. This is materially smaller than the plan implies and less likely to be over-engineered.

Confirmed not a problem: `jd-archive` is not in `COMMERCIAL_AUTO_ARCHIVE_COMMANDS`, so a manual archive does not also trigger an automatic one.

Accept-and-document tradeoff: on a dedup hit, the returned snapshot keeps its original `source_command` and `archive_reason`. The archive will therefore no longer record which later commands reused a snapshot. That is the correct consequence of pure reads, but it should be stated as an accepted loss rather than discovered later.

### M2. `--sync-legacy` flag placement conflicts with how `jd-archive` is dispatched

`tasks.py:245` defines `jd-archive` as `("scripts/build_jd_library.py", "archive")` and `run_task()` appends `extra_args`, so `python tasks.py jd-archive --sync-legacy` would arrive as `build_jd_library.py archive --sync-legacy`. That works only if the `archive` subparser at `build_jd_library.py:16` declares the flag, which is what the plan says.

Two things the plan should state so this does not get mis-implemented:

- `archive_texts()` currently defaults `sync_legacy=True` and `archive_active_context()` hardcodes `sync_legacy=True`. Both defaults must flip to `False`, otherwise adding the flag changes nothing.
- The plan describes `--sync-legacy` as a maintenance operation but attaches it to `archive`, which also creates a snapshot. Consider a separate `sync-legacy` subcommand so a user reconciling the index is not forced to also write a new archive row.

### M3. Timeout handling details that will bite during implementation

- `subprocess.TimeoutExpired.stdout` is `None` when nothing was buffered and is `bytes` rather than `str` in some paths even with `text=True`. `write_log()` at `run_resume_workflow.py:87` interpolates directly and will raise on `None`. The plan should require normalizing both streams before logging.
- On Windows, `subprocess.run(timeout=)` kills the direct child. Word COM or `soffice` grandchildren spawned by `render_checks.py` can survive and hold file locks, which then surfaces as the existing `file_locked` failure kind on the next run. The plan should require either a process-group kill or at minimum a documented note.
- A step killed mid-write can leave a partial `.docx` in `output/`. The plan says stop downstream steps but says nothing about the partial artifact, which a later `checklist` or `cover` run will happily pick up as "the newest matching tailored resume" via `latest_tailored_resume()`. Add cleanup or quarantine of artifacts produced by a timed-out step.

### M4. The `AGENTS.md` LinkedIn rule is genuinely ambiguous; the plan's fix is correct but incomplete

`AGENTS.md:25` reads "Keep Christian's LinkedIn URL visible in the contact line as plain text only." `.context/RULES_FOR_CLAUDE.md:13` uses the same unqualified wording, saying "in the resume contact line." Neither scopes to commercial, so both currently read as applying to federal.

The plan names `AGENTS.md` and "the system reference" but not `.context/RULES_FOR_CLAUDE.md`, which is the file Claude is instructed to read first by `CLAUDE.md`. If only `AGENTS.md` is corrected, the compact context Claude actually reads stays wrong. Add `.context/RULES_FOR_CLAUDE.md:13` and `.context/ARCHITECTURE_MAP.md:79` ("no LinkedIn external hyperlink relationship" under Validation Priorities) to the edit list.

Confirmed the federal contact contract is different by design: `build_federal_resume.py:2246` builds `location | email | phone` and line 2257 adds citizenship, veterans preference, clearance, and availability. No LinkedIn field exists in `FederalContact`. The plan's "do not alter the federal source schema" is consistent with the code.

### M5. `parser_fallback_required` is set but never consumed

`requirement_engine.py:384` computes `parser_fallback_required=len(requirements) < 3`, and no code anywhere reads it. Given C5 (the federal parser returns zero elements), this flag is currently `True` for the active posting and nothing acts on it.

The plan changes federal parsing in a way that will change this count, so it should either wire the flag to a real warning or delete it. Leaving a dead correctness signal in place while claiming improved audit clarity is worse than removing it.

---

## LOW

### L1. Dependency pin is verified

Installed `python-docx` is `1.2.0`, matching the plan. `requirements.txt` currently reads `python-docx>=0.8.11` with a comment claiming "Pinned versions to ensure API stability" that is factually wrong, which the plan correctly calls out.

`.github/workflows/smoke_test.yml` installs `python-docx` unpinned via `python -m pip install python-docx --break-system-packages`. Switching to `pip install -r requirements.txt` is correct. Keep `--break-system-packages` or drop it consistently; on `ubuntu-latest` with `actions/setup-python` it is not required.

### L2. Recovery preserves files into an importable location

On the backup-restore branch, `attempt_question_prep_recovery()` writes `question_prep.pre_recovery_<timestamp>.py` into `scripts/`, next to live modules. `scripts/fresh_corpus_rebuild.py:62` does `(PROJECT_ROOT / "scripts").rglob("*.py")` and would pick these up. The plan says to preserve existing backup-before-recovery behavior; it should additionally require that preserved copies land under `backups/`, not `scripts/`.

### L3. Verification section will pass vacuously as written

"Run `python tasks.py federal-dry-run` and confirm only real duties appear as federal requirements" is not falsifiable against `requirement_engine.parse_federal_requirements()`, which returns zero requirements today (C5) and so trivially contains no boilerplate. Restate the verification as a positive assertion with an expected count: the active VA posting must yield exactly N specialized-experience buckets corresponding to the N duty sentences in the `includes but is not limited to` list, with the `OR` route and the assessment paragraph absent.

Similarly, "confirm no archive files change" should be mechanized as a byte-level or hash comparison of `scratch/jd_library/` before and after, not a visual check.

---

## Recommended fix order for the plan pass

Dependencies matter here; several items will conflict if done in the wrong order.

1. **C3 + C4** read-only health checks. No dependencies, removes the destructive path, and must land before anyone runs the other verifications repeatedly.
2. **L1** dependency pin and CI change. Independent, makes every later test run reproducible.
3. **H4 + M1 + M2** archive purity, dedup, and `--sync-legacy`. Do purity and dedup together, because dedup reads the index and the drift-warning decision in H4 changes what dedup sees.
4. **H2 + H3** alignment reporting. H3 first (settle the predicate), then H2 (labels and the missing requirement line), because the fixture in H2 asserts against the predicate H3 fixes.
5. **C5 + H1 + M5** federal parsing. Largest and riskiest. Fix `requirement_engine` anchors first so `TargetContext` is non-empty, then the bucket parser, then resolve the dead flag.
6. **C1 + C2 + M3** timeouts. Last, because a timeout constant calibrated before steps 1 through 5 land will be measured against the wrong runtime.

## Open questions for the user before implementation

1. Should a timed-out step be retried once, or fail immediately? The plan implies immediate failure; the current code retries.
2. Is `requirement_engine.parse_federal_requirements()` in scope for this remediation, or is it deferred to a separate spec?
3. Should `--sync-legacy` be a flag on `archive` or its own subcommand?
