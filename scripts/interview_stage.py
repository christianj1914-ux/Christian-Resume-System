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
    sections: tuple[str, ...]


@dataclass(frozen=True)
class InterviewerContext:
    name: str = ""
    title: str = ""
    stage_hint: str = ""
    recruiter_feedback: tuple[str, ...] = ()
    emphasized_terms: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    raw_text: str = ""


STANDARD_ALWAYS_SECTIONS = (
    "Firm-Specific Interview Profile",
    "Recruiter Feedback To Carry Into This Round",
    "Interviewer-Specific Prep",
    "How To Use This Guide",
    "Company Hypothesis",
    "Anti-Filler And Length Control",
    "Self-Assessment: Your Likely Interview Risk",
    "Top Recurring Answer Risks",
    "Tell Me About Yourself: Time Ladder",
)

STANDARD_STAGE_SECTIONS: dict[str, tuple[str, ...]] = {
    "hr_screen": (
        "Rehearsal Method",
        "HR Screen Prep",
        "Company Fit And Common Questions",
        "Application / Supplemental Questions To Be Ready For",
        "Question Bank Coverage",
        "Recent Interview Questions To Be Ready For",
        "Three Supported Proof Themes",
    ),
    "hiring_manager": (
        "Competency Decoder",
        "Consultative Selling Reframe",
        "JD Scorecard BLUF Answer Bank",
        "Lane Lead-In And Story Priority",
        "Story Anchor System",
        "Latest Positioning Diagnosis",
        "Ownership And Consultative Rewrites",
        "Best Example To Use First",
        "Hiring Manager Prep",
        "What They Are Really Asking",
        "Role Challenge Forecast",
        "Focused Story Bank",
        "Likely Interview Questions",
        "Answer Mechanics Reference",
        "Answer Operating System",
        "Anticipated Questions From Notes",
    ),
    "panel": (
        "Competency Decoder",
        "Answer Framework Hierarchy",
        "Delivery Watch-List",
        "Consultative Selling Reframe",
        "High-Stakes Prompt Bank",
        "Lane Lead-In And Story Priority",
        "Story Anchor System",
        "Latest Positioning Diagnosis",
        "Ownership And Consultative Rewrites",
        "Panel Prep",
        "Extended Story-Type Reference",
        "Primary Story Bank With Sample Answers",
        "Additional Behavioral Answers",
        "Story Selection Decision Table",
        "Likely Pushbacks And Short Answers",
        "Business-Context Interview Questions",
        "Answer Mechanics Reference",
        "Answer Operating System",
    ),
    "presentation": (
        "Answer Framework Hierarchy",
        "Delivery Watch-List",
        "High-Stakes Prompt Bank",
        "Executive Evaluation: Four Trust Questions",
        "Executive Presence Signals",
        "Executive Presence Corrections",
        "Presentation Prep",
        "What They Are Really Asking",
        "Likely Pushbacks And Short Answers",
        "Business-Context Interview Questions",
        "Answer Mechanics Reference",
        "Answer Operating System",
    ),
    "technical": (
        "Competency Decoder",
        "JD Scorecard BLUF Answer Bank",
        "Lane Lead-In And Story Priority",
        "Story Anchor System",
        "Best Example To Use First",
        "Technical Prep",
        "Focused Story Bank",
        "Answer Mechanics Reference",
        "Answer Operating System",
        "Business-Context Interview Questions",
        "KEYWORD ANSWER REFERENCE",
    ),
    "final": (
        "High-Stakes Prompt Bank",
        "Story Anchor System",
        "Latest Positioning Diagnosis",
        "Ownership And Consultative Rewrites",
        "Best Example To Use First",
        "Six Offer Blockers To Avoid",
        "Executive Evaluation: Four Trust Questions",
        "Executive Presence Signals",
        "Executive Presence Corrections",
        "Post-Round Intelligence To Prepare",
        "Debrief-To-Prep Overlay",
        "Recurring Delivery Habits",
        "Final-Round Conversion Strategy",
        "Company Fit And Common Questions",
        "Pre-Interview Reflection Prompts",
        "Recent Interview Questions To Be Ready For",
        "Three Supported Proof Themes",
        "Answer Mechanics Reference",
        "Answer Operating System",
        "Anticipated Questions From Notes",
        "QUESTIONS TO ASK AND HOW TO CLOSE",
        "Thank-You Note Strategy",
    ),
}

