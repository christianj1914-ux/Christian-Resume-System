# Codex Spec: Skills-Row Italics Corruption and JD Hard-Truncation in Cover Letters

## Status
- Finding 1 (Skills italics) and Finding 2 (`mission_or_context_sentence` 400-char cut) were
  implemented and verified. Confirmed independently by rebuilding the Cox cover letters: the
  "...that supp." mid-word cut is gone from the Analyst II, Marketing Analytics letter, which now
  falls through cleanly to the `jd_concrete_hook()` fallback ("Cox is hiring an Analyst II,
  Marketing Analytics to support attribution and reporting for assigned campaigns.").
- Finding 3 below is a **new, separate** defect found during that same verification pass, in a
  different function than Finding 2. It produces the same class of symptom (an unpunctuated
  fragment gets a period stitched onto it) but is not fixed by the Finding 2 change. Do not send
  the Business Intelligence Senior Analyst or Client Solutions Consultant II cover letters until
  this is addressed — both currently ship a broken sentence.
- Finding 4 is a lower-priority, separate quality issue (not a truncation bug) surfaced in the
  same review. Flagged for awareness; does not block sending on its own, but worth fixing in the
  same pass since it's in the same code path.
- Finding 5 was found during final verification of Findings 2/3 and is now fully root-caused
  below. Not fixed yet. Low severity (drops one word, leaves a stray "/"), not a blocker for
  sending, but cheap to fix alongside Finding 4 since both live in the cover-letter smoothing
  pass.

## Context / how this was found
Reviewed the three Cox resumes/cover letters/checklists generated today (2026-08-05): Client
Solutions Consultant II, Analyst II Marketing Analytics, Business Intelligence Senior Analyst.
Tailoring itself is working correctly across the three roles (see note at the bottom) — the two
issues below are pre-existing formatting/text-generation bugs, not tailoring problems, found
while inspecting the generated DOCX XML and cover letter prose. Finding 1 is the italics bug the
user flagged directly. Finding 2 is a related-severity defect found in the same review pass.

---

## Finding 1 (High): Skills-section category label italics bleed into the skill list

### Symptom
In some generated resumes, an entire Skills row renders italic, e.g. (Business Intelligence
Senior Analyst resume, generated today):
`Solution Delivery and Program Leadership:  Structured Discovery  |  Requirements Definition  |
Solution Design  | ... | Non-Technical Stakeholders  |  Transformation` — every word italic.
Only the category label before the colon should be italic; the pipe-delimited items must be
regular (non-italic) text. Confirmed by unzipping the DOCX and reading `word/document.xml`: the
whole line is one `<w:r>` run with `<w:i w:val="1"/>`.

Confirmed this is NOT universal: the same category on the Analyst II, Marketing Analytics resume
(generated the same day, same pipeline) renders correctly as two runs — `Solution Delivery and
Program Leadership:` italic, followed by a separate non-italic run for the items. The only
functional difference between the two resumes is that the Business Intelligence resume triggered
a late-stage Skills insertion (it added "Non-Technical Stakeholders" and "Transformation" to
close a source-required skill gap) and the Marketing Analytics resume did not.

### Root cause
`set_paragraph_text()` (`scripts/resume_format.py:1069-1079`) is a generic "replace this
paragraph's visible text" helper. It grabs every `<w:t>` node in the paragraph, writes the full
new string into the **first** node, and blanks the rest:
```python
def set_paragraph_text(paragraph: ET.Element, text: str) -> None:
    text_nodes = paragraph.findall(f".//{W}t")
    ...
    text_nodes[0].text = text
    for text_node in text_nodes[1:]:
        text_node.text = ""
```
`format_core_competency_runs()` (`scripts/resume_content.py:3634-3661`) is the function that
correctly splits a Skills row into two runs: an italic run for `"{label}:"` and a non-italic run
for the items. Once that split has happened, the paragraph has two `<w:t>` nodes — run 1 (italic)
and run 2 (not italic). If anything downstream calls `set_paragraph_text(paragraph, f"{label}:  "
+ " | ".join(items))` on that same paragraph afterward, **all** the text (label + every item)
lands in text node 0, which belongs to the italic run. Run 2 is blanked but structurally still
present. Net effect: the whole line is now one italic run.

Three call sites write Skills rows this same way:
1. `add_simple_core_competencies()` — `scripts/resume_content.py:4084` and `:4109`.
2. `add_targeted_core_competencies()` → inner `write_row()` — `scripts/resume_content.py:4224-4226`.
3. `trim_redundant_targeted_core_competencies()` — `scripts/build_resume.py:3169`.

`build_resume.py` calls `format_core_competency_runs()` twice: once at line 7026 and again at
line 7137. The bug only manifests when a Skills-row-mutating call happens **after** the last
`format_core_competency_runs()` call with nothing re-splitting the runs afterward. Trace the live
call order in `build_resume()`:
- `7018` `add_simple_core_competencies()` — runs before the first split (7026), so safe today.
- `7026` `format_core_competency_runs()` — 1st split (correct).
- `7137` `format_core_competency_runs()` — 2nd split (still correct at this point).
- `7161-7176` `add_targeted_core_competencies()` (for `missing_source_skills`) — **runs after the
  last split, with no split afterward.** This is what fired for the Business Intelligence resume
  (it needed to close a source-required skill gap) and is the exact corruption point.
- `7177-7181` `trim_redundant_targeted_core_competencies()` — also runs after the last split, with
  no split afterward. Same exposure, triggers whenever Skills exceeds `max_items` (25).

This is call-order fragile: any Skills-row mutation added after line 7137 in the future will
reproduce this bug for whichever category it touches, and it will only show up on resumes that
happen to trigger that particular late-stage insertion/removal path — which is why it's
inconsistent across otherwise-identical pipeline runs.

### Fix (two parts — do both)

**Part A — required, minimal, closes the immediate hole.**
Add one more `format_core_competency_runs(document_xml)` call as the last Skills-touching
operation in `build_resume()`, after `trim_redundant_targeted_core_competencies()` returns
(`scripts/build_resume.py`, right after line 7181, before `final_snapshot =
resume_snapshot(document_xml)` at 7183):
```python
            competency_items_removed += trim_redundant_targeted_core_competencies(
                document_xml,
                job_description,
                source_required=required_source_skills,
            )
            format_core_competency_runs(document_xml)  # re-split after late-stage Skills edits

            final_snapshot = resume_snapshot(document_xml)
```
This guarantees run-splitting is always the final Skills-section operation regardless of which
upstream functions fired, closing the exposure window without touching the mutation functions
themselves.

**Part B — recommended, fixes the root cause so it can't regress on the next pipeline reorder.**
The three call sites listed above should not use the generic `set_paragraph_text()` for Skills
rows at all. Add a small dedicated writer in `scripts/resume_content.py` near
`format_core_competency_runs()` and use it everywhere a Skills row's full text is rewritten:
```python
def write_core_competency_row(paragraph: ET.Element, label: str, items: list[str]) -> None:
    """Rewrite a Skills-section paragraph as label(italic) + items(non-italic) runs.

    Use this instead of set_paragraph_text() for any Skills-section row rewrite —
    set_paragraph_text() collapses all text into the first existing run, which
    silently makes the whole line italic once format_core_competency_runs() has
    already split the paragraph into a label run and an items run.
    """
    remove_runs(paragraph)
    append_run(paragraph, f"{label}:", italic=True, bold=False)
    if items:
        append_run(paragraph, "  " + "  |  ".join(items), italic=False, bold=False)
```
Then:
- `scripts/resume_content.py:4084` and `:4109` (`add_simple_core_competencies`): replace
  `set_paragraph_text(target, f"{label}:  " + "  |  ".join(items))` with
  `write_core_competency_row(target, label, items)`.
- `scripts/resume_content.py:4224-4226` (`add_targeted_core_competencies` → `write_row`): replace
  `set_paragraph_text(paragraph, f"{label}:  " + "  |  ".join(items))` with
  `write_core_competency_row(paragraph, label, items)`.
- `scripts/build_resume.py:3169` (`trim_redundant_targeted_core_competencies`): replace
  `set_paragraph_text(paragraph, f"{label}:  " + "  |  ".join(kept))` with
  `write_core_competency_row(paragraph, label, kept)`.

Do not change `set_paragraph_text()` itself — it's a shared generic helper used correctly
elsewhere (summary/role-summary rewrites, single-run paragraphs) and changing its semantics is
higher-risk than routing Skills-row writers to a dedicated function.

With Part B done, Part A becomes a pure safety net (harmless no-op re-split) rather than the only
thing standing between correct output and a corrupted one — keep both.

### Tests
- Add a `smoke_test.py` regression: build (or simulate) a Skills paragraph, run
  `format_core_competency_runs()`, then run `add_simple_core_competencies()`,
  `add_targeted_core_competencies()`, and `trim_redundant_targeted_core_competencies()` against
  it in sequence (mirroring the live `build_resume()` order), and assert after each step that the
  paragraph still has exactly one italic run (the label) and the remaining run(s) are non-italic.
  Assert the italic run's text ends with `:` and never contains a `|`.
- Regenerate the Business Intelligence Senior Analyst resume for Cox (or any JD that forces
  `missing_source_skills` to be non-empty) and unzip the output DOCX; grep
  `word/document.xml` for the Skills paragraph and confirm two runs with `i w:val="1"` only on
  the label run.
- Run `scripts/smoke_test.py` and `python tasks.py validate` before considering this closed.
- Spot-check 2-3 older resumes in `output/` for the same corruption pattern (search generated
  DOCX XML for a Skills-section run where `<w:i w:val="1">` wraps a `<w:t>` containing `|`) —
  this bug predates today's run per the user's report, so there are likely other affected files
  worth knowing about (informational only; do not regenerate old outputs, they are not source
  truth).

---

## Finding 2 (High — sendable-document defect): cover-letter opening sentence truncates mid-word

### Symptom
Cover letters generated today contain garbled, mid-word/mid-clause cut-off sentences in the
opening paragraph, e.g. (Analyst II, Marketing Analytics cover letter):
> "Cox stands out to me because working within a defined scope across a subset of brands and
> products, this role builds. Maintains dashboards and reports, prepares data for analysis, and
> conducts campaign performance analysis that supp."

`"that supp."` is `"that supports"` cut mid-word with a period stitched on. Same symptom family
in the other two cover letters generated today: `"...analysis that supp."` (Marketing Analytics),
a run-on fragment ending `"...through commercial launch...; some."` (Client Solutions Consultant
II), and a garbled clause `"The work calls for lifecycle that keeps SQL clear..."` (Business
Intelligence Senior Analyst). These are sendable documents (cover letters are not warn-only prep
docs per `.context/COMMON_CHANGE_AREAS.md`), so a recruiter-facing document currently ships with a
sentence that stops mid-word.

### Root cause (confirmed and reproduced)
`mission_or_context_sentence()` (`scripts/question_prep.py:753-768`) builds the opening "why this
company/role" sentence. When no usable line is found in `company_research_text` (true for Cox —
no `jobs/company_research.txt` entry today), it falls back to scanning the raw job description:
```python
    for sentence in split_into_sentences(job_description[:400]):
```
`job_description[:400]` is a **hard character-count slice**, taken before any sentence splitting.
If character 400 lands inside a word, `split_into_sentences()` returns a final fragment with no
terminal punctuation, and that fragment is exactly what gets selected as the "context sentence."

