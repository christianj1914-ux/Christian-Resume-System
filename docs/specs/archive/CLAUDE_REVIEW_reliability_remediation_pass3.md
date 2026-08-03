# Claude Review Pass 3: Reliability Remediation Plan (Final Revised)

Review pass only. No source files were modified. Findings verified by executing the federal parsers and by simulating the plan's `weight_group_id` design against the active `jobs/federal_job_description.txt`.

---

## Verdict

The plan is close to implementable. B2 (do-not-insert terms in the gap list), H1 (core-experience sourced from the header), and H2 (hardcoded "nine competencies") from pass 2 are all resolved correctly.

One correction to my own pass-2 severity is below, and it is good news. Two blocking items remain: a self-contradictory assumption that will make Codex either over-constrain or abandon the fix, and a retry category that deletes a working recovery path. Everything else is a small addition.

---

## Correction to pass 2: B1 is real in mechanism but benign in outcome, and the plan's `weight_group_id` design works

I asserted in pass 2 that splitting duties would change which federal keywords survive truncation. I simulated it. The mechanism is real; the outcome on this posting is not.

Confirmed real: `federal_keyword_targets()` returns 16 terms, and only 8 come from `audit_keywords()`. The other 8 are pulled from cluster `keyword_terms` in weight order (lines 1609-1613). Half the target list is decided by cluster weights.

Simulated the plan's design (drop the two boilerplate specialized-experience buckets and the `gs_level` bucket, re-source core experience from the real duty block at lines 6-13, aggregate one contribution per weight group):

```
TODAY:    implementation_delivery 539, governance_risk 192, agile_delivery 96,
          change_adoption 96, customer_service_delivery 96, reporting_analytics 96,
          cloud_modernization 69, executive_alignment 69

POST-FIX: governance_risk 261, implementation_delivery 261, agile_delivery 165,
          change_adoption 96, reporting_analytics 96, customer_service_delivery 69

Target set diff:  dropped: []   added: []
```

The 16-term target set is **identical**. Only the ordering of the two cluster blocks swaps. So `weight_group_id` does its job, and the federal split is safe to proceed on this posting.

Worth noting what the old weights were made of: `cloud_modernization` and `executive_alignment` existed in the map only because the core-experience bucket contained the job title and agency header, and `customer_service_delivery` scored 96 only from the grade-eligibility boilerplate bucket. Removing them is the fix working as intended.

---

## BLOCKING

### B1. The stated assumption contradicts the plan's own goal, and the ordering change it forbids does occur

Assumptions section: "Splitting duties changes audit granularity only; it must not change cluster-weight ordering, target-keyword truncation, evidence strength, or warning volume."

Cluster-weight ordering does change, necessarily and correctly. `implementation_delivery` goes from 539 to 261 and ends tied with `governance_risk`, which then wins the top slot on the alphabetical tiebreak in `sorted(..., key=lambda item: (-item[1], item[0]))` at line 1650. That is unavoidable once boilerplate contributors are deleted, which is the entire point of the change. As written, Codex must either preserve the boilerplate to satisfy the assumption or ignore the assumption.

This matters more than the keyword-target result suggests, because cluster ordering has seven consumers beyond `federal_keyword_targets()`:

```
build_federal_resume.py:1805, 1899, 1921, 1992, 2198, 2207, 2281
```

Line 1992 builds `cluster_priority = [cluster for cluster, _weight in active_audit.cluster_weights]`, an explicit priority ordering that feeds evidence selection. A top-slot flip from `implementation_delivery` to `governance_risk` propagates there.

The 261/261 tie is also fragile. One point of difference in either direction flips the order, so this is not a stable outcome to build a fixture around by accident.

Required changes:

- Reword the assumption to constrain the observable output rather than the intermediate: "splitting duties must not change the federal keyword target set, and any change to cluster ordering must be reviewed deliberately."
- Add a fixture asserting the 16-term target set for the active posting, which I have confirmed is stable across the change.
- Add a second fixture pinning `cluster_priority` order, and require an explicit decision if it moves.
- Decide whether the `implementation_delivery` / `governance_risk` tie should be broken by something more meaningful than alphabetical order.

Related factual error in the same section: "keep the two distinct specialized-experience lists as two groups, matching the prior intent of two priority contributions." There are four specialized-experience contributions today, at buckets 2, 3, 5, and 6, all at priority 96. Two are genuine duty lists and two are boilerplate. Going to two groups is a reduction from four, not a preservation of two. State it that way so the fixture author is not looking for a match that was never there.

### B2. The three retry categories delete the `missing_resume_output` recovery

The plan enumerates exactly three outcomes: outer timeout, completed-process renderer failure, and "all other failures," with the last failing immediately and no automatic retry.

`run_with_recovery()` at `run_resume_workflow.py:354` has a fourth branch. On `missing_resume_output` it rebuilds the resume and retries the step. It is used in production at lines 619 and 678 via `can_rebuild_resume=True`, and it is documented behavior: `.context/ARCHITECTURE_MAP.md:46` describes the runner as having "basic recovery," and `.context/SCRIPT_INDEX.md` lists `run_with_recovery()` under recovery. It exists because `build_cover_letter.py` requires a matching resume output to exist.

Under the plan as written, that path falls into "all other failures" and is removed, so a cover-letter step that runs before a resume exists now fails the workflow instead of self-healing.

Required: add a fourth category for missing prerequisite output that keeps the rebuild-and-retry behavior, or state explicitly that the recovery is being retired and update both context docs.

