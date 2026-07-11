# Claude Planning Prompt Template

Use this with `python tasks.py claude-prompt plan --packet-mode ...` after a review pass.

```text
Review `{{PACKET_PATH}}`, `CLAUDE.md`, the `.context` files, and the review findings already in this thread.

Packet mode: `{{PACKET_MODE}}`
Packet refresh command: `{{PACKET_COMMAND}}`
Review prompt command: `{{REVIEW_PROMPT_COMMAND}}`
{{FOCUS_LINE}}

Do not write code.

Turn the review findings into an implementation-ready Codex plan.

Return only these sections in this order:

1. Recommended Fix Order
2. Detailed Fix Plan
3. Validation Checklist
4. Optional Follow-Up Improvements

For each fix item in Detailed Fix Plan, include:

- Priority
- Change target: exact file and exact function or section
- Problem summary in one or two sentences
- Exact fix plan
- Validation: exact commands and expected behavior
- Regression coverage: exact smoke test, integration test, or new test to add or update

Plan rules:

- Group related fixes only when they share one logic path.
- Prefer the smallest safe fix over broad refactors.
- Call out dependencies and anything that must happen first.
- If a finding is uncertain, say what one additional snippet is needed before Codex edits.
- Keep the plan concise, specific, and implementation-ready.
- Distinguish live behavior from proposals. If a recommended status, command, enum, or packet mode does not exist today, mark it as a proposed addition and include the propagation work required before it becomes a live system contract.
```
