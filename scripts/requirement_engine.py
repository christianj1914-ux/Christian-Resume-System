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


@dataclass(frozen=True)
class FederalRequirementSection:
    """A structural federal requirement unit shared by both federal consumers."""

    label: str
    kind: str
    text: str
    weight_group_id: str


@dataclass(frozen=True)
class RequirementCoverage:
    element: RequirementElement
    status: RequirementStatus
    matched_terms: tuple[str, ...]
    rationale: str


COMMERCIAL_SECTION_KINDS = {
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

SECTION_HEADING_RE = re.compile(r"^\s*([^\n:]{2,90}?)\s*:?[ \t]*$")
LIST_PREFIX_RE = re.compile(r"^\s*(?:[-*•]+|\d+[.)]|[A-Za-z][.)])\s*")
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


def commercial_requirement_sections(job_description: str) -> tuple[tuple[str, str], ...]:
    sections: list[tuple[str, list[str]]] = []
    active: tuple[str, list[str]] | None = None
    for raw in job_description.splitlines():
        stripped = raw.strip()
        heading_match = SECTION_HEADING_RE.match(stripped)
        heading = normalize_text(heading_match.group(1)).lower().replace("’", "'") if heading_match else ""
        if heading in COMMERCIAL_SECTION_KINDS:
            active = (heading, [])
            sections.append(active)
            continue
        if heading_match and active is not None and stripped.endswith(":"):
            active = None
            continue
        if active is not None and stripped:
            active[1].append(stripped)
    return tuple((heading, "\n".join(lines)) for heading, lines in sections if lines)


def parse_commercial_requirements(job_description: str) -> tuple[RequirementElement, ...]:
    elements: list[RequirementElement] = []
    for heading, body in commercial_requirement_sections(job_description):
        kind = COMMERCIAL_SECTION_KINDS[heading]
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


def parse_federal_requirement_sections(job_description: str) -> tuple[FederalRequirementSection, ...]:
    """Extract only the role-duty and specialized-experience evidence from a posting.

    Federal announcements reuse words such as "Qualifications" and "evaluated" in
    boilerplate.  Structure, rather than a growing stop-phrase list, keeps those
    routes out of the requirement surface.
    """
    lines = _federal_lines(job_description)
    sections: list[FederalRequirementSection] = []

    # The opening "you will" block is the real core-experience requirement, not
    # the announcement title and agency header that precede it.
    for index, line in enumerate(lines):
        if re.match(r"^As an .+?,\s*you will:\s*$", line, re.I):
            duty_lines: list[str] = [line]
            for following in lines[index + 1 :]:
                if re.match(r"^(?:For Grade|Qualifications\b|Specialized Experience\b)", following, re.I):
                    break
                duty_lines.append(following)
            if duty_lines:
                sections.append(
                    FederalRequirementSection(
                        label="Core Experience",
                        kind="core_experience",
                        text=" ".join(duty_lines),
                        weight_group_id="core_experience",
                    )
                )
            break

    # Announcements can state specialized experience twice.  Treat each stated
    # list as additive while exact-normalized duplicates are removed below.
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
                    )
                )
            current_label, current_kind, current_lines = "", "", []

        for line in lines:
            selective = re.match(r"^Selective Factor\s*:\s*(.*)$", line, re.I)
            gs = re.match(r"^(GS-\d+)\s*:\s*(.*)$", line, re.I)
            if selective or gs:
                flush_compact()
                current_label = "Selective Factor" if selective else gs.group(1).upper()
                current_kind = "selective_factor" if selective else "gs_level"
                trailing = (selective.group(1) if selective else gs.group(2)).strip()
                if trailing:
                    current_lines.append(trailing)
            elif current_label:
                current_lines.append(line)
        flush_compact()

    deduped: list[FederalRequirementSection] = []
    seen: set[tuple[str, str]] = set()
    for section in sections:
        key = (section.kind, normalize_key(section.text))
        if key and key not in seen:
            seen.add(key)
            deduped.append(section)
    return tuple(deduped)


def parse_federal_requirements(job_description: str) -> tuple[RequirementElement, ...]:
    grade, _equivalent, _years = parse_grade_clause(job_description)
    elements: list[RequirementElement] = []
    for section in parse_federal_requirement_sections(job_description):
        if section.kind != "specialized_experience":
            continue
        text = section.text
        elements.append(
            RequirementElement(
                element_id=_element_id("federal", "specialized_experience", text, grade),
                workflow="federal",
                section="specialized_experience",
                text=text,
                required=True,
                preferred=False,
                grade=grade,
                atomic_capabilities=atomic_capabilities(text),
                canonical_terms=canonical_terms(text),
                category=classify_requirement_category(text),
                priority=5,
                requirement_group_id=section.weight_group_id,
            )
        )
    return tuple(elements)


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


def parse_grade_clause(job_description: str) -> tuple[str, str, int | None]:
    target_match = re.search(
        r"Specialized Experience\s*(?::\s*)?(GS-\d+)\s+(?:grade\s+)?level",
        job_description,
        re.I,
    )
    equivalent_match = re.search(r"equivalent to the\s+(GS-\d+)\s+grade level", job_description, re.I)
    years_match = re.search(r"\b(one|1)\s+year of specialized experience", job_description, re.I)
    return (
        target_match.group(1).upper() if target_match else "",
        equivalent_match.group(1).upper() if equivalent_match else "",
        1 if years_match else None,
    )


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


def build_target_context(job_description: str, *, workflow: str = "commercial") -> TargetContext:
    # Lazy imports avoid making the lower-level parser depend on resume builders.
    import resume_analysis

    official_title = resume_analysis.extract_job_title(job_description) or ""
    company = resume_analysis.extract_company_name(job_description) or ""
    lane = resume_analysis.job_problem_profile(job_description).primary_lane
    if workflow == "federal":
        requirements = parse_federal_requirements(job_description)
        minimum, assessed = parse_federal_competencies(job_description)
        target_grade, equivalent_grade, years = parse_grade_clause(job_description)
        sections = (("specialized_experience", "\n".join(item.text for item in requirements)),)
    else:
        requirements = parse_commercial_requirements(job_description)
        minimum, assessed = (), ()
        target_grade, equivalent_grade, years = "", "", None
        sections = commercial_requirement_sections(job_description)
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
        target_grade=target_grade,
        equivalent_grade=equivalent_grade,
        equivalence_years=years,
        minimum_competencies=minimum,
        assessed_competencies=assessed,
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
