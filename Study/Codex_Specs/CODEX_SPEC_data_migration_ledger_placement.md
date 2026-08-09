# Codex Spec: "data migration" Ledger Placement Silently Fails, Blocking the Full Workflow

## Context / how this was found
Running `python tasks.py resume` in full-workflow mode against a live Paylocity - Senior IT
Project Manager, Enterprise Applications posting produced a `FAIL` resume (70/115, honest Stretch
Fit driven by a real Payroll/HR domain gap) and then hard-stopped before building the cover letter
and qualifications statement:
```
Building resume did not finish.
  Underlying error: SystemExit: balanced keyword policy blocked dependent documents: data
  migration: missing from the resume [supported-direct-unresolved]
```
This is the readiness gate working as designed: it refuses to build sendable documents on top of a
resume that's missing a term the system itself found strong evidence for. The interesting part is
*why* the term never landed despite that evidence existing. Root-caused below.

## Root cause (confirmed and reproduced)
The resume notes for this run show the system correctly identified evidence for "data migration"
and attempted to place it:
```
Ledger placement issue: data migration: missing after ledger placement
...
Supported but Unwritten:
- data migration: missing from the resume [supported-direct-unresolved]
...
Ledger Placement Diagnostics:
- data migration: missing; anchor: ETL/SQL validation checks, cutover coordination; landing: missing
```
`weave_supported_keywords_into_top_bullets()` (`scripts/build_resume.py:4706-4915`) is what attempts
placement. For each candidate bullet it calls `natural_keyword_bullet_rewrite()`
(`scripts/build_resume.py:3683-3998`), and only falls back to weaving the term into the Professional
Summary if every bullet attempt returns an empty string (the `for...else` at
`build_resume.py:4874-4895`).

`natural_keyword_bullet_rewrite()` first checks `keyword_evidence_fits_bullet()`
(`build_resume.py:3540-3598`). For "data migration" that check is broad and passes easily:
```python
if normalized == "data migration":
    return bool(re.search(r"\b(data|migration|etl|sql|validation|cutover)\b", lowered))
```
So the function proceeds past that gate for most candidate bullets. But the actual *rewrite* logic
for "data migration" is a single, narrow literal-substring lookup in the `replacements` dict
(`build_resume.py:3822`):
```python
"data migration": ("ETL", "SQL validation", "cutover"),
```
consumed by the loop at `build_resume.py:3830-3838`, which only fires if the bullet contains one of
those three *exact* substrings verbatim. Unlike most other keywords in this function (e.g. `"uat"`
at `build_resume.py:3917-3923`, which has three separate fallback triggers: `validation`, `sandbox
testing`, `testing`), "data migration" has no dedicated fallback block later in the function — the
replacements-dict entry is its only shot, and if none of its three literal strings appear, the
function falls through everything else and hits the final `return ""` at `build_resume.py:3998`.

Checked the actual generated bullets against those three required strings — none match verbatim,
even though the underlying evidence is clearly present:
- "...during **migration** and post-go-live support." (bare "migration", not "ETL")
- "Coordinated business users... across concurrent **migration**, reporting, and training
  workstreams..." (bare "migration" again)
- "Protected **migration** stability during Epicor Kinetic readiness by leading scope alignment,
  **sandbox testing**, **UAT validation**, and targeted training..." (has "sandbox testing" and
  "UAT validation" — close to the intended concepts, but not "SQL validation" or "cutover" as
  literally required)
- Skills section has "ETL and Data Validation" — contains "ETL", but Skills-row paragraphs aren't
  in the bullet-rewrite candidate set at all, so this never gets considered.

Every bullet-rewrite attempt returns `""`, the `for...else` falls to
`weave_keyword_into_summary_paragraphs()` (`build_resume.py:4066-4117`) as a last resort, and that
also did not land the term in this run (its generic fallback — appending ", with {keyword}
emphasis." to the summary's first sentence — is gated by a summary-safety check,
`summary_weave_candidate_is_safe()`, that this specific generic tack-on apparently didn't clear;
not traced further since the bullet-level fix below is the higher-quality fix anyway — a real bullet
placement beats a generic "with data migration emphasis" summary clause).

