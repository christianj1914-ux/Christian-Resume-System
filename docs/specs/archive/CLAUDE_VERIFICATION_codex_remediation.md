# Claude Verification: Codex Remediation Implementation

Independent verification by executing the changed code. No source files were modified.

---

## Verified working

Ran these directly against the active `jobs/federal_job_description.txt`:

| Check | Result |
|---|---|
| `test_active_federal_structural_requirement_fixture` | **PASS** (executed directly) |
| `parse_grade_clause()` | `('GS-14', 'GS-13', 1)` |
| `parse_federal_competencies()` | 4 minimum, 14 assessed |
| `federal_requirement_audit().cluster_weights` | `implementation_delivery 261, governance_risk 261, agile_delivery 165, change_adoption 96, reporting_analytics 96, customer_service_delivery 69` — exact match to the pinned tuple |
| Cluster-derived target tail | Exact match |
| `requirement_priority("core_experience", ...)` | Returns 69; branch added at line 1356 |
| `ensure_workspace_health_or_exit()` | Read-only, no recovery call |
| `read_index()` | Pure, one-shot drift warning |
| `STEP_TIMEOUT_SECONDS` | 600, with `outer_timeout` failure kind |
| `requirements.txt` / CI | `python-docx==1.2.0`, CI installs from `requirements.txt` |
| `align` display | All six components with `max_score`, requirement coverage included |
| `coverage_status()` | Accepts and receives `build_resume.contains_search_term` |
| Eligible/excluded keyword split | `total_kw = len(eligible_keywords)`, both lists returned |

Note for the record: my own pass-3 simulation of the cluster weights used a naive per-bucket aggregation and briefly appeared to disagree with the fixture. Running the real `federal_requirement_audit()` confirms the implementation is correct and my ad-hoc reproduction was wrong.

---

## Findings

### 1. HIGH — `python tasks.py validate` is still unverified

Codex reported the suite "exceeded the five-minute execution window without a failure report." I reproduced that: I ran `scripts/smoke_test.py` for roughly seven minutes and it never completed, emitting exactly **one** line of output the entire time.

This is the plan's primary verification gate, and no one has yet seen it pass. Every other check is a spot check around it.

Two separate problems:

- **Duration.** 466 test functions in a single 17,599-line module, run serially with no selection mechanism.
- **Observability.** Output appears to be buffered or only emitted at the end, so a run that is progressing normally is indistinguishable from one that is hung. That ambiguity is what produced Codex's non-answer.

Recommended before accepting the remediation as complete:

- Run `python scripts/smoke_test.py` to actual completion once, with no time limit, and record the pass/fail summary and wall-clock duration.
- Add per-test progress output (`flush=True`) so the suite reports as it goes.

### 2. MEDIUM — The second specialized-experience list was never split

`parse_federal_requirements()` returns 7 elements. The first six are correctly split duties from list 1. The seventh is an **801-character single element** containing six distinct duty sentences from list 2:

```
Leading project teams in advanced systems software/hardware project efforts.
Functioning as a technical authority in project management disciplines...
Planning and designing systems architecture...
Assuring software and systems functionality and quality.
Ensuring extensive application of security/information assurance policies...
Applying project management principles to large-scale, complex projects...
```

The same shows in the bucket output: `specialized_experience_1` produced six buckets, `specialized_experience_2` produced one.

This undercuts the plan's stated goal of per-duty evidence matching. `evidence_engine.match_requirements()` now scores that blob as one requirement, so a resume covering three of its six duties gets a single coarse verdict.

The difference between the lists: list 1 is newline-separated bullets, list 2 is one long line with sentence-separated duties. Sentence-level splitting is not being applied.

**Caution when fixing:** splitting list 2 into six buckets runs `infer_clusters()` per duty, and the union of per-duty clusters may exceed the current single-bucket cluster set. That can change `cluster_weights` and break the pinned fixture. Fix the split first, then re-derive and re-pin the tuple deliberately rather than adjusting the assertion to whatever comes out.

### 3. LOW — `align` computes excluded platforms but never shows them

`alignment_score_report()` returns `excluded_keywords` at `build_resume.py:6432`. `tasks.py run_align()` never prints it, so a posting requiring NetSuite or Workday now shows nothing at all in `align` where it previously showed a (wrongly actionable) gap.

The safety half is right — excluded terms no longer appear as a recommendation to add a tool. The visibility half is missing. The plan asked for them to be shown as non-actionable source gaps.

`run_check()` does this correctly, surfacing an `EXCLUDED` status alongside `COVERED` / `PARTIAL` / `MISSING`. Mirror that in `align` with a short "Unsupported platform requirements (do not add without source evidence)" block.
