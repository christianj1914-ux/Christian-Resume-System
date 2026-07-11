# Codex Fix Plan: Cover Letter Crashes, Robotic Output, Awkward Resume Sentences

Source: direct line-level read of scripts/build_cover_letter.py, scripts/resume_content.py,
scripts/run_resume_workflow.py, .context/SCRIPT_INDEX.md. Not generated from a packet paste.
Do not rewrite whole files. Apply fixes in priority order below.

## Recommended Fix Order

1. Critical: All-or-nothing QC gate architecture in build_cover_letter.py is the real source of "cover letter creation errors," not just the opening fallback chain.
2. Critical: explain_unresolved() in run_resume_workflow.py discards the one diagnostic asset the system already builds (the JSON trace file), so failures look opaque even though rich data exists.
3. High: Lane-keyed boilerplate sentence dictionaries make cover letters and interview guides read identically across different companies in the same role lane.
4. Medium: Blind regex phrase-stuffing in resume_content.py produces ungrammatical, redundant resume bullets.
5. Medium: .context/SCRIPT_INDEX.md and .context/COMMON_CHANGE_AREAS.md misattribute the functions implicated in fixes #3 and #4 to the wrong file, and contain a stale function name. Fix this before relying on packet-mode review again.

## Detailed Fix Plan

### Fix 1: Collect cover letter QC violations instead of failing on the first one

Priority: Critical

Change target: scripts/build_cover_letter.py, three functions:
- assert_cover_letter_qc() (line 5722)
- validate_cover_letter_shape() (line 5818)
- validate_cover_letter_text() (line 5851)

Problem summary: These three functions together contain roughly 45 independent `fail(message)` calls, one per regex/heuristic rule (banned phrases, word count, colon count, semicolon count, contraction check, cliche patterns, AI-writing word list, closing phrasing, paragraph count, and more). `fail()` is `utils.fail()`, which does `print(..., file=sys.stderr); raise SystemExit(1)` immediately on the first rule that trips. There is no aggregation and no retry for any of these checks. This means: (a) the user only ever sees one violation per run, fixes it, reruns, and discovers the next one, which matches the "cover letter creation errors" complaint exactly; (b) a perfectly fixable letter (e.g. one stray semicolon) aborts the entire build with the same severity as a structurally broken letter. The codebase already proves a better pattern works: `validate_cover_letter_specificity()` (called at line 5925, inside validate_cover_letter_text) returns a `problems: list[str]` instead of calling fail(), and the surrounding `cover_warnings` list (built at line 5359, extended at lines 5414-5415, line 5926) is a working non-fatal-issue collector sitting right next to the fatal checks. The front half of validate_cover_letter_text (lines 5860-5911) and all of assert_cover_letter_qc / validate_cover_letter_shape never adopted that pattern.

Exact fix plan:
1. In each of the three functions, replace every `fail(message)` with `issues.append(message)` (introduce a local `issues: list[str] = []` at the top of each function if not already present as `issues`).
2. Change each function's return type from `None` to `list[str]` (the issues it collected), and have it return `issues` at the end instead of implicitly returning None.
3. At the single call site in build_document() (lines 5392-5426), call all three in sequence, concatenate their returned issue lists with `cover_warnings`/`specificity_warnings`, and only call `fail()` once, after all three have run, with the full joined list: `fail("cover letter QC failed:\n- " + "\n- ".join(all_issues))`. This preserves the existing all-or-nothing save behavior (no partial/unsafe file gets saved) but tells the user everything wrong in one run instead of one issue per run.
4. Before that final fail(), add exactly one regeneration attempt: if `all_issues` is non-empty, call `opening_method_paragraph()` and `proof_paragraph()` again (the existing fallback functions already used inside opening_method_paragraph: `_direct_opening()`, `_pyramid_opening()`) to regenerate just the paragraphs implicated by the issue list, then re-run the three validators once on the regenerated text before failing for real. Do not add more than one retry pass; the goal is to absorb the common single-rule misses (contraction slipped in, one extra semicolon) without masking structural problems.

Validation:
- Run `python tasks.py dry-run` then a full `python tasks.py resume` against the current jobs/job_description.txt (Pax8 posting) and confirm the run either succeeds or fails with a single multi-line message listing every violation found, not just one.
- Manually re-introduce two known violations at once (one contraction + one passive close phrase) in a test draft and confirm both appear in the same failure message.

Regression coverage: scripts/smoke_test.py currently passes 258/258. Add a smoke-test case that feeds a draft with 2+ simultaneous QC violations and asserts the resulting SystemExit message contains both violation strings, not just the first one encountered in file order.

### Fix 2: Surface the existing trace file instead of a generic "review the log above"

Priority: Critical (pairs with Fix 1; do this one first since it requires no behavior change, only better surfacing)

Change target: scripts/run_resume_workflow.py, explain_unresolved() (line 295), `validation_failure` branch (line 308-309). Also scripts/build_cover_letter.py, write_cover_letter_trace() (line 2901) and its call sites at lines 5435 and 5450.