STATE_FARM_ALWAYS_SECTIONS = (
    "Workbook Promise",
    "Interview Process Map",
    "Answer Operating System",
    "Natural Storytelling System",
    "Questions, Rapport, And Closing Workbook",
    "Practice Plan",
    "Final Master Checklist",
)

STATE_FARM_STAGE_SECTIONS: dict[str, tuple[str, ...]] = {
    "hr_screen": ("Core Positioning Answer Lab", "On-Demand Video Workbook", "Mock Interview Dialogue Workbook"),
    "hiring_manager": (
        "State Farm Role Deconstruction",
        "Core Positioning Answer Lab",
        "Primary Story Workbook",
        "Master Q&A Workbook",
        "Leadership, Prioritization, And Pushback Workbook",
        "Deep Questions To Ask Bank",
    ),
    "panel": (
        "State Farm Role Deconstruction",
        "Primary Story Workbook",
        "Master Q&A Workbook",
        "Data Exercise Workbook",
        "Live Panel And Case Presentation Workbook",
        "Leadership, Prioritization, And Pushback Workbook",
        "Mock Interview Dialogue Workbook",
        "Deep Questions To Ask Bank",
    ),
    "presentation": (
        "State Farm Role Deconstruction",
        "Data Exercise Workbook",
        "Live Panel And Case Presentation Workbook",
    ),
    "technical": ("State Farm Role Deconstruction", "KEYWORD ANSWER REFERENCE", "Data Exercise Workbook"),
    "final": (
        "State Farm Role Deconstruction",
        "Core Positioning Answer Lab",
        "Primary Story Workbook",
        "Master Q&A Workbook",
        "Leadership, Prioritization, And Pushback Workbook",
        "Deep Questions To Ask Bank",
        "Post-Interview Strategy",
    ),
}

DYNAMIC_CHILD_INHERITANCE = (
    ("Story Deep Dive", "Primary Story Workbook"),
    ("Q&A category and question bars", "Master Q&A Workbook"),
    ("Exercise title bars", "Data Exercise Workbook"),
    ("Dialogue title bars", "Mock Interview Dialogue Workbook"),
    ("Question-bank title bars", "Deep Questions To Ask Bank"),
    ("Pushback question bars", "Leadership, Prioritization, And Pushback Workbook"),
    ("Story title bars", "Primary Story Bank With Sample Answers"),
)

COMPANION_ONLY_EXCLUSIONS = (
    "Know The Company",
    "Walk Me Through Your Background",
    "Recruiter Question Bank",
    "Recruiter Checklist",
    "Questions To Ask",
    "Keep These Three In View",
)

UNREACHABLE_STANDARD_EXCLUSIONS = ("Verified Company Research To Use", "Interpretive Interview Brief")

UNREACHABLE_STATE_FARM_EXCLUSIONS = (
    "State Farm Process Engineer Playbook",
    "Data Exercise And Case Study Strategy",
    "State Farm Master Q&A Bank",
    "Process Engineering Lens For State Farm",
    "Continuous Improvement And PM Operating System",
    "Interview Delivery Addendum From New Notes",
    "Video Interview Setup And Delivery",
    "Response Calibration And Short Answer Frameworks",
    "Why State Farm - Authenticity Warning",
    "5-7 Layers Of Drill-Down Readiness",
    "Coachability Signals In The Panel Round",
    "State Farm 2-Day Study System",
    "State Farm Story Skeletons And Spoken Models",
    "On-Demand Video Round Deep Dive",
    "Worked Data Exercise Example",
    "Pushback And Objection Handling",
    "First 90 Days - Process Engineer Plan",
    "Day-Of Protocol",
    "Questions, Rapport, And Tell Me More",
)

