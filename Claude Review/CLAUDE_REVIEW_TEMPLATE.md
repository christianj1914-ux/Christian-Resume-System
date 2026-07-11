# Claude Review Prompt Template

Use this with `python tasks.py claude-prompt review --packet-mode ...`.

```text
Review `{{PACKET_PATH}}` against `CLAUDE.md` and the `.context` files.

Packet mode: `{{PACKET_MODE}}`
Refresh command: `{{PACKET_COMMAND}}`
{{FOCUS_LINE}}

Do not rewrite whole files.

Return only these sections in this order:

1. Findings
2. Missing Tests And Weak Validation Coverage
3. Edge Cases That May Still Break
4. Single Most Useful Next File To Inspect

Rules for Findings:

- Order findings by severity.
- Use severity labels: `Critical`, `High`, `Medium`, or `Low`.
- For each finding, include:
  - exact issue
  - why it matters
  - affected file, function, or section
  - exact Codex-ready instruction or smallest useful replacement snippet
- Prioritize bugs, regressions, stale assumptions, unsupported-claim drift, output-naming risk, tracker-state risk, shared-logic drift, and validation gaps.
- If a finding is uncertain, say exactly what one additional file or snippet would confirm it.

Rules for the whole response:

- Prefer precise instructions over broad rewrites.
- Point out missing smoke-test or integration-test coverage when it matters.
- Name only the smallest next snippet needed if the packet is insufficient.
- Distinguish current live behavior from proposed improvements. If you recommend a new state, command, enum, packet mode, or public contract that does not exist today, label it explicitly as a proposal rather than describing it as current behavior.
- Before recommending a new shared state or contract, name the affected consumers that would need propagation, such as filenames, tracker fields, checklist logic, interview outputs, federal wrappers, workflow scripts, and Claude review docs.
```
