# CODEX SPEC: Commercial Resume Performance, Parser Coverage, Historical Rebuild, and Job Queue

Date: 2026-08-10
Branch: `main` at `707501e`, dirty
Status: Codex plan with Claude review additions in Part 7

---

# Summary

- The 600-second ceiling is intentional; the excessive runtime is an August 3 performance regression.
- Current parser coverage is poor: **190 of 477 archived snapshots and 85 of 197 unique postings return zero requirements** (independently reproduced).
- Artifact inspection found **five** surviving zero-parse resumes:
  - Epicor Associate Consulting Services Project Manager
  - Paylocity Client Project Manager Ops
  - Paylocity Senior IT Project Manager Enterprise Applications
  - Aptean ERP Consultant BRIDGE
  - Aptean ERP Consultant FAIL
- Paylocity Project Manager Release Operations parses three requirements and did not use the zero-parse path. Retain it as a control.
- Sequence: performance repair, parser behavior, historical impact, diagnostics, queue.

**Measured evidence** (single `ats_scan_terms()` call, reproduced independently):

| Posting | Length | Requirements | Time |
|---|---|---|---|
| Rippling | 1,868 chars | 12 | **1.44s** |
| Epicor | 2,881 chars | **0** | **4.60s** |
| RingCentral | 8,481 chars | **0** | **>42s, did not finish** |

RingCentral is 4.5x Rippling's length but at least 29x the time. The superlinear scaling is the signature of per-candidate re-parsing.

---

# 1. Eliminate repeated analysis without changing outputs

- Add an immutable cached commercial-analysis context keyed by complete posting text.
- Change `classify_keyword_candidate()` to use `None` for "requirements not supplied." An explicitly empty tuple must never trigger reparsing.
- Cache immutable internal results for parsing, core keywords, ATS terms, title phrases, evidence lookup, color priorities, and sort keys; preserve current public return types through copies.
- Replace repeated evidence-catalog scans with normalized indexes and precompute classifications before breadth reconciliation.
- Build a requirement term index once instead of applying regex searches across every requirement for every candidate.
- Establish a clean bisect point by proving representative keyword lists, fit grades, and generated text are unchanged before parser modifications begin.

# 2. Expand commercial parsing and make coverage measurable

- Add `parse_commercial_posting(job_description) -> CommercialParseResult` with `sections`, `requirements`, `parse_mode` (`structured`, `line_fallback`, `whole_posting_fallback`), `diagnostics`, `verified`.
- Retain `parse_commercial_requirements()` as a compatibility wrapper.
- Support the heading, punctuation, bullet, unbulleted-line, and nested-subsection formats found in RingCentral, Epicor, Celigo, Paylocity, Aptean, and the broader archive.
- Treat subsection labels as structure rather than requirement text.
- Use one deterministic non-boilerplate line fallback when structured parsing fails.
- If no trustworthy requirements remain, continue the full workflow using one cached whole-posting analysis. Emit a prominent warning, report `verified=false`, identify the fallback in tracker/queue metadata, and make the neutral requirement-score contribution explicit.

# 3. Keep parser coverage as a permanent regression surface

- Add stable command `python tasks.py parser-audit`.
- Audit all archived commercial snapshots and deduplicate by posting hash.
- Print and persist: snapshot and unique-posting totals, counts by parse mode, zero/fallback percentage, old and new requirement counts, and company/role/snapshot ID/diagnostics for every whole-posting fallback.
- Store the reviewed whole-posting-fallback ceiling as a tracked baseline. The command fails if fallback count increases unless the parser is fixed or the baseline is deliberately reviewed and updated.
- Run when changing requirement parsing, keyword classification, heading recognition, or job-description normalization.

# 4. Rebuild and measure the existing blast radius

- Copy the five affected resumes and their Resume Notes into a timestamped baseline under `scratch/parser_rebuild_audit/`.
- Rebuild those five from archived snapshots into an isolated comparison directory; do not overwrite current outputs.
- Rebuild Paylocity Project Manager Release Operations as the structured-parser control.
- Comparison report per artifact: old/new parse mode and requirement count, core and breadth keyword sets, ATS coverage, requirement-coverage score, total alignment score and fit grade, source resume and detected lane, summary/Skills/role-summary/bullet text differences, unsupported-claim audit result.
- Classify as: no material change; targeting changed but grade unchanged; fit grade/status changed.
- Report grade movement explicitly as potential historical application impact. Preserve both versions.

