"""Shared self-inventory and interview answer helpers."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SELF_INVENTORY_PATH = PROJECT_ROOT / "source" / "self_inventory.json"
DEFAULT_PREP_LOG_PATH = PROJECT_ROOT / "scratch" / "prep_log.csv"
DEFAULT_PREP_FOCUS_PATH = PROJECT_ROOT / "scratch" / "prep_focus.json"
DEFAULT_INVENTORY_CANDIDATES_PATH = PROJECT_ROOT / "scratch" / "inventory_candidates.json"
DAILY_PREP_MODES = ("job_search", "on_the_job")
DAILY_PREP_LOG_COLUMNS = ("date", "mode", "reps_done", "hedge_count", "self_rated_clarity")
DEBRIEF_FEEDBACK_VERSION = "2026-07-26-phase6-v1"
DAILY_REP_TYPES = ("self_inventory", "delivery", "story", "scorecard", "weakness")
NEAR_TERM_CAREER_ROLES = (
    "Implementation Consultant",
    "Solutions Consultant",
    "Business Systems Analyst",
    "Technical Program Manager",
)
STRETCH_CAREER_ROLES = ("Business Architect / AI Evangelist",)
STUDY_ROOT = "Study"
STUDY_FLASHCARDS_DIR = f"{STUDY_ROOT}/Flashcards"
STUDY_GUIDES_DIR = f"{STUDY_ROOT}/Guides"
STUDY_LEARNING_PATH_REFERENCE = f"{STUDY_GUIDES_DIR}/IT_Learning_Path_and_Schedule.docx"


def _study_flashcard_reference(track: str) -> str:
    return f"{STUDY_FLASHCARDS_DIR}/IT_Flashcards_{track}.txt"


STUDY_TRACK_REFERENCES = (
    STUDY_LEARNING_PATH_REFERENCE,
    _study_flashcard_reference("AI"),
    _study_flashcard_reference("AIAdoption"),
    _study_flashcard_reference("AIEngineeringMLOps"),
    _study_flashcard_reference("AWS"),
    _study_flashcard_reference("BusinessArchitecture"),
    _study_flashcard_reference("DataAnalyticsBI"),
    _study_flashcard_reference("Foundations"),
    _study_flashcard_reference("PMP"),
    _study_flashcard_reference("SecurityPlus"),
)
QUESTION_THEME_TRACKS: dict[str, tuple[str, ...]] = {
    "parallel_project_governance": (_study_flashcard_reference("PMP"),),
    "complex_project_leadership": (_study_flashcard_reference("PMP"),),
    "ambiguity_delivery": (_study_flashcard_reference("PMP"),),
    "ai_passion": (_study_flashcard_reference("AI"), _study_flashcard_reference("AIAdoption")),
    "saas_ai_company_experience": (_study_flashcard_reference("AIAdoption"),),
    "executive_reporting_trust": (
        _study_flashcard_reference("DataAnalyticsBI"),
        _study_flashcard_reference("BusinessArchitecture"),
    ),
    "implementation_success": (_study_flashcard_reference("DataAnalyticsBI"),),
}


def question_theme_tracks(category: str) -> tuple[str, ...]:
    return QUESTION_THEME_TRACKS.get(category, ())


UNSUPPORTED_CREDENTIAL_PATTERNS = (
    re.compile(r"\bSix Sigma certified\b", re.I),
    re.compile(r"\bLean Six Sigma certified\b", re.I),
    re.compile(r"\bTOGAF certified\b", re.I),
    re.compile(r"\bcertified TOGAF\b", re.I),
    re.compile(r"\bdeep (?:RAG|vector|AI engineering|agentic protocol)", re.I),
    re.compile(r"\bdirect hardware ownership\b", re.I),
)
UNSUPPORTED_ADVISORY_REPLACEMENTS = (
    (re.compile(r"\bLean Six Sigma certified\b", re.I), "formal Lean Six Sigma status"),
    (re.compile(r"\bSix Sigma certified\b", re.I), "formal Six Sigma status"),
    (re.compile(r"\bTOGAF certified\b", re.I), "formal TOGAF status"),
    (re.compile(r"\bcertified TOGAF\b", re.I), "formal TOGAF status"),
    (re.compile(r"\bdeep (?:RAG|vector|AI engineering|agentic protocol)", re.I), "advanced AI technical depth"),
    (re.compile(r"\bdirect hardware ownership\b", re.I), "hardware ownership depth"),
)


@dataclass(frozen=True)
class SelfInventory:
    status: str
    status_note: str
    strengths: tuple[dict[str, Any], ...]
    weaknesses: tuple[dict[str, Any], ...]
    signature_stories: tuple[dict[str, Any], ...]
    motivation: str
    values: tuple[str, ...]
    target_roles: tuple[str, ...]
    non_negotiables: tuple[str, ...]


@dataclass(frozen=True)
class ScorecardEntry:
    competency: str
    trigger_phrases: tuple[str, ...]
    framework_words: tuple[str, ...]
    mapped_story: str = ""
    story_reference: str = ""
    support_level: str = "gap"
    gap_pivot: str = ""


@dataclass(frozen=True)
class BlufAnswer:
    prompt: str
    answer: str
    example_story: str = ""
    result: str = ""
    relevance: str = ""
    is_gap: bool = False


@dataclass(frozen=True)
class DailyPrepRep:
    rep_type: str
    title: str
    duration_minutes: int
    instructions: tuple[str, ...]
    proof_reference: str = ""
    weight: str = "standard"


@dataclass(frozen=True)
class DailyPrepPlan:
    mode: str
    plan_date: date
    emphasis: str
    reps: tuple[DailyPrepRep, ...]
    completion_prompt: str
    question_bank_checklist: tuple[str, ...] = ()


@dataclass(frozen=True)
class CareerPlanGap:
    label: str
    safe_description: str
    track_references: tuple[str, ...]
    action: str


@dataclass(frozen=True)
class CareerPlanMode:
    name: str
    focus: str
    actions: tuple[str, ...]


@dataclass(frozen=True)
class CareerOperatingPlan:
    plan_date: date
    near_term_roles: tuple[str, ...]
    stretch_roles: tuple[str, ...]
    development_gaps: tuple[CareerPlanGap, ...]
    stretch_role_gaps: tuple[CareerPlanGap, ...]
    modes: tuple[CareerPlanMode, ...]
    checkpoints: tuple[str, ...]
    study_references: tuple[str, ...]


COMPETENCY_FRAMEWORKS: dict[str, tuple[str, ...]] = {
    "Discovery": ("current-state mapping", "requirements elicitation", "FRD", "SOW", "gap analysis"),
    "Requirements translation": ("FRD", "SOW", "business process modeling", "technical scoping", "written confirmation"),
    "Stakeholder alignment": ("RACI", "executive readout", "written confirmation", "escalation path", "decision owner"),
    "Customer relationship building": ("trusted advisor", "expectation management", "written confirmation", "FRD", "executive cadence", "escalation path"),
    "Project delivery": ("Agile", "Scrum", "backlog", "milestone", "risk register", "change control"),
    "Process improvement": ("DMAIC", "PDCA", "5 Whys", "root-cause analysis", "value stream mapping", "Lean Six Sigma"),
    "Data and analytics": ("KPI", "dashboard", "data quality", "ETL validation", "Power BI", "SQL"),
    "Implementation and integration": ("data migration", "UAT", "cutover", "ODBC", "API integration", "hypercare"),
    "Adaptability / fast ramp": ("learning agility", "ramp-up", "comfort with ambiguity", "map-to-fundamentals", "cross-training"),
    "AI adoption": ("adoption metrics", "enablement", "champions network", "literacy workshops", "prompt engineering"),
    "Technical fluency gap": ("working knowledge", "ramp plan", "architecture questions", "validation path", "learning track"),
}


COMPETENCY_TAXONOMY: dict[str, dict[str, tuple[str, ...]]] = {
    "Discovery": {
        "triggers": ("discovery", "discover", "requirements elicitation", "current state", "current-state", "workshop", "customer needs", "consultative"),
        "stories": ("Windows-95 discovery", "CEO escalation"),
    },
    "Requirements translation": {
        "triggers": ("requirements", "translate", "scope", "sow", "frd", "functional requirements", "business requirements", "technical requirements"),
        "stories": ("Windows-95 discovery", "CEO escalation"),
    },
    "Stakeholder alignment": {
        "triggers": ("stakeholder", "cross-functional", "executive", "alignment", "influence", "vendor", "finance", "leadership"),
        "stories": ("EFT/ACH cross-functional replacement", "CEO escalation"),
    },
    "Customer relationship building": {
        "triggers": (
            "relationship building",
            "build relationships",
            "relationships",
            "stakeholders",
            "trusted advisor",
            "customer-facing",
            "coach clients",
            "manage expectations",
            "expectation management",
        ),
        "stories": ("CEO escalation",),
    },
    "Project delivery": {
        "triggers": ("project", "program", "delivery", "milestone", "timeline", "risk", "scrum", "agile", "backlog", "change control"),
        "stories": ("EFT/ACH cross-functional replacement", "East West fast ramp"),
    },
    "Process improvement": {
        "triggers": ("process improvement", "continuous improvement", "lean", "six sigma", "root cause", "5 whys", "dmaic", "operational excellence", "workflow optimization"),
        "stories": ("Inventory automation / DMAIC",),
    },
    "Data and analytics": {
        "triggers": ("analytics", "data", "dashboard", "kpi", "reporting", "power bi", "sql", "etl", "metrics", "data quality"),
        "stories": ("Inventory automation / DMAIC",),
    },
    "Implementation and integration": {
        "triggers": ("implementation", "integration", "data migration", "uat", "cutover", "go-live", "hypercare", "api", "odbc", "configuration"),
        "stories": ("Windows-95 discovery", "EFT/ACH cross-functional replacement"),
    },
    "Adaptability / fast ramp": {
        "triggers": ("fast-paced", "ambiguity", "ambiguous", "learn quickly", "new domains", "wear many hats", "ramp", "ramp-up"),
        "stories": ("East West fast ramp",),
    },
    "AI adoption": {
        "triggers": ("ai adoption", "artificial intelligence", "ai", "llm", "copilot", "prompt", "enablement", "evangelist"),
        "stories": ("Inventory automation / DMAIC", "East West fast ramp"),
    },
    "Technical fluency gap": {
        "triggers": ("rag", "vector", "togaf", "hardware", "cloud", "aws", "security+", "protocol", "architecture certification", "tableau"),
        "stories": (),
    },
}


def _as_string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _as_mapping_tuple(value: object) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list):
        return ()
    return tuple(dict(item) for item in value if isinstance(item, Mapping))


def load_self_inventory(path: Path = SELF_INVENTORY_PATH) -> SelfInventory:
    """Load Christian's provisional self-inventory source."""

    with path.open(encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if not isinstance(payload, Mapping):
        raise ValueError(f"Self-inventory root must be a JSON object: {path}")
    return SelfInventory(
        status=str(payload.get("status", "")).strip(),
        status_note=str(payload.get("status_note", "")).strip(),
        strengths=_as_mapping_tuple(payload.get("strengths")),
        weaknesses=_as_mapping_tuple(payload.get("weaknesses")),
        signature_stories=_as_mapping_tuple(payload.get("signature_stories")),
        motivation=str(payload.get("motivation", "")).strip(),
        values=_as_string_tuple(payload.get("values")),
        target_roles=_as_string_tuple(payload.get("target_roles")),
        non_negotiables=_as_string_tuple(payload.get("non_negotiables")),
    )


def validate_self_inventory(inventory: SelfInventory) -> list[str]:
    """Return validation issues. An empty list means the inventory is usable."""

    issues: list[str] = []
    if inventory.status.lower() != "provisional":
        issues.append("status must be provisional until Christian confirms the self-picture")
    if len(inventory.strengths) != 3:
        issues.append(f"expected exactly 3 strengths; found {len(inventory.strengths)}")
    if len(inventory.weaknesses) != 3:
        issues.append(f"expected exactly 3 weaknesses; found {len(inventory.weaknesses)}")
    strength_fields = ("name", "one_line", "interview_safe", "evidence_stories", "how_it_shows_up", "keywords")
    for index, strength in enumerate(inventory.strengths, start=1):
        for field in strength_fields:
            if not strength.get(field):
                issues.append(f"strength {index} missing {field}")
        for field in ("evidence_stories", "keywords"):
            if not isinstance(strength.get(field), list) or not strength.get(field):
                issues.append(f"strength {index} field {field} must be a non-empty list")
    weakness_fields = ("honest_name", "interview_safe", "improvement_action", "improvement_spoken", "status")
    for index, weakness in enumerate(inventory.weaknesses, start=1):
        for field in weakness_fields:
            if not weakness.get(field):
                issues.append(f"weakness {index} missing {field}")
    if len(inventory.signature_stories) != 5:
        issues.append(f"expected exactly 5 signature stories; found {len(inventory.signature_stories)}")
    for index, story in enumerate(inventory.signature_stories, start=1):
        for field in ("name", "summary", "spoken_reference", "result", "competencies"):
            if not story.get(field):
                issues.append(f"signature story {index} missing {field}")
    if not inventory.motivation:
        issues.append("motivation is required")
    if not inventory.values:
        issues.append("values must include at least one item")
    if not inventory.target_roles:
        issues.append("target_roles must include at least one item")
    if not inventory.non_negotiables:
        issues.append("non_negotiables must include at least one item")
    return issues


def _join_sentence(*parts: str) -> str:
    cleaned = [part.strip().rstrip(".") for part in parts if part and part.strip()]
    joined = ". ".join(cleaned).strip()
    if not joined:
        return ""
    return joined if joined.endswith((".", "?", "!")) else joined + "."


def _first_list_item(value: object) -> str:
    if isinstance(value, list) and value:
        return str(value[0]).strip()
    return ""


def _story_lookup(inventory: SelfInventory) -> dict[str, dict[str, Any]]:
    return {str(story.get("name", "")).strip().lower(): story for story in inventory.signature_stories}


def _story_by_name(inventory: SelfInventory, name: str) -> dict[str, Any] | None:
    return _story_lookup(inventory).get(name.strip().lower())


def _spoken_story_reference(inventory: SelfInventory, story_name: str) -> str:
    story = _story_by_name(inventory, story_name)
    if not story:
        return ""
    return str(story.get("spoken_reference", "")).strip()


def _story_result(inventory: SelfInventory, story_name: str) -> str:
    story = _story_by_name(inventory, story_name)
    if not story:
        return ""
    return str(story.get("result", "")).strip()


def _sentence_start_reference(reference: str) -> str:
    """Capitalize only the authored reference when it starts its own sentence."""

    stripped = reference.strip()
    if not stripped:
        return ""
    return stripped[:1].upper() + stripped[1:]


def _honest_names(inventory: SelfInventory) -> tuple[str, ...]:
    return tuple(str(item.get("honest_name", "")).strip() for item in inventory.weaknesses if str(item.get("honest_name", "")).strip())


def assert_no_honest_name_leak(text: str, inventory: SelfInventory) -> None:
    lowered = text.lower()
    leaks = [name for name in _honest_names(inventory) if name.lower() in lowered]
    if leaks:
        raise ValueError(f"generated text leaked self-development-only weakness labels: {', '.join(leaks)}")


def assert_no_unsupported_credentials(text: str) -> None:
    matches = [pattern.pattern for pattern in UNSUPPORTED_CREDENTIAL_PATTERNS if pattern.search(text)]
    if matches:
        raise ValueError(f"generated text contains unsupported credential or ownership language: {matches}")


def assert_safe_generated_text(text: str, inventory: SelfInventory) -> None:
    assert_no_honest_name_leak(text, inventory)
    assert_no_unsupported_credentials(text)


def assert_clean_bluf_answer_text(text: str) -> None:
    doubled_patterns = (
        r"\bis\s+for example\b",
        r"\bexample\s+is\s+for example\b",
        r"\bexample,\s+for example\b",
        r"\bfor example,\s+for example\b",
    )
    for pattern in doubled_patterns:
        if re.search(pattern, text, re.I):
            raise ValueError(f"generated BLUF answer contains doubled example phrasing: {pattern}")
    if ". for example" in text:
        raise ValueError("generated BLUF answer contains lowercase example after a sentence break")
    if re.search(r"(?<!\bI\s)(?<!\bhe\s)(?<!\bshe\s)(?<!\bthey\s)(?<!\bwe\s)(?<!\bit\s)\bGot up to speed\b", text):
        raise ValueError("generated BLUF answer contains a subjectless fast-ramp fragment")


def build_strengths_answer(inventory: SelfInventory, job_description: str = "", resume_text: str = "") -> str:
    """Build a spoken BLUF answer for the literal three-strengths question."""

    issues = validate_self_inventory(inventory)
    if issues:
        raise ValueError("self-inventory is invalid: " + "; ".join(issues))
    lead = "My three biggest strengths are translating between business and technical teams, ramping quickly on unfamiliar systems, and aligning cross-functional groups without formal authority."
    proof_lines = []
    for strength in inventory.strengths:
        story = _first_list_item(strength.get("evidence_stories"))
        reference = _spoken_story_reference(inventory, story)
        proof = f"{str(strength['interview_safe']).rstrip('.')}, {reference}." if reference else str(strength["interview_safe"])
        proof_lines.append(proof)
    answer = _join_sentence(lead, *proof_lines, "Together, those strengths help me turn ambiguous system and business problems into work people can actually use.")
    assert_safe_generated_text(answer, inventory)
    return answer


def build_weaknesses_answer(inventory: SelfInventory) -> str:
    """Build a spoken answer that uses only safe weakness framing plus improvement."""

    issues = validate_self_inventory(inventory)
    if issues:
        raise ValueError("self-inventory is invalid: " + "; ".join(issues))
    lead = "The three areas I am actively working on are clearer headline-first communication, owning my impact accurately, and closing formal skill or certification gaps where my experience has been hands-on."
    lines = []
    for weakness in inventory.weaknesses:
        safe = str(weakness["interview_safe"]).strip().rstrip(".")
        improvement = re.sub(r"(?i)^\s*so\s+", "", str(weakness["improvement_spoken"]).strip().rstrip("."))
        lines.append(f"{safe}. In practice, {improvement}.")
    answer = _join_sentence(lead, *lines, "The pattern is that I name the gap, attach a concrete fix, and keep improving it.")
    assert_safe_generated_text(answer, inventory)
    return answer


def build_self_inventory_onepager_content(inventory: SelfInventory) -> dict[str, Any]:
    """Return render-ready one-pager content with leak and credential guards applied."""

    issues = validate_self_inventory(inventory)
    if issues:
        raise ValueError("self-inventory is invalid: " + "; ".join(issues))
    content: dict[str, Any] = {
        "title": "Self-Inventory Foundation",
        "status": f"Status: {inventory.status}. {inventory.status_note}",
        "strengths": [
            {
                "name": str(strength["name"]),
                "line": str(strength["interview_safe"]),
                "proof": ", ".join(str(item) for item in strength.get("evidence_stories", [])),
            }
            for strength in inventory.strengths
        ],
        "weaknesses": [
            {
                "line": str(weakness["interview_safe"]),
                "improvement": str(weakness["improvement_action"]),
                "status": str(weakness["status"]),
            }
            for weakness in inventory.weaknesses
        ],
        "motivation": inventory.motivation,
        "signature_stories": [
            {
                "name": str(story.get("name", "")),
                "summary": str(story.get("summary", "")),
            }
            for story in inventory.signature_stories
        ],
        "strengths_answer": build_strengths_answer(inventory),
        "weaknesses_answer": build_weaknesses_answer(inventory),
    }
    all_text = "\n".join(_flatten_content_text(content))
    assert_safe_generated_text(all_text, inventory)
    return content


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+#/.\- ]+", " ", value.lower())).strip()


def _term_present(text: str, term: str) -> bool:
    normalized_text = _normalize_text(text)
    normalized_term = _normalize_text(term)
    if not normalized_term:
        return False
    if len(normalized_term) <= 3:
        return bool(re.search(rf"\b{re.escape(normalized_term)}\b", normalized_text))
    return normalized_term in normalized_text


def _audit_keyword_set(job_description: str) -> set[str]:
    try:
        import resume_analysis

        return {str(keyword).lower() for keyword in resume_analysis.audit_keywords(job_description)}
    except Exception:
        return set()


def _federal_competency_text(job_description: str) -> str:
    try:
        import build_federal_resume

        prompts = build_federal_resume.extract_it_competencies(job_description)
    except Exception:
        return ""
    return "\n".join(f"{prompt.name} {prompt.description}" for prompt in prompts)


def _trigger_phrases(competency: str, job_description: str, audit_keywords: set[str], federal_text: str = "") -> tuple[str, ...]:
    search_text = f"{job_description}\n{federal_text}"
    triggers = []
    for term in COMPETENCY_TAXONOMY[competency]["triggers"]:
        normalized = term.lower()
        if _term_present(search_text, term) or normalized in audit_keywords:
            triggers.append(term)
    return tuple(dict.fromkeys(triggers))


def _story_support_level(competency: str, story: Mapping[str, Any] | None) -> str:
    if not story:
        return "gap"
    story_competencies = " ".join(str(item) for item in story.get("competencies", [])).lower()
    normalized_competency = competency.lower()
    if normalized_competency in story_competencies:
        return "strong"
    if competency == "Discovery" and any(term in story_competencies for term in ("requirements", "technical translation")):
        return "strong"
    if competency == "Stakeholder alignment" and any(term in story_competencies for term in ("cross-functional", "executive", "customer recovery")):
        return "strong"
    if competency == "Requirements translation" and any(term in story_competencies for term in ("requirements", "technical translation", "discovery")):
        return "strong"
    if competency == "Implementation and integration" and any(term in story_competencies for term in ("implementation", "integration", "delivery", "risk")):
        return "strong"
    if competency == "Customer relationship building" and any(term in story_competencies for term in ("customer recovery", "executive", "requirements confirmation")):
        return "strong"
    if competency == "Adaptability / fast ramp" and any(term in story_competencies for term in ("rapid learning", "adaptability", "training")):
        return "strong"
    if competency == "Project delivery" and any(term in story_competencies for term in ("delivery", "risk management", "cross-functional")):
        return "strong"
    if competency == "Process improvement" and any(term in story_competencies for term in ("process improvement", "root cause", "automation", "controls")):
        return "strong"
    if competency == "Data and analytics" and any(term in story_competencies for term in ("automation", "controls", "process improvement")):
        return "transferable"
    if competency == "AI adoption" and any(term in story_competencies for term in ("automation", "rapid learning", "training")):
        return "transferable"
    return "transferable"


def _candidate_story_names_for_competency(competency: str, inventory: SelfInventory) -> tuple[str, ...]:
    names: list[str] = []
    for story_name in COMPETENCY_TAXONOMY[competency]["stories"]:
        story = _story_by_name(inventory, story_name)
        if story and _story_support_level(competency, story) in {"strong", "transferable"}:
            names.append(story_name)
    return tuple(dict.fromkeys(names))


def _best_story_name_for_competency(competency: str, inventory: SelfInventory) -> str:
    candidates = _candidate_story_names_for_competency(competency, inventory)
    return candidates[0] if candidates else ""


def build_gap_pivot(competency: str, inventory: SelfInventory, default_story: str = "East West fast ramp") -> str:
    bridge = _spoken_story_reference(inventory, default_story)
    if not bridge:
        bridge = "for example, I have a pattern of ramping quickly on unfamiliar systems and turning that ramp into usable training and delivery"
    lowered = competency.lower()
    if "process" in lowered or "six sigma" in lowered:
        pivot = (
            "I have led process-improvement work, but I have not sat for a formal Six Sigma belt. "
            "I would bridge that through the inventory automation story, where I used the DMAIC pattern in practice. "
            "Which improvement framework does this team use most consistently?"
        )
    elif "technical" in lowered or "ai" in lowered or "hardware" in lowered:
        pivot = (
            "I do not want to overclaim depth there; my strongest experience is on the software, systems, analytics, and implementation side. "
            f"What gives me confidence is the ramp pattern: {bridge}. "
            "What does the expected ramp look like for this part of the role?"
        )
    else:
        pivot = (
            "That is an area where I would be careful not to overstate the match. "
            f"My bridge is the same ramp pattern I have used before: {bridge}. "
            "What would you want this person to learn first to be useful quickly?"
        )
    assert_safe_generated_text(pivot, inventory)
    return pivot


def map_stories_to_scorecard(scorecard: Sequence[ScorecardEntry], inventory: SelfInventory) -> list[ScorecardEntry]:
    mapped: list[ScorecardEntry] = []
    story_counts: dict[str, int] = {}
    signature_story_names = tuple(str(story.get("name", "")).strip() for story in inventory.signature_stories if str(story.get("name", "")).strip())
    spread_target = len(scorecard) >= len(signature_story_names)
    for entry in scorecard:
        candidates = (entry.mapped_story,) if entry.mapped_story else _candidate_story_names_for_competency(entry.competency, inventory)
        candidates = tuple(candidate for candidate in candidates if candidate and _story_by_name(inventory, candidate))
        story_name = ""
        if candidates:
            unused = [candidate for candidate in candidates if story_counts.get(candidate, 0) == 0]
            under_cap = [candidate for candidate in candidates if story_counts.get(candidate, 0) < 2]
            if spread_target and len(story_counts) < min(len(signature_story_names), len(scorecard)) and unused:
                story_name = unused[0]
            elif under_cap:
                story_name = min(under_cap, key=lambda candidate: story_counts.get(candidate, 0))
            else:
                story_name = min(candidates, key=lambda candidate: story_counts.get(candidate, 0))
        story = _story_by_name(inventory, story_name) if story_name else None
        support_level = _story_support_level(entry.competency, story)
        story_reference = _spoken_story_reference(inventory, story_name) if story_name else ""
        gap_pivot = "" if support_level in {"strong", "transferable"} else build_gap_pivot(entry.competency, inventory)
        if story_name and support_level in {"strong", "transferable"}:
            story_counts[story_name] = story_counts.get(story_name, 0) + 1
        mapped.append(
            ScorecardEntry(
                competency=entry.competency,
                trigger_phrases=entry.trigger_phrases,
                framework_words=entry.framework_words,
                mapped_story=story_name if story else "",
                story_reference=story_reference,
                support_level=support_level,
                gap_pivot=gap_pivot,
            )
        )
    return mapped


def scorecard_story_distribution(scorecard: Sequence[ScorecardEntry]) -> dict[str, int]:
    distribution: dict[str, int] = {}
    for entry in scorecard:
        if not entry.mapped_story:
            continue
        distribution[entry.mapped_story] = distribution.get(entry.mapped_story, 0) + 1
    return distribution


def jd_competency_scorecard(job_description: str, resume_text: str, federal: bool = False) -> list[ScorecardEntry]:
    inventory = load_self_inventory()
    issues = validate_self_inventory(inventory)
    if issues:
        raise ValueError("self-inventory is invalid: " + "; ".join(issues))
    audit_keywords = _audit_keyword_set(job_description)
    federal_text = _federal_competency_text(job_description) if federal else ""
    scored: list[tuple[int, int, ScorecardEntry]] = []
    for order, competency in enumerate(COMPETENCY_TAXONOMY):
        triggers = _trigger_phrases(competency, job_description, audit_keywords, federal_text)
        if not triggers:
            continue
        framework_words = COMPETENCY_FRAMEWORKS[competency]
        keyword_bonus = sum(1 for word in framework_words if _term_present(job_description, word) or word.lower() in audit_keywords)
        score = (len(triggers) * 10) + (keyword_bonus * 3)
        scored.append(
            (
                score,
                -order,
                ScorecardEntry(
                    competency=competency,
                    trigger_phrases=triggers,
                    framework_words=framework_words,
                ),
            )
        )
    if len(scored) < 4:
        defaults = ("Discovery", "Requirements translation", "Stakeholder alignment", "Implementation and integration", "Project delivery")
        existing = {entry.competency for _, _, entry in scored}
        for competency in defaults:
            if competency in existing:
                continue
            scored.append(
                (
                    1,
                    -list(COMPETENCY_TAXONOMY).index(competency),
                    ScorecardEntry(
                        competency=competency,
                        trigger_phrases=("default interview scorecard",),
                        framework_words=COMPETENCY_FRAMEWORKS[competency],
                    ),
                )
            )
            existing.add(competency)
            if len(scored) >= 4:
                break
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    selected = [entry for _, _, entry in scored[:8]]
    mapped = map_stories_to_scorecard(selected, inventory)
    rendered = "\n".join(
        "\n".join(
            (
                entry.competency,
                " ".join(entry.trigger_phrases),
                " ".join(entry.framework_words),
                entry.mapped_story,
                entry.story_reference,
                entry.support_level,
                entry.gap_pivot,
            )
        )
        for entry in mapped
    )
    assert_safe_generated_text(rendered, inventory)
    return mapped


def _trigger_summary(entry: ScorecardEntry) -> str:
    useful = [phrase for phrase in entry.trigger_phrases if phrase != "default interview scorecard"]
    if not useful:
        return "the role's core work"
    return ", ".join(useful[:3])


def _answer_focus(competency: str) -> str:
    focus = {
        "Discovery": "make the real workflow, risk, and decision visible before anyone jumps to a solution",
        "Requirements translation": "turn business needs into scope that technical and business teams can both trust",
        "Stakeholder alignment": "get the right people onto one path with clear ownership and documented decisions",
        "Customer relationship building": "build trust by making expectations explicit and following through in writing",
        "Project delivery": "keep scope, risk, milestones, and adoption moving together",
        "Process improvement": "define the problem, measure the baseline, find root cause, improve the workflow, and lock in controls",
        "Data and analytics": "start with the decision the data needs to support, then validate the numbers behind it",
        "Implementation and integration": "surface integration, data, UAT, and cutover risk early enough to manage it",
        "Adaptability / fast ramp": "map unfamiliar tools to the workflow fundamentals and become useful quickly",
        "AI adoption": "connect tool use to adoption, workflow fit, controls, and measurable impact",
        "Technical fluency gap": "be honest about depth, bridge to the ramp pattern, and ask what matters first",
    }
    return focus.get(competency, "turn the role requirement into a clear problem, proof point, and next action")


def _role_relevance(entry: ScorecardEntry, company_name: str, role_title: str) -> str:
    trigger_text = _trigger_summary(entry)
    company_label = company_name or "the company"
    role_label = role_title or "this role"
    role_phrase = f"{role_label} at {company_label}" if role_label.lower().endswith("role") else f"the {role_label} role at {company_label}"
    return f"That matters for {role_phrase} because the posting is really testing {trigger_text}."


def _build_inline_bluf_answer(
    *,
    prompt: str,
    lead: str,
    story_name: str,
    relevance: str,
    inventory: SelfInventory,
) -> BlufAnswer:
    """Build a proof answer that always keeps example and result inline."""

    reference = _spoken_story_reference(inventory, story_name)
    result = _story_result(inventory, story_name)
    if not reference:
        raise ValueError(f"non-gap BLUF answer for {prompt!r} is missing spoken_reference for story {story_name!r}")
    if not result:
        raise ValueError(f"non-gap BLUF answer for {prompt!r} is missing result for story {story_name!r}")
    answer = _join_sentence(lead, _sentence_start_reference(reference), result, relevance)
    assert_safe_generated_text(answer, inventory)
    assert_clean_bluf_answer_text(answer)
    return BlufAnswer(
        prompt=prompt,
        answer=answer,
        example_story=story_name,
        result=result,
        relevance=relevance,
    )


def build_scorecard_bluf_answers(
    scorecard: Sequence[ScorecardEntry],
    job_description: str,
    role_title: str,
    company_name: str,
) -> list[BlufAnswer]:
    inventory = load_self_inventory()
    answers: list[BlufAnswer] = []
    for entry in scorecard:
        prompt = f"{entry.competency}: BLUF answer"
        if entry.gap_pivot or not entry.mapped_story:
            answer = entry.gap_pivot or build_gap_pivot(entry.competency, inventory)
            assert_safe_generated_text(answer, inventory)
            answers.append(BlufAnswer(prompt=prompt, answer=answer, is_gap=True))
            continue
        relevance = _role_relevance(entry, company_name, role_title)
        answers.append(
            _build_inline_bluf_answer(
                prompt=prompt,
                lead=f"For {entry.competency.lower()}, my approach is to {_answer_focus(entry.competency)}",
                story_name=entry.mapped_story,
                relevance=relevance,
                inventory=inventory,
            )
        )
    return answers


def _scorecard_story(scorecard: Sequence[ScorecardEntry], preferred: str, fallback: str = "") -> ScorecardEntry | None:
    for entry in scorecard:
        if entry.mapped_story == preferred:
            return entry
    for entry in scorecard:
        if fallback and entry.mapped_story == fallback:
            return entry
    return None


def build_standard_high_stakes_answers(
    job_description: str,
    resume_text: str,
    company_name: str,
    role_title: str,
    scorecard: Sequence[ScorecardEntry],
) -> list[BlufAnswer]:
    inventory = load_self_inventory()
    relationship = _scorecard_story(scorecard, "CEO escalation")
    alignment = _scorecard_story(scorecard, "EFT/ACH cross-functional replacement")
    fast_ramp = _scorecard_story(scorecard, "East West fast ramp")
    gap_entry = next((entry for entry in scorecard if entry.gap_pivot), None)
    relationship_story = relationship.mapped_story if relationship and relationship.mapped_story else "CEO escalation"
    alignment_story = alignment.mapped_story if alignment and alignment.mapped_story else "EFT/ACH cross-functional replacement"
    fast_story = fast_ramp.mapped_story if fast_ramp and fast_ramp.mapped_story else "East West fast ramp"
    gap_answer = gap_entry.gap_pivot if gap_entry else build_gap_pivot("Technical fluency gap", inventory)
    questions = (
        f"What separates someone who is good from someone who is great in this {role_title} role?",
        "Where do requirements, stakeholder alignment, or handoff most often go sideways today?",
        "What would you want this person to learn first so they can be useful quickly?",
    )
    answers = [
        BlufAnswer(
            prompt="Why this role / why this company",
            answer=_join_sentence(
                f"What interests me about the {role_title} role at {company_name} is that it sits where business needs, systems, and adoption have to line up",
                inventory.motivation,
                "That is the pattern I would bring here: understand the real problem, make the next decision clearer, and help the work hold up after handoff",
            ),
            relevance=f"The answer ties Christian's motivation to the {role_title} role.",
        ),
        _build_inline_bluf_answer(
            prompt="Walk me through your last role",
            lead="My last role was business-systems ownership across ERP, reporting, access controls, and process improvement; the useful category is translating operational problems into system changes, data visibility, training, and controls",
            story_name=fast_story,
            relevance="That matters here because the same skill is getting productive quickly, understanding the workflow, and making the system useful for the business",
            inventory=inventory,
        ),
        _build_inline_bluf_answer(
            prompt="Build productive relationships",
            lead="I build productive relationships by making expectations explicit and proving follow-through",
            story_name=relationship_story,
            relevance="That is how I keep trust from depending on memory or personality alone",
            inventory=inventory,
        ),
        _build_inline_bluf_answer(
            prompt="Get alignment when perspectives differ",
            lead="When perspectives differ, I anchor the conversation to the current-state process and the decision everyone needs to make",
            story_name=alignment_story,
            relevance="That matters in this role because alignment has to become one usable path, not several private definitions of done",
            inventory=inventory,
        ),
        BlufAnswer(prompt="Your 3 greatest strengths", answer=build_strengths_answer(inventory), relevance="Uses the shared naturalized strengths answer."),
        BlufAnswer(prompt="3 development areas", answer=build_weaknesses_answer(inventory), relevance="Uses only interview-safe weakness language plus improvement."),
        BlufAnswer(prompt="Your biggest gap for this role", answer=gap_answer, is_gap=True),
        BlufAnswer(
            prompt="Role-specific 30/60/90",
            answer=_join_sentence(
                "Here is how I would think about the first 90 days",
                "In the first 30, I would learn the product, customer context, stakeholder map, and where discovery or handoff risk usually appears",
                "By 60, I would lead portions of discovery or requirements work with support and validate my notes against the team",
                "By 90, I would aim to run requirements documentation or handoff work independently and start catching integration or adoption risks myself",
                "Does that match what the team expects at this level",
            ),
        ),
        BlufAnswer(
            prompt="2-3 consultative questions to ask",
            answer=" ".join(f"{index}. {question}" for index, question in enumerate(questions, start=1)),
        ),
    ]
    rendered = "\n".join(answer.answer for answer in answers)
    assert_safe_generated_text(rendered, inventory)
    assert_clean_bluf_answer_text(rendered)
    return answers


def _validate_daily_prep_mode(mode: str) -> str:
    normalized = mode.strip().lower().replace("-", "_")
    if normalized not in DAILY_PREP_MODES:
        raise ValueError(f"daily prep mode must be one of {', '.join(DAILY_PREP_MODES)}; got {mode!r}")
    return normalized


def _rotated_item(items: Sequence[Mapping[str, Any]], index: int) -> Mapping[str, Any]:
    if not items:
        return {}
    return items[index % len(items)]


def _daily_scorecard_line(job_description: str) -> str:
    if not job_description.strip():
        return "Use the active posting or one pasted JD and build a 4-8 item scorecard in about five minutes."
    scorecard = jd_competency_scorecard(job_description, "")
    labels = ", ".join(entry.competency for entry in scorecard[:5])
    return f"Build today's live JD scorecard in about five minutes; first competencies to rehearse: {labels}."


def _self_inventory_hash(path: Path = SELF_INVENTORY_PATH) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _clean_debrief_lines(value: object) -> list[str]:
    if isinstance(value, str):
        raw_lines = value.splitlines()
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        raw_lines = [str(item) for item in value]
    else:
        raw_lines = []
    lines: list[str] = []
    seen: set[str] = set()
    for raw in raw_lines:
        cleaned = re.sub(r"\s+", " ", str(raw)).strip(" -")
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        lines.append(cleaned)
        seen.add(key)
    return lines


def _safe_advisory_text(value: object, inventory: SelfInventory) -> str:
    text = re.sub(r"\s+", " ", str(value)).strip()
    for weakness in inventory.weaknesses:
        honest = str(weakness.get("honest_name", "")).strip()
        safe = str(weakness.get("interview_safe", "")).strip().rstrip(".")
        if honest and safe:
            text = re.sub(re.escape(honest), safe, text, flags=re.I)
    for pattern, replacement in UNSUPPORTED_ADVISORY_REPLACEMENTS:
        text = pattern.sub(replacement, text)
    return text.strip()


def _safe_advisory_lines(value: object, inventory: SelfInventory) -> list[str]:
    return [line for line in (_safe_advisory_text(item, inventory) for item in _clean_debrief_lines(value)) if line]


def _normalize_answer_rating(item: object, inventory: SelfInventory) -> dict[str, str] | None:
    if isinstance(item, Mapping):
        prompt = _safe_advisory_text(item.get("prompt", ""), inventory)
        competency = _safe_advisory_text(item.get("competency", ""), inventory)
        rating = _safe_advisory_text(item.get("rating", ""), inventory).lower()
        note = _safe_advisory_text(item.get("note", ""), inventory)
    else:
        parts = [part.strip() for part in str(item).split("|")]
        if len(parts) >= 4:
            prompt, competency, rating, note = parts[0], parts[1], parts[2].lower(), " | ".join(parts[3:])
        elif len(parts) == 3:
            prompt, competency, rating, note = parts[0], parts[1], parts[2].lower(), ""
        else:
            return None
        prompt = _safe_advisory_text(prompt, inventory)
        competency = _safe_advisory_text(competency, inventory)
        note = _safe_advisory_text(note, inventory)
    rating = rating.strip().lower()
    if rating not in {"landed", "rambled", "missed"}:
        return None
    if not prompt and not competency and not note:
        return None
    return {"prompt": prompt, "competency": competency, "rating": rating, "note": note}


def debrief_answer_ratings(record: Mapping[str, object], inventory: SelfInventory | None = None) -> list[dict[str, str]]:
    inventory = inventory or load_self_inventory()
    value = record.get("answer_ratings", [])
    items: Sequence[object]
    if isinstance(value, str):
        items = _clean_debrief_lines(value)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        items = value
    else:
        items = ()
    ratings = []
    for item in items:
        normalized = _normalize_answer_rating(item, inventory)
        if normalized:
            ratings.append(normalized)
    return ratings


def _known_story_target(line: str, inventory: SelfInventory) -> str:
    lowered = line.lower()
    for story in inventory.signature_stories:
        name = str(story.get("name", "")).strip()
        if name and name.lower() in lowered:
            return name
    return ""


def _review_source(record: Mapping[str, object]) -> dict[str, str]:
    return {
        "company_name": str(record.get("company_name", "")).strip(),
        "role_title": str(record.get("role_title", "")).strip(),
        "interview_date": str(record.get("interview_date", "")).strip(),
        "round_number": str(record.get("round_number", "")).strip(),
    }


def debrief_review_summary(record: Mapping[str, object], inventory: SelfInventory | None = None) -> dict[str, list[str]]:
    inventory = inventory or load_self_inventory()
    ratings = debrief_answer_ratings(record, inventory)
    landed = [
        _safe_advisory_text(
            f"{item['prompt']}: {item['competency']} landed. {item['note']}".strip(),
            inventory,
        )
        for item in ratings
        if item["rating"] == "landed"
    ]
    fixes = [
        _safe_advisory_text(
            f"{item['prompt']}: {item['competency']} {item['rating']}. {item['note']}".strip(),
            inventory,
        )
        for item in ratings
        if item["rating"] in {"rambled", "missed"}
    ]
    fixes.extend(_safe_advisory_lines(record.get("hedge_observations", []), inventory))
    fixes.extend(_safe_advisory_lines(record.get("development_area_signals", []), inventory))
    strengths = _safe_advisory_lines(record.get("story_followups", []), inventory)
    focus = build_debrief_feedback_payloads(record, inventory=inventory)[0].get("next_day_focus", [])
    rendered = "\n".join((*landed, *strengths, *fixes, *[str(item) for item in focus]))
    assert_safe_generated_text(rendered, inventory)
    return {
        "what_went_well": [*landed, *[f"Story signal: {line}" for line in strengths]],
        "what_to_fix": fixes,
        "next_day_focus": [str(item) for item in focus],
    }


def build_debrief_feedback_payloads(
    record: Mapping[str, object],
    *,
    inventory: SelfInventory | None = None,
    updated_at: datetime | None = None,
) -> tuple[dict[str, object], dict[str, object]]:
    inventory = inventory or load_self_inventory()
    timestamp = (updated_at or datetime.now()).replace(microsecond=0).isoformat()
    ratings = debrief_answer_ratings(record, inventory)
    competencies = _safe_advisory_lines(record.get("competencies_probed", []), inventory)
    focus_rep_types: list[str] = []
    story_targets: list[str] = []
    weakness_targets = _safe_advisory_lines(record.get("development_area_signals", []), inventory)
    hedge_observations = _safe_advisory_lines(record.get("hedge_observations", []), inventory)

    if hedge_observations:
        focus_rep_types.append("delivery")
    if weakness_targets:
        focus_rep_types.append("weakness")
    for item in ratings:
        if item["competency"]:
            competencies.append(item["competency"])
        if item["rating"] == "rambled":
            focus_rep_types.append("delivery")
        elif item["rating"] == "missed":
            focus_rep_types.extend(("scorecard", "story"))
            if item["competency"]:
                story_targets.append(item["competency"])
    for line in _safe_advisory_lines(record.get("new_story_candidates", []), inventory):
        focus_rep_types.append("story")
        story_targets.append(_known_story_target(line, inventory) or line)
    if not focus_rep_types and competencies:
        focus_rep_types.append("scorecard")
    focus_rep_types = [rep for rep in DAILY_REP_TYPES if rep in set(focus_rep_types)]
    competencies = list(dict.fromkeys(competencies))
    story_targets = list(dict.fromkeys(story_targets))
    weakness_targets = list(dict.fromkeys(weakness_targets))

    focus_lines = []
    if "delivery" in focus_rep_types:
        focus_lines.append("Delivery drill: tighten answers that rambled and count hedges.")
    if "scorecard" in focus_rep_types:
        label = ", ".join(competencies[:3]) or "the competency that felt underprepared"
        focus_lines.append(f"Scorecard rep: rehearse the flagged competency language for {label}.")
    if "story" in focus_rep_types:
        label = ", ".join(target.strip().rstrip(".") for target in story_targets[:2] if target.strip()) or "the story that was not ready"
        focus_lines.append(f"Story rep: connect a certified story or honest pivot to {label}.")
    if "weakness" in focus_rep_types:
        focus_lines.append("Weakness rep: use only interview-safe wording and attach the improvement action.")

    prep_focus = {
        "version": DEBRIEF_FEEDBACK_VERSION,
        "updated_at": timestamp,
        "source": _review_source(record),
        "focus_rep_types": focus_rep_types,
        "competencies": competencies,
        "story_targets": story_targets,
        "weakness_targets": weakness_targets,
        "hedge_observations": hedge_observations,
        "next_day_focus": focus_lines,
    }

    candidates: list[dict[str, object]] = []
    for line in _safe_advisory_lines(record.get("new_story_candidates", []), inventory):
        candidates.append(
            {
                "type": "signature_story",
                "status": "review",
                "source_note": line,
                "promotion_rule": "Christian must manually confirm facts, ownership, metric, result, and wording before adding this to source/self_inventory.json.",
            }
        )
    for item in ratings:
        if item["rating"] == "landed" and (item["competency"] or item["note"]):
            candidates.append(
                {
                    "type": "strength_evidence",
                    "status": "review",
                    "competency": item["competency"],
                    "source_note": item["note"] or item["prompt"],
                    "promotion_rule": "Christian must manually decide whether this adds evidence to an existing strength.",
                }
            )
        if item["rating"] == "missed":
            candidates.append(
                {
                    "type": "competency_gap",
                    "status": "review",
                    "competency": item["competency"],
                    "source_note": item["note"] or item["prompt"],
                    "promotion_rule": "Use this as a practice gap unless Christian confirms it belongs in the self-inventory.",
                }
            )
    for line in weakness_targets:
        candidates.append(
            {
                "type": "weakness_status",
                "status": "review",
                "source_note": line,
                "promotion_rule": "Christian must manually confirm any weakness status change.",
            }
        )

    inventory_candidates = {
        "version": DEBRIEF_FEEDBACK_VERSION,
        "updated_at": timestamp,
        "source": _review_source(record),
        "candidates": candidates,
    }
    rendered = json.dumps({"prep_focus": prep_focus, "inventory_candidates": inventory_candidates}, sort_keys=True)
    assert_safe_generated_text(rendered, inventory)
    return prep_focus, inventory_candidates


def write_debrief_feedback_artifacts(
    record: Mapping[str, object],
    *,
    prep_focus_path: Path = DEFAULT_PREP_FOCUS_PATH,
    inventory_candidates_path: Path = DEFAULT_INVENTORY_CANDIDATES_PATH,
    self_inventory_path: Path = SELF_INVENTORY_PATH,
) -> dict[str, Path]:
    if prep_focus_path.resolve() == self_inventory_path.resolve() or inventory_candidates_path.resolve() == self_inventory_path.resolve():
        raise ValueError("debrief feedback artifacts must not target source/self_inventory.json")
    before_hash = _self_inventory_hash(self_inventory_path)
    inventory = load_self_inventory(self_inventory_path)
    prep_focus, inventory_candidates = build_debrief_feedback_payloads(record, inventory=inventory)
    prep_focus_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_candidates_path.parent.mkdir(parents=True, exist_ok=True)
    prep_focus_path.write_text(json.dumps(prep_focus, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    inventory_candidates_path.write_text(json.dumps(inventory_candidates, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    after_hash = _self_inventory_hash(self_inventory_path)
    if after_hash != before_hash:
        raise RuntimeError("source/self_inventory.json changed during debrief feedback generation")
    return {"prep_focus": prep_focus_path, "inventory_candidates": inventory_candidates_path}


def load_prep_focus(path: Path = DEFAULT_PREP_FOCUS_PATH) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, Mapping):
        return {}
    return dict(payload)


def _plan_render_text(plan: DailyPrepPlan) -> str:
    return "\n".join(
        (
            plan.mode,
            plan.plan_date.isoformat(),
            plan.emphasis,
            plan.completion_prompt,
            *plan.question_bank_checklist,
            *(
                "\n".join(
                    (
                        rep.rep_type,
                        rep.title,
                        rep.proof_reference,
                        rep.weight,
                        *rep.instructions,
                    )
                )
                for rep in plan.reps
            ),
        )
    )


def _question_bank_checklist(job_description: str) -> tuple[str, ...]:
    try:
        import question_bank_audit
        import question_prep
    except ImportError:
        return ()

    audit = question_bank_audit.audit_application_bank()
    stale_prompts = set()
    if job_description.strip():
        stale_prompts = set(
            question_prep.application_question_context_issues(
                job_description,
                tuple(row.prompt for row in audit.rows),
                workflow="commercial",
            )
        )
    rows = [row for row in audit.rows if row.prompt not in stale_prompts]
    if not rows:
        return ()

    def row_priority(index_row: tuple[int, object]) -> tuple[int, int]:
        index, row = index_row
        tracks = tuple(getattr(row, "theme_track_refs", ()))
        category = str(getattr(row, "category", ""))
        if tracks:
            return (0, index)
        if category == "generic_bridge":
            return (1, index)
        return (2, index)

    checklist: list[str] = []
    for _index, row in sorted(enumerate(rows), key=row_priority):
        category = row.category.replace("_", " ").title()
        tracks = "; ".join(row.theme_track_refs) if row.theme_track_refs else "no Study track"
        if row.category == "generic_bridge":
            action = "needs a mapped answer; rehearse with honest bridge language until it is categorized"
        else:
            action = "rehearse the answer with claim, proof, and role relevance"
        checklist.append(f"{category} ({tracks}): {action}. Prompt: {row.prompt}")
    return tuple(checklist)


def build_daily_prep_plan(
    mode: str,
    today: date | None = None,
    job_description: str = "",
    prep_focus_path: Path = DEFAULT_PREP_FOCUS_PATH,
) -> DailyPrepPlan:
    """Build a non-linear daily interview prep plan from the provisional self-inventory."""

    normalized_mode = _validate_daily_prep_mode(mode)
    plan_date = today or date.today()
    inventory = load_self_inventory()
    issues = validate_self_inventory(inventory)
    if issues:
        raise ValueError("self-inventory is invalid: " + "; ".join(issues))

    day_index = plan_date.toordinal()
    prep_focus = load_prep_focus(prep_focus_path)
    focus_rep_types = {str(item).strip() for item in prep_focus.get("focus_rep_types", []) if str(item).strip()} if prep_focus else set()
    focus_competencies = _safe_advisory_lines(prep_focus.get("competencies", []), inventory) if prep_focus else []
    focus_story_targets = _safe_advisory_lines(prep_focus.get("story_targets", []), inventory) if prep_focus else []
    focus_weakness_targets = _safe_advisory_lines(prep_focus.get("weakness_targets", []), inventory) if prep_focus else []
    focus_hedges = _safe_advisory_lines(prep_focus.get("hedge_observations", []), inventory) if prep_focus else []
    next_day_focus = _safe_advisory_lines(prep_focus.get("next_day_focus", []), inventory) if prep_focus else []
    story = _rotated_item(inventory.signature_stories, day_index)
    certified_story_names = {str(item.get("name", "")).strip().lower(): item for item in inventory.signature_stories}
    for target in focus_story_targets:
        matched = certified_story_names.get(target.lower())
        if matched:
            story = matched
            break
    weakness = _rotated_item(inventory.weaknesses, day_index + 1)
    delivery_focuses = (
        "Answer in sentence one, then give one example, one result, and stop.",
        "Record one answer and tally hedges: just, kind of, broadly speaking, it depended.",
        "Run one story at 30 seconds, 60 seconds, and 120 seconds without changing the core point.",
        "Turn one answer problem-first: client problem, what I did, measurable outcome.",
    )
    delivery_focus = delivery_focuses[day_index % len(delivery_focuses)]
    strength_names = ", ".join(str(strength["name"]) for strength in inventory.strengths)
    weakness_safe_lines = ", ".join(str(item["interview_safe"]).rstrip(".") for item in inventory.weaknesses)
    story_name = str(story.get("name", "")).strip()
    story_reference = str(story.get("spoken_reference", "")).strip()
    story_result = str(story.get("result", "")).strip()
    weakness_line = str(weakness.get("interview_safe", "")).strip().rstrip(".")
    weakness_action = str(weakness.get("improvement_spoken", weakness.get("improvement_action", ""))).strip().rstrip(".")

    if normalized_mode == "job_search":
        emphasis = "Job-search mode: prioritize delivery reps, live-JD scorecard practice, and application or interview readiness."
        weights = {
            "self_inventory": "standard",
            "delivery": "high",
            "story": "high",
            "scorecard": "high",
            "weakness": "standard",
        }
        scorecard_instruction = _daily_scorecard_line(job_description)
        closing_instruction = "End by choosing one application, follow-up, or interview answer that gets sharper because of today's reps."
    else:
        emphasis = "On-the-job mode: prioritize Study/ learning, logging new wins, and keeping interview stories warm without turning practice into a grind."
        weights = {
            "self_inventory": "standard",
            "delivery": "standard",
            "story": "high",
            "scorecard": "standard",
            "weakness": "high",
        }
        scorecard_instruction = "Use a real meeting, project, or internal opportunity as the scorecard: what competencies would someone be quietly judging?"
        closing_instruction = (
            "End by naming one new win or learning thread to capture later in the self-inventory; "
            f"use {STUDY_LEARNING_PATH_REFERENCE} when the gap is technical."
        )

    for rep_type in focus_rep_types:
        if rep_type in weights:
            weights[rep_type] = "focus"
    scorecard_focus_line = (
        f"Debrief focus: rehearse flagged competencies from the latest debrief: {', '.join(item.strip().rstrip('.') for item in focus_competencies[:5] if item.strip())}."
        if focus_competencies
        else ""
    )
    delivery_focus_line = (
        f"Debrief focus: hedge or delivery observation to tighten: {focus_hedges[0].strip().rstrip('.')}."
        if focus_hedges
        else ""
    )
    story_focus_line = ""
    if focus_story_targets:
        matched_story_names = {str(story.get("name", "")).strip().lower()}
        unmatched = [target for target in focus_story_targets if target.lower() not in matched_story_names and target.lower() not in certified_story_names]
        if unmatched:
            story_focus_line = f"Review-only story candidate from debrief: {unmatched[0].strip().rstrip('.')}. Do not treat it as certified proof until Christian promotes it."
        else:
            story_focus_line = f"Debrief focus: use the certified story target {story_name}."
    weakness_focus_line = (
        f"Debrief focus: practice the safe development signal: {focus_weakness_targets[0].strip().rstrip('.')}."
        if focus_weakness_targets
        else ""
    )
    plan_focus_line = next_day_focus[0] if next_day_focus else ""

    reps = (
        DailyPrepRep(
            rep_type="self_inventory",
            title="Self-inventory rehearsal",
            duration_minutes=3,
            instructions=(
                "Say the three strengths answer aloud with the BLUF first.",
                f"Strength anchors: {strength_names}.",
                f"Development areas stay interview-safe: {weakness_safe_lines}.",
            ),
            proof_reference="source/self_inventory.json",
            weight=weights["self_inventory"],
        ),
        DailyPrepRep(
            rep_type="delivery",
            title="Delivery drill",
            duration_minutes=3,
            instructions=(
                *((delivery_focus_line,) if delivery_focus_line else ()),
                delivery_focus,
                "Write the hedge count down; the target is visible improvement, not perfection.",
            ),
            proof_reference="interview_prep/Christian Estrada - Daily Confidence and Consultative Delivery Practice.md",
            weight=weights["delivery"],
        ),
        DailyPrepRep(
            rep_type="story",
            title=f"Signature story rep: {story_name}",
            duration_minutes=4,
            instructions=(
                *((story_focus_line,) if story_focus_line else ()),
                "Lead with the point before the timeline.",
                story_reference,
                f"Close with the result: {story_result}",
            ),
            proof_reference=story_name,
            weight=weights["story"],
        ),
        DailyPrepRep(
            rep_type="scorecard",
            title="Scorecard rep",
            duration_minutes=3,
            instructions=(
                *((scorecard_focus_line,) if scorecard_focus_line else ()),
                scorecard_instruction,
                "For the top item, say the competency, the words to say, and the story or honest pivot.",
            ),
            proof_reference="jd_competency_scorecard",
            weight=weights["scorecard"],
        ),
        DailyPrepRep(
            rep_type="weakness",
            title="One improvement action",
            duration_minutes=2,
            instructions=(
                *((weakness_focus_line,) if weakness_focus_line else ()),
                f"Work the safe development area: {weakness_line}.",
                f"Concrete action: {weakness_action}.",
                closing_instruction,
            ),
            proof_reference="source/self_inventory.json",
            weight=weights["weakness"],
        ),
    )
    plan = DailyPrepPlan(
        mode=normalized_mode,
        plan_date=plan_date,
        emphasis=_join_sentence(emphasis, plan_focus_line) if plan_focus_line else emphasis,
        reps=reps,
        completion_prompt="Log reps_done, hedge_count, and self_rated_clarity only when you intentionally mark the session complete.",
        question_bank_checklist=_question_bank_checklist(job_description),
    )
    assert_safe_generated_text(_plan_render_text(plan), inventory)
    return plan


def append_daily_prep_log(
    mode: str,
    reps_done: int,
    hedge_count: int,
    self_rated_clarity: int,
    path: Path = DEFAULT_PREP_LOG_PATH,
    today: date | None = None,
) -> Path:
    normalized_mode = _validate_daily_prep_mode(mode)
    log_date = today or date.today()
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=DAILY_PREP_LOG_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow(
            {
                "date": log_date.isoformat(),
                "mode": normalized_mode,
                "reps_done": str(reps_done),
                "hedge_count": str(hedge_count),
                "self_rated_clarity": str(self_rated_clarity),
            }
        )
    return path


def _inventory_target_roles(inventory: SelfInventory) -> tuple[tuple[str, ...], tuple[str, ...]]:
    role_lookup = {role.lower(): role for role in inventory.target_roles}
    near_term = tuple(role_lookup.get(role.lower(), role) for role in NEAR_TERM_CAREER_ROLES)
    stretch = tuple(
        role
        for role in inventory.target_roles
        if "business architect" in role.lower() or "ai evangelist" in role.lower()
    )
    return near_term, stretch or STRETCH_CAREER_ROLES


def _existing_study_references() -> tuple[str, ...]:
    existing = []
    for reference in STUDY_TRACK_REFERENCES:
        if (PROJECT_ROOT / reference).exists():
            existing.append(reference)
    return tuple(existing)


def _career_plan_render_text(plan: CareerOperatingPlan) -> str:
    return "\n".join(
        (
            plan.plan_date.isoformat(),
            *plan.near_term_roles,
            *plan.stretch_roles,
            *(
                "\n".join((gap.label, gap.safe_description, gap.action, *gap.track_references))
                for gap in plan.development_gaps
            ),
            *(
                "\n".join((gap.label, gap.safe_description, gap.action, *gap.track_references))
                for gap in plan.stretch_role_gaps
            ),
            *(
                "\n".join((mode.name, mode.focus, *mode.actions))
                for mode in plan.modes
            ),
            *plan.checkpoints,
            *plan.study_references,
        )
    )


def build_career_plan(today: date | None = None) -> CareerOperatingPlan:
    """Build the Phase 5 career operating plan without duplicating Study content."""

    inventory = load_self_inventory()
    issues = validate_self_inventory(inventory)
    if issues:
        raise ValueError("self-inventory is invalid: " + "; ".join(issues))

    near_term_roles, stretch_roles = _inventory_target_roles(inventory)
    strengths = ", ".join(str(strength["name"]) for strength in inventory.strengths)
    safe_weaknesses = [str(weakness["interview_safe"]).strip().rstrip(".") for weakness in inventory.weaknesses]
    study_references = _existing_study_references()
    if not study_references:
        raise ValueError("no Study references were found for the career operating plan")

    development_gaps = (
        CareerPlanGap(
            label="Delivery communication / BLUF discipline",
            safe_description=safe_weaknesses[0],
            track_references=(
                "daily-prep --mode job_search",
                "interview_prep/Christian Estrada - Daily Confidence and Consultative Delivery Practice.md",
            ),
            action="Run the daily delivery rep, track hedge count, and keep the answer pattern to headline, one example, result, relevance, then stop.",
        ),
        CareerPlanGap(
            label="Evidence ownership and win logging",
            safe_description=safe_weaknesses[1],
            track_references=(
                "source/self_inventory.json",
                "daily-prep --mode on_the_job",
                "scratch/prep_log.csv",
            ),
            action="Capture one new win each month and refresh the provisional self-inventory quarterly so the story bank keeps pace with real work.",
        ),
        CareerPlanGap(
            label="Formal methodology and technical fluency",
            safe_description=safe_weaknesses[2],
            track_references=(
                STUDY_LEARNING_PATH_REFERENCE,
                _study_flashcard_reference("PMP"),
                _study_flashcard_reference("AI"),
                _study_flashcard_reference("BusinessArchitecture"),
                _study_flashcard_reference("DataAnalyticsBI"),
            ),
            action="Choose the one track that blocks the current target role first: CAPM/PMP for delivery, AI Innovator and AI-900 for AI fluency, Business Architecture / TOGAF EA Foundation for architecture, or Data Analytics & BI / PL-300 for analytics.",
        ),
    )

    stretch_role_gaps = (
        CareerPlanGap(
            label="AI architecture and agent fluency",
            safe_description="For AI-heavy stretch roles, keep the positioning at adoption, workflow fit, controls, and learning velocity unless the Study work has created new proof.",
            track_references=(
                "AI Innovator track",
                "AI-900",
                _study_flashcard_reference("AI"),
                _study_flashcard_reference("AIEngineeringMLOps"),
                _study_flashcard_reference("EnterpriseAITools"),
            ),
            action="Build enough vocabulary to ask better architecture questions and explain adoption risk without implying hands-on engineering depth.",
        ),
        CareerPlanGap(
            label="Business architecture",
            safe_description="For Business Architect roles, frame current experience as requirements, process, stakeholder alignment, and operating-model translation while the formal architecture language catches up.",
            track_references=(
                "Track B Business Architecture / TOGAF EA Foundation",
                _study_flashcard_reference("BusinessArchitecture"),
            ),
            action="Practice converting implementation stories into capability, value-stream, stakeholder, and governance language.",
        ),
        CareerPlanGap(
            label="Analytics and BI proof",
            safe_description="Analytics strength is strongest when tied to business decisions, KPI visibility, data validation, and reporting outcomes.",
            track_references=(
                "Track D Data Analytics & BI / PL-300",
                _study_flashcard_reference("DataAnalyticsBI"),
            ),
            action="Keep analytics answers anchored to decisions improved, not tool-name collecting.",
        ),
        CareerPlanGap(
            label="AI adoption and change",
            safe_description="For AI adoption roles, lead with enablement, stakeholder trust, workflow fit, and measuring whether people actually change how they work.",
            track_references=(
                "Track E AI Adoption & Change Management / Prosci / ADKAR",
                _study_flashcard_reference("AIAdoption"),
            ),
            action="Translate the existing adoption stories into change-readiness, champions, training, and feedback-loop language.",
        ),
        CareerPlanGap(
            label="Cloud, coding, and security foundations",
            safe_description="Cloud, coding, and security should be positioned as foundations under active study, not as primary ownership unless the source evidence supports it.",
            track_references=(
                "AWS Cloud track",
                "Python/foundations track",
                "Security+ track where the role makes it relevant",
                _study_flashcard_reference("AWS"),
                _study_flashcard_reference("Foundations"),
                _study_flashcard_reference("SecurityPlus"),
            ),
            action="Use these tracks to improve technical conversation quality for implementation and architect-adjacent roles.",
        ),
    )

    modes = (
        CareerPlanMode(
            name="get a job now",
            focus="Prioritize the near-term roles, live JD scorecards, delivery reps, and only the learning gaps that block current interviews.",
            actions=(
                f"Use the strengths as the core value story: {strengths}.",
                "Run daily-prep --mode job_search before applications, recruiter calls, and interviews.",
                "For each live JD, build a scorecard and map every competency to a signature story or honest pivot.",
                "Study only the track that is blocking the current role; do not turn prep into a broad checklist.",
            ),
        ),
        CareerPlanMode(
            name="excel in the job",
            focus="Use the Study path, win logging, and light rehearsal to turn new work into stronger proof while staying interview-ready.",
            actions=(
                "Run daily-prep --mode on_the_job when a real project, meeting, or new responsibility gives fresh evidence.",
                "Log one concrete win, metric, decision, or adoption signal each month.",
                "Update source/self_inventory.json only after Christian confirms the wording still sounds true.",
                "Use quarterly review to decide whether the north-star track should move closer or stay a stretch.",
            ),
        ),
    )
    checkpoints = (
        "Monthly quick review: update one win, one gap, one target-role signal, and one Study priority.",
        "Quarterly deep review: refresh target roles, retire stale stories, confirm safe weakness wording, and choose the next Study track.",
    )

    plan = CareerOperatingPlan(
        plan_date=today or date.today(),
        near_term_roles=near_term_roles,
        stretch_roles=stretch_roles,
        development_gaps=development_gaps,
        stretch_role_gaps=stretch_role_gaps,
        modes=modes,
        checkpoints=checkpoints,
        study_references=study_references,
    )
    assert_safe_generated_text(_career_plan_render_text(plan), inventory)
    return plan


def _flatten_content_text(value: object) -> list[str]:
    if isinstance(value, Mapping):
        lines: list[str] = []
        for child in value.values():
            lines.extend(_flatten_content_text(child))
        return lines
    if isinstance(value, (list, tuple)):
        lines = []
        for child in value:
            lines.extend(_flatten_content_text(child))
        return lines
    return [str(value)]