Implementation note attached to the same change: `scripts/smoke_test.py` monkeypatches `run_with_recovery` at lines 14175, 14243, and 14301, each with the exact signature `(step_name, script_name, *, can_rebuild_resume=False)`. All three break if that signature changes. Name them in the plan.

---

## MEDIUM

### M1. The archive read-purity change still removes the only index/disk reconciliation

Raised in pass 1 and pass 2, not addressed in either revision. Flagging a third and final time so it is a decision rather than a gap.

`sync_legacy_archives()` at `job_context_archive.py:590` holds the only drift repair: `if raw_rows != disk_rows: _write_index(disk_rows)`. Making reads pure removes it. Rows whose snapshot directory was deleted persist in `index.csv`, `job_description_text_for_row()` (line 487) returns `""` for them, and `track_applications.py:146` consumes `read_index()` — so tracker backfill silently loses matches rather than reporting them. `.context/RULES_FOR_CLAUDE.md:90` states that safe backfill depends on a matching current or archived job description.

Minimum resolution: `read_index()` stays pure but compares row count against on-disk snapshot directories and prints one warning naming `python tasks.py jd-archive --sync-legacy` when they diverge. If you would rather accept the risk, say so in Assumptions and I will stop raising it.

### M2. State the `dedupe_by_content` default so `reset-jobs` is safe by construction

The plan says `tasks.py` passes `True` and manual `jd-archive` does not deduplicate "by default." `scripts/reset_jobs.py:46` is a third caller that the plan never mentions; it archives and then copies `interview_notes.txt` and other job files into the returned snapshot directory at lines 52-56.

If the new parameter defaults to `False`, `reset-jobs` is correct with no change. If it defaults to `True`, `reset-jobs` can receive an existing snapshot and write unrelated files into another archive event's directory. Just state the default explicitly: `dedupe_by_content: bool = False`.

### M3. The second keyword display surface is still uncovered

`coverage_status()` has two consumers in `tasks.py`: line 799 in `run_align()`, which the plan fixes, and line 593 in the "Top Keyword Coverage" table. The second will keep using the strict-literal `term_occurrences()` predicate and keep disagreeing with the scored report. Add it, or the inconsistency moves rather than resolves.

### M4. Name which `contains_search_term` is authoritative

Raised in pass 2, still unaddressed. Two functions carry that name: `build_resume.py:1926`, which shadows the `from resume_analysis import (...)` at line 101 and has the plural handling the plan describes, and `resume_analysis.py:94`, which does not. The plan should say `build_resume.contains_search_term` explicitly.

Reassurance worth recording for Codex: excluding do-not-insert terms from `total_kw` and `covered` does **not** change any score. `alignment_score_report()` already skips those terms before accumulating `covered_weight` and `total_weight`, so the fix corrects only the displayed ratio and the gap list. Alignment gate thresholds are unaffected.

---

## LOW: carried forward, still absent

These have survived three passes without landing. None are blocking; listing them once more for a keep-or-drop decision.

- `subprocess.TimeoutExpired.stdout` can be `None`, and `write_log()` at `run_resume_workflow.py:87` interpolates both streams directly. Normalize before logging, or the timeout handler raises inside its own error path.
- On Windows a killed child can leave Word COM or `soffice` grandchildren holding file locks, which resurfaces as the existing `file_locked` failure kind on the next run.
- A step killed mid-write can leave a partial `.docx` in `output/` that `latest_tailored_resume()` will later select as the newest matching resume. Quarantine artifacts from a timed-out step.
- `workspace_health.attempt_question_prep_recovery()` writes preserved copies as `question_prep.pre_recovery_<timestamp>.py` into `scripts/`, and `fresh_corpus_rebuild.py:62` globs `scripts/**/*.py`. Preserved copies belong under `backups/`.
- `parser_fallback_required` is set at `requirement_engine.py:384` and read nowhere. The federal changes alter the count it derives from. Wire it or delete it.
- The plan says "`AGENTS.md` and supporting reference docs" for the LinkedIn contract. The specific files are `AGENTS.md:25`, `.context/RULES_FOR_CLAUDE.md:13`, and `.context/ARCHITECTURE_MAP.md:79`. The last two are what `CLAUDE.md` tells Claude to read first, so they matter most.

---

## Fixture detail worth pinning before implementation

The minimum-competency section in the active posting runs from the announcement at line 17 ("Applicants must have IT-related experience demonstrating each of the four competencies listed below") through the four `Label - Description` lines at 19-22, and terminates at the `-AND-` separator on line 23. Structural extraction needs to treat `-AND-` as a terminator, and the fixture should assert exactly four minimum competencies plus the 14 assessed competencies already extracted correctly today.

---

## Fix order

Unchanged from pass 2.

1. Read-only health checks with before/after hashing of `question_prep.py` on both dry runs.
2. `python-docx==1.2.0` pin and CI install from `requirements.txt`.
3. Archive purity, `dedupe_by_content` threading with the stated default, `--sync-legacy`, and the M1 drift warning.
4. Alignment: name the predicate (M4), eligible-population exclusion, CLI components, and both display surfaces (M3).
5. Federal parsing: shared structural parser and competency extraction first, then the bucket refactor with `weight_group_id`, the target-set fixture, and the `cluster_priority` fixture.
6. Timeouts and retry classification last, including the fourth recovery category (B2) and the three smoke-test updates.
