# Claude Context Entry Point

This repository is Christian Estrada's resume automation system. The canonical operating rules live in `AGENTS.md`, but that file is intentionally broad and too large for routine Claude threads.

For most Claude work, read only these compact files first:

1. `.context/RESUME_SYSTEM_BRIEF.md`
2. `.context/ARCHITECTURE_MAP.md`
3. `.context/RULES_FOR_CLAUDE.md`

When Claude needs more implementation awareness but should not read full scripts, also read:

4. `.context/CODE_REVIEW_PACKET_GUIDE.md`
5. `.context/SCRIPT_INDEX.md`
6. `.context/COMMON_CHANGE_AREAS.md`

Use `AGENTS.md` only when a task requires checking a specific edge case that is not covered by the compact context files.

## Minimal Upload Strategy

Do not upload the whole repository to Claude unless the task genuinely spans many systems.

Use the smallest packet that can answer the question:

- Regenerate the live broad review packet with `python tasks.py claude-packet --mode broad` before a broad review thread.
- For subsystem review, generate the matching packet mode instead of pasting ad hoc snippets first:
  - `python tasks.py claude-packet --mode tracker`
  - `python tasks.py claude-packet --mode checklist`
  - `python tasks.py claude-packet --mode resume`
  - `python tasks.py claude-packet --mode cover`
  - `python tasks.py claude-packet --mode interview` for pitch ladder, rehearsable TMAY, story support, and question logic
  - `python tasks.py claude-packet --mode workflow`
- Generate the matching prompt instead of freehand review instructions:
  - `python tasks.py claude-prompt review --packet-mode tracker`
  - `python tasks.py claude-prompt plan --packet-mode tracker`
- If the issue is visual, include a small excerpt or screenshot from the rendered output. Otherwise, prefer code snippets and output excerpts over full generated documents.

## Claude's Best Role

Claude should usually act as a planner, logic reviewer, edge-case reviewer, or concise code reviewer. Avoid asking Claude to regenerate whole source files unless the file is very small.

Preferred Claude outputs:

- severity-ranked findings
- data-flow explanations
- exact review findings with file or function references
- small replacement snippets for Codex to apply
- dependency-aware implementation plans with validation and regression coverage


Keep these current workflow assumptions in mind during review:

- Standard private-sector resumes now follow a federal-style explicit-proof rule. Core experience should be visible in the summary and first bullets; do not assume the hiring manager will infer leadership, ownership, implementation depth, AI usage, or executive audience from weaker adjacent wording.
- For higher-level private-sector roles, bridge hard where truthful, but make leadership, manager/director-level audience, decision-making scope, and cross-functional ownership explicit when the source supports it.
- Federal runs now produce two Word documents by default: the exact two-page federal resume and a separate federal qualifications statement.
- Commercial filename audit states live today are PASS, BRIDGE, FAIL, and POOR. REVIEW is not a live audit state unless the code explicitly adds and propagates it.
- Federal outputs do not currently use the commercial fit-state filename system or tracker semantics.
- Standard commercial cover letters stay in the 80-170 word band by default, while the explicit long mode stays separate.
- Render warnings can be environmental. If the local DOCX-to-image converter is unavailable, builds may still succeed and only visual QA becomes manual.


Avoid:

- rewriting full scripts
- treating old generated outputs as source material
- using LinkedIn page content as resume evidence
- inventing resume claims, metrics, tools, responsibilities, or company values

## Two-Pass Workflow

Use Claude in two passes:

1. Review pass: generate a packet and ask Claude for severity-ranked findings.
2. Plan pass: feed Claude the review findings and ask for an implementation plan with fix order, validation, and regression coverage.
3. Implementation pass: give Codex the Claude plan so edits, tests, and output checks happen locally.

## Routine Workflow

1. Before replacing `jobs/job_description.txt`, run `python tasks.py jd-archive` if the current posting should remain available for tracker refresh or pattern review.
2. Put one active job posting in `jobs/job_description.txt`.
3. Generate the smallest useful packet with `python tasks.py claude-packet --mode ...`.
4. Generate the matching review prompt with `python tasks.py claude-prompt review --packet-mode ...`.
5. After Claude returns findings, generate the plan prompt with `python tasks.py claude-prompt plan --packet-mode ...`.
6. Give Claude's implementation plan or review notes to Codex for edits and validation.
7. Let Codex run scripts, validate generated Word documents, and keep final outputs in `output/`.
