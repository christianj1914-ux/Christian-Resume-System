#!/usr/bin/env python3
"""Refresh helpers for the Claude Review upload bundle."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys

import workspace_health


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTEXT_DIR = PROJECT_ROOT / ".context"
CLAUDE_REVIEW_DIR = PROJECT_ROOT / "Claude Review"
DEFAULT_PACKET_MODES = ("broad", "resume", "interview", "federal", "claude-review")
PROMPT_KINDS = ("review", "plan")


@dataclass(frozen=True)
class ReviewBundleFile:
    source: Path
    dest_name: str


EXACT_COPY_FILES = (
    ReviewBundleFile(CONTEXT_DIR / "ARCHITECTURE_MAP.md", "ARCHITECTURE_MAP.md"),
    ReviewBundleFile(CONTEXT_DIR / "CODE_REVIEW_PACKET_GUIDE.md", "CODE_REVIEW_PACKET_GUIDE.md"),
    ReviewBundleFile(CONTEXT_DIR / "SCRIPT_INDEX.md", "SCRIPT_INDEX.md"),
    ReviewBundleFile(CONTEXT_DIR / "CLAUDE_REVIEW_TEMPLATE.md", "CLAUDE_REVIEW_TEMPLATE.md"),
    ReviewBundleFile(CONTEXT_DIR / "CLAUDE_TASK_TEMPLATE.md", "CLAUDE_TASK_TEMPLATE.md"),
)

CORE_GUIDANCE_FILES = (
    "CLAUDE.md",
    "RESUME_SYSTEM_BRIEF.md",
    "ARCHITECTURE_MAP.md",
    "RULES_FOR_CLAUDE.md",
    "CODE_REVIEW_PACKET_GUIDE.md",
    "SCRIPT_INDEX.md",
    "COMMON_CHANGE_AREAS.md",
)

SUPPORTING_TEMPLATE_FILES = (
    "CLAUDE_REVIEW_TEMPLATE.md",
    "CLAUDE_TASK_TEMPLATE.md",
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return path


def write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def bundle_manifest_path() -> Path:
    return CLAUDE_REVIEW_DIR / "BUNDLE_MANIFEST.json"


def replace_anchor_block(text: str, anchor_id: str, replacement: str, label: str) -> str:
    start = f"<!-- {anchor_id}:START -->"
    end = f"<!-- {anchor_id}:END -->"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), flags=re.S)
    if not pattern.search(text):
        raise ValueError(f"{label}: missing anchor '{anchor_id}'")
    return pattern.sub(replacement.rstrip() + "\n", text, count=1)


def source_hashes() -> dict[str, str]:
    paths = [
        PROJECT_ROOT / "CLAUDE.md",
        CONTEXT_DIR / "RESUME_SYSTEM_BRIEF.md",
        CONTEXT_DIR / "ARCHITECTURE_MAP.md",
        CONTEXT_DIR / "RULES_FOR_CLAUDE.md",
        CONTEXT_DIR / "CODE_REVIEW_PACKET_GUIDE.md",
        CONTEXT_DIR / "SCRIPT_INDEX.md",
        CONTEXT_DIR / "COMMON_CHANGE_AREAS.md",
        CONTEXT_DIR / "CLAUDE_REVIEW_TEMPLATE.md",
        CONTEXT_DIR / "CLAUDE_TASK_TEMPLATE.md",
    ]
    return {
        workspace_health.rel_path(path): workspace_health.sha256_path(path)
        for path in paths
        if path.exists()
    }


def build_bundle_manifest() -> dict[str, object]:
    snapshot = workspace_health.workspace_snapshot()
    return {
        "project_root": snapshot["project_root"],
        "generated_at": snapshot["generated_at"],
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "git_health": snapshot["git"],
        "workspace_health": snapshot,
        "source_hashes": source_hashes(),
    }


def build_review_claude_md() -> str:
    text = read_text(PROJECT_ROOT / "CLAUDE.md")
    addition = """
Keep these current workflow assumptions in mind during review:

- Standard private-sector resumes now follow a federal-style explicit-proof rule. Core experience should be visible in the summary and first bullets; do not assume the hiring manager will infer leadership, ownership, implementation depth, AI usage, or executive audience from weaker adjacent wording.
- For higher-level private-sector roles, bridge hard where truthful, but make leadership, manager/director-level audience, decision-making scope, and cross-functional ownership explicit when the source supports it.
- Federal runs now produce two Word documents by default: the exact two-page federal resume and a separate federal qualifications statement.
- Commercial filename audit states live today are PASS, BRIDGE, FAIL, and POOR. REVIEW is not a live audit state unless the code explicitly adds and propagates it.
- Federal outputs do not currently use the commercial fit-state filename system or tracker semantics.
- Standard commercial cover letters stay in the 80-170 word band by default, while the explicit long mode stays separate.
- Render warnings can be environmental. If the local DOCX-to-image converter is unavailable, builds may still succeed and only visual QA becomes manual.
"""
    return replace_anchor_block(
        text,
        "CLAUDE_REVIEW:CLAUDE_ASSUMPTIONS",
        addition,
        "Claude Review CLAUDE.md",
    )


def build_review_resume_system_brief() -> str:
    text = read_text(CONTEXT_DIR / "RESUME_SYSTEM_BRIEF.md")
    text = replace_anchor_block(
        text,
        "CLAUDE_REVIEW:BRIEF_EXPLICIT_STANDARD",
        """
