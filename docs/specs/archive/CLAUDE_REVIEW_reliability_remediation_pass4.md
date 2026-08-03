# Claude Review Pass 4: Reliability Remediation Implementation Plan

Review pass only. No source files were modified. Findings verified by execution against the active `jobs/federal_job_description.txt`.

---

## Verdict

Ready to hand to Codex once three things are corrected. Every blocking item from passes 1 through 3 is now resolved, including the archive drift warning, the fourth recovery category, the `dedupe_by_content` default, both keyword display surfaces, the pre-recovery backup location, and `parser_fallback_required`.

Two of the three remaining items are defects in the pinned fixture values themselves, which is the highest-leverage place to catch them: a fixture pinned to a wrong value will either fail immediately or, worse, get "fixed" by changing the code to match.

---

## MUST FIX BEFORE IMPLEMENTATION

### 1. The pinned 16-term target set is correct as a set but wrong as a sequence

I verified the plan's term list against the actual output. The **set matches exactly** — no term added, none missing. The **order does not**.

```
Plan:     data management, agile delivery, project management, information management,
          information technology, configuration management, change management,
          records management, implementation, deployment, testing, go-live readiness,
          governance, risk management, access controls, audit readiness

Measured: data management, change management, records management, information management,
          agile delivery, project management, configuration management,
          information technology, implementation, deployment, testing, go-live readiness,
          governance, risk management, access controls, audit readiness
```

Positions 9-16 match exactly. Positions 2-8 differ.

The reason matters: the first 8 terms come from `audit_keywords()` in `federal_keyword_targets()` (lines 1596-1608) and are completely unaffected by cluster weights. Only the last 8 are cluster-derived. So the block the plan reordered is the block this change cannot influence.

Fix one of two ways:

- Assert set equality plus a separate assertion that the cluster-derived tail (positions 9-16) matches in order. This is the better test, because it isolates what the change actually controls.
- Or keep an ordered assertion and correct positions 2-8 to the measured sequence.

Do not implement against the plan's current sequence. It will fail on first run, and the tempting "fix" is to perturb `audit_keywords()` ordering, which is unrelated to this work.

### 2. The tie-break rationale is wrong, and the correct rule has a trap attached

The plan states: "For the active program-delivery fixture, an equal-weight tie places `implementation_delivery` ahead of `governance_risk`, because implementation delivery is the lane default."

The pinned outcome is right. The stated reason is not. The detected lane for this posting is:

```
job_problem_profile(jd, source_text).primary_lane  ->  'program_delivery'
```

`FEDERAL_DEFAULT_CLUSTERS_BY_LANE` (`build_federal_resume.py:843`) has no `program_delivery` key. Its keys are `implementation_delivery`, `customer_success`, `presales_solution`, `analytics_operations`, `change_enablement`, `process_improvement`, `corporate_strategy`. So line 1418 falls through to the hardcoded default `("implementation_delivery",)`, a single-element tuple.

`implementation_delivery` therefore wins the tie because it is the *fallback* default, not because `program_delivery` declares an ordering. The rest of the pinned order still holds: `change_adoption` and `reporting_analytics` tie at 96, neither appears in the fallback tuple, so alphabetical ordering puts `change_adoption` first, matching the plan.

**The trap:** `infer_clusters()` adds `+1` to any cluster present in `default_clusters`. If anyone later "fixes" the missing lane entry by adding `program_delivery: ("implementation_delivery", "data_migration", "executive_alignment", "governance_risk")` by analogy with the existing rows, then `executive_alignment` and `data_migration` gain a point in every bucket. That could reintroduce `executive_alignment` into the weight map — the exact cluster the plan's fixture asserts must be absent.

Required plan additions:

- Correct the rationale to say the tie resolves through the single-element fallback, since `program_delivery` is absent from the lane map.
- Add an explicit instruction: do not add a `program_delivery` entry to `FEDERAL_DEFAULT_CLUSTERS_BY_LANE` as part of this work. If that gap should be closed, it is a separate change with its own before/after cluster comparison.
- Note that the same map is read at line 1339 for federal application question sets, so a future entry affects more than requirement bucketing.

### 3. Confirmed correct, no change needed

`run_check()` exists as the plan describes: `check` is a registered command at `tasks.py:79`, dispatched at line 964, and `coverage_status()` line 593 sits inside `run_check()`. The plan's reference is accurate.

---

## Everything else verified as sound

Spot-checked the newly added items against the code they touch:

- **Archive drift detector.** Correct placement. `read_index()` stays pure and warns once per process, which matches the `_SYNC_COMPLETE` one-shot pattern already at `job_context_archive.py:46`.
- **`dedupe_by_content: bool = False` default.** Makes `reset_jobs.py:46` safe by construction, so it always gets a fresh directory before copying extra job files into it at lines 52-56.
- **Four recovery categories with the signature unchanged.** Preserves the `can_rebuild_resume` path used at `run_resume_workflow.py:619` and `678`, and keeps the three smoke-test monkeypatches at lines 14175, 14243, and 14301 working without signature edits.
- **Pre-recovery copies to `backups/workspace_health/`.** Removes them from the `scripts/**/*.py` glob at `fresh_corpus_rebuild.py:62`.
- **Removing `TargetContext.parser_fallback_required`.** Safe. It is set at `requirement_engine.py:384` and read nowhere in the tree.
- **Both display surfaces plus `build_resume.contains_search_term` named as authoritative.** Resolves the shadowing ambiguity at `build_resume.py:1926` versus `resume_analysis.py:94`.
- **Gate thresholds unchanged.** Correct. `alignment_score_report()` already skips do-not-insert terms before accumulating `covered_weight` and `total_weight`, so only displayed ratios move.

---

## One small suggestion, not blocking

The plan pins `cluster_priority` as a six-element sequence. Two of those six sit on ties: `implementation_delivery` and `governance_risk` at 261 each, and `change_adoption` and `reporting_analytics` at 96 each. A one-point shift in either pair flips the pinned order and fails the fixture for a reason unrelated to whatever change caused it.

Consider having the fixture assert the weights alongside the order, so a future failure message says "governance_risk moved from 261 to 262" rather than just "order changed." That turns a confusing regression into a self-explaining one.

---

## Fix order

Unchanged from pass 3. Correct items 1 and 2 above in the plan text first, since both are fixture values that step 5 depends on.

1. Read-only health checks, backup relocation, dry-run hash verification.
2. `python-docx==1.2.0` pin, CI install from `requirements.txt`.
3. Archive purity, drift warning, `dedupe_by_content`, `--sync-legacy`.
4. Alignment: eligible population, both display surfaces, component maxima.
5. Federal parsing: shared structural parser and competencies, then buckets with `weight_group_id`, then the corrected target-set and `cluster_priority` fixtures.
6. Timeouts, quarantine, and the four recovery categories.