STAGE_PAGE_BUDGETS: dict[str, tuple[int, int] | None] = {
    "hr_screen": (8, 15),
    "hiring_manager": (15, 30),
    "panel": (15, 30),
    "presentation": (10, 20),
    "technical": (15, 30),
    "final": (10, 20),
    "all": None,
}

STANDARD_SECTION_REGISTRY = (
    "Firm-Specific Interview Profile", "Recruiter Feedback To Carry Into This Round", "Interviewer-Specific Prep",
    "How To Use This Guide", "Competency Decoder", "Answer Framework Hierarchy", "Rehearsal Method",
    "Delivery Watch-List", "Consultative Selling Reframe", "Company Hypothesis", "Anti-Filler And Length Control",
    "JD Scorecard BLUF Answer Bank", "High-Stakes Prompt Bank", "Lane Lead-In And Story Priority",
    "Story Anchor System", "Self-Assessment: Your Likely Interview Risk", "Top Recurring Answer Risks",
    "Latest Positioning Diagnosis", "Ownership And Consultative Rewrites", "Best Example To Use First",
    "Six Offer Blockers To Avoid", "Executive Evaluation: Four Trust Questions", "Executive Presence Signals",
    "Executive Presence Corrections", "Post-Round Intelligence To Prepare", "Debrief-To-Prep Overlay",
    "Recurring Delivery Habits", "Tell Me About Yourself: Time Ladder", "HR Screen Prep", "Hiring Manager Prep",
    "Panel Prep", "Presentation Prep", "Technical Prep", "Final-Round Conversion Strategy", "Focused Story Bank",
    "What They Are Really Asking", "Company Fit And Common Questions", "Pre-Interview Reflection Prompts",
    "Role Challenge Forecast", "Extended Story-Type Reference", "Primary Story Bank With Sample Answers",
    "Additional Behavioral Answers", "Likely Interview Questions", "Application / Supplemental Questions To Be Ready For",
    "Question Bank Coverage", "Recent Interview Questions To Be Ready For", "Three Supported Proof Themes",
    "Answer Mechanics Reference", "Answer Operating System", "Story Selection Decision Table",
    "Likely Pushbacks And Short Answers", "Anticipated Questions From Notes", "Business-Context Interview Questions",
    "QUESTIONS TO ASK AND HOW TO CLOSE", "Thank-You Note Strategy", "KEYWORD ANSWER REFERENCE",
)

STATE_FARM_SECTION_REGISTRY = (
    "Workbook Promise", "State Farm Role Deconstruction", "Interview Process Map", "Answer Operating System",
    "KEYWORD ANSWER REFERENCE", "Natural Storytelling System", "Core Positioning Answer Lab",
    "Primary Story Workbook", "Master Q&A Workbook", "Mock Interview Dialogue Workbook", "Data Exercise Workbook",
    "Live Panel And Case Presentation Workbook", "Leadership, Prioritization, And Pushback Workbook",
    "On-Demand Video Workbook", "Questions, Rapport, And Closing Workbook", "Deep Questions To Ask Bank",
    "Post-Interview Strategy", "Practice Plan", "Final Master Checklist",
)


