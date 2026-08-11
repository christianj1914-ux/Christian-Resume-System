"""Shared announcement requirement parsing and target-context models.

The parser is intentionally deterministic.  It treats the posting's own
responsibility and qualification statements as the unit of tailoring and
keeps the older lane/cluster systems available as priors when parsing is weak.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache


class RequirementStatus(str, Enum):
    DIRECT = "Direct"
    ADJACENT = "Adjacent"
    TRANSFERABLE = "Transferable"
    UNSUPPORTED = "Unsupported"


@dataclass(frozen=True)
class RequirementElement:
    element_id: str
    workflow: str
    section: str
    text: str
    required: bool
    preferred: bool
    grade: str = ""
    atomic_capabilities: tuple[str, ...] = ()
    canonical_terms: tuple[str, ...] = ()
    category: str = "activity"
    priority: int = 3
    alternative_group_id: str = ""
    alternative_terms: tuple[str, ...] = ()
    requirement_group_id: str = ""


@dataclass(frozen=True)
class TargetContext:
    workflow: str
    company: str
    official_title: str
    display_title: str
    matching_title: str
    lane: str
    sanitized_job_description: str
    requirement_sections: tuple[tuple[str, str], ...]
    requirements: tuple[RequirementElement, ...]
    target_grade: str = ""
    equivalent_grade: str = ""
    equivalence_years: int | None = None
    minimum_competencies: tuple[str, ...] = ()
    assessed_competencies: tuple[str, ...] = ()
    agency: str = ""
    subagency: str = ""
    output_label: str = ""
    identity_source: str = "company"
    available_grades: tuple[str, ...] = ()
    duty_grade: str = ""
    parse_mode: str = ""
    parse_diagnostics: tuple[object, ...] = ()
    verified: bool = True


@dataclass(frozen=True)
class FederalRequirementSection:
    """A structural federal requirement unit shared by both federal consumers."""

    label: str
    kind: str
    text: str
    weight_group_id: str
    grade: str = ""
    equivalent_grade: str = ""
    equivalence_years: int | None = None


@dataclass(frozen=True)
class FederalParseDiagnostic:
    code: str
    message: str
    requires_draft: bool


@dataclass(frozen=True)
class FederalParseResult:
    duty_grade: str
    available_grades: tuple[str, ...]
    selected_grade: str
    equivalent_grade: str
    equivalence_years: int | None
    sections: tuple[FederalRequirementSection, ...]
    requirements: tuple[RequirementElement, ...]
    minimum_competencies: tuple[str, ...]
    assessed_competencies: tuple[str, ...]
    diagnostics: tuple[FederalParseDiagnostic, ...]
    verified: bool


@dataclass(frozen=True)
class CommercialParseDiagnostic:
    code: str
    message: str


@dataclass(frozen=True)
class CommercialParseResult:
    sections: tuple[tuple[str, str], ...]
    requirements: tuple[RequirementElement, ...]
    parse_mode: str
    diagnostics: tuple[CommercialParseDiagnostic, ...]
    verified: bool


@dataclass(frozen=True)
class RequirementCoverage:
    element: RequirementElement
    status: RequirementStatus
    matched_terms: tuple[str, ...]
    rationale: str


LEGACY_COMMERCIAL_SECTION_KINDS = {
    "what you'll do": "responsibility",
    "what you will do": "responsibility",
    "key objectives": "responsibility",
    "responsibilities": "responsibility",
    "duties": "responsibility",
    "the impact you will have": "responsibility",
    "what you'll need": "qualification",
    "what you will need": "qualification",
    "qualifications": "qualification",
    "requirements": "qualification",
    "basic qualifications": "qualification",
    "minimum qualifications": "qualification",
    "preferred qualifications": "preferred",
    "skills and experience": "qualification",
    "what you bring": "qualification",
    "what we're looking for": "qualification",
    "what makes a great fit": "qualification",
    "what makes a great fit here": "qualification",
    "who you are": "qualification",
}

COMMERCIAL_SECTION_KINDS = {
    **LEGACY_COMMERCIAL_SECTION_KINDS,
    "primary responsibilities": "responsibility",
    "core responsibilities": "responsibility",
    "key responsibilities": "responsibility",
    "job duties": "responsibility",
    "essential duties": "responsibility",
    "position responsibilities": "responsibility",
    "what you will be doing": "responsibility",
    "what you'll be doing": "responsibility",
    "your responsibilities": "responsibility",
    "people leadership and team development": "responsibility",
    "technical delivery and oversight": "responsibility",
    "client engagement and stakeholder management": "responsibility",
    "operational excellence and strategy": "responsibility",
    "experience and qualifications": "qualification",
    "education and experience": "qualification",
    "education and qualifications": "qualification",
    "desired qualifications": "qualification",
    "required qualifications": "qualification",
    "skills and qualifications": "qualification",
    "knowledge skills and abilities": "qualification",
    "about you": "qualification",
    "who are we looking for": "qualification",
    "skills and abilities": "qualification",
    "technical skills": "qualification",
    "what you will likely bring": "qualification",
    "what you'll likely bring": "qualification",
    "what could set you apart": "preferred",
    "nice to have": "preferred",
}

COMMERCIAL_STOP_HEADINGS = {
    "about us",
    "about the company",
    "about ringcentral",
    "about aptean",
    "benefits",
    "compensation",
    "equal opportunity",
    "legal",
    "physical requirements",
    "what's in it for you",
    "what is in it for you",
}

COMMERCIAL_SUBSECTION_KIND = {
    "required": "qualification",
    "minimum": "qualification",
    "preferred": "preferred",
    "preferred qualifications": "preferred",
}

SECTION_HEADING_RE = re.compile(r"^\s*([^\n:]{2,90}?)\s*:?[ \t]*$")
LIST_PREFIX_RE = re.compile(
    r"^\s*(?:[-*\u2022\u25cf\u25e6\u25aa]+|â€¢+|â—+|\d+[.)]|[A-Za-z][.)])\s*"
)
TERM_CANON: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("microsoft sql server", ("microsoft sql server", "ms sql server", "sql server")),
    ("version control", ("version control", "git", "github", "azure devops", "tfs")),
    ("high availability and disaster recovery", ("ha/dr", "high availability", "disaster recovery")),
    ("contact center", ("contact center", "call center", "customer service operations")),
    ("service level reporting", ("service level reporting", "service levels", "sla reporting")),
    ("customer interaction data", ("customer interaction data", "interaction data", "chat data")),
    ("workforce management", ("workforce management", "workload management", "staffing")),
    ("data models", ("data models", "data modeling", "reporting data models")),
    ("stored procedures", ("stored procedures", "stored procedure")),
    ("views", ("sql views", "database views", "views")),
    ("functions", ("sql functions", "database functions", "functions")),
    ("etl", ("etl", "extract transform load", "data integration")),
    ("training adaptation", ("adjust training", "learning styles", "adapt training")),
)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9+#.]+", " ", (value or "").lower()).strip()


def _element_id(workflow: str, section: str, text: str, grade: str = "") -> str:
    digest = hashlib.sha1(f"{workflow}|{section}|{grade}|{normalize_key(text)}".encode("utf-8")).hexdigest()[:12]
    return f"req-{digest}"


def canonical_terms(text: str) -> tuple[str, ...]:
    lowered = normalize_key(text)
    found: list[str] = []
    for canonical, variants in TERM_CANON:
        if canonical in {"views", "functions"} and not re.search(
            r"\b(?:sql|database|reporting|stored procedure|data model)\b", lowered
        ):
            continue
        if any(normalize_key(variant) in lowered for variant in variants):
            found.append(canonical)
    return tuple(found)


def atomic_capabilities(text: str) -> tuple[str, ...]:
    """Extract compact verb/object clauses without treating them as claims."""

    cleaned = normalize_text(LIST_PREFIX_RE.sub("", text)).rstrip(".")
    chunks = re.split(r"\s*;\s*|\s+(?=and\s+(?:leading|applying|engaging|evaluating|analyzing|administering|designing|developing|collaborating|providing)\b)", cleaned, flags=re.I)
    capabilities: list[str] = []
    for chunk in chunks:
        chunk = normalize_text(chunk)
        if len(chunk.split()) >= 3 and chunk.lower() not in {item.lower() for item in capabilities}:
            capabilities.append(chunk)
    return tuple(capabilities[:8])


def classify_requirement_category(text: str) -> str:
    lowered = normalize_key(text)
    if re.search(r"\b(sql|excel|salesforce|power bi|tableau|jira|servicenow|git|github|azure devops|tfs)\b", lowered):
        return "skill_tool"
    if re.search(
        r"\b(contact center|financial services|nonprofit|manufacturing|saas|philanthrop|federal|"
        r"supply chain|warehouse(?: automation| operations?)?|robotics(?: integration)?|"
        r"fulfillment operations?|eprocurement|e procurement|customer integration capabilities?)\b",
        lowered,
    ):
        return "domain"
    return "activity"


def alternative_requirement_terms(text: str) -> tuple[str, ...]:
    """Return explicit disjunctive noun-phrase alternatives from one requirement."""

    if not re.search(r"(?:,\s*or\s+|\s+or\s+)", text, re.I):
        return ()
    candidate = normalize_text(text).rstrip(".")
    # Prefer the object of a knowledge/experience preposition so leading
    # qualification language cannot become an alternative.
    object_match = re.search(
        r"\b(?:knowledge|experience|expertise|familiarity|background)\s+(?:of|with|in)\s+(.+)$",
        candidate,
        re.I,
    )
    if object_match:
        candidate = object_match.group(1)
    parts = [
        normalize_text(part)
        for part in re.split(r"\s*,\s*|\s+\bor\b\s+", candidate, flags=re.I)
    ]
    cleaned: list[str] = []
    for part in parts:
        value = re.sub(r"^(?:and|or)\s+", "", part, flags=re.I)
        value = re.sub(
            r"^(?:strong|deep|demonstrated|proven|required|preferred)\s+",
            "",
            value,
            flags=re.I,
        )
        words = value.split()
        if 1 <= len(words) <= 7 and value.lower() not in {item.lower() for item in cleaned}:
            cleaned.append(value)
    return tuple(cleaned) if len(cleaned) >= 2 else ()


def _split_requirement_lines(body: str) -> tuple[str, ...]:
    candidates: list[str] = []
    for raw in body.splitlines():
        line = normalize_text(LIST_PREFIX_RE.sub("", raw))
        if not line:
            continue
        if len(line) > 420:
            sentence_parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])", line)
        else:
            sentence_parts = [line]
        for part in sentence_parts:
            part = normalize_text(part)
            if len(part.split()) >= 3:
                candidates.append(part)
    return tuple(dict.fromkeys(candidates))


def _heading_key(value: str) -> str:
    cleaned = normalize_text(value).replace("â€™", "'").replace("’", "'")
    cleaned = re.sub(r"\s*[:\-–—]+\s*$", "", cleaned)
    cleaned = cleaned.replace("&", " and ")
    return normalize_key(cleaned)


def _looks_like_subsection_heading(value: str) -> bool:
    stripped = normalize_text(value)
    if not stripped or LIST_PREFIX_RE.match(stripped) or stripped.endswith((".", "!", "?")):
        return False
    words = re.findall(r"[A-Za-z][A-Za-z'/-]*", stripped.rstrip(":"))
    if not 1 <= len(words) <= 9:
        return False
    significant = [word for word in words if word.lower() not in {"and", "or", "of", "the", "for", "to"}]
    return bool(significant) and sum(word[:1].isupper() for word in significant) >= max(1, len(significant) - 1)


def _legacy_commercial_requirement_sections(job_description: str) -> tuple[tuple[str, str], ...]:
    sections: list[tuple[str, list[str]]] = []
    active: tuple[str, list[str]] | None = None
    for raw in job_description.splitlines():
        stripped = raw.strip()
        heading_match = SECTION_HEADING_RE.match(stripped)
        heading = normalize_text(heading_match.group(1)).lower().replace("’", "'") if heading_match else ""
        if heading in LEGACY_COMMERCIAL_SECTION_KINDS:
            active = (heading, [])
            sections.append(active)
            continue
        if heading_match and active is not None and stripped.endswith(":"):
            active = None
            continue
        if active is not None and stripped:
            active[1].append(stripped)
    return tuple((heading, "\n".join(lines)) for heading, lines in sections if lines)


def _structured_commercial_sections(job_description: str) -> tuple[tuple[str, str, str], ...]:
    sections: list[tuple[str, str, list[str]]] = []
    active_label = ""
    active_kind = ""
    active_lines: list[str] | None = None
    for raw in job_description.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        key = _heading_key(stripped)
        if key in COMMERCIAL_SECTION_KINDS:
            active_label = key
            active_kind = COMMERCIAL_SECTION_KINDS[key]
            active_lines = []
            sections.append((active_label, active_kind, active_lines))
            continue
        if key in COMMERCIAL_STOP_HEADINGS:
            active_label = ""
            active_kind = ""
            active_lines = None
            continue
        if active_lines is None:
            continue
        if key in COMMERCIAL_SUBSECTION_KIND and _looks_like_subsection_heading(stripped):
            active_kind = COMMERCIAL_SUBSECTION_KIND[key]
            active_lines = []
            sections.append((f"{active_label} / {key}", active_kind, active_lines))
            continue
        if _looks_like_subsection_heading(stripped):
            active_lines = []
            sections.append((f"{active_label} / {key}", active_kind, active_lines))
            continue
        active_lines.append(stripped)
    return tuple(
        (label, kind, "\n".join(lines))
        for label, kind, lines in sections
        if lines
    )


def _elements_from_commercial_sections(
    sections: tuple[tuple[str, str, str], ...],
) -> tuple[RequirementElement, ...]:
    elements: list[RequirementElement] = []
    for heading, kind, body in sections:
        for text in _split_requirement_lines(body):
            preferred = kind == "preferred" or bool(re.search(r"\bpreferred\b", text, re.I))
            required = not preferred
            alternatives = alternative_requirement_terms(text)
            elements.append(
                RequirementElement(
                    element_id=_element_id("commercial", heading, text),
                    workflow="commercial",
                    section=heading,
                    text=text,
                    required=required,
                    preferred=preferred,
                    atomic_capabilities=atomic_capabilities(text),
                    canonical_terms=canonical_terms(text),
                    category=classify_requirement_category(text),
                    priority=4 if required else 2,
                    alternative_group_id=(
                        _element_id("commercial-alternatives", heading, text)
                        if alternatives
                        else ""
                    ),
                    alternative_terms=alternatives,
                )
            )
    return tuple(elements)


@lru_cache(maxsize=512)
def parse_commercial_requirements_legacy(job_description: str) -> tuple[RequirementElement, ...]:
    sections = tuple(
        (heading, LEGACY_COMMERCIAL_SECTION_KINDS[heading], body)
        for heading, body in _legacy_commercial_requirement_sections(job_description)
    )
    return _elements_from_commercial_sections(sections)


COMMERCIAL_FALLBACK_SIGNAL_RE = re.compile(
    r"\b(?:ability|assist|collaborat|configur|coordinat|deliver|demonstrat|develop|ensure|"
    r"execut|experience|focus|implement|knowledge|lead|manage|oversee|own|partner|preferred|"
    r"proficien|project|provid|required|responsib|review|skill|support|technical|train|"
    r"translate|work with)\w*\b",
    re.I,
)
COMMERCIAL_FALLBACK_BOILERPLATE_RE = re.compile(
    r"\b(?:equal opportunity|reasonable accommodation|benefits|salary range|privacy|"
    r"applicant|background check|medical|dental|vision|401\(k\)|about the company)\b",
    re.I,
)


def _line_fallback_requirements(job_description: str) -> tuple[str, ...]:
    candidates: list[str] = []
    logical_lines: list[str] = []
    buffer = ""
    for raw in job_description.splitlines():
        stripped_raw = raw.strip()
        if not stripped_raw or re.match(r"^(?:company|job title|role)\s*:", stripped_raw, re.I):
            if buffer:
                logical_lines.append(buffer)
                buffer = ""
            continue
        is_list_item = bool(LIST_PREFIX_RE.match(stripped_raw))
        cleaned_raw = normalize_text(LIST_PREFIX_RE.sub("", stripped_raw))
        if is_list_item or (buffer and re.search(r"[.!?]$", buffer)):
            if buffer:
                logical_lines.append(buffer)
            buffer = cleaned_raw
        else:
            buffer = normalize_text(f"{buffer} {cleaned_raw}")
    if buffer:
        logical_lines.append(buffer)

    for raw in logical_lines:
        stripped = normalize_text(LIST_PREFIX_RE.sub("", raw))
        key = _heading_key(stripped)
        if (
            not stripped
            or key in COMMERCIAL_SECTION_KINDS
            or key in COMMERCIAL_STOP_HEADINGS
            or key in COMMERCIAL_SUBSECTION_KIND
            or re.match(r"^(?:company|job title|role)\s*:", stripped, re.I)
            or COMMERCIAL_FALLBACK_BOILERPLATE_RE.search(stripped)
            or not COMMERCIAL_FALLBACK_SIGNAL_RE.search(stripped)
        ):
            continue
        for line in _split_requirement_lines(stripped):
            if 4 <= len(line.split()) <= 80:
                candidates.append(line)
    return tuple(dict.fromkeys(candidates))


@lru_cache(maxsize=512)
def parse_commercial_posting(job_description: str) -> CommercialParseResult:
    structured_sections = _structured_commercial_sections(job_description)
    structured_requirements = _elements_from_commercial_sections(structured_sections)
    if structured_requirements:
        sections = tuple((label, body) for label, _kind, body in structured_sections)
        return CommercialParseResult(
            sections=sections,
            requirements=structured_requirements,
            parse_mode="structured",
            diagnostics=(
                CommercialParseDiagnostic(
                    "structured_requirements",
                    f"Parsed {len(structured_requirements)} requirements from {len(sections)} recognized sections.",
                ),
            ),
            verified=True,
        )

    fallback_lines = _line_fallback_requirements(job_description)
    if fallback_lines:
        fallback_sections = (("line fallback", "qualification", "\n".join(fallback_lines)),)
        requirements = _elements_from_commercial_sections(fallback_sections)
        return CommercialParseResult(
            sections=(("line fallback", "\n".join(fallback_lines)),),
            requirements=requirements,
            parse_mode="line_fallback",
            diagnostics=(
                CommercialParseDiagnostic(
                    "unrecognized_headings",
                    f"Used deterministic line fallback for {len(requirements)} requirement-shaped lines.",
                ),
            ),
            verified=True,
        )

    return CommercialParseResult(
        sections=(),
        requirements=(),
        parse_mode="whole_posting_fallback",
        diagnostics=(
            CommercialParseDiagnostic(
                "no_trustworthy_requirements",
                "No trustworthy structured or line-fallback requirements were found; analysis must use the whole posting.",
            ),
        ),
        verified=False,
    )


def commercial_requirement_sections(job_description: str) -> tuple[tuple[str, str], ...]:
    return parse_commercial_posting(job_description).sections


def parse_commercial_requirements(job_description: str) -> tuple[RequirementElement, ...]:
    return parse_commercial_posting(job_description).requirements


def _federal_lines(job_description: str) -> list[str]:
    return [normalize_text(line) for line in job_description.splitlines() if normalize_text(line)]


def _federal_deduped_lines(lines: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for line in lines:
        key = normalize_key(line)
        if key and key not in seen:
            seen.add(key)
            result.append(line)
    return tuple(result)


def normalize_federal_grade(value: str) -> str:
    match = re.fullmatch(r"\s*GS\s*-?\s*(\d{1,2})\s*", value or "", re.I)
    return f"GS-{int(match.group(1)):02d}" if match else ""


def _federal_duty_grade(lines: list[str]) -> str:
    for line in lines:
        match = re.match(
            r"^As\s+an?\s+.+?(?:,\s*(GS\s*-?\s*\d{1,2}))?\s+you\s+will\b",
            line,
            re.I,
        )
        if match:
            return normalize_federal_grade(match.group(1) or "")
    return ""


def _qualification_grade_opener(line: str) -> str:
    patterns = (
        r"^You qualify for the\s+(GS\s*-?\s*\d{1,2})\s+grade level\b",
        r"^For the\s+(GS\s*-?\s*\d{1,2})(?:\s+grade level)?\b",
        r"^Specialized Experience\s*:\s*(GS\s*-?\s*\d{1,2})(?:\s+grade level)?\b",
    )
    for pattern in patterns:
        match = re.match(pattern, line, re.I)
        if match:
            return normalize_federal_grade(match.group(1))
    return ""


def _legacy_grade_metadata(job_description: str) -> tuple[str, str, int | None]:
    target_match = re.search(
        r"(?:Specialized Experience\s*:\s*|For Grade\s+)(GS\s*-?\s*\d{1,2})(?:\s+grade level)?",
        job_description,
        re.I,
    )
    equivalent_match = re.search(
        r"equivalent to (?:the\s+)?(GS\s*-?\s*\d{1,2})\s+grade level",
        job_description,
        re.I,
    )
    years_match = re.search(r"\b(?:one(?:\s*\(1\))?|1)\s+year of specialized experience", job_description, re.I)
    return (
        normalize_federal_grade(target_match.group(1)) if target_match else "",
        normalize_federal_grade(equivalent_match.group(1)) if equivalent_match else "",
        1 if years_match else None,
    )


def _experience_lead_metadata(line: str) -> tuple[str, int | None] | None:
    match = re.match(
        r"^Experience\s*:\s*(?:One(?:\s*\(1\))?|1)\s+years?\s+of specialized experience "
        r"at the\s+(GS\s*-?\s*\d{1,2})\s+grade level or equivalent\b",
        line,
        re.I,
    )
    if not match:
        return None
    return normalize_federal_grade(match.group(1)), 1


def _qualification_stop(line: str) -> bool:
    return bool(
        re.match(
            r"^(?:You will be assessed\b|Qualifications\b|Education\b|Questionnaire\b|"
            r"Required Documents\b|How to Apply\b|Application Process\b|Basis of Rating\b|"
            r"Conditions of Employment\b|Additional Information\b)",
            line,
            re.I,
        )
    )


def _split_federal_duties(lines: list[str]) -> tuple[str, ...]:
    duties: list[str] = []
    for line in lines:
        cleaned_line = normalize_text(LIST_PREFIX_RE.sub("", line))
        if not cleaned_line or re.fullmatch(r"-?AND-?|OR", cleaned_line, re.I):
            continue
        for clause in re.split(r";\s*(?:and\s+)?", cleaned_line):
            cleaned = normalize_text(clause).rstrip(";,. ")
            cleaned = re.sub(r"\s+and$", "", cleaned, flags=re.I).strip()
            if len(cleaned.split()) >= 3:
                duties.append(cleaned)
    return _federal_deduped_lines(duties)


def parse_federal_requirement_sections(job_description: str) -> tuple[FederalRequirementSection, ...]:
    """Extract only the role-duty and specialized-experience evidence from a posting.

    Federal announcements reuse words such as "Qualifications" and "evaluated" in
    boilerplate.  Structure, rather than a growing stop-phrase list, keeps those
    routes out of the requirement surface.
    """
    lines = _federal_lines(job_description)
    sections: list[FederalRequirementSection] = []

    duty_grade = _federal_duty_grade(lines)

    # The opening "you will" block is the real core-experience requirement, not
    # the announcement title and agency header that precede it.
    for index, line in enumerate(lines):
        if re.match(r"^As\s+an?\s+.+?\s+you\s+will\b", line, re.I):
            duty_lines: list[str] = [line]
            for following in lines[index + 1 :]:
                if _qualification_grade_opener(following) or re.match(
                    r"^(?:For Grade|Qualifications\b|Specialized Experience\b)", following, re.I
                ):
                    break
                duty_lines.append(following)
            if duty_lines:
                sections.append(
                    FederalRequirementSection(
                        label="Core Experience",
                        kind="core_experience",
                        text=" ".join(duty_lines),
                        weight_group_id="core_experience",
                        grade=duty_grade,
                    )
                )
            break

    # Modern announcements group qualification duties beneath a grade opener.
    # Blank lines are intentionally unavailable after normalization, so block
    # boundaries are structural headers rather than whitespace counts.
    index = 0
    while index < len(lines):
        grade = _qualification_grade_opener(lines[index])
        if not grade:
            index += 1
            continue
        block: list[str] = []
        index += 1
        while index < len(lines):
            if _qualification_grade_opener(lines[index]) or _qualification_stop(lines[index]):
                break
            block.append(lines[index])
            index += 1
        equivalent_grade = ""
        equivalence_years: int | None = None
        duty_start = 0
        for block_index, block_line in enumerate(block):
            metadata = _experience_lead_metadata(block_line)
            if metadata:
                equivalent_grade, equivalence_years = metadata
                duty_start = block_index + 1
                break
        duties = _split_federal_duties(block[duty_start:])
        for duty in duties:
            sections.append(
                FederalRequirementSection(
                    label=f"{grade} Specialized Experience",
                    kind="specialized_experience",
                    text=duty,
                    weight_group_id=f"specialized_experience_{normalize_key(grade).replace(' ', '_')}",
                    grade=grade,
                    equivalent_grade=equivalent_grade,
                    equivalence_years=equivalence_years,
                )
            )

    # Announcements can state specialized experience twice.  Treat each stated
    # list as additive while exact-normalized duplicates are removed below.
    legacy_grade, legacy_equivalent, legacy_years = _legacy_grade_metadata(job_description)
    first_marker = re.compile(r"^Specialized experience is defined as demonstrated experience:?$", re.I)
    second_marker = re.compile(r"^Specialized experience for (?:this )?position includes(?: but is not limited to)?:\s*(.*)$", re.I)
    for index, line in enumerate(lines):
        if first_marker.match(line):
            entries: list[str] = []
            for following in lines[index + 1 :]:
                if re.match(r"^(?:Qualifications\b|For the GS-|Specialized Experience:|OR$|Applicants may also\b|Your qualifications will be evaluated\b)", following, re.I):
                    break
                entries.append(following)
            for entry in _federal_deduped_lines(entries):
                sections.append(
                    FederalRequirementSection("Specialized Experience", "specialized_experience", entry, "specialized_experience_1")
                )
        second = second_marker.match(line)
        if second:
            body = second.group(1).strip()
            # This prose list carries independent duty sentences.  Split it for
            # evidence matching, while keeping one audit-weight group below.
            for duty in re.split(r"(?<=[.!?])\s+(?=[A-Z])", body):
                cleaned = normalize_text(duty)
                if cleaned:
                    sections.append(
                        FederalRequirementSection(
                            "Specialized Experience",
                            "specialized_experience",
                            cleaned,
                            "specialized_experience_2",
                            legacy_grade,
                            legacy_equivalent,
                            legacy_years,
                        )
                    )

    # Keep compact questionnaire-style federal postings usable.  These do not
    # carry the richer structural markers above, but their explicit labels are
    # still requirements rather than boilerplate.
    if not sections:
        current_label = ""
        current_kind = ""
        current_lines: list[str] = []

        def flush_compact() -> None:
            nonlocal current_label, current_kind, current_lines
            if current_label and current_lines:
                sections.append(
                    FederalRequirementSection(
                        current_label,
                        current_kind,
                        " ".join(current_lines),
                        f"compact:{normalize_key(current_label)}",
                        normalize_federal_grade(current_label) if current_kind == "specialized_experience" else "",
                    )
                )
            current_label, current_kind, current_lines = "", "", []

        for line in lines:
            selective = re.match(r"^Selective Factor\s*:\s*(.*)$", line, re.I)
            gs = re.match(r"^(GS-\d+)\s*:\s*(.*)$", line, re.I)
            if selective or gs:
                flush_compact()
                current_label = "Selective Factor" if selective else gs.group(1).upper()
                current_kind = "selective_factor" if selective else "specialized_experience"
                trailing = (selective.group(1) if selective else gs.group(2)).strip()
                if trailing:
                    current_lines.append(trailing)
            elif current_label:
                current_lines.append(line)
        flush_compact()

    deduped: list[FederalRequirementSection] = []
    seen: set[tuple[str, str, str]] = set()
    for section in sections:
        if section.kind == "specialized_experience" and not section.grade and legacy_grade:
            section = FederalRequirementSection(
                section.label,
                section.kind,
                section.text,
                section.weight_group_id,
                legacy_grade,
                legacy_equivalent,
                legacy_years,
            )
        key = (section.kind, section.grade, normalize_key(section.text))
        if key and key not in seen:
            seen.add(key)
            deduped.append(section)
    return tuple(deduped)


def parse_federal_requirements(job_description: str) -> tuple[RequirementElement, ...]:
    return _federal_requirements_from_sections(parse_federal_requirement_sections(job_description))


def parse_federal_competencies(job_description: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    lines = _federal_lines(job_description)
    minimum: list[str] = []
    assessed: list[str] = []
    collecting_minimum = False
    collecting_assessed = False
    for line in lines:
        if re.search(r"each of the (?:\w+|\d+) competencies listed below", line, re.I):
            collecting_minimum = True
            continue
        if collecting_minimum:
            if re.fullmatch(r"-?AND-?", line, re.I):
                collecting_minimum = False
                continue
            match = re.match(r"^([A-Za-z][A-Za-z /-]+?)\s+-\s+", line)
            if match:
                minimum.append(match.group(1).strip())
            continue
        if re.search(r"assessed on the following competencies", line, re.I):
            collecting_assessed = True
            continue
        if collecting_assessed:
            if re.match(r"^(?:You may preview|Basis of Rating|Required Documents|How to Apply)\b", line, re.I):
                break
            cleaned = normalize_text(LIST_PREFIX_RE.sub("", line)).rstrip(".")
            if cleaned and len(cleaned.split()) <= 6:
                assessed.append(cleaned)
    return _federal_deduped_lines(minimum), _federal_deduped_lines(assessed)


def _federal_requirements_from_sections(
    sections: tuple[FederalRequirementSection, ...],
) -> tuple[RequirementElement, ...]:
    elements: list[RequirementElement] = []
    for section in sections:
        if section.kind != "specialized_experience":
            continue
        text = section.text
        elements.append(
            RequirementElement(
                element_id=_element_id("federal", "specialized_experience", text, section.grade),
                workflow="federal",
                section="specialized_experience",
                text=text,
                required=True,
                preferred=False,
                grade=section.grade,
                atomic_capabilities=atomic_capabilities(text),
                canonical_terms=canonical_terms(text),
                category=classify_requirement_category(text),
                priority=5,
                requirement_group_id=section.weight_group_id,
            )
        )
    return tuple(elements)


def select_federal_grade(
    sections: tuple[FederalRequirementSection, ...],
    target_grade: str = "",
) -> tuple[str, tuple[str, ...], tuple[FederalParseDiagnostic, ...]]:
    available_grades = tuple(
        dict.fromkeys(section.grade for section in sections if section.kind == "specialized_experience" and section.grade)
    )
    diagnostics: list[FederalParseDiagnostic] = []
    requested = normalize_federal_grade(target_grade)
    if target_grade and not requested:
        diagnostics.append(
            FederalParseDiagnostic(
                "invalid_target_grade",
                f"The requested grade {target_grade!r} is not a valid GS grade.",
                True,
            )
        )
    if len(available_grades) > 1:
        diagnostics.append(
            FederalParseDiagnostic(
                "multiple_qualification_grades",
                f"Qualification blocks were found for {', '.join(available_grades)}; the highest listed grade is the default.",
                False,
            )
        )
    if requested:
        if requested in available_grades:
            return requested, available_grades, tuple(diagnostics)
        diagnostics.append(
            FederalParseDiagnostic(
                "requested_grade_unavailable",
                f"Requested grade {requested} was not found among the parsed qualification blocks.",
                True,
            )
        )
        return requested, available_grades, tuple(diagnostics)
    if available_grades:
        selected = max(available_grades, key=lambda grade: int(grade.split("-")[1]))
        return selected, available_grades, tuple(diagnostics)
    diagnostics.append(
        FederalParseDiagnostic(
            "no_qualification_grade",
            "No grade-bearing federal qualification block could be parsed.",
            True,
        )
    )
    return "", available_grades, tuple(diagnostics)


def parse_federal_posting(job_description: str, target_grade: str = "") -> FederalParseResult:
    lines = _federal_lines(job_description)
    sections = parse_federal_requirement_sections(job_description)
    requirements = _federal_requirements_from_sections(sections)
    minimum, assessed = parse_federal_competencies(job_description)
    selected_grade, available_grades, selection_diagnostics = select_federal_grade(sections, target_grade)
    diagnostics = list(selection_diagnostics)
    duty_grade = _federal_duty_grade(lines)

    qualification_openers = tuple(
        grade for line in lines if (grade := _qualification_grade_opener(line))
    )
    parsed_requirement_grades = {requirement.grade for requirement in requirements if requirement.grade}
    for grade in dict.fromkeys(qualification_openers):
        if grade not in parsed_requirement_grades:
            diagnostics.append(
                FederalParseDiagnostic(
                    "qualification_block_without_requirements",
                    f"The {grade} qualification marker did not yield any capability requirements.",
                    True,
                )
            )

    selected_sections = tuple(
        section
        for section in sections
        if section.kind == "specialized_experience" and section.grade == selected_grade
    )
    selected_requirements = tuple(requirement for requirement in requirements if requirement.grade == selected_grade)
    equivalent_grade = next((section.equivalent_grade for section in selected_sections if section.equivalent_grade), "")
    equivalence_years = next(
        (section.equivalence_years for section in selected_sections if section.equivalence_years is not None),
        None,
    )
    if selected_grade and not selected_sections:
        diagnostics.append(
            FederalParseDiagnostic(
                "selected_grade_block_missing",
                f"No parsed qualification block is available for selected grade {selected_grade}.",
                True,
            )
        )
    if not selected_requirements:
        diagnostics.append(
            FederalParseDiagnostic(
                "zero_selected_requirements",
                "The selected federal grade has zero parsed capability requirements.",
                True,
            )
        )
    if duty_grade and selected_grade and duty_grade != selected_grade:
        diagnostics.append(
            FederalParseDiagnostic(
                "duty_qualification_grade_mismatch",
                f"The duty header names {duty_grade}, while the selected qualification grade is {selected_grade}.",
                True,
            )
        )
    verified = not any(diagnostic.requires_draft for diagnostic in diagnostics)
    return FederalParseResult(
        duty_grade=duty_grade,
        available_grades=available_grades,
        selected_grade=selected_grade,
        equivalent_grade=equivalent_grade,
        equivalence_years=equivalence_years,
        sections=sections,
        requirements=requirements,
        minimum_competencies=minimum,
        assessed_competencies=assessed,
        diagnostics=tuple(diagnostics),
        verified=verified,
    )


def parse_grade_clause(job_description: str) -> tuple[str, str, int | None]:
    result = parse_federal_posting(job_description)
    return result.selected_grade, result.equivalent_grade, result.equivalence_years


def _display_title(official_title: str, requirement_text: str) -> str:
    title = normalize_text(official_title)
    parts = [normalize_text(part) for part in re.split(r"\s+-\s+", title) if normalize_text(part)]
    if len(parts) < 2:
        return title
    requirement_words = set(normalize_key(requirement_text).split())
    kept = [parts[0]]
    for part in parts[1:]:
        content = {word for word in normalize_key(part).split() if len(word) > 3 and word not in {"focus", "track", "remote", "urgent"}}
        if content and content & requirement_words:
            kept.append(part)
    return " - ".join(kept)


def build_target_context(
    job_description: str,
    *,
    workflow: str = "commercial",
    target_grade: str = "",
) -> TargetContext:
    # Lazy imports avoid making the lower-level parser depend on resume builders.
    import resume_analysis

    official_title = (
        resume_analysis.extract_federal_official_title(job_description)
        if workflow == "federal"
        else resume_analysis.extract_job_title(job_description)
    ) or ""
    company, identity_source = resume_analysis.extract_semantic_organization(
        job_description,
        workflow=workflow,
    )
    lane = resume_analysis.job_problem_profile(job_description).primary_lane
    if workflow == "federal":
        parsed = parse_federal_posting(job_description, target_grade=target_grade)
        requirements = tuple(
            requirement for requirement in parsed.requirements if requirement.grade == parsed.selected_grade
        )
        minimum, assessed = parsed.minimum_competencies, parsed.assessed_competencies
        selected_grade = parsed.selected_grade
        equivalent_grade, years = parsed.equivalent_grade, parsed.equivalence_years
        sections = (("specialized_experience", "\n".join(item.text for item in requirements)),)
        agency = resume_analysis.extract_federal_agency_name(job_description) or ""
        subagency = resume_analysis.extract_federal_subagency_name(job_description) or ""
        output_label = resume_analysis.extract_target_output_label(
            job_description,
            workflow="federal",
            selected_grade=selected_grade,
        )
        available_grades = parsed.available_grades
        duty_grade = parsed.duty_grade
        diagnostics = parsed.diagnostics
        verified = parsed.verified
        parse_mode = "structured"
    else:
        parsed = parse_commercial_posting(job_description)
        requirements = parsed.requirements
        minimum, assessed = (), ()
        selected_grade, equivalent_grade, years = "", "", None
        sections = parsed.sections
        agency, subagency = "", ""
        output_label = company or official_title
        available_grades, duty_grade = (), ""
        diagnostics, verified, parse_mode = parsed.diagnostics, parsed.verified, parsed.parse_mode
    requirement_text = "\n".join(body for _heading, body in sections)
    display = _display_title(official_title, requirement_text)
    return TargetContext(
        workflow=workflow,
        company=company,
        official_title=official_title,
        display_title=display,
        matching_title=normalize_key(display),
        lane=lane,
        sanitized_job_description=job_description,
        requirement_sections=sections,
        requirements=requirements,
        target_grade=selected_grade,
        equivalent_grade=equivalent_grade,
        equivalence_years=years,
        minimum_competencies=minimum,
        assessed_competencies=assessed,
        agency=agency,
        subagency=subagency,
        output_label=output_label,
        identity_source=identity_source,
        available_grades=available_grades,
        duty_grade=duty_grade,
        parse_mode=parse_mode,
        parse_diagnostics=diagnostics,
        verified=verified,
    )


def commercial_requirement_coverage(
    job_description: str,
    resume_text: str,
) -> tuple[RequirementCoverage, ...]:
    elements = parse_commercial_requirements(job_description)
    resume_key = normalize_key(resume_text)
    resume_tokens = set(resume_key.split())
    stop = {
        "ability", "client", "clients", "customer", "customers", "company", "experience", "strong",
        "support", "work", "working", "required", "preferred", "skills", "other", "provide", "maintain",
        "plus", "software", "track", "verbal", "tasks", "updates", "setup", "team", "members", "using",
    }
    coverages: list[RequirementCoverage] = []
    for element in elements:
        canonical_hits = tuple(term for term in element.canonical_terms if normalize_key(term) in resume_key)
        content_tokens = {
            token for token in normalize_key(element.text).split()
            if len(token) >= 6 and token not in stop
        }
        token_hits = tuple(sorted(content_tokens & resume_tokens))
        if canonical_hits or len(token_hits) >= 3:
            status = RequirementStatus.DIRECT
            rationale = "Visible resume language covers the named capability."
            matches = tuple(dict.fromkeys((*canonical_hits, *token_hits[:5])))
        elif token_hits:
            status = RequirementStatus.ADJACENT
            rationale = "Related source language is visible, but the full requirement is not established."
            matches = token_hits[:5]
        elif element.preferred:
            status = RequirementStatus.TRANSFERABLE
            rationale = "Preferred requirement is not explicit; broader transferable experience may apply."
            matches = ()
        else:
            status = RequirementStatus.UNSUPPORTED
            rationale = "No visible source-supported match was found."
            matches = ()
        coverages.append(RequirementCoverage(element, status, matches, rationale))
    return tuple(coverages)
