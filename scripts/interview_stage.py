#!/usr/bin/env python3
"""Interview-stage resolution and interviewer-context parsing helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STAGE_PATH = PROJECT_ROOT / "jobs" / "interview_stage.txt"
DEFAULT_INTERVIEWER_CONTEXT_PATH = PROJECT_ROOT / "jobs" / "interviewer_context.txt"


@dataclass(frozen=True)
class StageProfile:
    key: str
    label: str
    filename_label: str
    section_title: str
    focus_areas: tuple[str, ...]


@dataclass(frozen=True)
class InterviewerContext:
    name: str = ""
    title: str = ""
    stage_hint: str = ""
    recruiter_feedback: tuple[str, ...] = ()
    emphasized_terms: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    raw_text: str = ""


STAGE_PROFILES: dict[str, StageProfile] = {
    "hr_screen": StageProfile(
        key="hr_screen",
        label="HR Screen",
        filename_label="HR Screen",
        section_title="HR Screen Prep",
        focus_areas=("background", "motivation", "logistics", "salary", "recruiter questions"),
    ),
    "hiring_manager": StageProfile(
        key="hiring_manager",
        label="Hiring Manager",
        filename_label="Hiring Manager",
        section_title="Hiring Manager Prep",
        focus_areas=("hero stories", "first 90 days", "role fit", "gap pushback"),
    ),
    "panel": StageProfile(
        key="panel",
        label="Panel",
        filename_label="Panel",
        section_title="Panel Prep",
        focus_areas=("collaboration breadth", "multiple angles", "stakeholder clarity", "cross-functional proof"),
    ),
    "presentation": StageProfile(
        key="presentation",
        label="Presentation",
        filename_label="Presentation",
        section_title="Presentation Prep",
        focus_areas=("case framing", "executive summary", "q&a defense", "objection handling"),
    ),
    "technical": StageProfile(
        key="technical",
        label="Technical",
        filename_label="Technical",
        section_title="Technical Prep",
        focus_areas=("scenario reasoning", "system tradeoffs", "business framing", "validation"),
    ),
    "final": StageProfile(
        key="final",
        label="Final",
        filename_label="Final Round",
        section_title="Final-Round Prep",
        focus_areas=("executive presence", "motivation", "close", "compensation"),
    ),
    "all": StageProfile(
        key="all",
        label="All Stages",
        filename_label="All Stages",
        section_title="All-Stages Prep",
        focus_areas=("shared core", "hr screen", "hiring manager", "panel", "presentation", "technical", "final"),
    ),
}


STAGE_ALIASES = {
    "hr": "hr_screen",
    "hr_screen": "hr_screen",
    "screen": "hr_screen",
    "recruiter": "hr_screen",
    "recruiter_screen": "hr_screen",
    "hiring_manager": "hiring_manager",
    "manager": "hiring_manager",
    "hm": "hiring_manager",
    "panel": "panel",
    "presentation": "presentation",
    "case": "presentation",
    "technical": "technical",
    "tech": "technical",
    "final": "final",
    "final_round": "final",
    "all": "all",
}


def _normalize_stage_key(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    return STAGE_ALIASES.get(normalized, normalized)


def _read_optional_text(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig").strip()


def _split_terms(value: str) -> tuple[str, ...]:
    terms = [re.sub(r"\s+", " ", part).strip() for part in re.split(r"[;,]", value) if part.strip()]
    deduped: list[str] = []
    seen: set[str] = set()
    for term in terms:
        key = term.casefold()
        if key not in seen:
            deduped.append(term)
            seen.add(key)
    return tuple(deduped)


def parse_interviewer_context(text: str) -> InterviewerContext:
    cleaned = text.strip()
    if not cleaned:
        return InterviewerContext(raw_text="")

    name = ""
    title = ""
    stage_hint = ""
    recruiter_feedback: list[str] = []
    emphasized_terms: list[str] = []
    notes: list[str] = []

    bare_line_used = False
    for raw_line in cleaned.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        labeled = re.match(r"^(?P<label>[A-Za-z][A-Za-z /_-]+):\s*(?P<value>.+)$", line)
        if labeled:
            label = labeled.group("label").strip().lower()
            value = labeled.group("value").strip()
            if label in {"name", "interviewer", "interviewer name"}:
                name = value
                continue
            if label in {"title", "interviewer title", "role"}:
                title = value
                continue
            if label == "stage":
                stage_hint = value
                continue
            if label in {"recruiter feedback", "feedback", "recruiter note", "recruiter notes"}:
                recruiter_feedback.extend(_split_terms(value) or (value,))
                continue
            if label in {"emphasize", "emphasized terms", "focus", "focus terms", "keywords"}:
                emphasized_terms.extend(_split_terms(value))
                continue
            notes.append(line)
            continue
        if not bare_line_used and "," in line:
            left, right = [part.strip() for part in line.split(",", 1)]
            if left and right:
                name = name or left
                title = title or right
                bare_line_used = True
                continue
        notes.append(line)

    return InterviewerContext(
        name=name,
        title=title,
        stage_hint=stage_hint,
        recruiter_feedback=tuple(dict.fromkeys(recruiter_feedback)),
        emphasized_terms=tuple(dict.fromkeys(emphasized_terms)),
        notes=tuple(notes),
        raw_text=cleaned,
    )


def read_interviewer_context(path: Path | None = None) -> InterviewerContext:
    return parse_interviewer_context(_read_optional_text(path or DEFAULT_INTERVIEWER_CONTEXT_PATH))


def resolve_stage(
    cli_stage: str = "",
    interviewer_context: InterviewerContext | None = None,
    stage_path: Path | None = None,
) -> StageProfile:
    candidates = (
        cli_stage.strip(),
        (interviewer_context.stage_hint if interviewer_context else "").strip(),
        _read_optional_text(stage_path or DEFAULT_STAGE_PATH),
    )
    raw_stage = next((candidate for candidate in candidates if candidate), "all")
    normalized = _normalize_stage_key(raw_stage)
    if normalized not in STAGE_PROFILES:
        supported = ", ".join(STAGE_PROFILES)
        raise ValueError(f"Unknown interview stage '{raw_stage}'. Expected one of: {supported}.")
    return STAGE_PROFILES[normalized]


def stage_filename_suffix(stage: str | StageProfile) -> str:
    profile = stage if isinstance(stage, StageProfile) else STAGE_PROFILES[_normalize_stage_key(stage)]
    if profile.key == "all":
        return ""
    return f" ({profile.filename_label})"
