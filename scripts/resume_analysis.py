#!/usr/bin/env python3
"""Job-description analysis and targeting helpers for resume workflows."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import business_context
from config.job_profiles import (
    BRIDGE_EVIDENCE_AREAS,
    EMPLOYER_CONTEXTS,
    POOR_FIT_REQUIREMENT_AREAS,
    PRESALES_SIGNALS,
    SPECIALTY_GAP_AREAS,
    STORY_LENSES,
    TARGETING_LANES,
    UNSUPPORTED_REQUIREMENT_PATTERNS,
)
from config.company_profiles import match_company_profile
from config.language_rules import GENERIC_SOFT_KEYWORDS, PLACEHOLDER_PATTERNS
from utils import fail

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT_ROOT / "source"
IMPLEMENTATION_RESUME = SOURCE_DIR / "Estrada_Resume_Implementation.docx"
PRESALES_CSM_RESUME = SOURCE_DIR / "Estrada_Resume_PreSales_CSM.docx"

MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
ZERO_WIDTH_CHAR_RE = re.compile(r"[\u200b\u200c\u200d\ufeff]")


def contains_search_term(text: str, term: str) -> bool:
    normalized = ZERO_WIDTH_CHAR_RE.sub(" ", text.lower())
    parts = ZERO_WIDTH_CHAR_RE.sub(" ", term.lower()).strip().split()
    if not parts:
        return False

    last = parts[-1]
    variants = [" ".join(parts)]
    if last.endswith("ies") and len(last) > 4:
        variants.append(" ".join(parts[:-1] + [last[:-3] + "y"]))
    elif last.endswith("es") and len(last) > 4:
        singular_base = last[:-2]
        if singular_base.endswith(("ss", "sh", "ch", "x", "z")):
            variants.append(" ".join(parts[:-1] + [singular_base]))
    elif last.endswith("s") and len(last) > 4 and not last.endswith(("ss", "ics")):
        variants.append(" ".join(parts[:-1] + [last[:-1]]))
    elif not last.endswith("s") and not last.endswith("ing"):
        if last.endswith("y") and len(last) > 3 and last[-2] not in "aeiou":
            variants.append(" ".join(parts[:-1] + [last[:-1] + "ies"]))
        elif last.endswith(("ss", "sh", "ch", "x", "z")):
            variants.append(" ".join(parts[:-1] + [last + "es"]))
        else:
            variants.append(" ".join(parts[:-1] + [last + "s"]))

    return any(
        re.search(rf"(?<![a-z0-9]){re.escape(variant)}(?![a-z0-9])", normalized) is not None
        for variant in dict.fromkeys(variants)
    )


def is_valid_job_title(value: str) -> bool:
    stripped = value.strip()
    normalized = normalize_compare(stripped)
    return (
        is_valid_filename_piece(value)
        and not looks_like_sentence_fragment(value)
        and not stripped.startswith("#")
        and not re.match(r"(?i)^#?li[- ]?(hybrid|remote|onsite|on site)\b", stripped)
        and normalized not in {"hybrid", "remote", "onsite", "on site"}
    )


@dataclass(frozen=True)
class JobProblemProfile:
    primary_lane: str
    lane_label: str
    core_problem: str
    audience: str
    outcomes: tuple[str, ...]
    direct_matches: tuple[str, ...]
    adjacent_matches: tuple[str, ...]
    unsupported_requirements: tuple[str, ...]
    safe_terms: tuple[str, ...]
    specialty_matches: tuple[str, ...] = ()
    specialty_gaps: tuple[str, ...] = ()


CORPORATE_STRATEGY_PROFILE = {
    "key": "corporate_strategy",
    "label": "Corporate Strategy and Consulting",
    "problem": "ambiguous client problems that need structured analysis, executive alignment, and practical recommendations that hold up in execution",
    "audience": "clients, executives, case teams, and cross-functional stakeholders",
    "outcomes": ("clear recommendations", "client confidence", "decision quality", "measurable follow-through"),
}

GENERAL_CONSULTING_EXCLUSION_SIGNALS = (
    "implementation consultant",
    "solutions implementation consultant",
    "solution implementation consultant",
    "technical consultant",
    "professional services consultant",
    "customer success consultant",
    "solution consultant",
    "solutions consultant",
    "pre-sales",
    "presales",
    "sales engineer",
    "go-live",
    "data migration",
    "customer onboarding",
    "technical implementation",
    "implementation delivery",
    "change management",
    "change enablement",
    "organizational change",
)

GENERAL_CONSULTING_ROLE_SIGNALS = (
    "management consulting",
    "strategy consulting",
    "consulting firm",
    "advisory",
    "case team",
    "case teams",
    "associate consultant",
    "associate consultants",
    "analyses",
    "analysis",
    "recommendation",
    "recommendations",
    "executive",
    "executives",
    "client",
    "clients",
    "private equity",
)

STRATEGY_CONSULTING_TITLE_SIGNALS = (
    "strategy",
    "strategic",
    "transformation",
    "operating model",
)

STRATEGY_CONSULTING_ROLE_WORDS = (
    "consultant",
    "consulting",
    "advisor",
    "advisory",
    "analyst",
    "associate",
    "manager",
)

STRATEGY_CONSULTING_TITLE_EXCLUSION_SIGNALS = (
    "implementation",
    "technical",
    "solution",
    "solutions",
    "pre-sales",
    "presales",
    "sales engineer",
    "go-live",
    "migration",
    "customer success",
    "support",
    "architect",
    "engineer",
)

CONSULTING_KEYWORD_SOURCE_SIGNALS = (
    "consulting",
    "consultant",
    "client",
    "clients",
    "case",
    "cases",
    "analysis",
    "analyses",
    "advisory",
    "strategy",
    "strategic",
    "executive",
    "stakeholder",
    "decision",
    "recommendation",
    "outcome",
    "private equity",
)

AUDIT_NOISE_KEYWORDS = {
    "about",
    "addition",
    "advance",
    "affinity",
    "allow",
    "allows",
    "also",
    "analytical",
    "anything",
    "apply",
    "assigned",
    "because",
    "below",
    "best",
    "bonds",
    "build",
    "building",
    "built",
    "advanced",
    "capabilities",
    "career",
    "careers",
    "come",
    "community",
    "competence",
    "competitor",
    "contribute",
    "contributes",
    "contributing",
    "connections",
    "consistently",
    "consistent",
    "critical",
    "curious",
    "determined",
    "dozens",
    "enduring",
    "enjoy",
    "entry",
    "globe",
    "global",
    "guru",
    "functional",
    "guidance",
    "including",
    "highest",
    "high",
    "home",
    "idea",
    "into",
    "interests",
    "learn",
    "learning",
    "major",
    "members",
    "mentorship",
    "mixture",
    "nothing",
    "office",
    "opportunity",
    "people",
    "places",
    "prepare",
    "prepared",
    "prepares",
    "proven",
    "professionally",
    "rank",
    "reason",
    "reasons",
    "sharing",
    "related",
    "require",
    "required",
    "requires",
    "review",
    "reviews",
    "serve",
    "serves",
    "serving",
    "strong",
    "specification",
    "specifications",
    "suits",
    "support",
    "supporting",
    "successful",
    "sustainable",
    "senior",
    "similar",
    "team-based",
    "toolkit",
    "tour",
    "trained",
    "travel",
    "typically",
    "visiting",
    "will",
    "within",
    "working",
    "meet",
    "both",
    "provides",
    "provide",
    "demonstrates",
    "demonstrate",
    "defining",
    "defines",
    "define",
    "coordinates",
    "coordinate",
    "executes",
    "execute",
    "understanding",
    "knowledge",
    "function",
    "potential",
}

AUDIT_PRIORITY_KEYWORDS = {
    "adoption",
    "advisory",
    "analysis",
    "analyses",
    "ai-assisted",
    "analytics",
    "assessment",
    "accessibility",
    "change",
    "client",
    "clients",
    "configuration",
    "consultant",
    "consulting",
    "customer",
    "customers",
    "data",
    "decision",
    "decisions",
    "delivery",
    "discovery",
    "executive",
    "executives",
    "fairness",
    "go-live",
    "implementation",
    "integration",
    "kpi",
    "migration",
    "measurement",
    "operations",
    "process",
    "program",
    "quality",
    "qbr",
    "qbrs",
    "recommendation",
    "recommendations",
    "reporting",
    "requirements",
    "risk",
    "scope",
    "solution",
    "solutions",
    "stakeholder",
    "stakeholders",
    "status",
    "strategy",
    "strategic",
    "technical",
    "training",
    "transformation",
    "validation",
    "workshop",
    "workshops",
}

CONSULTING_TAXONOMY_PHRASES = {
    "management consulting",
    "strategy consulting",
}

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "our",
    "that",
    "the",
    "their",
    "this",
    "to",
    "with",
    "you",
    "your",
    "plus",
    "software",
    "track",
    "verbal",
    "tasks",
    "updates",
    "setup",
    "team",
    "members",
    "using",
}

AUDIT_BLOCKED_PHRASES = {
    "delivery training",
    "documentation training",
}

AUDIT_ACTION_LEAD_WORDS = {
    "answer",
    "answers",
    "build",
    "builds",
    "close",
    "closes",
    "communicate",
    "communicates",
    "coordinate",
    "coordinates",
    "contribute",
    "contributes",
    "contributing",
    "define",
    "defines",
    "demonstrate",
    "demonstrates",
    "develop",
    "develops",
    "document",
    "documents",
    "enable",
    "enables",
    "evaluate",
    "evaluates",
    "evaluating",
    "execute",
    "executes",
    "identify",
    "identifies",
    "incorporate",
    "incorporates",
    "maintain",
    "maintains",
    "meet",
    "meets",
    "participate",
    "participates",
    "participating",
    "prepare",
    "prepares",
    "perform",
    "performs",
    "performing",
    "provide",
    "provides",
    "review",
    "reviews",
    "solve",
    "solves",
    "solving",
}

AUDIT_LOW_SIGNAL_TRAIL_WORDS = {
    "abilities",
    "ability",
    "effort",
    "efforts",
    "expectation",
    "expectations",
    "operation",
    "operations",
    "plan",
    "plans",
    "question",
    "questions",
    "requirement",
    "requirements",
    "solution",
    "solutions",
    "skills",
}

AUDIT_ALLOWED_QUALITY_HEADS = {
    "content",
    "data",
    "delivery",
    "implementation",
    "model",
    "service",
    "workflow",
}

AUDIT_PHRASE_TAIL_PRIORITY_WORDS = {
    "adoption",
    "center",
    "centers",
    "delivery",
    "integration",
    "management",
    "migration",
    "operations",
    "operation",
    "power",
    "quality",
    "readiness",
    "reporting",
    "scope",
    "service",
    "support",
    "training",
}

BLOCKED_FILENAME_NAMES = {
    "resume",
    "targeted",
    "targeted resume",
    "custom resume",
    "tailored resume",
    "company",
    "company name",
    "job title",
    "us",
    "about us",
}

MAX_OUTPUT_TARGET_LENGTH = 120
AUDIT_STATUS_ORDER = {"PASS": 0, "BRIDGE": 1, "FAIL": 2, "POOR": 3}

ROLE_REQUIREMENT_SECTION_RE = re.compile(
    r"^\s*(?:"
    r"position summary|job summary|role summary|position overview|job overview|summary|overview|"
    r"essential responsibilities|essential duties(?: and responsibilities)?|responsibilities|"
    r"key responsibilities|duties|what you(?:'|’)ll do|what you will do|"
    r"knowledge,\s*skills(?:,?\s*and abilities)?|knowledge and skills|skills and abilities|"
    r"education|experience|education (?:and|&)\s*experience|skills|qualifications|requirements|"
    r"licenses and certifications|required licenses(?: and| &| and/or)? certifications|"
    r"required qualifications|preferred qualifications|minimum qualifications|basic qualifications"
    r")\s*:?\s*$",
    re.I,
)

BOILERPLATE_SECTION_RE = re.compile(
    r"^\s*(?:"
    r"about\s+(?:us|the company|our company|the team)|company overview|who we are|"
    r"benefits|compensation|salary|pay range|travel required|physical.*demands|mental demands|"
    r"working conditions|position type|work environment|disclaimer|compliance requirement|"
    r"equal employment opportunity|eeo|privacy notice|privacy policy|data privacy|"
    r"reasonable accommodation|background check|drug screen"
    r")\s*:?\s*$",
    re.I,
)

BOILERPLATE_LINE_RE = re.compile(
    r"\b("
    r"comprehensive inventory of (?:all )?duties|general nature and essential duties|"
    r"code of business conduct|company(?:'s)? handbook|privacy policies? and procedures|"
    r"notice of privacy practices|information security policy|covered information|cardholder data|"
    r"confidential customer information|employees? must comply|must comply with both|"
    r"applicable federal and state laws|company policies and training requirements|"
    r"equal opportunity employer|reasonable accommodation|background check|drug screen|"
    r"benefits package|salary range|pay range|travel regularly from|lifting:"
    r")\b",
    re.I,
)

IMPORTANT_SHORT_ATS_TERMS = {"ai", "bi", "cs", "cx", "erp", "qbr", "crm", "uat", "sql", "api", "sso", "etl", "kpi"}

SUMMARY_PLACEMENT_TERMS = {
    "adoption", "ai-assisted", "analytics", "assessment", "automation", "bi", "business intelligence", "change", "client", "customer",
    "dashboard", "dashboards", "data", "etl", "fairness", "implementation", "kpi", "measurement", "operations",
    "power bi", "program", "project management", "qbr", "reporting", "sql", "stakeholder",
    "strategy", "training", "transformation", "uat", "validation", "workshops", "process", "process improvement",
    "continuous improvement", "root cause", "operational efficiency", "standard work", "quality", "workflow validation", "accessibility",
}

COLOR_AUDIT_BLOCKED_KEYWORDS = {
    "ability", "about", "above", "across", "also", "around", "best", "build", "care",
    "companies", "company", "completion", "deliver", "delivery", "ensure", "including",
    "description", "here", "job", "key", "meet", "must", "needs", "only", "other",
    "overall", "people", "provide", "responsibilities", "strong", "support", "their",
    "through", "using", "while", "within", "working",
}

COLOR_AUDIT_PRIORITY_TERMS = (
    "process improvement", "process design", "process analyst", "lean six sigma", "six sigma", "lean",
    "root cause", "operational metrics", "operational efficiency", "service quality",
    "customer experience", "cost benefit", "project management", "excel", "access", "visio",
    "agile", "standard work", "work segmentation", "continuous improvement", "action plans",
    "sop", "standard operating procedure", "quality control", "risk controls", "bottleneck",
    "cycle time", "waste", "pilot", "feedback loops", "lessons learned", "retrospective",
)

UNSUPPORTED_OWNERSHIP_LABELS = {
    "HR Policy Ownership",
    "Legal or Compliance Program Ownership",
    "DEI Governance Ownership",
    "Enterprise AI Ethics or Disclosure Ownership",
    "Enterprise AI Strategy Ownership",
}

OWNERSHIP_ACTION_RE = re.compile(
    r"\b(own|owns|owned|lead|leads|leading|develop|develops|developing|create|creates|creating|"
    r"draft|drafts|drafting|design|designs|designing|govern|governs|governing|manage|manages|"
    r"managing|establish|establishes|establishing|set|sets|setting|maintain|maintains|"
    r"maintaining|administer|administers|administering|oversee|oversees|overseeing|drive|drives|driving)\b",
    re.I,
)
DIRECT_REPORTING_LINE_RE = re.compile(
    r"\bdirect report(?:s)?\s+(?:to\s+)?(?:[a-z/&.-]+\s+){0,4}(manager|director|vp|vice president|head|lead|chief)\b",
    re.I,
)
EXPLICIT_PEOPLE_MANAGEMENT_RE = re.compile(
    r"\b(manage(?:s|d|ing)?\s+(?:a|the)?\s*team|lead(?:s|ing)?\s+a\s+team|supervis(?:e|es|ed|ing)|"
    r"people manager|manage(?:s|d|ing)?\s+\d+\s+direct reports?|has\s+\d+\s+direct reports?)\b",
    re.I,
)

def choose_resume(job_description: str) -> Path:
    normalized = job_description.lower()
    matches = {signal for signal in PRESALES_SIGNALS if signal in normalized}
    return PRESALES_CSM_RESUME if len(matches) >= 2 else IMPLEMENTATION_RESUME

def extract_output_name(job_description: str) -> str:
    company_name = extract_company_name(job_description)
    if company_name:
        # Validate it's not a placeholder
        if any(re.search(pattern, company_name, re.I) for pattern in PLACEHOLDER_PATTERNS):
            # Placeholder detected, don't use it
            company_name = None
        else:
            return company_name

    job_title = extract_job_title(job_description)
    if job_title:
        # Validate job title is not a placeholder
        if any(re.search(pattern, job_title, re.I) for pattern in PLACEHOLDER_PATTERNS):
            # Placeholder detected, don't use it
            job_title = None
        else:
            return job_title

    fail("could not determine company name or job title from jobs/job_description.txt; refusing to use a placeholder filename")


def _clean_output_role_title(company_name: str, role_title: str) -> str:
    cleaned = clean_job_title(role_title)
    if company_name:
        cleaned = re.sub(rf"(?i)^{re.escape(company_name)}\s*(?:[-:|]\s*)?", "", cleaned).strip(" -:|")
    return cleaned


def extract_output_target_name(job_description: str) -> str:
    company_name = extract_company_name(job_description)
    role_title = extract_display_job_title(job_description)
    if company_name and role_title:
        cleaned_role = _clean_output_role_title(company_name, role_title)
        if (
            cleaned_role
            and is_valid_filename_piece(cleaned_role)
            and looks_like_job_title(cleaned_role)
            and normalize_compare(cleaned_role) != normalize_compare(company_name)
        ):
            combined = f"{company_name} - {cleaned_role}"
            if len(combined) > MAX_OUTPUT_TARGET_LENGTH:
                max_role_length = max(20, MAX_OUTPUT_TARGET_LENGTH - len(company_name) - 3)
                cleaned_role = cleaned_role[:max_role_length].rstrip(" .-|:")
                combined = f"{company_name} - {cleaned_role}"
            return combined
    return extract_output_name(job_description)


def output_name_candidates(job_description: str) -> tuple[str, ...]:
    candidates: list[str] = []
    for candidate in (
        extract_output_target_name(job_description),
        extract_company_name(job_description),
        extract_output_name(job_description),
    ):
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    return tuple(candidates)


def matching_output_files(
    output_dir: Path,
    job_description: str,
    suffix_pattern: str,
    *,
    allow_company_fallback: bool | None = None,
) -> list[Path]:
    if not output_dir.exists():
        return []

    role_title = clean_job_title(extract_job_title(job_description) or "")
    if allow_company_fallback is None:
        allow_company_fallback = not bool(role_title)

    search_names: list[str] = []
    target_name = extract_output_target_name(job_description)
    if target_name:
        search_names.append(target_name)

    if allow_company_fallback:
        company_name = extract_company_name(job_description) or extract_output_name(job_description)
        if company_name and company_name not in search_names:
            search_names.append(company_name)

    matches: list[tuple[int, float, str, Path]] = []
    seen: set[Path] = set()
    for priority, output_name in enumerate(search_names):
        pattern = f"Christian Estrada - {output_name}*{suffix_pattern}"
        for candidate in output_dir.glob(pattern):
            if " DRAFT" in candidate.stem.upper():
                continue
            if candidate in seen:
                continue
            seen.add(candidate)
            matches.append((priority, -candidate.stat().st_mtime, candidate.name.lower(), candidate))

    matches.sort(key=lambda item: (item[0], item[1], item[2]))
    return [item[3] for item in matches]

def extract_company_name(job_description: str) -> str | None:
    job_description = job_description.replace("\ufeff", "")
    first_lines = [line.strip() for line in job_description.splitlines() if line.strip()]
    patterns = (
        r"(?im)^\s*company(?:\s+name)?\s*[:\-]\s*\r?\n\s*(.+?)\s*$",
        r"(?im)^\s*company(?:\s+name)?\s*[:\-]\s*(.+?)\s*$",
        r"(?im)^\s*agency\s*[:\-]\s*(.+?)\s*$",
        r"(?im)^\s*hiring\s+agency\s*[:\-]\s*(.+?)\s*$",
        r"(?im)^\s*department\s*[:\-]\s*(.+?)\s*$",
        r"(?im)^\s*subagency\s*[:\-]\s*(.+?)\s*$",
        r"(?im)^\s*organization\s*[:\-]\s*(.+?)\s*$",
        r"(?im)^\s*employer\s*[:\-]\s*(.+?)\s*$",
        r"(?im)^\s*about\s+([A-Z][A-Za-z0-9&.,' -]{1,60})\s*$",
        r"(?m)^\s*([A-Z][A-Za-z0-9&.' -]{1,50})\s+is\s+(?:a|an|the)\b",
        r"(?m)^\s*With\s+([A-Z][A-Za-z0-9&.' -]{1,50}),",
        r"(?m)^\s*([A-Z][A-Za-z0-9&.' -]{1,50})\s+is\s+headquartered\b",
    )
    for pattern in patterns:
        match = re.search(pattern, job_description)
        if match:
            candidate = clean_company_name(match.group(1))
            federal_label_pattern = any(label in pattern for label in ("agency", "hiring\\s+agency", "department", "subagency"))
            if federal_label_pattern and is_valid_filename_piece(candidate) and not re.search(r"[.!?]", candidate):
                return candidate
            if is_valid_company_name(candidate):
                return candidate

    for line in first_lines[:20]:
        match = re.match(r"^([A-Z][A-Za-z0-9&.' -]{1,50})\s+-\s+.+$", line)
        if match:
            candidate = clean_company_name(match.group(1))
            if is_valid_company_name(candidate):
                return candidate

    return None

def clean_company_name(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip(" -:\t\r\n")
    cleaned = re.sub(r"[\\/:*?\"<>|]", "", cleaned)
    cleaned = re.sub(r"\b(inc\.?|llc|ltd\.?|corp\.?|corporation)\b$", "", cleaned, flags=re.I).strip()
    if not cleaned:
        return ""
    return cleaned[:80]

def is_valid_company_name(value: str) -> bool:
    return is_valid_filename_piece(value) and not looks_like_job_title(value) and not looks_like_sentence_fragment(value)

def extract_job_title(job_description: str) -> str | None:
    job_description = job_description.replace("\ufeff", "")
    first_lines = [line.strip() for line in job_description.splitlines() if line.strip()]
    explicit_patterns = (
        r"(?im)^\s*(?:job\s+title|role\s+title|role|position)\s*[:\-]?\s*(.+?)\s*$",
        r"(?im)^\s*your\s+role\s+at\s+[^:]+:\s*(.+?)\s*$",
    )
    for pattern in explicit_patterns:
        match = re.search(pattern, job_description)
        if not match:
            continue
        candidate = clean_extracted_job_title(match.group(1))
        if (
            is_valid_filename_piece(candidate)
            and looks_like_job_title(candidate)
            and len(candidate.split()) <= 12
            and not re.search(r"\b(?:you|your|our|this|will|responsible|team|department|supports?|executing|measured)\b", candidate, re.I)
            and not re.search(r"[.!?]", candidate)
        ):
            return candidate

    skipped = {
        "apply",
        "locations",
        "time type",
        "full time",
        "posted today",
        "about the role",
        "what you'll do",
        "what you will do",
        "who you are",
        "basic qualifications",
        "preferred qualifications",
    }
    for line in first_lines[:12]:
        normalized = line.lower().rstrip(":")
        if (
            normalized in skipped
            or normalized.startswith(("company", "job requisition", "posted on"))
            or normalized.startswith("#")
        ):
            continue
        candidate = clean_extracted_job_title(line)
        if is_valid_job_title(candidate):
            return candidate

    patterns = (
        r"(?i)\blooking for (?:a|an)\s+([A-Z][A-Za-z0-9&,+/ -]{2,80}?)\s+who\b",
        r"(?i)\bseeking (?:a|an)\s+([A-Z][A-Za-z0-9&,+/ -]{2,80}?)\s+(?:who|to|with)\b",
        r"(?i)\bfor this\s+([A-Z][A-Za-z0-9&,+/ -]{2,80}?)\s+role\b",
    )
    for pattern in patterns:
        match = re.search(pattern, job_description)
        if match:
            candidate = clean_extracted_job_title(match.group(1))
            if is_valid_job_title(candidate):
                return candidate
    return None

def clean_extracted_job_title(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip(" -:\t\r\n")
    cleaned = re.sub(r"(?i)^\s*(?:job\s+title|title|role\s+title|role|position)\s*[:\-]?\s+", "", cleaned).strip()
    cleaned = re.sub(r"[\\/:*?\"<>]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:80]


def extract_display_job_title(job_description: str) -> str | None:
    """Return the concise title used in filenames and resume headers."""

    official = extract_job_title(job_description)
    if not official:
        return None
    from requirement_engine import _display_title, commercial_requirement_sections

    requirement_text = "\n".join(body for _heading, body in commercial_requirement_sections(job_description))
    return _display_title(official, requirement_text) or official

def clean_job_title(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip(" -:\t\r\n")
    cleaned = re.sub(r"(?i)^\s*(?:job\s+title|title|role\s+title|role|position)\s*[:\-]?\s+", "", cleaned).strip()
    cleaned = re.sub(r"[\\/:*?\"<>|]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:80]


def objective_business_context(job_description: str) -> dict[str, str]:
    """Extract objective business context signals from a posting or notes."""
    context = business_context.extract_business_context(job_description)
    return {
        "business_model": context.business_model,
        "product_context": context.product_or_service,
        "customer_type": context.customer_type,
        "industry": context.industry,
        "geography": context.geography,
        "scale": context.scale,
        "revenue": context.revenue_or_account_size,
        "growth_stage": context.growth_stage,
        "operational_complexity": context.operational_complexity,
        "technical_stack": ", ".join(context.technical_stack),
        "compliance_signals": ", ".join(context.compliance_signals),
        "role_success_outcomes": ", ".join(context.role_success_outcomes),
    }


def objective_business_context_sentence(job_description: str) -> str:
    return business_context.business_context_sentence(job_description)

def is_valid_filename_piece(value: str) -> bool:
    normalized = normalize_compare(value)
    return bool(value and normalized not in BLOCKED_FILENAME_NAMES)

def looks_like_job_title(value: str) -> bool:
    return bool(
        re.search(
            r"\b(consultant|engineer|manager|director|analyst|specialist|architect|lead|principal|senior|role|job|apply)\b",
            value,
            re.I,
        )
    )

def looks_like_sentence_fragment(value: str) -> bool:
    return bool(
        len(value.split()) > 5
        or re.search(r"[.!?]", value)
        or re.search(r"\b(you|your|our|the|this|will|responsible|team|practice|department)\b", value, re.I)
    )

def is_general_management_consulting_role(job_description: str) -> bool:
    role_title = normalize_compare(extract_job_title(job_description) or "")
    explicit_strategy_consulting_title = (
        role_title
        and any(contains_search_term(role_title, signal) for signal in STRATEGY_CONSULTING_TITLE_SIGNALS)
        and any(contains_search_term(role_title, signal) for signal in STRATEGY_CONSULTING_ROLE_WORDS)
        and not any(contains_search_term(role_title, signal) for signal in STRATEGY_CONSULTING_TITLE_EXCLUSION_SIGNALS)
    )
    explicit_strategy_consulting_context = (
        explicit_strategy_consulting_title
        and text_mentions(
            job_description,
            "consulting firm",
            "advisory",
            "client",
            "clients",
            "recommendation",
            "recommendations",
            "strategy session",
            "strategy sessions",
            "executive",
            "executives",
        )
    )
    if explicit_strategy_consulting_context:
        return True

    if not is_consulting_job_description(job_description):
        return False

    if explicit_strategy_consulting_title:
        return True

    scoped = role_requirement_text(job_description).lower()
    if any(contains_search_term(scoped, signal) for signal in GENERAL_CONSULTING_EXCLUSION_SIGNALS):
        return False

    generic_consulting_title = role_title in {
        "consultant",
        "senior consultant",
        "associate consultant",
        "principal consultant",
        "management consultant",
        "strategy consultant",
        "business analyst",
        "consulting analyst",
        "associate",
    }

    hits = sum(1 for signal in GENERAL_CONSULTING_ROLE_SIGNALS if contains_search_term(scoped, signal))
    return generic_consulting_title or hits >= 3


def role_requirement_text(job_description: str) -> str:
    """Return job text suitable for targeting, excluding boilerplate/admin sections."""
    lines = job_description.splitlines()
    kept: list[str] = []
    skipping_boilerplate = False

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            if kept and kept[-1] != "":
                kept.append("")
            continue

        if re.match(r"^\s*(?:company(?:\s+name)?|job\s+title|title|role(?:\s+title)?|position)\s*[:\-]", line, re.I):
            continue

        if ROLE_REQUIREMENT_SECTION_RE.match(line):
            skipping_boilerplate = False
            kept.append(raw_line)
            continue

        if BOILERPLATE_SECTION_RE.match(line):
            skipping_boilerplate = True
            continue

        if skipping_boilerplate:
            continue

        if BOILERPLATE_LINE_RE.search(line):
            continue

        kept.append(raw_line)

    cleaned = "\n".join(kept)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned or job_description

def clean_keyword_candidate(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip()
    cleaned = re.sub(r"^[^A-Za-z0-9]+", "", cleaned)
    cleaned = re.sub(r"[^A-Za-z0-9]+$", "", cleaned)
    return cleaned.lower()


def line_ngram_phrases(line: str, min_words: int = 2, max_words: int = 2) -> set[str]:
    phrases: set[str] = set()
    for segment in re.split(r"[,;:()]+", line):
        words = [
            clean_keyword_candidate(word)
            for word in re.findall(r"[A-Za-z][A-Za-z+.#-]{1,}", segment)
        ]
        words = [word for word in words if word and word not in STOP_WORDS]
        for size in range(min_words, min(max_words, len(words)) + 1):
            for index in range(len(words) - size + 1):
                phrase = " ".join(words[index : index + size]).strip()
                if (
                    phrase
                    and phrase not in AUDIT_BLOCKED_PHRASES
                    and not any(part in STOP_WORDS for part in phrase.split())
                ):
                    phrases.add(phrase)
    return phrases


def title_phrase_candidates(job_description: str) -> tuple[str, ...]:
    raw_title = extract_job_title(job_description) or ""
    title = clean_job_title(raw_title)
    title_segments = [
        re.sub(r"\s+", " ", segment).strip()
        for segment in re.split(r"[,/|]", title)
        if re.sub(r"\s+", " ", segment).strip()
    ]
    phrases: list[str] = []
    if len(title_segments) > 1:
        for segment in title_segments:
            words = [
                clean_keyword_candidate(word)
                for word in re.findall(r"[A-Za-z][A-Za-z+.#-]{1,}", segment)
            ]
            words = [word for word in words if word and word not in STOP_WORDS]
            if len(words) >= 2:
                phrases.append(" ".join(words[:2]))
                if len(words) == 3:
                    phrases.append(" ".join(words))
    else:
        words = [
            clean_keyword_candidate(word)
            for word in re.findall(r"[A-Za-z][A-Za-z+.#-]{1,}", title)
        ]
        words = [word for word in words if word and word not in STOP_WORDS]
        if len(words) < 2:
            return ()
        phrases.append(" ".join(words[:2]))
        phrases.append(" ".join(words[-2:]))
        if len(words) == 3:
            phrases.append(" ".join(words))
    ordered: list[str] = []
    seen: set[str] = set()
    for phrase in phrases:
        normalized = normalize_compare(phrase)
        if normalized and normalized not in seen and not all(part in AUDIT_NOISE_KEYWORDS for part in normalized.split()):
            ordered.append(normalized)
            seen.add(normalized)
    return tuple(ordered)


def keyword_source_lines(job_description: str) -> list[str]:
    lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in role_requirement_text(job_description).splitlines()
        if re.sub(r"\s+", " ", line).strip()
    ]
    if not is_general_management_consulting_role(job_description):
        return lines

    role_title = normalize_compare(extract_job_title(job_description) or "")
    filtered = [
        line
        for line in lines
        if normalize_compare(line) == role_title
        or any(contains_search_term(line.lower(), signal) for signal in CONSULTING_KEYWORD_SOURCE_SIGNALS)
    ]
    return filtered or lines


def keyword_set(job_description: str) -> set[str]:
    keywords: set[str] = set()
    phrases: set[str] = set()
    for line in keyword_source_lines(job_description):
        for word in re.findall(r"[A-Za-z][A-Za-z+.#-]{2,}", line):
            cleaned = clean_keyword_candidate(word)
            if cleaned and cleaned not in STOP_WORDS:
                keywords.add(cleaned)
        phrases.update(line_ngram_phrases(line))
    phrases.update(title_phrase_candidates(job_description))
    return keywords | phrases


UNSUPPORTED_PLATFORM_KEYWORDS = (
    "acumatica",
    "smartsheet",
    "netsuite",
    "workday",
    "sap s/4",
    "sap s/4hana",
    "prismhr",
)


def keyword_occurrence_count(text: str, keyword: str) -> int:
    normalized = keyword.strip()
    if not normalized:
        return 0
    if " " in normalized:
        return len(re.findall(re.escape(normalized), text, flags=re.I))
    return len(re.findall(rf"\b{re.escape(normalized)}\b", text, flags=re.I))


def canonical_audit_keyword(keyword: str) -> str:
    if keyword == "analyses":
        return "analysis"
    if keyword.endswith("ies") and len(keyword) > 4:
        return keyword[:-3] + "y"
    if keyword.endswith("es") and len(keyword) > 4:
        singular_base = keyword[:-2]
        if singular_base.endswith(("ss", "sh", "ch", "x", "z")):
            return singular_base
    if keyword.endswith("s") and len(keyword) > 4 and not keyword.endswith(("ss", "ics", "us")):
        return keyword[:-1]
    return keyword


def affiliate_company_tokens(job_description: str) -> set[str]:
    tokens: set[str] = set()
    for match in re.finditer(r"\ba\s+([A-Z][A-Za-z0-9&.-]*(?:\s+[A-Z][A-Za-z0-9&.-]*){0,2})\s+company\b", job_description):
        candidate = normalize_compare(match.group(1))
        if candidate:
            tokens.update(candidate.split())
    return tokens


def is_low_signal_audit_keyword(keyword: str) -> bool:
    parts = keyword.split()
    if not parts:
        return True
    if len(parts) == 1:
        return parts[0] in AUDIT_NOISE_KEYWORDS or parts[0] in AUDIT_LOW_SIGNAL_TRAIL_WORDS
    if len(parts) == 2 and parts[-1] == "quality" and parts[0] not in AUDIT_ALLOWED_QUALITY_HEADS:
        return True
    first = parts[0]
    last = parts[-1]
    if first in AUDIT_ACTION_LEAD_WORDS or first in AUDIT_NOISE_KEYWORDS:
        return True
    if last in AUDIT_NOISE_KEYWORDS:
        return True
    if last in AUDIT_LOW_SIGNAL_TRAIL_WORDS and not any(part in AUDIT_PRIORITY_KEYWORDS for part in parts[:-1]):
        return True
    if all(part in AUDIT_NOISE_KEYWORDS for part in parts):
        return True
    return False


def repeated_keyword_is_signal(keyword: str, job_description: str, title_phrases: set[str]) -> bool:
    normalized = normalize_compare(keyword)
    if not normalized:
        return False
    if normalized in title_phrases:
        return True
    if normalized in SUMMARY_PLACEMENT_TERMS or normalized in AUDIT_PRIORITY_KEYWORDS:
        return True
    if any(part in SUMMARY_PLACEMENT_TERMS or part in AUDIT_PRIORITY_KEYWORDS for part in normalized.split()):
        return True

    hits = keyword_occurrence_count(job_description, normalized)
    if " " in normalized:
        return hits >= 2 and len(normalized.split()) <= 3
    if "-" in normalized:
        return hits >= 2 and len(normalized) >= 6
    return hits >= 3 and len(normalized) >= 6

def audit_keywords(job_description: str) -> set[str]:
    blocked = {
        "company",
        "experience",
        "job",
        "looking",
        "manage",
        "managed",
        "maintain",
        "maintained",
        "join",
        "lead",
        "role",
        "team",
        "hands on",
        "hands-on",
        "what",
        "work",
        "responsible",
        "candidate",
        "requirements",
        "qualifications",
        "preferred",
        "required",
        "job title",
        "role title",
        "senior solution",
        "senior solutions",
        "testing delivery",
        "multiple",
        "impact",
        "quickly",
        "social",
        "adjust training",
    }
    original_job_description = job_description
    try:
        from requirement_engine import parse_commercial_requirements

        parsed_requirements = parse_commercial_requirements(job_description)
    except Exception:
        parsed_requirements = ()
    if len(parsed_requirements) >= 3:
        job_description = "\n".join(element.text for element in parsed_requirements)
    explicit_company = re.search(r"(?im)^\s*company(?:\s+name)?\s*[:\-]\s*(.+?)\s*$", original_job_description)
    company_name = normalize_compare(explicit_company.group(1) if explicit_company else (extract_company_name(original_job_description) or ""))
    company_tokens = set(company_name.split())
    company_tokens |= affiliate_company_tokens(original_job_description)
    title_phrases = set(title_phrase_candidates(original_job_description))
    consulting_mode = is_general_management_consulting_role(original_job_description)
    keywords: set[str] = set()
    for keyword in keyword_set(job_description):
        if len(keyword) >= 4 \
            and keyword not in blocked \
            and keyword != company_name \
            and keyword not in company_tokens \
            and not (" " in keyword and any(part in company_tokens for part in keyword.split()) and keyword not in title_phrases) \
            and (keyword in title_phrases or " " not in keyword or keyword.split()[-1] in AUDIT_PHRASE_TAIL_PRIORITY_WORDS) \
            and (keyword in title_phrases or not is_low_signal_audit_keyword(keyword)) \
            and keyword not in CONSULTING_TAXONOMY_PHRASES \
            and not (not consulting_mode and keyword == "consulting") \
            and not (
                keyword not in title_phrases
                and
                any(part in AUDIT_NOISE_KEYWORDS for part in keyword.split())
                and not any(part in AUDIT_PRIORITY_KEYWORDS for part in keyword.split())
                and not any(part in SUMMARY_PLACEMENT_TERMS for part in keyword.split())
            ) \
            and repeated_keyword_is_signal(keyword, job_description, title_phrases) \
            and (
                not consulting_mode
                or " " not in keyword
                or (
                    len(keyword.split()) <= 2
                    and all(part in AUDIT_PRIORITY_KEYWORDS for part in keyword.split())
                )
            ) \
            and not keyword.isdigit() \
            and not is_generic_soft_keyword(keyword):
            keywords.add(canonical_audit_keyword(keyword))

    if jd_mentions(job_description, "analytics & reporting", "analytics and reporting"):
        keywords.discard("analytics reporting")
        keywords.add("analytics and reporting")
    if jd_mentions(job_description, "ai-assisted", "ai guided", "ai-guided"):
        keywords.add("ai-assisted")

    if consulting_mode:
        keywords = {
            keyword
            for keyword in keywords
            if " " not in keyword or not all(part in keywords for part in keyword.split())
        }
    for element in parsed_requirements:
        if element.category in {"skill_tool", "domain"} or "training adaptation" in element.canonical_terms:
            keywords.update(element.canonical_terms)
    if parsed_requirements:
        requirement_vocabulary = {
            "adoption", "analytics", "client", "communication", "configuration", "customer", "data",
            "excel", "implementation", "integration", "migration", "reporting", "sql", "stakeholder",
            "testing", "training", "uat", "workflow",
        }
        scoped_normalized = normalize_compare(job_description)
        keywords.update(
            term
            for term in requirement_vocabulary
            if re.search(rf"\b{re.escape(term)}s?\b", scoped_normalized)
        )
    return keywords


def is_unsupported_do_not_insert(keyword: str, resume_text: str, job_description: str = "") -> bool:
    normalized = normalize_compare(keyword)
    if normalized not in UNSUPPORTED_PLATFORM_KEYWORDS:
        return False
    if job_description and not contains_search_term(job_description.lower(), keyword):
        return False
    return not contains_search_term(resume_text.lower(), keyword)


def audit_keyword_sort_key(job_description: str, keyword: str) -> tuple[int, int, int, int, int, int, str]:
    normalized = normalize_compare(keyword)
    title_phrases = set(title_phrase_candidates(job_description))
    parts = normalized.split()
    clean_edge = 1
    if parts:
        if parts[0] in AUDIT_ACTION_LEAD_WORDS or parts[0] in AUDIT_NOISE_KEYWORDS:
            clean_edge = 0
        if parts[-1] in AUDIT_LOW_SIGNAL_TRAIL_WORDS or parts[-1] in AUDIT_NOISE_KEYWORDS:
            clean_edge = 0
    return (
        1 if normalized in title_phrases else 0,
        1 if " " in normalized else 0,
        1 if normalized in AUDIT_PRIORITY_KEYWORDS or any(part in AUDIT_PRIORITY_KEYWORDS for part in normalized.split()) else 0,
        clean_edge,
        1 if is_keyword_color_candidate(keyword, job_description) else 0,
        1 if normalized in SUMMARY_PLACEMENT_TERMS or any(part in SUMMARY_PLACEMENT_TERMS for part in normalized.split()) else 0,
        keyword_occurrence_count(job_description, keyword),
        len(keyword.split()),
        keyword,
    )

def is_generic_soft_keyword(keyword: str) -> bool:
    normalized = normalize_compare(keyword)
    if normalized in GENERIC_SOFT_KEYWORDS:
        return True
    return any(term in normalized for term in GENERIC_SOFT_KEYWORDS if " " in term)

def keyword_hits(text: str, keywords: set[str]) -> int:
    normalized = text.lower()
    hits = 0
    for keyword in keywords:
        if " " in keyword:
            if keyword in normalized:
                hits += 2
        elif re.search(rf"\b{re.escape(keyword)}\b", normalized):
                hits += 1
    return hits

def keyword_regex(keyword: str) -> str:
    escaped = re.escape(keyword).replace(r"\ ", r"\s+")
    if re.search(r"^[\w\s+-]+$", keyword):
        return rf"(?<!\w){escaped}(?!\w)"
    return escaped

def jd_color_priority_terms(job_description: str) -> set[str]:
    lowered = job_description.lower()
    return {term for term in COLOR_AUDIT_PRIORITY_TERMS if re.search(keyword_regex(term), lowered)}

def is_keyword_color_candidate(keyword: str, job_description: str) -> bool:
    normalized = keyword.lower().strip()
    if not normalized or normalized in COLOR_AUDIT_BLOCKED_KEYWORDS:
        return False
    if normalized in IMPORTANT_SHORT_ATS_TERMS or normalized in SUMMARY_PLACEMENT_TERMS:
        return True
    if " " in normalized:
        parts = normalized.split()
        if any(part in COLOR_AUDIT_BLOCKED_KEYWORDS for part in parts):
            return False
        if normalized in jd_color_priority_terms(job_description):
            return True
        return 2 <= len(parts) <= 3 and keyword_hits(job_description, {normalized}) >= 2
    return keyword_hits(job_description, {normalized}) >= 2

def jd_priority_phrases(job_description: str) -> tuple[str, ...]:
    keywords = [
        keyword for keyword in audit_keywords(job_description)
        if " " in keyword and is_keyword_color_candidate(keyword, job_description)
    ]
    keywords.sort(key=lambda keyword: (keyword_hits(job_description, {keyword}), len(keyword)), reverse=True)
    return tuple(keywords[:5])

def jd_explicitly_requires_erp(job_description: str) -> bool:
    return jd_mentions(
        job_description,
        "erp", "enterprise resource planning", "sap", "oracle erp", "microsoft dynamics",
        "epicor", "aptean", "netsuite", "manufacturing systems",
    )

def should_deemphasize_erp_for_role(job_description: str) -> bool:
    return not jd_explicitly_requires_erp(job_description)

def jd_mentions(job_description: str, *needles: str) -> bool:
    normalized = role_requirement_text(job_description).lower()
    return any(contains_search_term(normalized, needle) for needle in needles)

def text_mentions(text: str, *needles: str) -> bool:
    normalized = text.lower()
    return any(contains_search_term(normalized, needle) for needle in needles)

def unsupported_requirement_hit(label: str, job_description: str, patterns: tuple[str, ...]) -> bool:
    normalized = ZERO_WIDTH_CHAR_RE.sub(" ", role_requirement_text(job_description).lower())
    if label == "Direct People Leadership":
        if DIRECT_REPORTING_LINE_RE.search(normalized) and not EXPLICIT_PEOPLE_MANAGEMENT_RE.search(normalized):
            cleaned = DIRECT_REPORTING_LINE_RE.sub(" ", normalized)
            if not any(contains_search_term(cleaned, needle) for needle in patterns):
                return False

    if not any(contains_search_term(normalized, needle) for needle in patterns):
        return False
    if label not in UNSUPPORTED_OWNERSHIP_LABELS:
        return True

    sentences = re.split(r"(?<=[.!?])\s+|[\r\n]+", job_description)
    for sentence in sentences:
        if text_mentions(sentence, *patterns) and OWNERSHIP_ACTION_RE.search(sentence):
            return True
    return False

def signal_hits(text: str, signals: tuple[str, ...]) -> int:
    normalized = text.lower()
    return sum(1 for signal in signals if contains_search_term(normalized, signal))

def fit_status(current: str, candidate: str) -> str:
    return candidate if AUDIT_STATUS_ORDER[candidate] > AUDIT_STATUS_ORDER[current] else current


def output_audit_state(output_file: str | Path | None) -> str:
    if not output_file:
        return "PASS"
    stem = Path(output_file).stem.upper()
    if " DRAFT" in stem:
        return "DRAFT"
    if " POOR" in stem:
        return "POOR"
    if " FAIL" in stem:
        return "FAIL"
    if " BRIDGE" in stem:
        return "BRIDGE"
    return "PASS"


def output_audit_suffix(status: str) -> str:
    normalized = (status or "PASS").strip().upper()
    return "" if normalized == "PASS" else f" {normalized}"

def poor_fit_requirements(job_description: str, resume_text: str) -> tuple[str, ...]:
    job_description = role_requirement_text(job_description)
    poor: list[str] = []
    for area in POOR_FIT_REQUIREMENT_AREAS:
        job_hits = signal_hits(job_description, tuple(area["job_terms"]))
        resume_hits = signal_hits(resume_text, tuple(area["resume_terms"]))
        if job_hits >= int(area["minimum_job_hits"]) and resume_hits == 0:
            poor.append(str(area["label"]))
    return tuple(dict.fromkeys(poor))


def specialty_gap_requirements(job_description: str, resume_text: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    job_description = role_requirement_text(job_description)
    matches: list[str] = []
    gaps: list[str] = []
    for area in SPECIALTY_GAP_AREAS:
        job_hits = signal_hits(job_description, tuple(area["job_terms"]))
        if job_hits < int(area["minimum_job_hits"]):
            continue
        resume_hits = signal_hits(resume_text, tuple(area["resume_terms"]))
        if resume_hits:
            matches.append(str(area["label"]))
        else:
            gaps.append(str(area["label"]))
    return tuple(dict.fromkeys(matches)), tuple(dict.fromkeys(gaps))

def job_problem_profile(job_description: str, resume_text: str = "") -> JobProblemProfile:
    original_job_description = job_description
    job_description = role_requirement_text(job_description)
    if is_general_management_consulting_role(original_job_description):
        lane = CORPORATE_STRATEGY_PROFILE
    else:
        lane_scores = [
            (signal_hits(job_description, tuple(lane["signals"])), lane)
            for lane in TARGETING_LANES
        ]
        lane_scores.sort(key=lambda item: item[0], reverse=True)
        score, lane = lane_scores[0]
        if score == 0:
            lane = next(item for item in TARGETING_LANES if item["key"] == "implementation_delivery")

    direct_matches: list[str] = []
    adjacent_matches: list[str] = []
    safe_terms: list[str] = []
    for area in BRIDGE_EVIDENCE_AREAS:
        job_hit = text_mentions(job_description, *area["job_terms"])
        resume_hit = text_mentions(resume_text, *area["resume_terms"])
        if job_hit and resume_hit:
            direct_matches.append(area["label"])
            safe_terms.extend(area["safe_terms"])
        elif job_hit:
            adjacent_matches.append(area["label"])

    unsupported: list[str] = []
    for label, patterns in UNSUPPORTED_REQUIREMENT_PATTERNS:
        if unsupported_requirement_hit(label, job_description, patterns) and not text_mentions(resume_text, *patterns):
            unsupported.append(label)

    specialty_matches, specialty_gaps = specialty_gap_requirements(job_description, resume_text)
    unique_safe_terms = tuple(dict.fromkeys(safe_terms))
    return JobProblemProfile(
        primary_lane=str(lane["key"]),
        lane_label=str(lane["label"]),
        core_problem=str(lane["problem"]),
        audience=str(lane["audience"]),
        outcomes=tuple(lane["outcomes"]),
        direct_matches=tuple(dict.fromkeys(direct_matches)),
        adjacent_matches=tuple(dict.fromkeys(adjacent_matches)),
        unsupported_requirements=tuple(dict.fromkeys(unsupported)),
        safe_terms=unique_safe_terms,
        specialty_matches=specialty_matches,
        specialty_gaps=specialty_gaps,
    )


def natural_problem_phrase(profile: JobProblemProfile) -> str:
    return {
        "implementation_delivery": "getting complex implementations to go-live without losing adoption",
        "customer_success": "turning adoption and renewal risk into retained, growing accounts",
        "analytics_operations": "turning reporting gaps into decisions leaders can act on",
        "change_enablement": "helping teams actually adopt new systems after launch",
        "presales_solution": "translating buyer needs into a solution that survives implementation",
        "corporate_strategy": "making an ambiguous problem concrete enough for a team to act on",
    }.get(profile.primary_lane, "turning ambiguous system problems into usable outcomes")

STARTUP_OPERATOR_STRONG_SIGNALS = (
    "startup",
    "start-up",
    "series a",
    "series b",
    "series c",
    "growth stage",
    "scaleup",
    "scale-up",
    "founder",
    "scrappy",
    "0 to 1",
    "zero to one",
    "wear many hats",
)

STARTUP_OPERATOR_BROAD_SIGNALS = (
    "technical operations",
    "business operations",
    "bizops",
    "revops",
    "revenue operations",
    "systems operations",
    "business systems",
    "systems analyst",
    "implementation operations",
    "implementation manager",
    "implementation program",
    "solution delivery",
    "solutions operations",
    "customer operations",
    "customer onboarding",
    "operations program manager",
    "technical program manager",
    "program manager",
    "process improvement",
    "process automation",
    "workflow automation",
    "scale operations",
    "operational excellence",
)

STARTUP_OPERATOR_ENTERPRISE_COUNTER_RE = re.compile(
    r"\b(fortune 500|fortune500|publicly traded|nasdaq|nyse|global operations|enterprise scale|"
    r"thousands of employees|worldwide|multinational|established leader|largest privately held)\b",
    re.I,
)


def is_startup_or_broad_operator_role(job_description: str) -> bool:
    scoped = role_requirement_text(job_description).lower()
    strong_hits = sum(1 for signal in STARTUP_OPERATOR_STRONG_SIGNALS if contains_search_term(scoped, signal))
    broad_hits = sum(1 for signal in STARTUP_OPERATOR_BROAD_SIGNALS if contains_search_term(scoped, signal))
    enterprise_counter_signal = bool(STARTUP_OPERATOR_ENTERPRISE_COUNTER_RE.search(scoped))

    if strong_hits >= 1:
        return True
    if broad_hits >= 3:
        return True
    if broad_hits >= 2 and not enterprise_counter_signal:
        return True
    return False

def employer_context_matches(job_description: str) -> list[dict[str, object]]:
    matches: list[tuple[int, dict[str, object]]] = []
    for context in EMPLOYER_CONTEXTS:
        signals = tuple(str(signal) for signal in context["signals"])
        hits = signal_hits(job_description, signals)
        if hits:
            matches.append((hits, context))
    matches.sort(key=lambda item: item[0], reverse=True)
    return [context for _, context in matches]

def story_lens_matches(job_description: str) -> list[dict[str, object]]:
    matches: list[tuple[int, dict[str, object]]] = []
    for lens in STORY_LENSES:
        signals = tuple(str(signal) for signal in lens["signals"])
        hits = signal_hits(job_description, signals)
        if hits:
            matches.append((hits, lens))
    matches.sort(key=lambda item: item[0], reverse=True)
    return [lens for _, lens in matches]

def primary_story_lens(job_description: str) -> dict[str, object] | None:
    matches = story_lens_matches(job_description)
    return matches[0] if matches else None

def story_lens_sentence(job_description: str) -> str:
    lens = primary_story_lens(job_description)
    if not lens:
        return ""
    return str(lens["resume_context"])

def story_lens_identity(job_description: str) -> str:
    lens = primary_story_lens(job_description)
    return str(lens["identity"]) if lens else "practical delivery and measurable outcomes"

def story_lens_business_problem(job_description: str) -> str:
    lens = primary_story_lens(job_description)
    return str(lens["business_problem"]) if lens else "ambiguous work that needs structure, adoption, and measurable progress"

def story_lens_candidate_story(job_description: str) -> str:
    lens = primary_story_lens(job_description)
    return str(lens["candidate_story"]) if lens else "ERP ownership, client delivery, reporting, stakeholder alignment, and account recovery"

def story_lens_interview_lens(job_description: str) -> str:
    lens = primary_story_lens(job_description)
    return str(lens["interview_lens"]) if lens else "Speak to the business problem, the structure used, the stakeholders involved, and the measurable result."

def primary_employer_context(job_description: str) -> dict[str, object] | None:
    matches = employer_context_matches(job_description)
    lowered = job_description.lower()
    if matches and any(
        signal in lowered
        for signal in (
            "cloud platform",
            "proprietary cloud",
            "software platform",
            "saas",
            "software as a service",
            "platform enables",
        )
    ) and not re.search(
        r"\b(consulting firm|management consulting|strategy consulting|advisory practice|professional services firm)\b",
        lowered,
    ):
        saas_context = next((context for context in matches if context.get("key") == "saas"), None)
        if saas_context:
            return saas_context
    return matches[0] if matches else None

def visible_role_specialties(job_description: str) -> tuple[str, ...]:
    job_description = role_requirement_text(job_description)
    specialties = (
        ("Microsoft Dynamics 365 Business Central", ("dynamics 365 business central", "business central")),
        ("Microsoft Dynamics 365", ("dynamics 365",)),
        ("Power BI", ("power bi",)),
        ("ERP implementation", ("erp implementation", "erp systems", "enterprise resource planning", "manufacturing erp")),
        ("core financials", ("core financial", "finance module", "financial modules", "chart of accounts", "dimensions")),
        ("solution architecture", ("solution architecture", "solution architect")),
        ("solution consulting", ("solution consulting", "solutions engineer", "pre-sales", "presales", "demo")),
        ("customer success", ("customer success", "customer outcomes", "retention", "renewal", "expansion")),
        ("change adoption", ("change adoption", "change management", "ways of working")),
        ("assessment and learning systems", ("school assessment", "assessment item", "assessment and learning", "measurement and learning", "learning systems", "learner-facing", "instructional", "k-12", "psychometric", "constructed-response", "technology-enhanced items", "tei")),
        ("AI-assisted workflows", ("ai-assisted", "ai-guided", "agentic", "intelligent systems")),
        ("contact center technology", ("contact center", "ccaas", "ucaas", "voice", "chat", "messaging")),
        ("analytics and reporting", ("analytics", "reporting", "dashboard", "kpi", "business intelligence")),
        ("manufacturing operations", ("manufacturing", "supply chain", "warehouse", "bom", "materials management", "inventory management", "inventory control")),
        ("financial services operations", ("financial services", "banking", "payments", "fintech", "insurance")),
        ("healthcare technology", ("healthcare", "health care", "patient", "clinical", "claims")),
    )
    lowered = job_description.lower()
    found: list[str] = []
    for label, signals in specialties:
        if label in found:
            continue
        if any(contains_search_term(lowered, signal) for signal in signals):
            found.append(label)
    return tuple(found[:3])

def visible_company_values(job_description: str) -> tuple[str, ...]:
    values = (
        ("client success", ("client success", "customer success", "client satisfaction", "customer outcomes")),
        ("continuous learning", ("continuous learning", "professional development", "learning culture", "growth is supported")),
        ("inclusion and diversity", ("inclusion", "inclusive", "diversity", "belonging")),
        ("collaboration", ("collaborative", "collaboration", "cross-functional", "team environment")),
        ("innovation", ("innovation", "innovative", "modernize", "transformation")),
        ("quality", ("quality", "best practices", "exceptional", "seamless project delivery")),
        ("ownership", ("ownership", "account ownership", "manage expectations", "accountable")),
    )
    lowered = job_description.lower()
    found: list[str] = []
    for label, signals in values:
        if any(signal in lowered for signal in signals):
            found.append(label)
    return tuple(found[:3])

def role_specialty_phrase(job_description: str, fallback: str = "enterprise software delivery") -> str:
    specialties = visible_role_specialties(job_description)
    if not specialties:
        return fallback
    if len(specialties) == 1:
        return specialties[0]
    if len(specialties) == 2:
        return f"{specialties[0]} and {specialties[1]}"
    return f"{specialties[0]}, {specialties[1]}, and {specialties[2]}"

def visible_values_phrase(job_description: str) -> str:
    values = visible_company_values(job_description)
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return f"{values[0]}, {values[1]}, and {values[2]}"

def detect_company_profile(company_name: str, job_description: str) -> dict[str, object] | None:
    profile = match_company_profile(company_name, job_description)
    return dict(profile) if profile else None

def employer_context_sentence(job_description: str, profile: JobProblemProfile) -> str:
    lens_sentence = story_lens_sentence(job_description)
    if lens_sentence:
        return lens_sentence
    contexts = employer_context_matches(job_description)
    if not contexts:
        return ""
    sentence = str(contexts[0]["summary"])
    # Avoid repeating near-identical summary language for analytics-first roles.
    if profile.primary_lane == "analytics_operations" and contexts[0]["key"] == "analytics_operations":
        return ""
    return sentence

def is_consulting_job_description(job_description: str) -> bool:
    # Keep this strict. Generic "Consultant" titles often mean solution sales,
    # implementation, or customer advisory roles rather than a consulting-firm resume.
    # Check for firm names and consulting role descriptors with context awareness.
    
    if not job_description:
        return False
    
    # Negative signals that override consulting detection
    # (e.g., "NOT a consulting role" or "not for consulting firms")
    if re.search(r"\b(not|non-?)(.*?)consulting\b", job_description, re.I):
        return False
    
    # Positive signals for consulting firm roles
    consulting_firm_signals = (
        "bain", "mckinsey", "bcg", "deloitte", "kpmg", "ey", "pwc", "accenture"
    )
    for firm in consulting_firm_signals:
        if re.search(rf"\b{firm}\b", job_description, re.I):
            return True
    
    # Generic consulting role signals - be more careful here
    generic_consulting = (
        "consulting firm", "management consulting", "strategy consulting",
        "advisory services", "professional services", "client service"
    )
    match_count = 0
    for signal in generic_consulting:
        if re.search(rf"\b{signal}\b", job_description, re.I):
            match_count += 1
    
    # Require at least 2 generic consulting signals to trigger, or check for advisory
    # This reduces false positives from single mentions in company context
    if match_count >= 2:
        return True
    
    # Check explicitly for "advisory" role but avoid company names that contain it
    if re.search(r"\b(advisory|advisories)\b.*\b(services|firm|practice)\b", job_description, re.I):
        return True
    
    return False

def normalize_title(text: str) -> str:
    month_pattern = "|".join(MONTHS)
    text = re.split(rf"(?:{month_pattern})\s+\d{{4}}", text, maxsplit=1)[0]
    text = re.sub(r"\s+", " ", text).strip()
    return text

def normalize_compare(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