The current tailoring standard is deliberately explicit:

- Standard private-sector resumes should behave more like federal submissions in the top third. Core experiences must be named directly in the summary and first bullets instead of being left implicit.
- Higher-level private-sector roles should surface leadership, ownership, executive audience, and decision-making scope explicitly where supported, and otherwise use the strongest truthful adjacent bridge.
- Federal runs should map posting requirements into visible resume bullets and a separate qualifications statement rather than expecting reviewers to infer fit.
""",
        "Claude Review RESUME_SYSTEM_BRIEF.md explicit standard block",
    )
    text = replace_anchor_block(
        text,
        "CLAUDE_REVIEW:BRIEF_RENDER_NOTE",
        "If a build prints a render warning because the local DOCX-to-image converter is unavailable, treat that as an environmental visual-QA limitation rather than an automatic content failure.",
        "Claude Review RESUME_SYSTEM_BRIEF.md render note",
    )
    text = replace_anchor_block(
        text,
        "CLAUDE_REVIEW:BRIEF_FEDERAL_INPUTS",
        """
Federal runs use:

- `jobs/federal_job_description.txt`
- `source/Christian_Estrada_Federal_Source.json`
""",
        "Claude Review RESUME_SYSTEM_BRIEF.md federal inputs block",
    )
    text = replace_anchor_block(
        text,
        "CLAUDE_REVIEW:BRIEF_FEDERAL_OUTPUT",
        "- Federal Qualifications Statement: generated alongside `scripts/build_federal_resume.py`",
        "Claude Review RESUME_SYSTEM_BRIEF.md federal output line",
    )
    return text


def build_review_rules_for_claude() -> str:
    text = read_text(CONTEXT_DIR / "RULES_FOR_CLAUDE.md")
    text = replace_anchor_block(
        text,
        "CLAUDE_REVIEW:RULES_FEDERAL_FORMATTING",
        "- Federal resume output stays at exactly two pages, and the federal qualifications statement is a separate Word document that should mirror supplemental federal questions or KSAs when they are present.",
        "Claude Review RULES_FOR_CLAUDE.md federal formatting line",
    )
    text = replace_anchor_block(
        text,
        "CLAUDE_REVIEW:RULES_TOP_THIRD",
        "Standard private-sector resumes should follow the same no-assumptions mindset as federal resumes in the top third. Important experience should be explicit, not merely inferable.",
        "Claude Review RULES_FOR_CLAUDE.md top-third rule",
    )
    text = replace_anchor_block(
        text,
        "CLAUDE_REVIEW:RULES_SUMMARY_SCOPE",
        "- make higher-level private-sector leadership, ownership, executive audience, and decision-making scope explicit when the source supports them",
        "Claude Review RULES_FOR_CLAUDE.md summary rule",
    )
    text = replace_anchor_block(
        text,
        "CLAUDE_REVIEW:RULES_BRIDGE_HARD",
        "Protect bridge-hard bullets that carry explicit AI usage, technical scoping, testing, delivery ownership, executive advisory, or leadership scope when the target role depends on those areas.",
        "Claude Review RULES_FOR_CLAUDE.md bridge-hard rule",
    )
    text = replace_anchor_block(
        text,
        "CLAUDE_REVIEW:RULES_REVIEW_OUTPUT",
        """
If document-render warnings appear, separate content or logic defects from environmental render limitations. Missing local DOCX-to-image tooling should not be treated as a resume-writing failure.

If you recommend a new status, command, enum, packet mode, or public contract that does not exist today, label it as a proposal and name the consumers that would need propagation before treating it as live behavior.
""",
        "Claude Review RULES_FOR_CLAUDE.md render distinction rule",
    )
    return text


def build_review_common_change_areas() -> str:
    text = read_text(CONTEXT_DIR / "COMMON_CHANGE_AREAS.md")
    text = replace_anchor_block(
        text,
        "CLAUDE_REVIEW:COMMON_SUMMARY_RISKS",
        """
- private-sector core experience left implicit instead of explicit in the top third
- higher-level roles missing visible leadership, ownership, executive audience, or decision-making scope
""",
        "Claude Review COMMON_CHANGE_AREAS.md summary risks",
    )
    text = replace_anchor_block(
        text,
        "CLAUDE_REVIEW:COMMON_BULLET_RISKS",
        "- trimming bullets that carry explicit AI usage, leadership scope, executive audience, technical scoping, testing, or delivery ownership",
        "Claude Review COMMON_CHANGE_AREAS.md bullet selection risks",
    )
    text = replace_anchor_block(
        text,
        "CLAUDE_REVIEW:COMMON_FEDERAL_BLOCK",
        """
Review note:

- Standard private-sector bullet selection now intentionally protects explicit-proof bullets in the same spirit as the federal workflow. If a change weakens that protection, treat it as a high-risk regression.