Reproduced directly against today's archived Cox Marketing Analytics JD
(`scratch/jd_library/20260805_182951_Cox_Analyst_II_Marketing_Analytics_cc97859a/job_description.txt`):
```python
>>> jd[380:420]
'e analysis that supports data-driven dec'
>>> question_prep.split_into_sentences(jd[:400])[-1]
'Working within a defined scope across a subset of brands and products, this role builds and '
'maintains dashboards and reports, prepares data for analysis, and conducts campaign performance '
'analysis that supp'
>>> question_prep.mission_or_context_sentence("Cox", "", jd)
'Cox stands out to me because working within a defined scope across a subset of brands and '
'products, this role builds and maintains dashboards and reports, prepares data for analysis, '
'and conducts campaign performance analysis that supp.'
```
This is a one-line reproduction of the exact defect in the shipped cover letter. Downstream
formatting (`ensure_company_named()` → `clean_answer_sentence()` / `ensure_sentence()`) has no
check for "does this fragment actually end where the source text ended a sentence" — it just
appends a period to whatever string it's given if one isn't already there, so a mid-word cut is
indistinguishable to that code from a real short sentence.

Only one call site does this raw slice-before-split (confirmed via repo-wide grep):
`scripts/question_prep.py:760`. `scripts/smoke_test.py:2576` exercises the same 400-char slice in
a test, but only asserts a known-complete sentence is still found inside a well-formed sample —
it does not assert anything about the truncation boundary, so it will not need updating for
either fix option below, and it won't catch a regression here either (worth strengthening, see
Tests).