Problem summary: build_cover_letter.py already writes a full JSON diagnostic (specificity_warnings, cover_warnings, preflight_warnings, prose_report, failure message) to a timestamped file via write_cover_letter_trace() on every failure, and prints `COVER LETTER TRACE: {trace_path}` to stdout right before re-raising (line 5446). But run_resume_workflow.py's explain_unresolved() never reads or repeats that path; its `validation_failure` branch just prints "review the validation message above," and run_resume.bat's `:failed` branch only prints a generic "stopped before creating a partial or unsafe file" line. The single most useful diagnostic artifact in the whole pipeline is being built and then effectively thrown away from the user's perspective, which is a major reason the failures feel opaque ("bad" output, unclear errors) even though the system has the data to explain itself.

Exact fix plan:
1. In run_step()/run_with_recovery() (run_resume_workflow.py), capture subprocess stdout (it likely already does, to compute `result`/`StepResult` — confirm by reading run_step() before editing) and scan it for a line matching `^COVER LETTER TRACE: (.+)$`.
2. Store the matched path on the `StepResult` (add a field, e.g. `trace_path: str | None`).
3. In explain_unresolved(), in the `validation_failure` branch, if `result.trace_path` is set, print it explicitly: `print(f"Full diagnostic detail: {result.trace_path}")` before the existing "Next action" line.

Validation: deliberately trigger a cover letter QC failure (e.g. temporarily shorten jobs/job_description.txt to trip the empty/keyword check, or feed a draft missing the LinkedIn URL) and confirm the final console output names the exact trace JSON path, and that opening that file shows the full warnings/failure payload.

Regression coverage: add a smoke-test or integration-test case asserting `StepResult.trace_path` is populated whenever the underlying script prints a `COVER LETTER TRACE:` line.

### Fix 3: Break lane-only boilerplate so two companies in the same lane stop reading identically

Priority: High

Change target:
- scripts/build_cover_letter.py: `method_sentences` dict inside opening_method_paragraph() (line 3912 onward), and the analogous `complication_by_lane` dict inside proof_paragraph().
- scripts/build_interview_cheat_sheet.py: `human_motivation_sentence()`, `story_human_connection_line()`, `behavioral_answer_scripts()` (its `PreparedAnswer` templates), `questions_to_ask()` (`base_questions` dict).

Problem summary: each of these is a dict keyed only by role lane (presales_solution, customer_success, change_enablement, analytics_operations, etc.). Every applicant in the same lane gets the exact same sentence, word for word, regardless of company. This is the single biggest contributor to "robotic" output, because two different employers in the same function produce textually identical paragraphs apart from the company name substitution done elsewhere in the pipeline.

Exact fix plan: the file already computes job-specific signal in nearby functions — `company_specific_context_sentence()` (line 245), `company_context_sentence()` (line 4432), and `build_resume.job_problem_profile()` / `build_resume.audit_keywords()` are already available at the call sites for all five target functions. For each lane-keyed sentence dict:
1. Keep the lane sentence as a structural template (it encodes a legitimate, reusable point of view), but require one company- or JD-specific clause be appended or substituted in before the sentence is returned — pull it from the same `company_context_sentence()` / JD-keyword extraction already used elsewhere in the file rather than introducing a new mechanism.
2. Add a guard (mirroring `assert_no_template_leakage()`, already in utils.py) that fails the build, or at minimum appends a `cover_warnings` entry, if a generated paragraph exactly matches the raw lane-template string with no company-specific token inserted — this gives an automatic detector for future regressions of the same kind, not just a one-time fix.

Validation: generate cover letters and interview guides for two different companies in the same lane (e.g. two "customer_success" postings) and diff the opening/proof paragraphs and the interview "human motivation" line; confirm they are no longer textually identical.

Regression coverage: add a smoke-test fixture pair (two job descriptions, same lane, different companies) and assert the rendered opening_method_paragraph/proof_paragraph/human_motivation_sentence outputs differ between the two.

### Fix 4: Stop blind keyword-substitution from producing ungrammatical resume bullets

Priority: Medium

Change target: scripts/resume_content.py, `rewrite_supported_text()` (line 599).

Problem summary: this function runs a series of JD-keyword-triggered `re.sub()` calls that mechanically expand or stitch resume phrases (for example turning "order processing" into "order management and order processing") with no grammar or redundancy check afterward. The result is the "awkward resume sentences" the user is seeing — stitched, run-on, or redundant clauses introduced purely because a keyword from the job description matched a trigger pattern.

Exact fix plan:
1. After each substitution inside rewrite_supported_text(), run the resulting clause through a lightweight redundancy guard: reject the substitution if the same root word (case-insensitive, stem-matched) appears twice within a ~6-word window, or if the substitution increases the sentence's word count past whatever cap build_resume.py already enforces for bullet length.
2. If the guard rejects a substitution, fall back to the original unmodified phrase and append a note to whatever warnings list the caller already tracks (apply_supported_rewrites(), line 797) rather than silently dropping the keyword — so keyword-gap auditing upstream still knows the term wasn't inserted and can choose another route.

