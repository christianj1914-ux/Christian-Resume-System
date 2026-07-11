# Code Review Packet Guide

Claude cannot see the code unless you provide it in the Claude thread or project. Use the built-in packet and prompt commands instead of assembling broad manual uploads.

## Default Workflow

Use the same two-pass flow every time:

1. Generate the smallest useful packet.
2. Run the review prompt.
3. Run the plan prompt against Claude's findings.
4. Hand the plan to Codex for edits and validation.

Commands:

```text
python tasks.py claude-packet --mode broad
python tasks.py claude-prompt review --packet-mode broad
python tasks.py claude-prompt plan --packet-mode broad
```

Use a narrower mode whenever possible:

- `tracker`
- `checklist`
- `resume`
- `cover`
- `interview`
- `workflow`

## Packet Modes

Use the smallest matching packet first:

- `broad`: cross-system logic review, stale assumptions, regression hunting
- `tracker`: application tracker, search analytics, JD backfill, workflow auto-tracking, debrief sync
- `checklist`: analysis resume basis, fit snapshot logic, keyword coverage, debrief carry-through
- `resume`: summary logic, fit audit, output naming, source selection, two-page targeting logic
- `cover`: resume dependency, opening selection, proof paragraph, closing logic
- `interview`: cheat sheet, detailed guide, cover-letter-to-interview pitch reuse, human-motivation logic, extended TMAY, story support, question logic
- `workflow`: dry run, recovery path, step sequencing, output repair, workflow orchestration
- `federal`: federal resume planning, qualifications statement generation, federal supporting-doc wrappers, and federal workflow diagnostics
- `claude-review`: the Claude review bundle, packet generator, prompt generator, and refresh workflow itself

Use the `interview` packet when the problem touches:

- 30-second, 60-second, or 90-second elevator speeches
- "Tell Me About Yourself" logic in either interview document
- human-element or motivation language in longer answers
- drift between cover-letter positioning and interview positioning

Use the `resume` packet when the problem touches:

- source-resume selection or company/title extraction
- job-profile, lane, employer-context, or story-lens drift
- professional summary wording, role-summary rewrites, supported bullet rewrites, or Core Competencies shaping
- two-page content selection where the logic crosses `resume_analysis.py`, `resume_content.py`, and `build_resume.py`

If a packet still lacks one critical function, add only that function or snippet next. Do not upload whole scripts unless the problem truly spans most of the file.

For function-level guidance on what to inspect next, use `.context/COMMON_CHANGE_AREAS.md` and `.context/SCRIPT_INDEX.md`.

## What The Generated Packet Should Contain

The generated packet should already include:

- packet mode and timestamp
- recommended `claude-packet` and `claude-prompt` commands
- current system contract notes that distinguish live behavior from proposed additions
- review goal
- context files read
- current behavior and desired behavior
- relevant code excerpts
- packet self-audit warnings when context or excerpt drift is detected

If you need extra evidence, add only:

- exact output or error excerpts
- exact tracker rows involved
- exact archived JD index lines involved
- a short rendered-output excerpt when the issue is visual

## Review Pass Contract

Use:

```text
python tasks.py claude-prompt review --packet-mode tracker
```

The review pass should force Claude to return:

1. `Findings`
2. `Missing Tests And Weak Validation Coverage`
3. `Edge Cases That May Still Break`
4. `Single Most Useful Next File To Inspect`

Claude should rank findings by severity and give Codex-ready instructions, not broad rewrites.
Claude should also verify whether any proposed state or command already exists before describing it as current behavior.

## Plan Pass Contract

Use:

```text
python tasks.py claude-prompt plan --packet-mode tracker
```

The plan pass should force Claude to return:

1. `Recommended Fix Order`
2. `Detailed Fix Plan`
3. `Validation Checklist`
4. `Optional Follow-Up Improvements`

Each fix item should name the exact file/function, exact logic change, exact validation commands, and exact regression coverage to add.

## What Not To Include

Do not include:

- whole `output/` documents
- old generated resumes or PDFs as evidence
- backup folder contents
- render-check images unless the issue is visual
- full scripts when only two or three functions are relevant
- LinkedIn page content
- old outputs as source truth