### Fix (pick one; Option A is simpler and lower-risk)

**Option A — reject incomplete trailing fragments (minimal, recommended).**
After slicing and splitting, drop the last candidate sentence if it does not actually end at a
sentence boundary in the *original*, un-truncated `job_description`. Concretely, in
`scripts/question_prep.py`, replace the loop at line 760:
```python
    for sentence in split_into_sentences(job_description[:400]):
```
with a helper that discards a trailing fragment:
```python
    for sentence in _complete_sentences_within(job_description, 400):
```
and add, near `split_into_sentences()`:
```python
def _complete_sentences_within(text: str, char_budget: int) -> list[str]:
    """Sentences fully contained in text[:char_budget], never a mid-word/mid-clause cut.

    split_into_sentences() on a hard character slice can return a trailing fragment
    that only looks like a sentence because ensure_sentence() later appends a period
    to it. Drop that fragment instead of shipping it in a cover letter.
    """
    window = text[:char_budget]
    sentences = split_into_sentences(window)
    if not sentences:
        return []
    last = sentences[-1].strip()
    # A genuine sentence in the source text is immediately followed by ., !, or ?
    # (allowing for closing quotes) or is the literal end of job_description.
    tail_ok = (
        window.rstrip()[-1:] in ".!?\"'”’" if window.rstrip() else False
    )
    if not tail_ok and len(text) > len(window):
        sentences = sentences[:-1]
    return sentences
```
This preserves current behavior whenever the 400-char window happens to end cleanly (the common
case) and only drops the fragment when it would otherwise ship a truncated clause. If dropping the
last sentence empties the result, the existing fallback chain in `proof_first_opening_paragraph()`
(`scripts/build_cover_letter.py:3516-3524`) already handles an empty `mission_or_context` by
falling through to `company_specific_fact` or the synthesized `fallback_context_sentence` built
from `jd_concrete_hook()` — both of which build clean, complete sentences rather than slicing raw
JD text — so there is no dead-end case to handle separately.

