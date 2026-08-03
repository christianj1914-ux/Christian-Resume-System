# Claude Review: Validation Observability and Federal Follow-up

Review pass only. No source files were modified. Verified by executing the current code and simulating the proposed split.

---

## Verdict

Sound plan. Two findings, one of which will visibly work against the plan's own concision goal. Several of the plan's riskier-looking assumptions turned out to be already satisfied by the existing implementation, which is noted below so Codex does not rebuild them.

---

## Confirmed by execution — no action needed

- **The sentence split yields exactly 6.** Applying `(?<=[.!?])\s+(?=[A-Z])` to the current 801-character element produces six duties, so the plan's "12 specialized requirements (six per list)" fixture target is correct.
- **The pinned weights are provably safe.** Rejoining the six sentences with a single space reproduces the original text **byte-identically**, and `infer_clusters()` returns the same tuple for both. The 261/261 weights and the ordered keyword tail cannot move.
- **Group-level concatenated-text inference already exists.** `build_federal_resume.py:1570-1576` builds `grouped_text` per `weight_group_id` and calls `infer_clusters(" ".join(texts), ...)`. The plan's "never from the union of per-duty clusters" constraint is already how the code works, so this is a constraint to preserve, not to implement.
- **No competing split rule.** `_split_requirement_lines()` with its 420-character threshold is now called only from `parse_commercial_requirements()` (line 244). The federal path does not use it, which is why list two stayed merged. Adding sentence splitting to the federal parser will not collide with it.
- **The packet-builder assumption is correct.** `CONTEXT_FILES` is a fixed seven-entry tuple of `CLAUDE.md` plus `.context/` files, and the `spec.rel_path` references at lines 503 and 518 are `FunctionExcerpt` records pointing at Python files, not markdown. Moving root `CODEX_SPEC_*.md` files will not break packet generation or trigger `packet_self_audit()` warnings.
- **`validate` accepts pass-through arguments.** Unlike `align`, `check`, `commands`, and others, `validate` has no "does not accept extra arguments" guard, so `python tasks.py validate --federal` forwards cleanly with no dispatcher change.

---

## Findings

### 1. HIGH — Splitting list two nearly triples unsupported-requirement warnings

I simulated the split and ran `evidence_engine.match_requirements()` against the real federal evidence catalog:

```
CURRENT  (7 elements):   UNSUPPORTED 3,  DIRECT 1,  TRANSFERABLE 3
SPLIT   (12 elements):   UNSUPPORTED 8,  DIRECT 1,  TRANSFERABLE 3
```

The merged 801-character blob matched as a single `UNSUPPORTED`. Split into sentences, five of the six duties come back `UNSUPPORTED` individually and one becomes `TRANSFERABLE`:

```
UNSUPPORTED   Leading project teams in advanced systems software/hardware...
TRANSFERABLE  Functioning as a technical authority in project management...
UNSUPPORTED   Planning and designing systems architecture as they relate...
UNSUPPORTED   Assuring software and systems functionality and quality.
UNSUPPORTED   Ensuring extensive application of security/information...
UNSUPPORTED   Applying project management principles to large-scale...
```

This is not a defect in the split — it is more honest reporting, since a long blob clears token-overlap matching that its individual sentences cannot. But it has two consequences the plan does not address:

- `federal_requirement_audit()` appends one `Unsupported federal requirement: {element.text}` warning **per element**, with no group aggregation. That loop goes from 3 warnings to 8. The plan carefully aggregates *bucket* warnings by `weight_group_id` but leaves these element-level warnings ungrouped.
- Each `UNSUPPORTED` element also flows into `evidence_engine.build_coverage_report()` at line 438 and generates an additional `Evidence confirmation question:` entry.

Net effect: the federal dry-run report gets noisier at exactly the moment the plan is trying to make it concise.

Recommended addition: aggregate the element-level unsupported warnings by `weight_group_id` the same way bucket warnings already are — one line naming the source list with a count and the first two duty texts, rather than eight separate lines.

**Verified not a hard failure.** I checked `build_coverage_report()`: `missing_direct` at line 437 only collects elements whose status is `DIRECT` but not visible in the selected resume. `UNSUPPORTED` elements take the branch at line 438 instead. So the `fail("Federal direct-requirement coverage gate failed: ...")` gate at line 2069 will not trip on the new elements, and the federal build will not break. Worth stating explicitly in the plan so nobody discovers this by watching a build fail.

### 2. MEDIUM — The second high-priority warning loop emits byte-identical duplicates

`build_federal_resume.py:2043` iterates coverages and appends:

```python
warnings.append(f"{coverage.bucket.label} is supported in the source but not explicit enough in the selected 2-page resume.")
```

The message interpolates only `coverage.bucket.label`, which is `"Specialized Experience"` for every specialized bucket. The enclosing `warnings = list(audit.warnings)` list is never deduplicated.

So this already emits up to six identical strings today from list one's six buckets, and will emit up to twelve after list two splits. The group-dedup the plan preserves applies to `initial_warnings` at line 1601, not to this loop.

Fix alongside the split: apply the same `warned_groups` pattern here, or include something bucket-distinguishing in the message so the repeats are at least informative.

---

## Two small suggestions

- **`--federal` and `--alignment` being mutually exclusive** will be mildly annoying once a change touches both, which this plan's own work does. Consider allowing them to combine and running the union of tagged tests. Cheap now, awkward to retrofit.
- **Record the baseline in the archive index.** The plan asks for the full-suite duration to go in the implementation handoff. Put it in `docs/specs/README.md` too, so the next person knows whether eleven minutes is normal or a regression.

---

## Test-plan gap

The plan verifies `--federal` and `--alignment` but never asserts that the **selector itself is correct** — that a focused run actually executes the tests it claims and skips the rest. A selector bug that silently runs zero tagged tests would report a clean pass.

Add: assert that `--federal` reports a selected-test count greater than zero and less than the full-suite count, and that a deliberately broken federal assertion causes `--federal` to exit nonzero.
