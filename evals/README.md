# Writing Evaluation

This folder is the start of a writing-quality workflow for resume summaries and cover-letter prose. The goal is to measure the exact problems Christian keeps seeing before we change the live generators again.

## Recommended folders

Use this simple split:

- `evals/examples/good/`: full Word outputs you would happily send
- `evals/examples/bad/`: full Word outputs you want the system to reject
- `evals/snippets/good/`: judged text excerpts that passed review
- `evals/snippets/bad/`: judged text excerpts that should fail review
- `evals/writing_gold_set.files.template.jsonl`: file-based index that points at those examples
- `evals/writing_gold_set.template.jsonl`: inline version if you prefer keeping everything in one file
- `evals/writing_gold_set.reviewed_snippets.jsonl`: the first reviewed snippet set built from real documents
- `evals/writing_gold_set.reviewed_docx.jsonl`: the same style of review, but pointed directly at `.docx` files with section extraction

If you are just testing a fresh output and do not want to keep it yet, save it in `scratch` and grade it with `writing-eval --text-file ...`.

## What this catches

The evaluator currently flags:

- system-style closers like `This background fits ...` and `The same pattern fits ...`
- proof narration like `Work includes ...`
- appended setup clauses like `during periods when ...`
- cover-letter scene-setting like `The team appears to be at a point where ...`
- summary sentences that start with `That`
- resume summaries that drift away from the repo's 3-sentence and 75-140 word rules

## How to use it

Run the built-in gold-set template:

```powershell
python tasks.py writing-eval --dataset evals/writing_gold_set.template.jsonl
```

Run the file-based template:

```powershell
python tasks.py writing-eval --dataset evals/writing_gold_set.files.template.jsonl
```

Run the first reviewed snippet set:

```powershell
python tasks.py writing-eval --dataset evals/writing_gold_set.reviewed_snippets.jsonl
```

Run the same kind of review directly against Word files:

```powershell
python tasks.py writing-eval --dataset evals/writing_gold_set.reviewed_docx.jsonl
```

Grade a candidate summary file:

```powershell
python tasks.py writing-eval --text-file scratch/candidate_summary.txt --artifact resume_summary
```

Grade a cover-letter opening without failing the command:

```powershell
python tasks.py writing-eval --text-file scratch/candidate_opening.txt --artifact cover_letter_opening --allow-failures
```

Grade a Word file directly:

```powershell
python tasks.py writing-eval --text-file "evals/examples/bad/Christian Estrada - Bain Resume.docx" --artifact resume_summary --allow-failures
```

Extract snippets from Word files into text companions:

```powershell
python tasks.py writing-extract evals/examples/good evals/examples/bad --out-dir evals/snippets
```

## Gold-set workflow

Use this folder as the source of truth for taste, not just syntax.

1. Save real outputs you like as `expected_outcome: "pass"`.
2. Save real outputs you reject as `expected_outcome: "fail"`.
3. Add `must_flag` rules for the exact failure you want the evaluator to catch.
4. Add `must_not_flag` rules for approved examples so the evaluator does not punish strong prose.
5. When comparing models or prompts, generate the same artifact from the same brief, save each result as plain text, and run the evaluator on every candidate.
6. Human review still decides the winner, but the grader filters out obvious narration and template drift first.

## Word-first workflow

If you prefer saving full `.docx` files first, that works now.

1. Save the full document in `evals/examples/good/` or `evals/examples/bad/`.
2. Either point a dataset line directly at the `.docx` file with an `extract` field, or run `writing-extract` to generate `.txt` snippets.
3. Keep only the passages you want to judge in `evals/snippets/good/` or `evals/snippets/bad/`.

Important: a document saved in `examples/good/` can still produce a bad snippet if only one section missed the standard. The snippet folders should reflect passage quality, not the label on the full document.

Example DOCX-backed JSONL line:

```json
{"id":"cover_letter_opening_bain_docx_bad_01","artifact":"cover_letter_opening","file":"examples/bad/Christian Estrada - Bain Cover Letter.docx","extract":"cover_letter_opening","expected_outcome":"fail","must_flag":["reputation_first_opening","i_want_to_do_more_of"]}
```

## File naming examples

Keep names plain and consistent:

- `resume_summary_clorox_good_01.txt`
- `resume_summary_bad_that_opener_01.txt`
- `cover_letter_opening_direct_good_01.txt`
- `cover_letter_opening_scene_setting_bad_01.txt`
- `cover_letter_proof_work_includes_bad_01.txt`

Helpful naming pattern:

`artifact_company_or_issue_good-or-bad_number.txt`

Examples:

- `resume_summary_clorox_good_02.txt`
- `resume_summary_system_narration_bad_02.txt`
- `cover_letter_opening_mckinsey_good_01.txt`
- `cover_letter_opening_at-a-point-where_bad_01.txt`

You do not need perfect naming. The real rule is: make it obvious whether the file is a good example or a bad example, and make the artifact type visible in the name.

## Easiest way to add a file-based example

1. Save the prose as a plain `.txt` file in `evals/examples/good/` or `evals/examples/bad/`.
2. Add one line to `evals/writing_gold_set.files.template.jsonl`.
3. Point the `file` field at the saved text file.

Example JSONL line:

```json
{"id":"resume_summary_clorox_good_02","artifact":"resume_summary","file":"examples/good/resume_summary_clorox_good_02.txt","expected_outcome":"pass","must_not_flag":["system_fit_closer","proof_opener_includes"]}
```

## JSONL schema

Each line is one JSON object. Supported fields:

- `id`: short sample name
- `artifact`: `resume_summary`, `cover_letter_opening`, `cover_letter_proof`, `cover_letter_full`, or `generic`
- `text`: candidate prose to grade
- `file`: optional path to a `.txt` example, relative to the JSONL file
- `expected_outcome`: optional `pass` or `fail`
- `must_flag`: optional list of rule codes the evaluator must catch
- `must_not_flag`: optional list of rule codes the evaluator must avoid

## Next step after this scaffold

Once the gold set has 30-50 approved and rejected examples, we can run a real bakeoff across different prompts or model providers without editing production language factories first.
