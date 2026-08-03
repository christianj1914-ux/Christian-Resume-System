# Claude Review Pass 2: Reliability Remediation Plan (Revised)

Review pass only. No source files were modified. Verified against the working tree and by executing the federal parsers against the active `jobs/federal_job_description.txt`.

---

## Verdict

The revision resolves the three blocking items from pass 1. C1 (timeout retry) is now explicit and correct, C2 (five-minute limit) is raised to ten minutes with the nested renderer limit acknowledged, and C5 (`requirement_engine` returning zero requirements) is now in scope with the exact grade-wording variants named.

Four new issues surfaced when I traced the revised federal design through the code it will actually touch. Two are blocking. The remaining pass-1 items that were dropped rather than addressed are listed at the end so the omission is deliberate rather than accidental.

---

## BLOCKING

### B1. Splitting specialized experience into per-duty buckets silently multiplies cluster weights and changes evidence targeting

This is the single highest-risk consequence of the revised federal design, and the plan does not mention it.

`federal_requirement_audit()` at `build_federal_resume.py:1634` accumulates cluster weight per bucket:

```python
for cluster in bucket.clusters:
    cluster_weight_map[cluster] = cluster_weight_map.get(cluster, 0) + bucket.priority
```

Today the active posting yields one merged specialized-experience duty bucket at priority 96 contributing to three clusters. Under the revised plan that becomes roughly six independent duty buckets, each at priority 96, each running `infer_clusters()` on its own short text. Cluster weights will increase several-fold and their relative ordering will shift.

Those weights are not diagnostic. `sorted_cluster_weights` is passed straight into `federal_keyword_targets()` at line 1651, which at lines 1609-1613 walks clusters in weight order and appends each cluster's `keyword_terms` into a list truncated to 16 targets at line 1619. Reordering the clusters therefore changes which federal keywords survive the cut, which changes what the federal resume targets.

Pass 1 of the plan carried an explicit guard for exactly this: "the parser change may improve ranking and audit clarity but cannot promote adjacent evidence to direct evidence." The revision dropped that sentence. It needs to come back, made concrete:

- Normalize per-duty bucket priority so total specialized-experience weight is conserved rather than multiplied. Either divide priority across the split duties, or deduplicate cluster contributions per section rather than per bucket.
- Add a regression fixture asserting `federal_keyword_targets()` output for the active posting before and after the split, and require any change to be reviewed deliberately rather than accepted silently.
- Note the second consumer at line 2073, which gates on the same `HIGH_PRIORITY_BUCKET_THRESHOLD` of 80 (line 70). Six duty buckets at priority 96 each clearing that gate will produce six "not well supported" warnings where there was previously one, which inverts the plan's stated goal of a concise dry-run report.

### B2. "Every term not covered appears in the gap list" will recommend inserting platforms Christian has never used

`alignment_score_report()` skips keywords for which `is_unsupported_do_not_insert()` is true, so they never earn or lose score credit. That predicate (`resume_analysis.py:2128`) returns true for terms in `UNSUPPORTED_PLATFORM_KEYWORDS` (`resume_analysis.py:1616`): `acumatica`, `smartsheet`, `netsuite`, `workday`, `sap s/4`, `sap s/4hana`, `prismhr`, when present in the JD and absent from the resume.

The revised rule states flatly that every term not covered by the predicate appears in the gap list. Applied literally, a NetSuite or Workday posting produces a "Top Missing Keywords" list telling the user to add NetSuite or Workday to a resume that cannot support either. That contradicts `.context/RULES_FOR_CLAUDE.md:10` ("Never invent content, claims, metrics, tools, platforms") and the pass-1 language "do not recommend unsupported insertion," which the revision dropped.

To be fair to the current code: this is a pre-existing defect, since `coverage_status()` does not filter these terms today either. The problem is that the revision promotes it from bug to specification.

Required change: the gap list must exclude, or visibly quarantine under a separate non-actionable heading, any term where `is_unsupported_do_not_insert()` is true. The rule should read "every term not covered and not on the do-not-insert list appears in the gap list."

Related arithmetic problem in the same area: the plan's fixture "the displayed gap count agrees with the report's exact coverage count" cannot pass as written. In `alignment_score_report()`, `covered` is incremented only for non-skipped keywords while `total_kw = len(keywords)` counts all of them, including skipped ones. So `covered + gaps != total_kw` whenever a do-not-insert term appears. Fixing B2 fixes the fixture; specify both together.

---

## HIGH

### H1. The core-experience bucket currently captures the posting header, not duties, and the plan's wording hides the actual fix

The revision says to "retain a narrowly scoped core-experience bucket for pre-grade role duties." The active posting does contain genuine pre-grade duties, at lines 6-13:

```
As an IT Project Manager/Scrum Master, you will:
Lead multifaceted Information Technology (IT) software and infrastructure projects...
Work across functional and organizational lines...
Manage project resources, including overseeing contractors and mentoring IT and business teams.
...
```