def _normalized_title(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _assert_unique_titles(titles: tuple[str, ...], label: str) -> None:
    normalized = [_normalized_title(title) for title in titles]
    duplicates = sorted({title for title in normalized if normalized.count(title) > 1})
    if duplicates:
        raise ValueError(f"Duplicate normalized {label} section title(s): {', '.join(duplicates)}")


_assert_unique_titles(STANDARD_SECTION_REGISTRY, "standard")
_assert_unique_titles(STATE_FARM_SECTION_REGISTRY, "State Farm")
ALL_SECTION_TITLES = frozenset(_normalized_title(title) for title in (*STANDARD_SECTION_REGISTRY, *STATE_FARM_SECTION_REGISTRY))


def _profile_sections(stage_key: str) -> tuple[str, ...]:
    if stage_key == "all":
        return (*STANDARD_SECTION_REGISTRY, *STATE_FARM_SECTION_REGISTRY)
    return (
        *STANDARD_ALWAYS_SECTIONS,
        *STANDARD_STAGE_SECTIONS[stage_key],
        *STATE_FARM_ALWAYS_SECTIONS,
        *STATE_FARM_STAGE_SECTIONS[stage_key],
    )


def stage_includes(profile: StageProfile, title: str) -> bool:
    normalized = _normalized_title(title)
    if normalized not in ALL_SECTION_TITLES:
        raise ValueError(f"Unknown logical interview-guide section title: {title!r}")
    return profile.key == "all" or normalized in {_normalized_title(item) for item in profile.sections}


def standard_stage_includes(profile: StageProfile, title: str) -> bool:
    normalized = _normalized_title(title)
    registry = {_normalized_title(item) for item in STANDARD_SECTION_REGISTRY}
    if normalized not in registry:
        raise ValueError(f"Unknown logical standard interview-guide section title: {title!r}")
    selected = (*STANDARD_ALWAYS_SECTIONS, *STANDARD_STAGE_SECTIONS.get(profile.key, ()))
    return profile.key == "all" or normalized in {_normalized_title(item) for item in selected}


def state_farm_stage_includes(profile: StageProfile, title: str) -> bool:
    normalized = _normalized_title(title)
    registry = {_normalized_title(item) for item in STATE_FARM_SECTION_REGISTRY}
    if normalized not in registry:
        raise ValueError(f"Unknown logical State Farm interview-guide section title: {title!r}")
    selected = (*STATE_FARM_ALWAYS_SECTIONS, *STATE_FARM_STAGE_SECTIONS.get(profile.key, ()))
    return profile.key == "all" or normalized in {_normalized_title(item) for item in selected}


STAGE_PROFILES: dict[str, StageProfile] = {
    "hr_screen": StageProfile(
        key="hr_screen",
        label="HR Screen",
        filename_label="HR Screen",
        section_title="HR Screen Prep",
        focus_areas=("background", "motivation", "logistics", "salary", "recruiter questions"),
        sections=_profile_sections("hr_screen"),
    ),
    "hiring_manager": StageProfile(
        key="hiring_manager",
        label="Hiring Manager",
        filename_label="Hiring Manager",
        section_title="Hiring Manager Prep",
        focus_areas=("hero stories", "first 90 days", "role fit", "gap pushback"),
        sections=_profile_sections("hiring_manager"),
    ),
    "panel": StageProfile(
        key="panel",
        label="Panel",
        filename_label="Panel",
        section_title="Panel Prep",
        focus_areas=("collaboration breadth", "multiple angles", "stakeholder clarity", "cross-functional proof"),
        sections=_profile_sections("panel"),
    ),
    "presentation": StageProfile(
        key="presentation",
        label="Presentation",
        filename_label="Presentation",
        section_title="Presentation Prep",
        focus_areas=("case framing", "executive summary", "q&a defense", "objection handling"),
        sections=_profile_sections("presentation"),
    ),
    "technical": StageProfile(
        key="technical",
        label="Technical",
        filename_label="Technical",
        section_title="Technical Prep",
        focus_areas=("scenario reasoning", "system tradeoffs", "business framing", "validation"),
        sections=_profile_sections("technical"),
    ),
    "final": StageProfile(
        key="final",
        label="Final",
        filename_label="Final Round",
        section_title="Final-Round Prep",
        focus_areas=("executive presence", "motivation", "close", "compensation"),
        sections=_profile_sections("final"),
    ),
    "all": StageProfile(
        key="all",
        label="All Stages",
        filename_label="All Stages",
        section_title="All-Stages Prep",
        focus_areas=("shared core", "hr screen", "hiring manager", "panel", "presentation", "technical", "final"),
        sections=_profile_sections("all"),
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
