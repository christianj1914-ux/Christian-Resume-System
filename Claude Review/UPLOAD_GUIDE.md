# Claude Review Upload Guide

Use this folder as the single upload location for Claude guidance and current review artifacts.

Quick refresh:

- `python tasks.py claude-refresh`
- `python tasks.py claude-refresh --skip-checks`
- double-click `run_claude_refresh.bat` for the simple yes or no version

The packet and prompt generators also write here by default:

- `python tasks.py claude-packet --mode broad`
- `python tasks.py claude-packet --mode resume`
- `python tasks.py claude-packet --mode interview`
- `python tasks.py claude-prompt review --packet-mode broad`
- `python tasks.py claude-prompt plan --packet-mode broad`
- `python tasks.py claude-prompt review --packet-mode resume`
- `python tasks.py claude-prompt plan --packet-mode resume`
- `python tasks.py claude-prompt review --packet-mode interview`
- `python tasks.py claude-prompt plan --packet-mode interview`

Recommended sets:

- Core guidance only:
  `CLAUDE.md`
  `RESUME_SYSTEM_BRIEF.md`
  `ARCHITECTURE_MAP.md`
  `RULES_FOR_CLAUDE.md`
  `CODE_REVIEW_PACKET_GUIDE.md`
  `SCRIPT_INDEX.md`
  `COMMON_CHANGE_AREAS.md`

- Broad review:
  all core guidance files
  `TEMP_FOR_REVIEW.md`
  `TEMP_CLAUDE_REVIEW_PROMPT_BROAD.txt`
  `TEMP_CLAUDE_PLAN_PROMPT_BROAD.txt`

- Resume logic review:
  all core guidance files
  `TEMP_FOR_REVIEW_RESUME.md`
  `TEMP_CLAUDE_REVIEW_PROMPT_RESUME.txt`
  `TEMP_CLAUDE_PLAN_PROMPT_RESUME.txt`

- Interview review:
  all core guidance files
  `TEMP_FOR_REVIEW_INTERVIEW.md`
  `TEMP_CLAUDE_REVIEW_PROMPT_INTERVIEW.txt`
  `TEMP_CLAUDE_PLAN_PROMPT_INTERVIEW.txt`

- Federal review:
  all core guidance files
  `TEMP_FOR_REVIEW_FEDERAL.md`
  `TEMP_CLAUDE_REVIEW_PROMPT_FEDERAL.txt`
  `TEMP_CLAUDE_PLAN_PROMPT_FEDERAL.txt`

- Claude review tooling review:
  all core guidance files
  `TEMP_FOR_REVIEW_CLAUDE_REVIEW.md`
  `TEMP_CLAUDE_REVIEW_PROMPT_CLAUDE_REVIEW.txt`
  `TEMP_CLAUDE_PLAN_PROMPT_CLAUDE_REVIEW.txt`

Supporting templates:

- `CLAUDE_REVIEW_TEMPLATE.md`
- `CLAUDE_TASK_TEMPLATE.md`
- `CLAUDE_PROGRESS_CHECK_TEMPLATE.md`

Authoritative current review artifacts:

- the latest `TEMP_FOR_REVIEW*.md` packet files
- the matching `TEMP_FOR_REVIEW*.manifest.json` manifest files
- `BUNDLE_MANIFEST.json` for workspace provenance and source hashes

Archived notes in `Claude Review/history/` are supplemental history only. Do not treat them as the default upload set.
