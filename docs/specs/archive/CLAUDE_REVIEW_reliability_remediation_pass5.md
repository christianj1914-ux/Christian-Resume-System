# Claude Review Pass 5: Final Implementation Plan

Review pass only. No source files were modified.

---

## Verdict

Approved for implementation. Both pass-4 corrections landed correctly, and I re-verified every pinned value against measured output.

One addition below. It is not a defect in the plan, it is a missing precondition that the pinned numbers silently depend on. Add it and hand this to Codex.

---

## Verified against measured output

All three pinned fixtures now match what the code actually produces:

- **16-term set.** Matches exactly, in the measured order.
- **Cluster-derived tail, ordered.** `implementation`, `deployment`, `testing`, `go-live readiness`, `governance`, `risk management`, `access controls`, `audit readiness` — exactly positions 9-16 of the real output.
- **Cluster-weight tuple.** `implementation_delivery: 261`, `governance_risk: 261`, `agile_delivery: 165`, `change_adoption: 96`, `reporting_analytics: 96`, `customer_service_delivery: 69` — matches my simulation of the `weight_group_id` design.

The tie-break rationale is now stated correctly, and the "do not add a `program_delivery` entry" guard is in place.

---

## ADD BEFORE HANDOFF

### The pinned weights depend on an unstated core-experience priority of 69

Every one of the six pinned cluster weights decomposes as follows:

```
implementation_delivery   69 + 96 + 96 = 261
governance_risk           69 + 96 + 96 = 261
agile_delivery            69 + 96      = 165
change_adoption                96      =  96
reporting_analytics            96      =  96
customer_service_delivery 69           =  69
```

The `69` in four of those six rows is the core-experience bucket priority. The plan re-sources that bucket's *text* but never states its *priority*, and `parse_requirement_buckets()` currently carries two different values for the same `core_experience` kind:

- `build_federal_resume.py:1490` — priority `70`, in the branch used when no buckets were found at all
- `build_federal_resume.py:1503` — priority `69`, in the branch that inserts core experience ahead of found buckets

The pinned fixture assumes `69`. If the re-sourced core-experience bucket is built through the `70` path, or if the two are unified on `70` during the refactor, then four of the six pinned weights shift by one and the fixture fails for a reason that has nothing to do with the parsing change.

Add to the plan:

- State that the re-sourced core-experience bucket keeps priority `69`.
- Note that `build_federal_resume.py:1490` and `:1503` currently disagree, and say whether they should be unified. If they are unified on `70`, the pinned weights become 262 / 262 / 166 / 96 / 96 / 70 and the plan text must be updated to match.

### Reproduction note for whoever writes the fixture

The cluster set for the re-sourced core-experience bucket is:

```
('agile_delivery', 'implementation_delivery', 'customer_service_delivery', 'governance_risk')
```

I obtained that by running `infer_clusters()` over the joined non-empty lines 6 through 13 of the active posting — that is, **including** the `As an IT Project Manager/Scrum Master, you will:` lead-in line, not just the duty bullets beneath it. If the implementation excludes the lead-in, re-derive the clusters before trusting the pinned weights.

---

## Nothing else outstanding

Every item raised across passes 1 through 4 is now resolved, deliberately scoped out, or recorded in Assumptions. The archive drift warning, the fourth recovery category, the `dedupe_by_content` default, both keyword display surfaces, the backup relocation, `parser_fallback_required`, and the three `.context` LinkedIn files are all accounted for.

One optional implementation detail, worth a line of code comment rather than a plan change: the cluster sort's second key is "current default-cluster fallback rank." Clusters absent from the fallback tuple have no index, so that key needs an explicit sentinel (rank if present, otherwise infinity) rather than a bare `.index()` call, which raises `ValueError` on every cluster except `implementation_delivery`.