# 5. Improve timeout and launcher reporting

- Emit unbuffered, flushed timings for analysis, assembly, final audits, page fitting, and final rendering.
- Keep the ten-minute outer timeout non-retryable.
- Bound LibreOffice conversion and rasterization separately and terminate their complete process trees on timeout.
- Log the last completed phase and interrupted temporary-build location.
- Fix the task-result branch in `run_resume.bat` to compare exact exit codes. Preserve the descending `if errorlevel` logic used by `choice`.
- Exit 124 reports failure. Exit 2 reports generic review-required completion while Python supplies the artifact-specific message.

# 6. Add the sequential commercial queue

- Add `jobs/commercial_queue/README.md`; ignore user queue `.txt` files in Git.
- One posting per ordinary `.txt` file, optional `<stem>.questions.txt` sidecar.
- Add `python tasks.py resume-queue` with default full workflow, `--resume-only`, `--rerun`.
- Add launcher option `[B]`, asking once whether every queued posting receives Resume-only or Full workflow.
- Process sequentially, continue after individual failures, leave active job/question files unchanged.
- Preserve normal archiving, question pairing, output naming, validation, and tracker behavior.
- Reject duplicate company/role output targets before execution.
- Keep queue inputs in place. Skip unchanged completed jobs whose outputs still exist unless `--rerun`.
- Write atomic queue state and per-run manifests under `scratch/`, then print completed, fallback-warning, review-required, failed, and skipped summaries with durations and logs.

---

# 7. Claude additions

## 7.1 Name the regression commit before fixing it

The plan says "August 3 regression" without identifying it. Two commits touched the relevant files in that window:

```
9ded742  fix: parse federal requirements structurally and group feedback
dc759ad  fix: align keyword coverage with supported evidence
```

**`dc759ad` is the likely source.** Its subject matches the described behavior change exactly, and `9ded742` is federal-scoped.

Before starting Phase 1:

1. `git show dc759ad --stat` and confirm it introduced the `if not parsed_requirements:` re-parse at what is now `resume_analysis.py:1764`.
2. Check whether the same commit introduced the `len(parsed_requirements) >= 3` narrowing at line 2127. If both came from one commit, that commit is the whole defect and its diff is the specification for the fix.
3. Review everything else `dc759ad` touched. A commit that introduced one sentinel-conflation bug may have introduced others.

This costs minutes and either confirms the diagnosis or redirects it. Do not skip it because the symptom is already understood.

## 7.2 Phase 1 forces the deferred `contains_search_term` decision

**This changes Phase 1's scope and should be settled before work starts.**

`contains_search_term` still has **two live definitions with materially different behavior**:

`scripts/resume_analysis.py:95` delegates to `_search_term_regexes()`, an `lru_cache(maxsize=8192)` helper.

`scripts/build_resume.py:1916` expands plurals in **both** directions inline: `ies→y`, `ss→sses`, `s→singular`, and `no-s→plural`.

The hot-path caller is the `resume_analysis` version, invoked inside `classify_keyword_candidate()` at line 1774 for every candidate against every requirement.

Phase 1 says "build a requirement term index once instead of applying regex searches across every requirement for every candidate." **An index has to encode what counts as a match.** You cannot build it without choosing the plural semantics, which is exactly the decision `contains_search_term` consolidation has been deferred pending.

So the deferral's entry condition is met by proximity rather than by symptom. Before Phase 1:

- Decide the semantics explicitly: singular-to-plural, plural-to-singular, or bidirectional.
- Run `keyword_reliability_corpus.py` before and after, and diff alignment scores, suppressed gaps, selected bullets, and selected competencies **separately**, per the original deferral conditions.
- Consolidate to one definition, or document precisely why two must persist and which one the index reflects.

Note that `_search_term_regexes` already carries an `lru_cache` and a docstring explaining it exists to avoid recompilation "across the many contains_search_term() calls." Someone has already optimized this exact path once. That is evidence the hot spot was known and the fix was incomplete, and a reason to check whether `maxsize=8192` is thrashing at roughly 1,400 candidates per posting across multiple postings per session.

## 7.3 Guard with operation counts, not wall-clock

The plan correctly refuses to make timing a unit test. But it then leaves the performance property unenforced except by manual observation.