But `parse_requirement_buckets()` at `build_federal_resume.py:1497` builds that bucket from `preamble_lines[:4]`, and I confirmed by execution that the resulting text is:

```
Information Technology Project Manager Department of Veterans Affairs
Electronic Health Record Modernization Office of Program Executive Director
```

That is lines 1-4, the job title and agency header. The `[:4]` slice consumes the header and discards every real duty. "Retain" therefore describes keeping a bucket that currently contains no requirement content at all.

Restate the plan item as a fix, not a retention: the core-experience bucket must be sourced from the pre-grade duty block introduced by a "you will" style lead-in, and must exclude the title/agency header block. Add a fixture asserting the core-experience bucket text contains "Lead multifaceted" and does not contain "Department of Veterans Affairs".

### H2. "Preserve existing competency extraction" preserves a broken extractor

`parse_federal_competencies()` at `requirement_engine.py:299` anchors the minimum-competency list on the literal `r"following nine competencies:"` at line 302. The active posting reads "demonstrating each of the four competencies listed below." I confirmed by execution:

```
parse_federal_competencies(jd) -> 0 minimum competencies, 14 assessed
```

The four required competencies at lines 19-22 (Attention to Detail, Customer Service, Oral Communication, Problem Solving) are not extracted at all. The plan instructs Codex to preserve this, which locks in the failure.

Since the revision is already opening this function's neighborhood, generalize the anchor to accept any number word or digit, and add the count to the fixture: the active posting must yield exactly four minimum competencies.

### H3. Changing retry behavior breaks three existing smoke tests, and the signature they patch is not mentioned

`scripts/smoke_test.py` monkeypatches `run_resume_workflow.run_with_recovery` in three places (lines 14175, 14243, 14301), each substituting a fake with the exact signature `(step_name, script_name, *, can_rebuild_resume=False)`. Any change to that signature or to the retry contract will break all three.

Separately, the revised plan enumerates retry policy for timeout, renderer failure, and generic traceback, but says nothing about the fourth existing branch: `missing_resume_output` at `run_resume_workflow.py:354`, which rebuilds the resume and retries. That branch is legitimate recovery and must be explicitly preserved, or Codex may read "retry exactly once only for a known renderer failure" as authorization to delete it.

Add to the plan: preserve the `can_rebuild_resume` recovery path, name the three smoke tests that need updating, and state whether `run_with_recovery()` keeps its signature.

### H4. The federal runner has no retry infrastructure at all, so "apply the same behavior" is new construction

`run_federal_resume_workflow.py` has `run_step()` (line 59) and nothing else. There is no `run_with_recovery()`, no `failure_kind()`, and its `StepResult` is constructed positionally as `StepResult(step_name, result.returncode, result.stdout, result.stderr, log_path)` at line 76, a different shape from the commercial runner's keyword-constructed result with `trace_path` and three warning lists.

"Apply the same timeout/result behavior to commercial and federal workflow runners" therefore means either duplicating the classification logic in two places or extracting a shared helper. The plan should pick one. Recommended: extract `run_step_with_timeout()` and the failure classifier into a shared module both runners import, since divergent copies are what produced the current inconsistency.

---

## MEDIUM

### M1. The shared coverage helper must name which `contains_search_term` wins

The plan says "`contains_search_term()` remains the authoritative exact-coverage predicate, including its plural handling," but there are two functions with that name and different semantics. `build_resume.py:1926` defines a plural-tolerant version that shadows the `from resume_analysis import (...)` at line 101; `resume_analysis.py:94` defines a different one built on `_search_term_regexes()`.

Only the `build_resume` version has the `ies`/`y` and trailing-`s` handling the plan describes. Name it explicitly as `build_resume.contains_search_term`, or the shared helper may be built on the wrong one and the fixture will still pass because both are plural-ish.

### M2. A second keyword display surface is not covered

The plan addresses the gap list in `run_align()` at `tasks.py:799`. `coverage_status()` has a second consumer at `tasks.py:593`, the "Top Keyword Coverage" table, which will keep using the strict-literal predicate and keep disagreeing with the scored report. Add it to the scope, or the inconsistency simply moves rather than resolving.

### M3. `reset-jobs` also calls `archive_active_context()` and is unclassified

`scripts/reset_jobs.py:46` calls `archive_active_context(source_command="reset-jobs", archive_reason="reset_jobs_archive")` and then copies additional job files into the returned snapshot directory at lines 52-56.

The plan says to pass `dedupe_by_content=True` "only from `tasks.py` automatic application-command archiving," which by omission leaves `reset-jobs` at `False`. That is probably correct, since reset-jobs is an intentional point-in-time capture before the posting is replaced. But it must be stated, because there is a concrete hazard: if `reset-jobs` were ever deduplicated, it would receive an existing snapshot directory and then copy `interview_notes.txt` and friends into a snapshot belonging to a different archive event.

State explicitly that `reset-jobs` and `jd-archive` both remain non-deduplicating.

