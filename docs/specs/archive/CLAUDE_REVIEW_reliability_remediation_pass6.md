# Claude Review Pass 6: Final Implementation Plan

Review pass only. No source files were modified.

---

## Verdict

Approved, with one correction to the priority-unification item. The plan says "unify the existing fallback core-experience priority from 70 to 69, so every core-experience path has one defined priority and the fixture is not branch-dependent." That is the right instinct, but it names two paths when there are three. As written, the fixture stays branch-dependent.

---

## The one correction: there are three core-experience priorities, not two

```
build_federal_resume.py:1490   priority=70    fallback branch, fires when no buckets found
build_federal_resume.py:1503   priority=69    insert branch, fires when buckets exist
build_federal_resume.py:1366   return 68      requirement_priority() fall-through
```

The third one is easy to miss because it is a bare `return 68` at the end of `requirement_priority()`. There is no `core_experience` branch in that function, so any bucket of that kind built through `flush_current()` gets **68**, since `flush_current()` calls `requirement_priority(current_kind or "core_experience", current_label)`.

This is not hypothetical for this plan. The plan re-sources core experience from the opening role-duty block and elsewhere calls for "structural boundaries for headings." The natural structural implementation is to make the `As an IT Project Manager/Scrum Master, you will:` line a recognized section start, which routes the resulting bucket through `flush_current()` — and therefore through `requirement_priority()` at 68, not the hardcoded 69.

Consequences if that happens:

```
priority 68:  implementation_delivery 260, governance_risk 260,
              agile_delivery 164, customer_service_delivery 68

priority 74:  (if classified as the existing "duties" kind at line 1364)
              implementation_delivery 266, governance_risk 266,
              agile_delivery 170, customer_service_delivery 74
```

Either outcome fails four of the six pinned weights, for a reason unrelated to the parsing repair.

Recommended plan wording, replacing the current unification bullet:

> Give `core_experience` an explicit branch in `requirement_priority()` returning 69, and change the fallback at line 1490 from 70 to 69. All three core-experience construction paths — the fallback branch, the insert branch, and `flush_current()` — must then yield 69 regardless of how the opening duty block is structurally detected.

Also confirm the opening duty block is not classified as the existing `"duties"` kind, which returns 74 at line 1364.

Low risk on the 70 → 69 change itself: nothing in `smoke_test.py` references `core_experience`, and the fallback branch only fires when no buckets are found at all, which is not the case for the active fixture.

---

## Everything else confirmed

The remaining additions since pass 5 are correct as written:

- Core-experience text sourced from the joined block **including** the lead-in line, matching how I derived the cluster set.
- Core cluster set pinned as `agile_delivery`, `implementation_delivery`, `customer_service_delivery`, `governance_risk`, with an instruction to re-derive.
- Sentinel rank for clusters absent from the fallback tuple.
- Priority 69 recorded in Assumptions.

With the three-path correction above, the pinned weights are reproducible from a cold start and the plan is complete.