**Option B — widen the lookahead to the next sentence boundary instead of dropping (alternative).**
Instead of discarding the trailing fragment, extend the slice forward (cap at, say, 700 chars) to
the next `.`, `!`, or `?` in the source text so the sentence completes naturally rather than being
lost. Slightly more code, marginally better sentence variety; not necessary unless Option A proves
to drop the mission sentence too often in practice (see Tests below for how to check that).

Recommend Option A first; only move to Option B if the smoke-test corpus run below shows Option A
frequently loses a usable sentence.

### Tests
- Unit test in `smoke_test.py`: reuse the exact Cox Marketing Analytics JD text (or a trimmed
  version reproducing the same 400-char cut) and assert
  `question_prep.mission_or_context_sentence("Cox", "", jd)` either returns `""` or a string whose
  last non-punctuation character sequence is a real, complete word (e.g. assert the returned
  sentence, minus trailing punctuation, does not end mid-word by checking it matches a case where
  the same substring appears verbatim followed by whitespace or a sentence terminator in the
  source `job_description`).
- Regression-guard the existing `test_mission_or_context_sentence_survives_job_label_header` test
  in `smoke_test.py:2562` still passes unchanged (Option A does not touch its well-formed sample).
- Rebuild cover letters for the three Cox roles from today's archived JDs in `scratch/jd_library/`
  and confirm the opening paragraph no longer contains a mid-word cutoff for any of the three.
