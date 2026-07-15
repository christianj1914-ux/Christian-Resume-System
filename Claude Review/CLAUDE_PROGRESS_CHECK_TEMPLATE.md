# Claude Progress Check Prompt Template

Use this with `python tasks.py claude-prompt review --packet-mode claude-review` when Claude is acting as the implementation progress checker.

```text
Review `{{PACKET_PATH}}`, `CLAUDE.md`, the `.context` files, the current repo state, and the implementation notes already in this thread.

Packet mode: `{{PACKET_MODE}}`
Packet refresh command: `{{PACKET_COMMAND}}`
{{FOCUS_LINE}}

Do not write code.

Return only these sections in this order:

1. Overall Status
2. Interview Feature Track
3. Commit Train Track
4. Active Risks
5. Validation Gates
6. Repo Hygiene
7. Next Exact Action

Progress-check rules:

- Keep the top-level Overall Status language to: `ON TRACK`, `NEEDS ATTENTION`, `BLOCKED`, or `COMPLETE`.
- Track the implementation in two views at once:
  - Interview Feature Track: Phases 1 to 4
  - Commit Train Track: Commits 1 to 7
- Keep interview-feature completion separate from commit-packaging progress so late support, archive, or docs commits do not look like feature regressions.
- Treat runtime proof as stronger than code-shape-only evidence when they disagree.
- Call out risk IDs explicitly when relevant:
  - `R1` Medium: companion outputs exceed original Phase 4 scope unless they stay opt-in
  - `R2` High: `scratch/jd_library/index.csv` normalization is the riskiest commit gate
  - `R3` Medium: hunk-split commits can fail if staged in the wrong order
  - `R4` Low: commits 5 to 7 are real work but should not make interview-feature completion look incomplete
- For Phase 3, do not report complete unless the shared `question_prep` path is proven by live qualifications behavior and an unrelated-company leakage check.
- For Phase 4, fail the check if default `python tasks.py guide` behavior auto-emits companions. Companion outputs must stay opt-in.
- For Commit 6, block the train if the archive subsystem still leaves malformed or dropped `scratch/jd_library/index.csv` rows.
- In Repo Hygiene, state whether disposable validation logs are still uncommitted and whether `jobs/`, `scratch/`, or `Claude Review/CODEX_*` files appear to be staged into the wrong commit bucket.
- In Next Exact Action, name the single next validation or staging action that should happen before another commit.
- Distinguish current live behavior from proposals. If a status contract, output section, or validation gate does not exist in the repo yet, label it as a required monitor update rather than describing it as already live.
```
