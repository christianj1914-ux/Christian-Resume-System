# Claude Review: Validation, Federal Granularity, and Spec Hygiene (Revised)

Review pass only. No source files were modified.

---

## Verdict

Approved. One correction to my own prior finding, two confirmations that should stop Codex from writing unnecessary code, and one new item that this refactor is uniquely well-positioned to catch.

---

## I was wrong about the duplicate warnings, and the plan is right to reject it

I reported that `apply_selection_visibility()` emits byte-identical warnings with no deduplication. That was an error. The function does dedupe, at `build_federal_resume.py:2076-2080`:

```python
deduped_warnings: list[str] = []
for warning in warnings:
    if warning not in deduped_warnings:
        deduped_warnings.append(warning)
return replace(..., warnings=tuple(deduped_warnings))
```

I inspected lines 2030-2075 and stopped four lines short of it. The plan's instruction to leave that loop alone is correct.

---

## Two confirmations that reduce scope

### `resume_candidate_quality()` is not affected by grouping — no action needed

This one looks alarming and isn't, so it is worth recording before someone finds it mid-implementation and panics.

`build_federal_resume.py:2097` computes `warning_penalty = len(audit.warnings) * 25`, and line 2930 feeds that score into layout-candidate ranking. Collapsing eight unsupported warnings into two changes the penalty by 150 points.

It does not change the outcome. The grouped unsupported warnings originate in `federal_requirement_audit()` and are identical across every layout candidate, so the collapse shifts all candidates by the same constant. The argmax over `resume_candidates` is unchanged. Only the per-candidate visibility warnings vary, and those are untouched.

### `build_coverage_report()` is federal-only, so the commercial safeguard is unnecessary

The plan says commercial requirements "retain their current per-element behavior by leaving `requirement_group_id` empty." There is no commercial path to protect. `evidence_engine.build_coverage_report()` has exactly two call sites, both in `build_federal_resume.py` (lines 2059 and 2878), and `parse_commercial_requirements()` never reaches it.

Keeping the field optional is still good hygiene, but Codex should not write defensive branches or fixtures for a commercial path that does not exist.

**Do note the two call sites.** The plan describes grouping "in `build_coverage_report()`" as a single change, which is correct, but both call sites will inherit the new grouped questions. Confirm line 2878's report is intended to be grouped too, and cover it in the fixture rather than only line 2059.

---

## New finding: the registry refactor should catch orphaned tests

`scripts/smoke_test.py` currently contains:

```
467   top-level `def test_*` functions
381   registered `("name", lambda: ...)` entries
```

That is an 86-function gap. Some are legitimate helpers invoked by other tests, but any that are neither registered nor called are dead tests that have never run and never will — and nobody would know, because the suite reports a clean pass either way.

This plan is the one moment when detecting that is nearly free, since it is building the tagged registry anyway. Add:

- A meta-check that collects every module-level `test_*` function, subtracts those registered and those referenced by another test, and fails if the remainder is non-empty.
- If that remainder turns out to be large, downgrade it to a printed warning with an explicit allowlist rather than blocking this work. The point is visibility, not a cleanup project.

Related: the plan's example summary string hardcodes `(466 total)`, which matches neither count above and came from a figure I quoted earlier. Derive the total from the registry at runtime so the number cannot drift.

---

## Everything else confirmed sound

- Sentence split yields exactly six duties; the rejoined text is byte-identical to the current element, so the pinned 261/261 weights and ordered keyword tail provably cannot move.
- Group-level concatenated-text cluster inference already exists at lines 1570-1576. Preserve, do not reimplement.
- `_split_requirement_lines()` is now commercial-only, so the new federal sentence rule will not collide with its 420-character threshold.
- `missing_direct` collects only `DIRECT`-but-not-visible elements, so the added `UNSUPPORTED` results stay advisory and cannot trip the federal coverage gate. The plan states this correctly.
- `validate` has no extra-argument guard, so `--federal` and `--alignment` pass through with no dispatcher change.
- `CONTEXT_FILES` is a fixed seven-entry tuple and the packet builder's `spec.rel_path` records point at Python files, not markdown. Moving root specs is safe and needs no packet-builder change.

---

## Acceptance gate

The plan's strongest addition is treating a completed full `python tasks.py validate` run as the gate before closing the work. That is the one thing nobody has produced yet across this entire remediation. Hold the line on it: a recorded pass count and wall-clock duration, not a timeout report.