- Scan a handful of other recent `output/*Cover Letter*.docx` files for the same symptom (a
  sentence ending in a truncated word immediately followed by a period, or a stray trailing
  fragment like `"; some."`) to gauge how many already-sent letters may be affected
  (informational only, not a regeneration order).
- Run `scripts/smoke_test.py` and `python tasks.py validate` before considering this closed.

---

## Finding 3 (High — sendable-document defect, NOT fixed by Finding 2): `jd_concrete_hook()` word-count cutoff strands mid-clause fragments

### Symptom
After the Finding 2 fix shipped, two of the three rebuilt Cox cover letters still ship a broken
sentence:
- Business Intelligence Senior Analyst: "...to identify business opportunities & develop the
  **associated.**"
- Client Solutions Consultant II: "...in accordance with the EVBS Implementation Framework;
  **some.**"

Both are grammatically incomplete clauses with a period stitched onto the last surviving word —
the same symptom family as Finding 2 ("...that supp."), but Finding 2 does not touch this code
path, so it did not fix these.

### Root cause (confirmed and reproduced)
`_clean_jd_hook_candidate()` (`scripts/build_cover_letter.py:3401-3421`) is what builds
`jd_concrete_hook()`'s return value, which feeds `cover_safe_concrete_hook()` and from there
`proof_first_opening_paragraph()`'s `fallback_context_sentence` and `role_sentence`. It hard-caps
the candidate JD line to 22 **words**, regardless of clause boundary:
```python
    words = cleaned.split()
    if len(words) > 22:
        cleaned = " ".join(words[:22]).rstrip(" ,;:.")
```
This is the same defect class as Finding 2 (accept a mid-clause cut, then let `ensure_sentence()`
append a period to it) but with a word budget instead of a character budget, and it fires whenever
`company_research_text` has no usable line — which is every Cox letter today, since there's no
`jobs/company_research.txt` entry — because that's exactly when `context_sentence ==
fallback_context_sentence` and the code falls back to this hook.

Reproduced directly against both archived Cox JDs:
```python
>>> jd_concrete_hook(bi_job_description)
'collaborate with senior leaders in allied and supported functions (e.g., Product, Operations, '
'Finance, Marketing) to identify business opportunities & develop the associated'
>>> len(_.split())
22
# Source line (25 words): "...& develop the associated informational and data requirements."
# -> truncated 3 words short of the actual clause boundary.

>>> jd_concrete_hook(csc_job_description)
'manage and drive all activities and artifacts from RFP/RFI through delivery and warranty phase '
'in accordance with the EVBS Implementation Framework; some'
>>> len(_.split())
22
# Source line: "...EVBS Implementation Framework; some work may continue long after commercial
# Go-Live." -> the semicolon starts a second independent clause the 22-word cap cuts into.
```
Two distinct failure shapes, two matching fixes:

**3a — semicolon-joined independent clause (required, low-risk).** The existing sentence-boundary
split at line 3410 only stops at `.`, `!`, `?`. A semicolon joining two independent clauses (like
the CSC II line) should be treated the same way — the second clause isn't part of the hook at all,
regardless of word count. Add a split on `;` right after the existing sentence split:
```python
    cleaned = re.split(r"(?<=[.!?])\s+", cleaned, maxsplit=1)[0]
    cleaned = re.split(r"\s*;\s*", cleaned, maxsplit=1)[0]  # stop at a semicolon clause boundary