### M4. Flipping the `sync_legacy` defaults is required but unstated

`archive_texts()` defaults `sync_legacy: bool = True` at `job_context_archive.py:383` and `archive_active_context()` hardcodes `sync_legacy=True` at line 442. The plan's "run legacy normalization/import only when that flag is explicitly provided" implies both must flip to `False`, but does not say so. If Codex only adds the CLI flag, nothing changes.

### M5. Pass-1 H4 was dropped: read-only reads remove the only index/disk reconciliation

I raised this in pass 1 and the revision does not address it. Restating once so it is a decision rather than an oversight.

`sync_legacy_archives()` at `job_context_archive.py:590` contains the only drift repair: `if raw_rows != disk_rows: _write_index(disk_rows)`. Making reads pure removes it. Rows whose snapshot directory was deleted will persist in `index.csv`; `job_description_text_for_row()` (line 487) returns `""` for them; `track_applications.py:146` consumes `read_index()`, so tracker backfill silently loses matches. `.context/RULES_FOR_CLAUDE.md:90` states that safe backfill depends on a matching current or archived job description, so silent loss violates a written rule.

Minimum acceptable resolution: `read_index()` stays pure but detects drift and prints a one-line warning naming the remediation command.

---

## LOW: pass-1 items not carried into the revision

Listing these so the omission is explicit. None are blocking.

- **Timeout mechanics.** `subprocess.TimeoutExpired.stdout` can be `None`, and `write_log()` at `run_resume_workflow.py:87` interpolates both streams directly. Normalize before logging. On Windows a killed child can leave Word COM or `soffice` grandchildren holding file locks, which resurfaces as the existing `file_locked` kind on the next run. A step killed mid-write can also leave a partial `.docx` in `output/` that `latest_tailored_resume()` will later select as the newest matching resume; the plan should require quarantining artifacts from a timed-out step.
- **`workspace_health` preserved copies land in an importable directory.** The backup-restore branch writes `question_prep.pre_recovery_<timestamp>.py` into `scripts/`, and `fresh_corpus_rebuild.py:62` does `(PROJECT_ROOT / "scripts").rglob("*.py")`. Preserved copies belong under `backups/`.
- **`parser_fallback_required` is dead.** Set at `requirement_engine.py:384`, read nowhere. The federal changes will alter the count it derives from. Wire it to a real warning or delete it.
- **Compact context files still carry the unqualified LinkedIn rule.** The revision names `AGENTS.md` and "system documentation." `.context/RULES_FOR_CLAUDE.md:13` and `.context/ARCHITECTURE_MAP.md:79` also state the rule without scoping it to commercial, and `CLAUDE.md` directs Claude to read those first.

---

## Two design questions the revision leaves open

1. **The posting declares specialized experience twice, with different duty lists.** Line 29 introduces "Specialized experience is defined as demonstrated experience:" followed by bullets, and line 63 introduces "Specialized experience for this position includes but is not limited to:" followed by a different list. The plan says to extract from "each declared specialized-experience section" but does not say whether the two lists are additive, whether overlapping duties should deduplicate, or whether they should be ranked equally. This determines the expected bucket count in the fixture, so it has to be settled before the fixture is written.

2. **The stop-phrase lists are literal-prefix matched and did not catch this posting.** `FEDERAL_BUCKET_STOP_PHRASES` (line 386), `FEDERAL_KSA_STOP_PHRASES` (line 518), and `FEDERAL_COMPETENCY_PREFIXES` (line 405) are hand-maintained literal prefixes, and the KSA checks only apply when `current_kind == "specialized_experience"`. None of them matched `OR`, `Applicants may also be considered...`, or `Your qualifications will be evaluated based on...`, which is why all three ended up inside bucket 6. Adding three more literals fixes this posting and fails on the next one. The plan should state whether the fix is structural (stop on any section-introducing line, alternate-route conjunction, or evaluation verb pattern) or another round of literals, and accept the maintenance cost either way.

---

## Recommended fix order

Unchanged in shape from pass 1, with B1 inserted as a gate on the federal work.

1. Read-only health checks and dry-run byte-hash verification. No dependencies, removes the destructive path.
2. `python-docx==1.2.0` pin and CI install from `requirements.txt`. Makes every later run reproducible.
3. Archive purity, `dedupe_by_content` threading, `--sync-legacy`, plus the M5 drift warning and M3/M4 clarifications.
4. Alignment: settle the predicate (M1), fix the do-not-insert gap rule (B2), then the CLI components and both display surfaces (M2).
5. Federal parsing: `requirement_engine` anchors and competency count (H2) first so `TargetContext` is non-empty, then the bucket refactor with the B1 weight-conservation guard and the H1 core-experience fix, then resolve `parser_fallback_required`.
6. Timeouts and retry classification last, including the shared-helper extraction (H4) and the three smoke-test updates (H3), so the limit is calibrated against post-fix runtimes.