Net effect: a term the system has genuine, well-anchored evidence for (ETL/SQL validation work,
cutover coordination, migration project involvement — all clearly present in the resume's actual
prose) never gets placed, purely because the three hand-picked trigger phrases for this one keyword
don't match how this particular resume's sentences happen to be worded. This is not a "no evidence"
gap; it's a recipe-coverage gap for one keyword.

## Fix (recommended)
Add a dedicated fallback block for "data migration" in `natural_keyword_bullet_rewrite()`, matching
the pattern already used for "uat" and other multi-trigger keywords. Insert near the existing "uat"
block (`build_resume.py:3917-3923`):
```python
if normalized == "data migration":
    if re.search(r"\bmigration\b", lowered) and not re.search(r"\bdata migration\b", lowered):
        return safe_keyword_bullet_candidate(replace_first_ci(text, r"\bmigration\b", "data migration"), surface)
    if re.search(r"\bSQL-based\b", text):
        return safe_keyword_bullet_candidate(replace_first_ci(text, r"\bSQL-based\b", "data migration and SQL-based"), surface)
    if re.search(r"\bUAT validation\b", lowered):
        return safe_keyword_bullet_candidate(replace_first_ci(text, r"\bUAT validation\b", "data migration and UAT validation"), surface)
    if re.search(r"\bsandbox testing\b", lowered):
        return safe_keyword_bullet_candidate(replace_first_ci(text, r"\bsandbox testing\b", "data migration sandbox testing"), surface)
```
The first branch (bare "migration" -> "data migration") is the one that resolves this specific
Paylocity case: three separate bullets already say "migration" as a standalone word, so the very
first ranked candidate paragraph would succeed. `safe_keyword_bullet_candidate()` already guards
against stem repetition, so replacing a lone "migration" with "data migration" is safe (it only
ever fires when "data migration" isn't already present). The `not re.search(r"\bdata migration\b",
...)` guard prevents a no-op double-insert if a future JD/resume pairing already has the phrase.

Do not widen `keyword_evidence_fits_bullet()` — it already passes correctly; the gap is entirely in
the rewrite step, not the eligibility check.

### Scope note
This is not a claim that every keyword in the `replacements` dict (`build_resume.py:3790-3829`) has
this same gap — most either have generic, high-frequency trigger words (e.g. "change management":
`migration readiness`/`adoption`/`training`) or a dedicated multi-trigger fallback block elsewhere in
the function. "data migration" is the one case checked here where the three literal triggers happen
not to match this resume's actual phrasing. Worth a quick pass over the other `replacements` entries
at some point to spot-check for the same single-shot fragility, but that's a separate, lower-urgency
audit, not part of this fix.

## Tests
- Add a `smoke_test.py` regression using the three real Paylocity bullet variants above (bare
  "migration", "SQL-based", "UAT validation" / "sandbox testing") and assert
  `natural_keyword_bullet_rewrite(bullet, "data migration", ...)` returns a non-empty rewrite
  containing "data migration" for each, with `has_same_stem_repetition()` false on the result.
- Add a regression on `weave_supported_keywords_into_top_bullets()` confirming "data migration"
  lands in a bullet (not just the summary) when the resume text contains a bare "migration" mention.
- Rebuild the Paylocity resume from the archived JD (`scratch/jd_library/` — archive it first with
  `python tasks.py jd-archive` if it isn't already captured, since it's still the live active job
  right now) and confirm the `SystemExit` blocker clears and the full workflow (resume + cover
  letter + qualifications) completes.
- Run `scripts/smoke_test.py` and `python tasks.py validate`.

## Not in scope here
The Stretch Fit score (70/115) and the Payroll/HR domain gap are legitimate, honest signals, not
bugs — the launcher's own guidance already suggests weighing whether this posting is worth full
prep time. Fixing the "data migration" placement gap unblocks the workflow so that decision can be
made with a complete draft in hand; it doesn't change the underlying fit assessment.
