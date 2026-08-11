#!/usr/bin/env python3
"""Job-description analysis and targeting helpers for resume workflows."""

from __future__ import annotations

import re
import importlib.util
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path

import business_context
from config.job_profiles import (
    BRIDGE_EVIDENCE_AREAS,
    EMPLOYER_CONTEXTS,
    POOR_FIT_REQUIREMENT_AREAS,
    PRESALES_SIGNALS,
    SCOPE_PACE_MISMATCH_SIGNALS,
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


@lru_cache(maxsize=8192)
def _search_term_regexes(term: str) -> tuple[re.Pattern, ...]:
    """Compile the search regexes for a term once and cache by term.

    Independent of the searched text, so callers reuse the compiled patterns
    across the many contains_search_term() calls in signal_hits /
    job_problem_profile instead of recompiling per call. Matching behavior is
    identical to the previous inline implementation.
    """
    parts = ZERO_WIDTH_CHAR_RE.sub(" ", term.lower()).strip().split()
    if not parts:
        return ()

    last = parts[-1]
    variants = [" ".join(parts)]
    if last.endswith("ies") and len(last) > 4:
        variants.append(" ".join(parts[:-1] + [last[:-3] + "y"]))
    elif last.endswith("es") and len(last) > 4:
        singular_base = last[:-2]
        if singular_base.endswith(("ss", "sh", "ch", "x", "z")):
            variants.append(" ".join(parts[:-1] + [singular_base]))
    elif last.endswith("s") and len(last) > 4 and not last.endswith(("ss", "ics", "is")):
        variants.append(" ".join(parts[:-1] + [last[:-1]]))
    elif not last.endswith("s") and not last.endswith("ing"):
        if last.endswith("y") and len(last) > 3 and last[-2] not in "aeiou":
            variants.append(" ".join(parts[:-1] + [last[:-1] + "ies"]))
        elif last.endswith(("ss", "sh", "ch", "x", "z")):
            variants.append(" ".join(parts[:-1] + [last + "es"]))
        else:
            variants.append(" ".join(parts[:-1] + [last + "s"]))

    def variant_pattern(variant: str) -> str:
        tokens = variant.split()
        if len(tokens) <= 1:
            return re.escape(variant)
        connector = r"(?:\s+(?:and|&)\s+|\s+)"
        return connector.join(re.escape(token) for token in tokens)

    return tuple(
        re.compile(rf"(?<![a-z0-9]){variant_pattern(variant)}(?![a-z0-9])")
        for variant in dict.fromkeys(variants)
    )


def contains_search_term(text: str, term: str) -> bool:
    normalized = ZERO_WIDTH_CHAR_RE.sub(" ", text.lower())
    return any(regex.search(normalized) is not None for regex in _search_term_regexes(term))


BULLET_PLACEMENT_EXCLUDED = {
    "approach",
    "briefings training",
    "business",
    "corporate",
    "deliver",
    "enterprise",
    "executive",
    "growth",
    "international training",
    "solution",
    "strategic",
    "team",
    "teams delivery",
    "teams delivery plans",
}


@lru_cache(maxsize=1)
def evidence_terms() -> tuple[dict[str, object], ...]:
    path = SOURCE_DIR / "evidence_terms.py"
    if not path.exists():
        return ()
    spec = importlib.util.spec_from_file_location("source_evidence_terms", path)
    if spec is None or spec.loader is None:
        return ()
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    raw_terms = getattr(module, "EVIDENCE_TERMS", ())
    terms: list[dict[str, object]] = []
    for item in raw_terms:
        if not isinstance(item, dict):
            continue
        concept = str(item.get("concept", "")).strip()
        variants = tuple(str(value).strip() for value in item.get("variants", ()) if str(value).strip())
        permitted_surfaces = tuple(
            str(value).strip()
            for value in item.get("permitted_surfaces", variants)
            if str(value).strip()
        )
        anchor = str(item.get("anchor", "")).strip()
        strength = str(item.get("strength", "strong")).strip().lower() or "strong"
        concept_id = str(item.get("concept_id", "")).strip()
        placement_types = tuple(str(value).strip() for value in item.get("placement_types", ()) if str(value).strip())
        if concept and concept_id and variants and permitted_surfaces and anchor:
            terms.append(
                {
                    "concept": concept,
                    "concept_id": concept_id,
                    "variants": variants,
                    "permitted_surfaces": permitted_surfaces,
                    "anchor": anchor,
                    "strength": strength,
                    "source_file": str(item.get("source_file", "")).strip(),
                    "source_employer": str(item.get("source_employer", "")).strip(),
                    "source_role": str(item.get("source_role", "")).strip(),
                    "source_contains": str(item.get("source_contains", "")).strip(),
                    "source_fingerprint": str(item.get("source_fingerprint", "")).strip(),
                    "placement_types": placement_types,
                    "competency_label": str(item.get("competency_label", "")).strip(),
                    "ownership_limit": str(item.get("ownership_limit", "")).strip(),
                }
            )
    return tuple(terms)


def evidence_term_for_variant(term: str) -> dict[str, object] | None:
    normalized = canonical_audit_keyword(normalize_compare(term))
    if not normalized:
        return None
    for entry in evidence_terms():
        forms = (
            str(entry.get("concept", "")),
            str(entry.get("competency_label", "")),
            *tuple(str(value) for value in entry.get("permitted_surfaces", ())),
        )
        if normalized in {canonical_audit_keyword(normalize_compare(form)) for form in forms}:
            return entry
    return None


def evidence_entry_context_supported(entry: dict[str, object], job_description: str) -> bool:
    variants = tuple(str(value) for value in entry.get("permitted_surfaces", ()))
    if not any(contains_search_term(job_description, variant) for variant in variants):
        return False
    if str(entry.get("strength", "strong")).lower() == "strong":
        return True
    concept = normalize_compare(str(entry.get("concept", "")))
    if concept == "digital transformation":
        return jd_mentions(
            job_description,
            "digital transformation",
            "technology transformation",
            "ai transformation",
            "workflow modernization",
            "modernization",
        )
    if concept == "ai adoption":
        return jd_mentions(job_description, "ai adoption", "ai pilot", "ai-assisted", "ai-enabled", "automation", "robotics")
    if concept == "global program":
        return jd_mentions(job_description, "global program", "global programs", "global scale", "worldwide", "cross-site")
    return False


def evidence_preferred_surface(concept_term: str, job_description: str) -> str:
    entry = evidence_term_for_variant(concept_term)
    if not entry or not evidence_entry_context_supported(entry, job_description):
        return concept_term
    def literal_occurs(surface: str) -> bool:
        pattern = re.escape(surface).replace(r"\ ", r"\s+")
        return re.search(rf"(?<!\w){pattern}(?!\w)", job_description, re.I) is not None

    supported_variants = [
        str(value)
        for value in entry.get("permitted_surfaces", ())
        if literal_occurs(str(value))
    ]
    if supported_variants:
        assigned_action_re = re.compile(
            r"\b(?:own|owns|owned|lead|leads|led|drive|drives|drove|manage|manages|managed|"
            r"deliver|delivers|delivered|implement|implements|implemented|coordinate|coordinates|"
            r"coordinated|responsible for|serve as|act as|function as)\b",
            re.I,
        )
        counterpart_re = re.compile(
            r"\b(?:partner|collaborate|work|coordinate)\w*\s+(?:closely\s+)?with\b",
            re.I,
        )

        def assignment_score(surface: str) -> int:
            pattern = re.escape(surface).replace(r"\ ", r"\s+")
            score = 0
            for line in re.split(r"[\r\n]+|(?<=[.!?])\s+", job_description):
                if not re.search(rf"(?<!\w){pattern}(?!\w)", line, re.I):
                    continue
                line_score = 1
                if assigned_action_re.search(line):
                    line_score += 4
                if counterpart_re.search(line):
                    line_score -= 5
                score = max(score, line_score)
            return score

        best_assignment_score = max(assignment_score(value) for value in supported_variants)
        assigned_variants = [
            value
            for value in supported_variants
            if assignment_score(value) == best_assignment_score
        ]
        if best_assignment_score > 1 and len(assigned_variants) == 1:
            return assigned_variants[0]
        normalized_concept = normalize_compare(concept_term)
        containing_variants = [
            value
            for value in supported_variants
            if normalize_compare(value) != normalized_concept
            and re.search(rf"\b{re.escape(normalized_concept)}\b", normalize_compare(value))
        ]
        if containing_variants:
            return sorted(
                containing_variants,
                key=lambda value: (len(normalize_compare(value).split()), len(value)),
                reverse=True,
            )[0]
        exact_variant = next(
            (value for value in supported_variants if normalize_compare(value) == normalized_concept),
            None,
        )
        if exact_variant:
            return exact_variant
        return sorted(supported_variants, key=lambda value: (len(normalize_compare(value).split()), len(value)), reverse=True)[0]
    return concept_term


def evidence_supported_surfaces(job_description: str) -> tuple[str, ...]:
    surfaces: list[str] = []
    seen: set[str] = set()
    for entry in evidence_terms():
        if not evidence_entry_context_supported(entry, job_description):
            continue
        supported_variants = [
            str(value)
            for value in entry.get("permitted_surfaces", ())
            if contains_search_term(job_description, str(value))
        ]
        for variant in sorted(supported_variants, key=lambda value: (len(normalize_compare(value).split()), len(value)), reverse=True):
            normalized = normalize_compare(variant)
            if normalized and normalized not in seen:
                surfaces.append(variant)
                seen.add(normalized)
    return tuple(surfaces)


def evidence_anchor_for_term(term: str) -> str:
    entry = evidence_term_for_variant(term)
    return str(entry.get("anchor", "")) if entry else ""


def jd_preferred_surface(concept_term: str, job_description: str, supported_text: str = "") -> str:
    """Return the JD's literal surface form for a supported equivalent concept."""
    concept = concept_term.strip()
    normalized_concept = normalize_compare(concept)
    if not normalized_concept:
        return concept

    evidence_surface = evidence_preferred_surface(concept, job_description)
    if evidence_surface != concept:
        return evidence_surface

    return concept


def is_bullet_placement_excluded(keyword: str) -> bool:
    normalized = normalize_compare(keyword)
    if not normalized:
        return True
    if normalized in BULLET_PLACEMENT_EXCLUDED:
        return True
    if normalized.endswith(" delivery") and normalized.split()[0] in {"team", "teams"}:
        return True
    return False


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
    scope_pace_signals: tuple[str, ...] = ()


SCOPE_PACE_MISMATCH_LOOKUP = {str(area["label"]): area for area in SCOPE_PACE_MISMATCH_SIGNALS}


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
    "improve",
    "improves",
    "improving",
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


class KeywordCandidateClass(str, Enum):
    REQUIREMENT = "requirement_concept"
    COMPETENCY = "skill_tool_method"
    DOMAIN = "domain_term"
    NOISE = "excluded_noise"


@dataclass(frozen=True)
class KeywordCandidateClassification:
    normalized: str
    candidate_class: KeywordCandidateClass
    validated_requirement: bool
    reason: str
    requirement_relation: str = "none"
    validating_requirement_text: str = ""
    alternative_group_id: str = ""
    alternative_terms: tuple[str, ...] = ()


KEYWORD_NOISE_SINGLETONS = {
    "booking",
    "engineering",
    "external",
    "focused",
    "have",
    "identify",
    "internal",
    "managing",
    "operational",
    "outcome",
    "portfolio",
    "profile",
    "rather",
    "scalable",
    "strategy",
    "trusted",
}

KEYWORD_NOISE_PHRASES = {
    "between customer",
    "same delivery",
    "sql advanced excel",
}

KEYWORD_COMPETENCY_SINGLETONS = {
    "adoption",
    "analytics",
    "automation",
    "communication",
    "configuration",
    "consulting",
    "customer",
    "data",
    "delivery",
    "discovery",
    "implementation",
    "integration",
    "measurement",
    "migration",
    "process",
    "quality",
    "reporting",
    "scope",
    "stakeholder",
    "status",
    "testing",
    "technical",
    "training",
    "transformation",
    "validation",
    "workflow",
}

KEYWORD_DOMAIN_SIGNALS = {
    "apparel",
    "contact center",
    "data center",
    "fashion",
    "federal",
    "financial services",
    "healthcare",
    "legal",
    "manufacturing",
    "philanthropy",
    "retail",
    "saas",
    "supply chain",
    "textile",
    "warehouse automation",
    "warehouse operations",
    "robotics integration",
    "fulfillment operations",
    "eprocurement",
    "customer integration",
}

ROLE_NOUN_TAILS = {
    "administrator",
    "advisor",
    "analyst",
    "architect",
    "consultant",
    "coordinator",
    "director",
    "engineer",
    "lead",
    "manager",
    "owner",
    "specialist",
}


def _candidate_requirement_relation(
    normalized: str,
    matching_elements: tuple[object, ...],
    job_title: str,
    fallback_text: str = "",
) -> tuple[str, str, tuple[str, ...]]:
    """Classify whether the candidate performs a role or merely works with it."""

    matched_texts = tuple(
        str(getattr(element, "text", "")).strip()
        for element in matching_elements
        if str(getattr(element, "text", "")).strip()
    )
    if not matched_texts and fallback_text:
        flexible = re.escape(normalized).replace(r"\ ", r"[\s-]+")
        matched_texts = tuple(
            line.strip()
            for line in re.split(r"[\r\n]+|(?<=[.!?])\s+", fallback_text)
            if line.strip() and re.search(rf"\b{flexible}s?\b", line, re.I)
        )
    alternative_elements = tuple(
        element
        for element in matching_elements
        if getattr(element, "alternative_group_id", "")
        and any(
            normalize_compare(str(term)) == normalized
            or contains_search_term(str(term), normalized)
            for term in tuple(getattr(element, "alternative_terms", ()))
        )
    )
    non_alternative_elements = tuple(
        element
        for element in matching_elements
        if not getattr(element, "alternative_group_id", "")
    )
    if alternative_elements and not non_alternative_elements:
        return "domain_alternative", matched_texts[0] if matched_texts else "", tuple(
            str(term)
            for term in getattr(alternative_elements[0], "alternative_terms", ())
        )

    parts = normalized.split()
    is_role_noun = bool(parts and parts[-1] in ROLE_NOUN_TAILS)
    if not is_role_noun:
        return "assigned" if matched_texts else "none", matched_texts[0] if matched_texts else "", ()

    escaped = re.escape(normalized).replace(r"\ ", r"[\s-]+")
    assigned_re = re.compile(
        rf"\b(?:serve|serves|served|act|acts|acted|function|functions|functioned)\s+as\s+(?:an?\s+|the\s+)?{escaped}s?\b"
        rf"|\b(?:be|become|is|are|was|were)\s+(?:an?\s+|the\s+)?{escaped}s?\b",
        re.I,
    )
    counterpart_re = re.compile(
        rf"\b(?:partner|partners|partnered|collaborate|collaborates|collaborated|work|works|worked|"
        rf"coordinate|coordinates|coordinated)\s+(?:closely\s+)?with\b[^.;:\n]{{0,80}}\b{escaped}s?\b",
        re.I,
    )
    if normalized and (
        normalize_compare(job_title) == normalized
        or any(assigned_re.search(text) for text in matched_texts)
    ):
        return "assigned", next(
            (text for text in matched_texts if assigned_re.search(text)),
            matched_texts[0] if matched_texts else job_title,
        ), ()
    if any(counterpart_re.search(text) for text in matched_texts):
        return "counterpart", next(
            text for text in matched_texts if counterpart_re.search(text)
        ), ()
    return "assigned" if matching_elements else "none", matched_texts[0] if matched_texts else "", ()


def _domain_candidate(normalized: str, matching_elements: tuple[object, ...]) -> bool:
    if normalized in KEYWORD_DOMAIN_SIGNALS:
        return True
    if any(str(getattr(element, "category", "")) == "domain" for element in matching_elements):
        return bool(
            re.search(
                r"\b(?:supply chain|warehouse|robotics|fulfillment|eprocurement|e procurement)\b",
                normalized,
                re.I,
            )
            or (
                "customer integration" in normalized
                and any(
                    re.search(r"\beprocurement|e procurement|product|feature|capabilit", str(getattr(element, "text", "")), re.I)
                    for element in matching_elements
                )
            )
        )
    return False

KEYWORD_VALID_PHRASE_TAILS = {
    "adoption",
    "analysis",
    "analytics",
    "configuration",
    "consulting",
    "delivery",
    "discovery",
    "documentation",
    "implementation",
    "integration",
    "management",
    "migration",
    "operations",
    "optimization",
    "outcome",
    "planning",
    "process",
    "quality",
    "readiness",
    "reporting",
    "requirements",
    "service",
    "support",
    "testing",
    "training",
    "transformation",
    "validation",
    "workflow",
}

KEYWORD_GENERIC_REQUIREMENT_HEAD_TAILS = {
    "client": {"adoption", "delivery", "reporting", "service", "support"},
    "customer": {"adoption", "delivery", "reporting", "service", "support"},
    "documentation": KEYWORD_VALID_PHRASE_TAILS,
    "initiative": KEYWORD_VALID_PHRASE_TAILS,
    "platform": {"adoption", "delivery", "reporting", "service", "support"},
    "product": {"adoption", "delivery", "reporting", "service", "support"},
    "service": {"reporting"},
}

KEYWORD_ACRONYM_BREADTH_TAILS = {
    "analysis",
    "analytics",
    "reporting",
}

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
        r"(?im)^\s*((?:U\.S\.\s+)?Department of [A-Z][A-Za-z0-9&.,'() \-]{2,80})\s*$",
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
            federal_label_pattern = any(
                label in pattern
                for label in ("agency", "hiring\\s+agency", "department", "subagency", "Department of")
            )
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


def extract_federal_agency_name(job_description: str) -> str | None:
    patterns = (
        r"(?im)^\s*agency\s*[:\-]\s*(.+?)\s*$",
        r"(?im)^\s*hiring\s+agency\s*[:\-]\s*(.+?)\s*$",
        r"(?im)^\s*department\s*[:\-]\s*(.+?)\s*$",
        r"(?im)^\s*((?:U\.S\.\s+)?Department of [A-Z][A-Za-z0-9&.,'() \-]{2,80})\s*$",
    )
    for pattern in patterns:
        match = re.search(pattern, job_description)
        if match:
            candidate = clean_company_name(match.group(1))
            if candidate:
                return candidate
    return None


def extract_federal_subagency_name(job_description: str) -> str | None:
    explicit = re.search(r"(?im)^\s*subagency\s*[:\-]\s*(.+?)\s*$", job_description)
    if explicit:
        return clean_company_name(explicit.group(1)) or None
    lines = [re.sub(r"\s+", " ", line).strip() for line in job_description.splitlines() if line.strip()]
    agency = extract_federal_agency_name(job_description)
    if not agency:
        return None
    try:
        agency_index = next(index for index, line in enumerate(lines) if clean_company_name(line) == agency)
    except StopIteration:
        return None
    candidates: list[str] = []
    for line in lines[agency_index + 1 :]:
        if re.match(r"^(?:As\s+an?\b|Duties\b|Qualifications\b|You qualify\b|For the GS-)", line, re.I):
            break
        if re.search(r"\b(?:Administration|Agency|Service|Commission|Bureau|Office|Enforcement|Advisor)\b", line):
            cleaned = clean_company_name(line)
            if cleaned and cleaned != agency:
                candidates.append(cleaned)
    return " / ".join(dict.fromkeys(candidates)) or None


def extract_federal_official_title(job_description: str) -> str | None:
    explicit = re.search(
        r"(?im)^\s*(?:job\s+title|role\s+title|role|position)\s*[:\-]\s*(.+?)\s*$",
        job_description,
    )
    if explicit:
        candidate = clean_extracted_job_title(explicit.group(1))
        if candidate and is_valid_filename_piece(candidate):
            return candidate
    return extract_job_title(job_description)


def extract_semantic_organization(
    job_description: str,
    *,
    workflow: str = "commercial",
) -> tuple[str, str]:
    if workflow == "federal":
        agency = extract_federal_agency_name(job_description)
        if agency:
            return agency, "agency"
    company = extract_company_name(job_description)
    if company:
        return company, "company"
    role_title = extract_federal_official_title(job_description) if workflow == "federal" else extract_job_title(job_description)
    if role_title:
        return role_title, "title_fallback"
    return "", "title_fallback"


def extract_target_output_label(
    job_description: str,
    *,
    workflow: str = "commercial",
    selected_grade: str = "",
) -> str:
    organization, _source = extract_semantic_organization(job_description, workflow=workflow)
    role_title = (extract_federal_official_title(job_description) if workflow == "federal" else extract_job_title(job_description)) or ""
    if workflow != "federal":
        return extract_output_target_name(job_description)
    pieces = [organization]
    if role_title and role_title.lower() not in organization.lower():
        pieces.append(role_title)
    if selected_grade:
        pieces.append(selected_grade)
    label = " - ".join(piece for piece in pieces if piece)
    if label:
        return label
    fail("could not determine agency name or job title from jobs/federal_job_description.txt; add an Agency: or Role: line at the top")

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
            r"\b(advisor|analyst|architect|consultant|director|engineer|lead|manager|owner|principal|product|role|senior|specialist|job|apply)\b",
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
        for phrase in line_ngram_phrases(line, min_words=3, max_words=3):
            if len(re.findall(re.escape(phrase), job_description, flags=re.I)) >= 2:
                phrases.add(phrase)
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
    if keyword == "status":
        return keyword
    if keyword == "analyses":
        return "analysis"
    if keyword.endswith("ies") and len(keyword) > 4:
        return keyword[:-3] + "y"
    if keyword.endswith("es") and len(keyword) > 4:
        singular_base = keyword[:-2]
        if singular_base.endswith(("ss", "sh", "ch", "x", "z")):
            return singular_base
    if keyword.endswith("s") and len(keyword) > 4 and not keyword.endswith(("ss", "ics", "us", "is")):
        return keyword[:-1]
    return keyword


def classify_keyword_candidate(
    keyword: str,
    job_description: str,
    parsed_requirements: tuple[object, ...] = (),
) -> KeywordCandidateClassification:
    """Classify one literal before frequency or ranking can promote it."""

    normalized = canonical_audit_keyword(normalize_compare(keyword))
    if not normalized:
        return KeywordCandidateClassification("", KeywordCandidateClass.NOISE, False, "empty")

    if not parsed_requirements:
        try:
            from requirement_engine import parse_commercial_requirements

            parsed_requirements = tuple(parse_commercial_requirements(job_description))
        except Exception:
            parsed_requirements = ()

    matching_elements = tuple(
        element
        for element in parsed_requirements
        if normalized in normalize_compare(str(getattr(element, "text", "")))
        or contains_search_term(str(getattr(element, "text", "")), normalized)
        or normalized
        in {
            normalize_compare(str(term))
            for term in tuple(getattr(element, "canonical_terms", ()))
            if normalize_compare(str(term))
        }
    )
    validated = bool(matching_elements) or (
        not parsed_requirements
        and contains_search_term(role_requirement_text(job_description), normalized)
    )
    parts = normalized.split()
    job_title = normalize_compare(extract_job_title(job_description) or "")
    title_phrases = {normalize_compare(term) for term in title_phrase_candidates(job_description)}
    relation, validating_text, alternative_terms = _candidate_requirement_relation(
        normalized,
        matching_elements,
        job_title,
        role_requirement_text(job_description),
    )
    if normalized in title_phrases:
        relation = "assigned"
        validating_text = validating_text or job_title
    alternative_group_id = next(
        (
            str(getattr(element, "alternative_group_id", ""))
            for element in matching_elements
            if getattr(element, "alternative_group_id", "")
        ),
        "",
    )

    def classified(
        candidate_class: KeywordCandidateClass,
        is_validated: bool,
        reason: str,
    ) -> KeywordCandidateClassification:
        return KeywordCandidateClassification(
            normalized,
            candidate_class,
            is_validated,
            reason,
            relation,
            validating_text,
            alternative_group_id,
            alternative_terms,
        )

    if normalized in KEYWORD_NOISE_SINGLETONS or normalized in KEYWORD_NOISE_PHRASES:
        return classified(KeywordCandidateClass.NOISE, validated, "invalid standalone or malformed phrase")
    if len(parts) > 1 and parts[0] in {"complex", "experienced"}:
        return classified(
            KeywordCandidateClass.NOISE,
            validated,
            "non-concept modifier fragment",
        )
    if len(parts) > 1 and (parts[-1] == "supply" or parts[0] == "chain"):
        return classified(
            KeywordCandidateClass.NOISE,
            validated,
            "partial domain phrase",
        )
    if (
        len(parts) == 3
        and parts[-2:] == ["supply", "chain"]
        and parts[0] in IMPORTANT_SHORT_ATS_TERMS
    ):
        return classified(
            KeywordCandidateClass.NOISE,
            validated,
            "overlapping acronym/domain fragment",
        )
    if _domain_candidate(normalized, matching_elements):
        return classified(
            KeywordCandidateClass.DOMAIN,
            validated,
            "validated domain surface or alternative family",
        )
    if normalized in {"customer facing", "client facing", "customer focused", "client focused"}:
        return classified(
            KeywordCandidateClass.REQUIREMENT,
            validated,
            "validated customer-delivery requirement",
        )
    if normalized == "consulting" and re.search(r"\bconsultants?\b", job_title):
        relation = "assigned"
        return classified(
            KeywordCandidateClass.REQUIREMENT,
            True,
            "role-title consulting requirement",
        )
    if normalized in title_phrases:
        return classified(KeywordCandidateClass.REQUIREMENT, True, "role-title requirement phrase")
    catalog_entry = evidence_term_for_variant(normalized)
    catalog_literal_present = bool(
        catalog_entry
        and any(
            canonical_audit_keyword(normalize_compare(str(surface))) == normalized
            and contains_search_term(job_description, str(surface))
            for surface in tuple(catalog_entry.get("permitted_surfaces", ()))
        )
    )
    catalog_validated = bool(
        catalog_entry
        and evidence_entry_context_supported(catalog_entry, job_description)
        and catalog_literal_present
    )
    if catalog_validated:
        concept = canonical_audit_keyword(normalize_compare(str(catalog_entry.get("concept", ""))))
        if len(parts) == 1:
            singleton_class = (
                KeywordCandidateClass.DOMAIN
                if normalized in KEYWORD_DOMAIN_SIGNALS
                else KeywordCandidateClass.COMPETENCY
            )
            return classified(
                singleton_class,
                True,
                "catalog singleton retained outside core",
            )
        if (
            len(parts) >= 2
            and parts[-1] in KEYWORD_GENERIC_REQUIREMENT_HEAD_TAILS.get(parts[0], set())
            and normalized != concept
            and not contains_search_term(job_description, concept)
        ):
            return classified(
                KeywordCandidateClass.COMPETENCY,
                True,
                "generic catalog surface retained as breadth competency",
            )
        if relation == "counterpart":
            return classified(
                KeywordCandidateClass.COMPETENCY,
                True,
                "catalog-backed role appears only as a counterpart",
            )
        return classified(
            KeywordCandidateClass.REQUIREMENT,
            True,
            "validated evidence-catalog requirement surface",
        )
    if normalized in AUDIT_BLOCKED_PHRASES or normalized in BULLET_PLACEMENT_EXCLUDED:
        return classified(KeywordCandidateClass.NOISE, validated, "blocked low-signal phrase")
    if breadth_term_is_noise(normalized) or is_low_signal_audit_keyword(normalized):
        return classified(KeywordCandidateClass.NOISE, validated, "failed shared phrase-shape gate")
    if any(part in STOP_WORDS for part in parts):
        return classified(KeywordCandidateClass.NOISE, validated, "contains stopword fragment")
    if parts and parts[0] in AUDIT_ACTION_LEAD_WORDS:
        return classified(KeywordCandidateClass.NOISE, validated, "dangling action phrase")

    if normalized in IMPORTANT_SHORT_ATS_TERMS or normalized in KEYWORD_COMPETENCY_SINGLETONS:
        return classified(KeywordCandidateClass.COMPETENCY, validated, "recognized competency")
    if (
        len(parts) >= 2
        and parts[-1] in KEYWORD_GENERIC_REQUIREMENT_HEAD_TAILS.get(parts[0], set())
    ):
        return classified(
            KeywordCandidateClass.COMPETENCY,
            validated,
            "generic-head phrase retained as breadth competency",
        )
    if (
        len(parts) >= 2
        and parts[0] in IMPORTANT_SHORT_ATS_TERMS
        and parts[-1] in KEYWORD_ACRONYM_BREADTH_TAILS
    ):
        return classified(
            KeywordCandidateClass.COMPETENCY,
            validated,
            "tool-reporting phrase retained as breadth competency",
        )
    if len(parts) >= 2 and (
        parts[-1] in KEYWORD_VALID_PHRASE_TAILS
        or any(part in IMPORTANT_SHORT_ATS_TERMS for part in parts)
    ):
        return classified(
            KeywordCandidateClass.REQUIREMENT,
            validated,
            "validated requirement-shaped phrase",
        )
    element_categories = {str(getattr(element, "category", "")) for element in matching_elements}
    if "domain" in element_categories or normalized in KEYWORD_DOMAIN_SIGNALS:
        return classified(KeywordCandidateClass.DOMAIN, validated, "validated domain surface")
    if "skill_tool" in element_categories:
        return classified(KeywordCandidateClass.COMPETENCY, validated, "validated skill or tool")
    return classified(KeywordCandidateClass.NOISE, validated, "not requirement or competency shaped")


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


def collapse_core_concept_families(
    keywords: set[str],
    job_description: str,
) -> set[str]:
    """Keep one scoring surface for each catalog-backed requirement concept.

    Exact JD surfaces remain available to breadth/placement diagnostics. Core
    coverage, however, must not count every permitted spelling of the same
    evidence concept as a separate requirement.
    """
    ungrouped: set[str] = set()
    grouped: dict[str, list[str]] = {}
    concept_names: dict[str, str] = {}
    for keyword in keywords:
        entry = evidence_term_for_variant(keyword)
        concept_id = str((entry or {}).get("concept_id", "")).strip()
        if not entry or not concept_id:
            ungrouped.add(keyword)
            continue
        grouped.setdefault(concept_id, []).append(keyword)
        concept_names[concept_id] = normalize_compare(str(entry.get("concept", "")))

    collapsed = set(ungrouped)
    for concept_id, surfaces in grouped.items():
        concept_name = concept_names.get(concept_id, "")
        def assigned_literal_score(surface: str) -> int:
            score = 0
            assigned_action_re = re.compile(
                r"\b(?:own|owns|owned|lead|leads|led|drive|drives|drove|"
                r"manage|manages|managed|deliver|delivers|delivered|"
                r"implement|implements|implemented|coordinate|coordinates|"
                r"coordinated|maintain|maintains|maintained|responsible for|"
                r"serve as|act as|function as)\b",
                re.I,
            )
            counterpart_re = re.compile(
                r"\b(?:partner|collaborate|work|coordinate)\w*\s+"
                r"(?:closely\s+)?with\b",
                re.I,
            )
            for line in re.split(r"[\r\n]+|(?<=[.!?])\s+", job_description):
                if not contains_search_term(line, surface):
                    continue
                line_score = 1
                if assigned_action_re.search(line):
                    line_score += 3
                if counterpart_re.search(line):
                    line_score -= 4
                score = max(score, line_score)
            return score

        collapsed.add(
            max(
                surfaces,
                key=lambda surface: (
                    assigned_literal_score(surface),
                    normalize_compare(surface) == concept_name,
                    keyword_occurrence_count(job_description, surface),
                    len(normalize_compare(surface).split()),
                    len(surface),
                    normalize_compare(surface),
                    surface,
                ),
            )
        )
    return collapsed


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
        "teams delivery",
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
        classification = classify_keyword_candidate(keyword, original_job_description, tuple(parsed_requirements))
        if (
            classification.candidate_class != KeywordCandidateClass.REQUIREMENT
            or not classification.validated_requirement
        ):
            continue
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
    if contains_search_term(original_job_description, "go-live"):
        keywords.discard("go live")
        keywords.add("go-live")

    if consulting_mode:
        keywords = {
            keyword
            for keyword in keywords
            if " " not in keyword or not all(part in keywords for part in keyword.split())
        }
    for element in parsed_requirements:
        keywords.update(
            term
            for term in element.canonical_terms
            if classify_keyword_candidate(
                term,
                original_job_description,
                tuple(parsed_requirements),
            ).candidate_class
            == KeywordCandidateClass.REQUIREMENT
        )
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
            and classify_keyword_candidate(term, original_job_description, tuple(parsed_requirements)).candidate_class
            == KeywordCandidateClass.REQUIREMENT
        )
    for entry in evidence_terms():
        for surface in tuple(str(value) for value in entry.get("permitted_surfaces", ())):
            normalized_surface = canonical_audit_keyword(normalize_compare(surface))
            if not normalized_surface or not contains_search_term(original_job_description, surface):
                continue
            classification = classify_keyword_candidate(
                normalized_surface,
                original_job_description,
                tuple(parsed_requirements),
            )
            if (
                classification.candidate_class == KeywordCandidateClass.REQUIREMENT
                and classification.validated_requirement
            ):
                keywords.add(re.sub(r"\s+", " ", surface.strip().lower()))
    return collapse_core_concept_families(keywords, original_job_description)


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
    phrase_signal = 0
    if " " in normalized:
        phrase_signal = 2 if keyword_occurrence_count(job_description, keyword) >= 2 and len(parts) <= 3 else 1
    return (
        1 if normalized in title_phrases else 0,
        phrase_signal,
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


def high_value_audit_keywords(job_description: str) -> list[str]:
    return sorted(
        (
            keyword
            for keyword in audit_keywords(job_description)
            if not is_generic_soft_keyword(keyword) and not is_bullet_placement_excluded(keyword)
        ),
        key=lambda keyword: audit_keyword_sort_key(job_description, keyword),
        reverse=True,
    )


def ats_scan_terms(job_description: str, *, limit: int = 25) -> list[str]:
    """Return a broader advisory ATS surface without widening placement gates."""
    original_job_description = job_description
    try:
        from requirement_engine import parse_commercial_requirements

        parsed_requirements = parse_commercial_requirements(job_description)
    except Exception:
        parsed_requirements = ()
    if parsed_requirements:
        job_description = "\n".join(element.text for element in parsed_requirements)

    explicit_company = re.search(r"(?im)^\s*company(?:\s+name)?\s*[:\-]\s*(.+?)\s*$", original_job_description)
    company_name = normalize_compare(explicit_company.group(1) if explicit_company else (extract_company_name(original_job_description) or ""))
    company_tokens = set(company_name.split())
    company_tokens |= affiliate_company_tokens(original_job_description)
    title_phrases = set(title_phrase_candidates(original_job_description))

    candidates: set[str] = set(high_value_audit_keywords(original_job_description))
    candidates.update(title_phrases)
    for line in keyword_source_lines(job_description):
        candidates.update(line_ngram_phrases(line, min_words=2, max_words=2))
        candidates.update(line_ngram_phrases(line, min_words=3, max_words=3))
        for word in re.findall(r"[A-Za-z][A-Za-z+.#-]{2,}", line):
            cleaned = clean_keyword_candidate(word)
            if cleaned:
                candidates.add(cleaned)
    for element in parsed_requirements:
        candidates.update(element.canonical_terms)

    candidates.update(evidence_supported_surfaces(original_job_description))

    phrase_blockers = {
        "accordingly",
        "additional",
        "all",
        "avoid",
        "conduct",
        "drive",
        "drives",
        "early",
        "end",
        "employee",
        "employees",
        "ensuring",
        "experience",
        "help",
        "including",
        "identify",
        "impact",
        "its",
        "job",
        "join",
        "lead",
        "leverage",
        "looking",
        "may",
        "not",
        "organization",
        "possible",
        "promote",
        "providing",
        "report",
        "role",
        "state",
        "such",
        "taking",
        "them",
        "total",
        "through",
        "united",
        "what",
        "when",
        "where",
        "which",
        "work",
        "would",
        "worldwide",
        "year",
        "years",
    }

    def keep(term: str) -> bool:
        normalized = canonical_audit_keyword(normalize_compare(term))
        if not normalized or len(normalized) < 3:
            return False
        classification = classify_keyword_candidate(
            normalized,
            original_job_description,
            tuple(parsed_requirements),
        )
        if (
            classification.candidate_class == KeywordCandidateClass.NOISE
            or not classification.validated_requirement
        ):
            return False
        if normalized.isdigit() or normalized in STOP_WORDS:
            return False
        if normalized in company_tokens or normalized == company_name:
            return False
        if " " in normalized and any(part in company_tokens for part in normalized.split()) and normalized not in title_phrases:
            return False
        if classification.reason == "validated evidence-catalog requirement surface":
            entry = evidence_term_for_variant(normalized)
            return bool(
                entry
                and any(
                    canonical_audit_keyword(normalize_compare(str(surface))) == normalized
                    and contains_search_term(original_job_description, str(surface))
                    for surface in tuple(entry.get("permitted_surfaces", ()))
                )
            )
        if normalized in BULLET_PLACEMENT_EXCLUDED or normalized in AUDIT_BLOCKED_PHRASES:
            return False
        if breadth_term_is_noise(normalized):
            return False
        if is_generic_soft_keyword(normalized):
            return False
        parts = normalized.split()
        if any(part in STOP_WORDS for part in parts):
            return False
        if any(part in phrase_blockers for part in parts):
            return False
        if any(part in AUDIT_NOISE_KEYWORDS for part in parts) and not (
            normalized in title_phrases
            or any(part in AUDIT_PRIORITY_KEYWORDS for part in parts)
            or any(part in SUMMARY_PLACEMENT_TERMS for part in parts)
        ):
            return False
        if " " in normalized and (
            parts[0] in AUDIT_ACTION_LEAD_WORDS
            or parts[-1] in AUDIT_LOW_SIGNAL_TRAIL_WORDS
            or parts[-1] in AUDIT_NOISE_KEYWORDS
        ):
            return False
        if " " in normalized and normalized not in title_phrases:
            if (
                keyword_occurrence_count(original_job_description, normalized) < 2
                and parts[-1] not in AUDIT_PHRASE_TAIL_PRIORITY_WORDS
                and not any(part in IMPORTANT_SHORT_ATS_TERMS for part in parts)
            ):
                return False
        if " " not in normalized and normalized not in IMPORTANT_SHORT_ATS_TERMS:
            if (
                normalized not in AUDIT_PRIORITY_KEYWORDS
                and normalized not in SUMMARY_PLACEMENT_TERMS
                and keyword_occurrence_count(original_job_description, normalized) < 2
            ):
                return False
        return contains_search_term(original_job_description, normalized)

    ordered: list[str] = []
    seen: set[str] = set()
    for term in sorted(
        (canonical_audit_keyword(candidate) for candidate in candidates),
        key=lambda keyword: audit_keyword_sort_key(original_job_description, keyword),
        reverse=True,
    ):
        normalized = normalize_compare(term)
        if normalized in seen or not keep(term):
            continue
        ordered.append(term)
        seen.add(normalized)
    return collapse_breadth_compound_families(ordered, original_job_description)[:limit]


def ats_coverage(job_description: str, resume_text: str, *, limit: int = 5) -> dict[str, object]:
    promoted_core_terms = {"project management", "professional services", "professional service"}
    title_phrases = set(title_phrase_candidates(job_description))
    placed_promoted_core = {
        surface
        for surface in evidence_supported_surfaces(job_description)
        if normalize_compare(surface) in promoted_core_terms
        and contains_search_term(resume_text, surface)
    }
    raw_keywords = set(high_value_audit_keywords(job_description)) | placed_promoted_core
    keywords = [
        keyword
        for keyword in raw_keywords
        if not is_unsupported_do_not_insert(keyword, resume_text, job_description)
        and not (
            normalize_compare(keyword) in promoted_core_terms
            and not contains_search_term(resume_text, keyword)
            and normalize_compare(keyword) not in title_phrases
            and keyword_occurrence_count(job_description, keyword) < 2
        )
    ]
    present = [keyword for keyword in keywords if contains_search_term(resume_text, keyword)]
    missing = [keyword for keyword in keywords if keyword not in present]
    total = len(keywords)
    percent = round((len(present) / total) * 100) if total else 100
    breadth_keywords = [
        keyword
        for keyword in ats_scan_terms(job_description)
        if not is_unsupported_do_not_insert(keyword, resume_text, job_description)
    ]
    breadth_present = [keyword for keyword in breadth_keywords if contains_search_term(resume_text, keyword)]
    breadth_missing = [keyword for keyword in breadth_keywords if keyword not in breadth_present]
    breadth_total = len(breadth_keywords)
    breadth_percent = round((len(breadth_present) / breadth_total) * 100) if breadth_total else 100
    thin_denominator = len(re.findall(r"\b[\w+.#'-]+\b", role_requirement_text(job_description))) > 250 and breadth_total < 10
    return {
        "percent": percent,
        "present": len(present),
        "total": total,
        "missing": missing[:limit],
        "core": {
            "percent": percent,
            "present": len(present),
            "total": total,
            "missing": missing[:limit],
        },
        "breadth": {
            "percent": breadth_percent,
            "present": len(breadth_present),
            "total": breadth_total,
            "missing": breadth_missing[:limit],
            "thin_denominator": thin_denominator,
        },
    }

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


ATS_BREADTH_BLOCKED_TERMS = {
    "agreement training",
    "approaches throughout",
    "conduct orientation training",
    "development technical training",
    "directly influence",
    "embraces diverse",
    "excellent time management",
    "executive briefings training",
    "ged",
    "growth solution consultant",
    "high school",
    "highly preferred",
    "ideal candidate",
    "improve approach",
    "independently manage",
    "initiative quality",
    "leading edge",
    "long-term",
    "long-term platform stability",
    "may",
    "nature scope",
    "orientation training",
    "planning uat",
    "prioritizations skill",
    "quality delivery",
    "research emerging ai",
    "school diploma",
    "school equivalency",
    "solutions across",
    "subordinate management",
    "such",
    "test planning uat",
    "trade agreement training",
    "translate high-level",
    "translate physical",
    "virtual client training",
}

ATS_BREADTH_EDGE_PREPOSITIONS = {
    "across",
    "for",
    "into",
    "of",
    "on",
    "throughout",
    "to",
    "with",
}

ATS_BREADTH_COMPOUND_COLLAPSE_TAILS = {"adoption", "delivery", "integration", "service"}


def breadth_term_is_noise(term: str) -> bool:
    normalized = normalize_compare(term)
    if not normalized:
        return True
    if normalized in ATS_BREADTH_BLOCKED_TERMS:
        return True
    parts = normalized.split()
    if not parts:
        return True
    if parts[0] in ATS_BREADTH_EDGE_PREPOSITIONS or parts[-1] in ATS_BREADTH_EDGE_PREPOSITIONS:
        return True
    if len(parts) > 1 and parts[0].endswith("ing") and parts[0] not in AUDIT_PRIORITY_KEYWORDS:
        return True
    if len(parts) > 1 and parts[-1] == "training":
        return True
    return False


def collapse_breadth_compound_families(terms: list[str], job_description: str) -> list[str]:
    catalog_groups: dict[str, list[str]] = {}
    ungrouped_terms: list[str] = []
    for term in terms:
        entry = evidence_term_for_variant(term)
        concept_id = str((entry or {}).get("concept_id", "")).strip()
        if concept_id:
            catalog_groups.setdefault(concept_id, []).append(term)
        else:
            ungrouped_terms.append(term)
    catalog_representatives: list[str] = []
    for family in catalog_groups.values():
        entry = evidence_term_for_variant(family[0]) or {}
        preferred = evidence_preferred_surface(str(entry.get("concept", family[0])), job_description)
        representative = next(
            (
                term
                for term in family
                if normalize_compare(term) == normalize_compare(preferred)
            ),
            max(
                family,
                key=lambda term: (
                    keyword_occurrence_count(job_description, term),
                    len(normalize_compare(term).split()),
                    len(term),
                ),
            ),
        )
        catalog_representatives.append(representative)

    terms = [*ungrouped_terms, *catalog_representatives]
    grouped: dict[str, list[str]] = {}
    passthrough: list[str] = []
    for term in terms:
        parts = normalize_compare(term).split()
        if len(parts) > 1 and parts[-1] in ATS_BREADTH_COMPOUND_COLLAPSE_TAILS:
            grouped.setdefault(parts[-1], []).append(term)
        else:
            passthrough.append(term)

    collapsed = list(passthrough)
    seen = {normalize_compare(term) for term in collapsed}
    for tail, family in grouped.items():
        sorted_family = sorted(
            family,
            key=lambda keyword: (
                keyword_occurrence_count(job_description, keyword),
                *audit_keyword_sort_key(job_description, keyword),
            ),
            reverse=True,
        )
        keep: list[str] = []
        if any(normalize_compare(term) == tail for term in terms):
            keep.append(tail)
        keep.extend(term for term in sorted_family if normalize_compare(term) != tail)
        for term in keep[:2]:
            normalized = normalize_compare(term)
            if normalized and normalized not in seen:
                collapsed.append(term)
                seen.add(normalized)
    ordered = sorted(
        collapsed,
        key=lambda keyword: (
            keyword_occurrence_count(job_description, keyword),
            -len(normalize_compare(keyword).split()),
            audit_keyword_sort_key(job_description, keyword),
        ),
        reverse=True,
    )
    reconciled: list[str] = []
    for term in ordered:
        term_parts = normalize_compare(term).split()
        term_class = classify_keyword_candidate(term, job_description).candidate_class
        overlaps = False
        for kept in reconciled:
            if classify_keyword_candidate(kept, job_description).candidate_class != term_class:
                continue
            kept_parts = normalize_compare(kept).split()
            shorter, longer = (
                (term_parts, kept_parts)
                if len(term_parts) <= len(kept_parts)
                else (kept_parts, term_parts)
            )
            if any(
                longer[index : index + len(shorter)] == shorter
                for index in range(len(longer) - len(shorter) + 1)
            ):
                overlaps = True
                break
        if not overlaps:
            reconciled.append(term)
    return sorted(
        reconciled,
        key=lambda keyword: audit_keyword_sort_key(job_description, keyword),
        reverse=True,
    )


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

def scope_pace_signal_labels(job_description: str) -> tuple[str, ...]:
    """Flag posting language suggesting a faster/higher-volume or lower-complexity role
    than Christian's enterprise implementation background, so guides and letters can
    address the mismatch proactively instead of only conceding it if asked."""
    job_description = role_requirement_text(job_description)
    hits: list[str] = []
    for area in SCOPE_PACE_MISMATCH_SIGNALS:
        if signal_hits(job_description, tuple(area["job_terms"])) >= int(area["minimum_job_hits"]):
            hits.append(str(area["label"]))
    return tuple(dict.fromkeys(hits))


def job_problem_profile(job_description: str, resume_text: str = "") -> JobProblemProfile:
    original_job_description = job_description
    job_description = role_requirement_text(job_description)
    if is_general_management_consulting_role(original_job_description):
        lane = CORPORATE_STRATEGY_PROFILE
    else:
        title_text = extract_job_title(original_job_description) or ""
        title_priority_lanes = {"program_delivery", "product_ownership", "process_improvement", "technical_support_admin"}
        lane_scores = [
            (
                signal_hits(job_description, tuple(lane["signals"]))
                + (signal_hits(title_text, tuple(lane["signals"])) * 8 if str(lane["key"]) in title_priority_lanes else 0),
                lane,
            )
            for lane in TARGETING_LANES
        ]
        lane_scores.sort(key=lambda item: item[0], reverse=True)
        score, lane = lane_scores[0]
        if (
            str(lane["key"]) == "technical_support_admin"
            and signal_hits(title_text, tuple(lane["signals"])) == 0
            and signal_hits(job_description, tuple(lane["signals"])) < 4
        ):
            score, lane = next(
                item for item in lane_scores if str(item[1]["key"]) != "technical_support_admin"
            )
        if (
            str(lane["key"]) == "process_improvement"
            and not signal_hits(title_text, tuple(lane["signals"]))
            and text_mentions(original_job_description, "assessment", "measurement", "learning", "academic content")
        ):
            lane = next(item for item in TARGETING_LANES if item["key"] == "analytics_operations")
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
        scope_pace_signals=scope_pace_signal_labels(original_job_description),
    )


def natural_problem_phrase(profile: JobProblemProfile) -> str:
    return {
        "program_delivery": "turning cross-functional program ambiguity into visible milestones, risks, and delivery decisions",
        "product_ownership": "turning stakeholder needs into prioritized product work people can actually adopt",
        "process_improvement": "turning operational friction into measurable workflow improvement",
        "technical_support_admin": "turning application issues, access needs, and incidents into stable technical support",
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