Operation counts are deterministic and machine-independent. Extend the existing "one parse per distinct posting" assertion into a bounded-work check:

- For a fixed RingCentral fixture, assert total `classify_keyword_candidate()` invocations stay under an explicit ceiling.
- Assert total `parse_commercial_requirements()` invocations equal the number of distinct posting texts.
- Assert requirement-text extraction count scales with requirement count, not with candidate count.

The profile recorded 4,504 classifications, 4,506 parses, and 9,083 extractions for one posting. Any ceiling near those numbers catches quadratic reintroduction immediately, and does so identically on every machine. Keep the wall-clock numbers as recorded evidence, not as gates.

## 7.4 Sweep for the same sentinel pattern elsewhere

The defect is `if not X:` treating "not supplied" and "supplied but legitimately empty" as the same state, then doing expensive work to re-derive `X`.

Grep `scripts/` for falsy-checked parameters that trigger recomputation, particularly in `resume_analysis.py`, `requirement_engine.py`, `resume_content.py`, and `evidence_engine.py`. Any parameter defaulting to `()`, `[]`, `{}`, or `""` and re-derived under a bare truthiness test is the same bug waiting for the right input.

This is a read-only sweep. Record findings; fix only what is demonstrably hot.

## 7.5 Constrain `parser-audit` to read-only

`parser-audit` walks `scratch/jd_library/`, which holds the 475 metadata records repaired earlier this month after all lanes were silently blanked.

Require the command to open snapshots read-only and never write `metadata.json` or `index.csv`. Add an assertion that snapshot file hashes are unchanged after a full audit run. The archive has already been corrupted once by a pass that rewrote metadata as a side effect; the guard costs nothing.

## 7.6 State expected queue duration and ceiling behavior

Each posting can consume the full 600-second step timeout. A five-posting queue therefore has a worst case near 50 minutes with no upper bound stated.

Add to the queue design:

- Print the expected worst case at start: posting count times the step ceiling.
- Report cumulative elapsed time in the final summary, not just per-posting durations.
- Decide and document whether a queue-level ceiling exists. Recommendation: no queue-level timeout, since per-posting ceilings already bound each unit and an outer timeout would kill completed work in flight. State this explicitly so it reads as a decision rather than an oversight.
- Confirm the queue continues after a 124 timeout on one posting, which is the same exit code the launcher currently misreports. That path needs a test, since it combines the two defects being fixed.

## 7.7 Sequencing note

7.1 and 7.2 come **before** Phase 1, not alongside it. One tells you whether the diagnosis is right; the other resolves a decision Phase 1 cannot proceed without. Both are cheap. Neither should be discovered mid-implementation.

---

# Tests and Acceptance

- Assert one parse/context construction per distinct posting text and zero reparses for an explicitly empty requirement tuple.
- Assert repeated ATS/core calls reuse cached classifications.
- Assert bounded operation counts per 7.3.
- Confirm Phase 1 preserves keyword outputs and fit results on structured and zero-parse fixtures.
- Verify RingCentral, Epicor, Celigo, Paylocity, and Aptean parser behavior, including required/preferred grouping and subsection exclusion.
- Run the permanent parser audit over all 477 snapshots and review every residual whole-posting fallback.
- Assert `parser-audit` leaves all snapshot hashes unchanged.
- Record manual performance evidence without making wall-clock a gate: RingCentral ATS under five seconds; `tasks.py check` under five seconds; RingCentral resume-only under three minutes with a healthy renderer.
- Complete the five rebuilds plus the Paylocity control and publish the comparison report.
- Verify exit 124 cannot print the DRAFT success message and renderer timeouts leave no child processes.
- Queue-test successful, fallback-warning, review-required, failed, and **timed-out** postings; verify continuation, sidecar pairing, duplicate protection, skip/rerun behavior, and unchanged active-file hashes.
- Finish with the smoke suite, `python tasks.py validate`, command-inventory verification, a RingCentral resume-only build, and a two-posting full queue build.

# Assumptions

- Whole-posting fallback continues generation with visible warnings.
- Historical rebuilds are isolated comparisons and never overwrite existing artifacts.
- Queue processing remains commercial-only, sequential, Word-only, one posting per child build.
- Queue files are never moved or deleted automatically.
- Existing unrelated dirty-worktree changes remain untouched.