## Federal Resume and Qualifications Statement

Inspect:

- `scripts/build_federal_resume.py`: federal summary builders, requirement audit logic, bullet scoring and selection, qualifications-statement generation, layout selection, and federal fit checks
- `source/Christian_Estrada_Federal_Source.json`: supported federal source truth

Common risks:

- federal resume leaving selective-factor or specialized-experience language implicit
- federal bullet scoring surfacing lower-value bullets while burying stronger AI, analytics, testing, deployment, or executive-scope evidence
- qualifications statement drifting away from the same evidence map as the resume or missing supplemental-question/KSA structure
- body text dropping below 10pt or the federal resume exceeding two pages
""",
        "Claude Review COMMON_CHANGE_AREAS.md federal review block",
    )
    text = replace_anchor_block(
        text,
        "CLAUDE_REVIEW:COMMON_RENDER_FALLBACK",
        "- treating missing local render tooling as a content failure instead of a manual visual-QA fallback",
        "Claude Review COMMON_CHANGE_AREAS.md render fallback risk",
    )
    text = replace_anchor_block(
        text,
        "CLAUDE_REVIEW:COMMON_COVER_RISKS",
        """
- short standard cover letters dropping the communication or cross-functional signal when they compress to three paragraphs
- review tooling or Claude packets describing proposed states such as REVIEW as if they were already live system behavior
""",
        "Claude Review COMMON_CHANGE_AREAS.md cover compression risk",
    )
    return text


def build_upload_guide() -> str:
    broad_files = (
        "TEMP_FOR_REVIEW.md",
        "TEMP_CLAUDE_REVIEW_PROMPT_BROAD.txt",
        "TEMP_CLAUDE_PLAN_PROMPT_BROAD.txt",
    )
    resume_files = (
        "TEMP_FOR_REVIEW_RESUME.md",
        "TEMP_CLAUDE_REVIEW_PROMPT_RESUME.txt",
        "TEMP_CLAUDE_PLAN_PROMPT_RESUME.txt",
    )
    interview_files = (
        "TEMP_FOR_REVIEW_INTERVIEW.md",
        "TEMP_CLAUDE_REVIEW_PROMPT_INTERVIEW.txt",
        "TEMP_CLAUDE_PLAN_PROMPT_INTERVIEW.txt",
    )
    federal_files = (
        "TEMP_FOR_REVIEW_FEDERAL.md",
        "TEMP_CLAUDE_REVIEW_PROMPT_FEDERAL.txt",
        "TEMP_CLAUDE_PLAN_PROMPT_FEDERAL.txt",
    )
    review_system_files = (
        "TEMP_FOR_REVIEW_CLAUDE_REVIEW.md",
        "TEMP_CLAUDE_REVIEW_PROMPT_CLAUDE_REVIEW.txt",
        "TEMP_CLAUDE_PLAN_PROMPT_CLAUDE_REVIEW.txt",
    )
    core_list = "\n".join(f"  `{name}`" for name in CORE_GUIDANCE_FILES)
    broad_list = "\n".join(f"  `{name}`" for name in broad_files)
    resume_list = "\n".join(f"  `{name}`" for name in resume_files)
    interview_list = "\n".join(f"  `{name}`" for name in interview_files)
    federal_list = "\n".join(f"  `{name}`" for name in federal_files)
    review_system_list = "\n".join(f"  `{name}`" for name in review_system_files)
    template_list = "\n".join(f"- `{name}`" for name in SUPPORTING_TEMPLATE_FILES)
    return f"""# Claude Review Upload Guide

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
{core_list}

- Broad review:
  all core guidance files
{broad_list}

- Resume logic review:
  all core guidance files
{resume_list}

- Interview review:
  all core guidance files
{interview_list}

- Federal review:
  all core guidance files
{federal_list}

- Claude review tooling review:
  all core guidance files
{review_system_list}

Supporting templates:

{template_list}

Authoritative current review artifacts:

- the latest `TEMP_FOR_REVIEW*.md` packet files
- the matching `TEMP_FOR_REVIEW*.manifest.json` manifest files
- `BUNDLE_MANIFEST.json` for workspace provenance and source hashes

Archived notes in `Claude Review/history/` are supplemental history only. Do not treat them as the default upload set.
"""


def refresh_support_files() -> list[Path]:
    written: list[Path] = []
    for item in EXACT_COPY_FILES:
        written.append(write_text(CLAUDE_REVIEW_DIR / item.dest_name, read_text(item.source)))
    generated = {
        "CLAUDE.md": build_review_claude_md(),
        "RESUME_SYSTEM_BRIEF.md": build_review_resume_system_brief(),
        "RULES_FOR_CLAUDE.md": build_review_rules_for_claude(),
        "COMMON_CHANGE_AREAS.md": build_review_common_change_areas(),
        "UPLOAD_GUIDE.md": build_upload_guide(),
    }
    for name, text in generated.items():
        written.append(write_text(CLAUDE_REVIEW_DIR / name, text))
    written.append(write_json(bundle_manifest_path(), build_bundle_manifest()))
    return written