```
This alone fully fixes the CSC II case (the candidate becomes "...EVBS Implementation Framework",
a complete clause, well under 22 words — no truncation needed at all).

**3b — legitimate clause runs a few words past the cap (required).** The BI case has no semicolon;
it's one clause that is 25 words long and gets guillotined at 22. Don't cut on a bare word index —
search backward from the cap for the nearest coordinating conjunction (`and`/`or`/`but`) or comma,
and cut there; only fall back to the bare word-index cut if no such boundary exists within a small
extra allowance (e.g. word 30). Concretely, replace the word-count block with something like:
```python
    words = cleaned.split()
    if len(words) > 22:
        search_upper = min(len(words), 30)
        boundary = None
        for idx in range(search_upper - 1, 14, -1):
            token = words[idx].rstrip(",")
            if words[idx].lower() in {"and", "or", "but"}:
                boundary = idx
                break
            if token != words[idx]:  # token had a trailing comma -> safe clause break after it
                boundary = idx + 1
                break
        cleaned = " ".join(words[: boundary or 22]).rstrip(" ,;:.")
```
Applied to the BI line, this still won't reach "requirements" (there's no comma/conjunction
between "associated" and "informational"), so the practical fix for that specific case is that 3a
doesn't help it and 3b's boundary search should be allowed to extend far enough to reach the true
end of a clause that's only slightly over budget — the reviewer should size the `search_upper`
allowance (or consider capping by clause rather than by word count, using the same `.!?;` split
already used for the length-under-22 path) so a clause that's within ~10 words of the cap is kept
whole rather than clipped. Whatever exact number is chosen, the acceptance test is non-negotiable:
never return a candidate whose last word is not the true last word of a clause in the source JD.

### Tests
- Reproduce both cases above as fixed smoke-test inputs (BI "develop the associated..." line, CSC
  II "...Framework; some work..." line) and assert `jd_concrete_hook()` / `_clean_jd_hook_candidate()`
  returns a complete clause for each — i.e., the returned string, with a period appended, must
  appear as a real substring-plus-terminator in the source JD (the same "is this actually where a
  clause ends in the source text" check used for Finding 2).
- Rebuild the BI and CSC II cover letters from the archived JDs and confirm the opening paragraph
  no longer contains "associated." or "some." as a standalone truncated sentence.
- Run `scripts/smoke_test.py` and `python tasks.py validate`.

---

## Finding 4 (Lower priority — template/term mismatch, not a truncation bug)
Same review pass surfaced a separate, unrelated quality issue in the same fallback path. When
`role_specific_cover_work_sentence()` (`scripts/build_cover_letter.py:3547-3581`) builds its
sentence, it plugs JD-matched terms into a fixed template:
```python
return (
    f"The work calls for {first} that keeps {second} clear and uses {third} "
    "to connect scope with launch readiness and handoff discipline."
)
```
`extract_cover_letter_terms()` (`build_cover_letter.py:2587-2621`) returns whatever pattern-matched
labels it finds (tool names like `SQL`, `Excel` are valid, common matches), but the template
assumes slot 2 and 3 are abstract process nouns ("communication," "documentation"), not tools.
That mismatch produced "The work calls for lifecycle that keeps SQL clear and uses Excel to
connect scope with launch readiness and handoff discipline" (BI) and "...validation that keeps SQL
clear and uses Excel..." (Marketing Analytics) — grammatically well-formed but semantically odd
("keeps SQL clear" isn't a real phrase). This is a template-design issue, not a truncation bug, and
is a larger lift (needs per-term grammatical-role tagging or a redesigned template that reads
naturally for both tool names and abstract nouns). Recommend scoping this as its own follow-up
rather than folding it into the Finding 3 fix — flagging here so it isn't lost, not requesting
immediate action.

---

## Finding 5 (Low priority — fully root-caused): paired acronym scrub drops one half of "RFP/RFI"

### Symptom
Verified against the Finding 2/3 rebuilds: the Client Solutions Consultant II letter still reads
"...manage and drive all activities and artifacts from **RFP/** through delivery and warranty
phase..." — "RFI" is silently dropped, leaving a dangling slash. Pre-existing (present in the very
first draft this morning), unrelated to Findings 1-3, and not touched by either of those fixes.

### Root cause (confirmed and reproduced)
`smooth_cover_letter_text()` (`scripts/build_cover_letter.py:5264-5268`) scrubs any all-caps token
of 3+ letters that isn't in an allow-list, replacing it with a single space:
```python
    cleaned = re.sub(
        r"\b[A-Z]{3,}\b",
        lambda match: match.group(0) if match.group(0).upper() in allowed_tokens else " ",
        cleaned,
    )
