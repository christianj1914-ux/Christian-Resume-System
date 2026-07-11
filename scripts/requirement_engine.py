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
    parser_fallback_required: bool = False


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
    if re.search(r"\b(contact center|financial services|nonprofit|manufacturing|saas|philanthrop|federal)\b", lowered):
        return "domain"
    return "activity"


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
                )
            )
    return tuple(elements)


def _federal_block(job_description: str, start_pattern: str, end_pattern: str) -> str:
    match = re.search(start_pattern, job_description, re.I)
    if not match:
        return ""
    remainder = job_description[match.end():]
    end = re.search(end_pattern, remainder, re.I | re.M)
    return remainder[: end.start()] if end else remainder


def parse_federal_requirements(job_description: str) -> tuple[RequirementElement, ...]:
    grade_match = re.search(r"Specialized Experience\s+(GS-\d+)\s+Level", job_description, re.I)
    grade = grade_match.group(1).upper() if grade_match else ""
    body = _federal_block(
        job_description,
        r"Specialized Experience\s+GS-\d+\s+Level:.*?includes:\s*",
        r"^\s*(?:How you will be evaluated|Education|Time in Grade|Conditions of Employment)\b",
    )
    elements: list[RequirementElement] = []
    for text in _split_requirement_lines(body):
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
            )
        )
    return tuple(elements)


def parse_federal_competencies(job_description: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    minimum: list[str] = []
    minimum_match = re.search(
        r"following nine competencies:\s*(.+?)(?:\n\s*Specialized Experience|\n\s*AND\b)",
        job_description,
        re.I | re.S,
    )
    if minimum_match:
        for item in re.split(r"(?:,\s*|\s+and\s+)(?=\d+\))", minimum_match.group(1)):
            cleaned = normalize_text(re.sub(r"^\d+\)\s*", "", item)).rstrip(".")
            if cleaned:
                minimum.append(cleaned)

    assessed_body = _federal_block(
        job_description,
        r"assessed on the following competencies[^:]*:\s*",
        r"^\s*(?:You may preview|Basis of Rating|Required Documents|How to Apply)\b",
    )
    assessed: list[str] = []
    for line in assessed_body.splitlines():
        cleaned = normalize_text(LIST_PREFIX_RE.sub("", line)).rstrip(".")
        if cleaned and len(cleaned.split()) <= 6 and not cleaned.lower().startswith("you will"):
            assessed.append(cleaned)
    return tuple(dict.fromkeys(minimum)), tuple(dict.fromkeys(assessed))


def parse_grade_clause(job_description: str) -> tuple[str, str, int | None]:
    target_match = re.search(r"Specialized Experience\s+(GS-\d+)\s+Level", job_description, re.I)
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
        parser_fallback_required=len(requirements) < 3,
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
