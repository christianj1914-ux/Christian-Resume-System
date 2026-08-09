# Codex Packet: PROSE_NESTED_LIST repair does not converge

Prepared for the implementation (Codex) pass. Review pass findings plus a fix plan with
validation and regression coverage. A minimal content fix has already been applied to unblock
the active CreatorIQ build; the real fix below is still needed.

## Summary

`prose_engine.PROSE_NESTED_LIST` can flag a sentence that its own repair pass cannot rewrite,
so `repair_text` returns `converged=False` and the commercial resume build fails hard
(`build_resume.py` role-summary loop, ~line 4344:
`Commercial model role-summary repair did not converge for <employer>`).

## Severity-ranked findings

### F1 (High) Detector and repair thresholds are misaligned

`scripts/prose_engine.py`

- Detector `_nested_list` (line ~87) fires when a sentence has `count(",") >= 4` AND
  `>= 3` of `(and|or|including)`.
- Repair for `PROSE_NESTED_LIST` in `repair_text` (line ~253) runs
  `_repair_and_chain(_split_semicolons(current))`.
  - `_split_semicolons` only helps when semicolons exist.
  - `_repair_and_chain` (line ~155) only rewrites sentences with `>= 4` `and` tokens.

A sentence with exactly 4 commas and 3 `and/or/including` (with fewer than 4 literal `and`
tokens) and no semicolon trips the rule but is left unchanged, so `current == before`, the
loop breaks, and repair reports not converged.

Reproduction (East West, "decision" emphasis, before the content patch):

> Turned operations, finance, and engineering tradeoffs into clearer system decisions by
> owning Aptean Intuitive administration across a five-site manufacturing environment,
> supporting 150+ users, and guiding Epicor Kinetic transition planning and launch readiness.

commas=4, and/or/including=3, literal-and=3 -> trips detector, repair is a no-op.

### F2 (Medium) Additional un-repairable branches remain in resume_content.py

Same class of failure exists in other hardcoded East West branches in
`optimized_role_summary` (`scripts/resume_content.py`). Confirmed still failing repair:

- `elif profile.primary_lane` ... solution-architecture branch (line ~2371)
- the `documentation_phrase or training_phrase` assembled branch (line ~2347), which appends
  `comma_series(support_terms)` and can push commas/conjunctions over the threshold.

These do not trip for the current CreatorIQ JD (it lands on "decision"), but they will fail
for JDs that select those branches. The change_enablement and corporate_strategy branches
currently pass.

### F3 (High, environmental) Frozen mtimes defeat Python bytecode invalidation

Source files in the workspace keep a stale mtime after being written (observed:
`scripts/resume_content.py` stayed at 2026-07-13 20:56 after an edit). Because timestamp-based
`.pyc` validation compares source mtime to the mtime recorded in the cached `.pyc`
(`scripts/__pycache__/resume_content.cpython-312.pyc`, 2026-07-13 20:57), Python loads stale
bytecode and silently runs old code even though the source is correct. This makes any future
fix appear to "not take effect." `__pycache__` files could not be deleted from the mount
(Operation not permitted); `touch` on the source did bump the mtime and force recompilation.

## Fix plan

1. F1: give `PROSE_NESTED_LIST` a repair that actually splits a comma-based nested list.
   Add a dedicated splitter and call it before/with the existing and-chain repair. Sketch:

   ```python
   def _repair_nested_list(text: str) -> str:
       out = []
       for item in _sentences(text):
           # keep splitting while the sentence still trips the nested-list rule
           while _nested_list(item):
               last = None
               for m in re.finditer(r",\s+and\s+", item):
                   last = m
               if not last:
                   break
               first = item[: last.start()].rstrip(" ,;:.") + "."
               second = item[last.end():].strip()
               if second:
                   second = second[0].upper() + second[1:]
                   if second[-1] not in ".!?":
                       second += "."
               out.append(first)
               item = second
           out.append(item)
       return " ".join(p for p in out if p)
   ```

   Then in `repair_text`, when `PROSE_NESTED_LIST in hard`, run this splitter (and keep
   `_split_semicolons` + `_repair_and_chain`). Ensure the pass is idempotent and that
   `max_passes` is enough for multi-clause sentences.

2. F2: after the repair is fixed, re-run the audit across all `optimized_role_summary`
   branches to confirm none report `converged=False`. If any sentence is a better fix at the
   source (splitting into two sentences, as done for the "decision" branch), do that too.

3. F3: make builds resilient to frozen mtimes. Options, pick one: clear `scripts/__pycache__`
   at launcher start; run the workflow Python with hash-based invalidation; or `touch` sources
   before import. Also worth tracing why writes preserve old mtimes (sync/editor layer).

## Validation and regression coverage

- Add prose-engine regression cases asserting `repair_text(..., "summary").converged is True`
  for these exact strings (all currently fail):
  - the East West "decision" sentence quoted in F1
  - the solution-architecture branch sentence (resume_content.py ~2371)
  - the documentation/training assembled sentence (resume_content.py ~2347)
- Keep the existing assertion at `scripts/smoke_test.py:8925` (Aptean customer_success role
  summary passes prose repair without PROSE_NESTED_LIST) green.
- Add a property-style check: any sentence that trips `_nested_list` must be changed by the
  repair (guard against future detector/repair drift).
- Run the full smoke suite; verify commercial resume build completes for a JD that selects
  each East West branch.

## Already applied (content stopgap)

`scripts/resume_content.py`, East West "decision" branch (~line 2340) split into two
sentences so it converges. This unblocks the CreatorIQ build but does not fix F1/F2/F3.