Validation: re-run a resume build against a JD known to trigger several of these substitutions (the Pax8 posting in jobs/job_description.txt has heavy keyword density) and manually proofread the bullets that previously read awkwardly; confirm no duplicated root words within a clause.

Regression coverage: add a unit test directly against rewrite_supported_text() with an input phrase and JD keyword pair already known to produce a redundant result, asserting the guard either blocks the substitution or produces a non-redundant result.

### Fix 5: Repair stale .context documentation before trusting packet-mode review again

Priority: Medium (do this before the next `claude-packet` review pass, since later packets are built from these files)

Change target: .context/SCRIPT_INDEX.md, lines 43-54 and line 142; .context/COMMON_CHANGE_AREAS.md (same misattributed functions — grep for the same function names).

Problem summary: SCRIPT_INDEX.md lists `rewrite_supported_text()`, `apply_supported_rewrites()`, `strengthen_outcome_framing()`, `apply_outcome_framing_rewrites()`, `apply_consulting_story_rewrites()`, `apply_startup_operator_rewrites()`, `apply_value_story_rewrites()` (lines 52-54) and `build_problem_first_summary()`, `optimized_role_summary()`, `optimize_role_summaries()`, `summary_positioning_sentence()`, `summary_job_poster_sentence()` (lines 43-46) under the `scripts/build_resume.py` heading. None of these functions exist in build_resume.py anymore; they all live in an entirely separate, currently undocumented module, scripts/resume_content.py. Separately, line 142 still references `cover_letter_pitch_parts()`, which was renamed to `interview_pitch_parts()` — confirmed by the packet generator's own self-audit warning in a previously generated interview-mode packet. Any Claude review pass that trusted this map (including earlier passes in this project) was pointed at the wrong file for exactly the logic behind Fix 4 above.

Exact fix plan:
1. Add a new `## scripts/resume_content.py` section to SCRIPT_INDEX.md, immediately after the existing `## scripts/build_resume.py` section, listing the real functions and line numbers from that module (rewrite_supported_text, apply_supported_rewrites, apply_outcome_framing_rewrites, summary_requires_erp_proof, summary_proof_sentence, summary_demands_explicit_leadership, summary_fit_close_sentence, summary_word_count, ensure_summary_minimum_words, startup_operator_summary, summary_positioning_sentence, summary_job_poster_sentence, consulting_story_summary, build_problem_first_summary, rewrite_professional_summary_for_role, optimized_role_summary, apply_consulting_story_rewrites, apply_startup_operator_rewrites, apply_value_story_rewrites, competency_label_rewrites, condense_professional_summary).
2. Remove those same function names from the `scripts/build_resume.py` section (lines 43-46, 52-54) since they no longer live there.
3. Replace `cover_letter_pitch_parts()` with `interview_pitch_parts()` at line 142.
4. Apply the same two corrections to .context/COMMON_CHANGE_AREAS.md wherever the same function names or the old name appear.

Validation: `grep -n "^def " scripts/resume_content.py` and `grep -n "^def " scripts/build_resume.py`, diff against the updated SCRIPT_INDEX.md sections to confirm every listed function actually exists in the file it's listed under. Re-run `python tasks.py claude-packet --mode broad` and confirm the packet generator's self-audit step reports zero missing-excerpt warnings.

Regression coverage: none needed (documentation-only change), but flag this fix as a prerequisite note in any future `claude-prompt review` invocation until the self-audit step is confirmed clean.

## Validation Checklist

- `python scripts/smoke_test.py` still reports 258/258 (or higher, if new cases were added per Fix 1 and Fix 4) passing.
- A full `python tasks.py resume` run against the current Pax8 posting in jobs/job_description.txt completes without a cover letter crash, or fails with one consolidated multi-issue message plus a printed trace path.
- Two cover letters generated for different companies in the same role lane no longer share identical opening or proof paragraphs.
- `python tasks.py claude-packet --mode broad` self-audit reports zero missing-function warnings after the SCRIPT_INDEX.md correction.
- Manual proofread of at least one resume build confirms no duplicated-root-word bullets from rewrite_supported_text().

## Optional Follow-Up Improvements

- Extend the Fix 3 anti-template-leakage guard beyond cover letters into build_detailed_interview_guide.py's behavioral_answer_scripts() and questions_to_ask(), which share the same lane-only-dict pattern but were not included in this pass's line-level read.
- Consider adding a `--explain-last-failure` flag to tasks.py that reads the most recent file in the cover-letter trace directory and pretty-prints it, instead of relying on the user to find the path in scrollback.
- Once Fix 1 is live, consider lowering the retry-once behavior into a config flag so it can be disabled during smoke testing (a deterministic, non-regenerating mode is easier to test than a retry-on-failure mode).