```
The allow-list comes from `cover_allowed_acronyms()` (`build_cover_letter.py:1680-1694`), which
only allow-lists a JD-sourced acronym if it appears **2 or more times** in the job description:
```python
    token_counts = Counter(token.upper() for token in re.findall(r"\b[A-Z]{2,6}\b", job_description or ""))
    for token, count in token_counts.items():
        if count >= 2:
            allowed.add(token)
```
Counted directly against the archived CSC II JD: `RFP` appears 2 times (allow-listed), `RFI`
appears 1 time (not allow-listed), `EVBS` appears 2 times (allow-listed, which is why "EVBS
Implementation Framework" survives intact in the same sentence), `SOW` appears 1 time (would be
scrubbed too if it appeared standalone in a surviving sentence). The frequency-2 threshold is a
reasonable heuristic for filtering out one-off JD noise tokens in isolation, but it breaks on a
paired/compound acronym like "RFP/RFI" or "SOW/FRD" where both halves are legitimate, JD-quoted
terms that happen to co-occur once as a unit — the scrub regex removes the low-frequency half and
leaves the slash orphaned, rather than either keeping or dropping the pair together.

### Fix (recommended)
Make the allow-list pair-aware: if two acronym tokens appear joined by a `/` anywhere in the job
description (e.g. `RFP/RFI`, `SOW/FRD`), treat that as sufficient evidence both are legitimate and
allow-list both together, independent of each token's standalone frequency. In
`cover_allowed_acronyms()`, after the existing frequency loop, add:
```python
    for pair in re.findall(r"\b([A-Z]{2,6})/([A-Z]{2,6})\b", job_description or ""):
        allowed.update(token.upper() for token in pair)
```
This is additive and low-risk: it only ever widens the allow-list for tokens that are already
visibly paired in the source JD (so nothing untruthful gets added), and it doesn't change the
existing frequency-2 behavior for standalone acronyms.

### Tests
- Add a smoke-test case with a JD line containing a low-frequency paired acronym (e.g., an
  `RFP/RFI` or `SOW/FRD` occurring only once) and assert `cover_allowed_acronyms()` includes both
  halves, and that `smooth_cover_letter_text()` on a sentence containing that pair preserves both
  tokens with no orphaned `/`.
- Rebuild the Client Solutions Consultant II Cox cover letter and confirm the sentence reads
  "...from RFP/RFI through delivery..." with both acronyms intact.
- Run `scripts/smoke_test.py` and `python tasks.py validate`.

---

## Tailoring review (informational, no action needed)
The three Cox resumes generated today (Client Solutions Consultant II, Analyst II Marketing
Analytics, Business Intelligence Senior Analyst) are genuinely tailored, not copy-paste variants:
each has a different header/title line, a different Professional Summary opening clause,
different bullet selection and ordering within East West Manufacturing / Aptean / Home Depot
(e.g., the CSC II resume leads with the Amazon Robotics warehouse launch and RFP/SOW authorship;
the BI Senior Analyst resume leads with the $20M inventory/downtime bullet; the Marketing
Analytics resume drops both of those in favor of dashboard/reporting-forward bullets), and
different Skills category sets and ordering (Customer Success and Revenue / Solution Consulting
for CSC II vs. Solution Delivery and Program Leadership / Customer Success and Account Value for
the other two). All three were tagged `FAIL` by the audit, but for role-specific, legitimate
reasons unrelated to either bug above (missing JD terms like "business management," "ROI
reporting," or "business intelligence" not visible early enough, and per-role Skills relevance
warnings) — that is the audit doing its job and flagging them for human review before submission,
not a defect to fix.
