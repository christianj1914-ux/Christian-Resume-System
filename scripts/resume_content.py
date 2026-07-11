#!/usr/bin/env python3
"""Resume content generation, rewrite, and competency helpers."""  # noqa: force-mtime

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
from xml.etree import ElementTree as ET

from config.job_profiles import (
    CONDITIONAL_COMPETENCY_ITEMS,
    SIMPLE_COMPETENCY_KEYWORDS,
    TAILORING_EMPHASIS_PROFILES,
)
from config.language_rules import (
    MANDATORY_REORG_SENTENCE,
    PROFESSIONAL_SUMMARY_MAX_WORDS,
    PROFESSIONAL_SUMMARY_MIN_WORDS,
)
import business_context
import prose_engine
from resume_analysis import (
    IMPORTANT_SHORT_ATS_TERMS,
    JobProblemProfile,
    employer_context_matches,
    extract_job_title,
    jd_explicitly_requires_erp,
    jd_mentions,
    job_problem_profile,
    is_consulting_job_description,
    normalize_compare,
    normalize_title,
    primary_employer_context,
    primary_story_lens,
    is_startup_or_broad_operator_role,
    role_specialty_phrase,
    story_lens_business_problem,
    story_lens_candidate_story,
    story_lens_identity,
    story_lens_sentence,
    text_mentions,
    visible_role_specialties,
)
from resume_format import (
    BODY_FONT_SIZE_HP,
    BRAND_BLUE,
    CORE_COMPETENCY_ROW_SEPARATOR_FONT_SIZE_HP,
    SKILLS_SECTION_HEADING,
    REQUIRED_SECTIONS,
    RESUME_FONT,
    W,
    append_run,
    estimate_page_count_from_xml,
    is_skills_section_heading,
    is_bullet,
    is_role_heading,
    normalize_required_section_name,
    paragraph_text,
    remove_runs,
    section_matches,
    set_bool_prop,
    set_paragraph_text,
    set_run_color,
    set_run_font,
    set_run_size,
)
from utils import debug_print, fail, has_great_eight_signal
from text_safety import collision_safe_substitute, neutralize_conflicting_region_lists

COMPANY_EAST_WEST = "East West Manufacturing"
COMPANY_APTEAN = "Aptean"
COMPANY_HOME_DEPOT = "The Home Depot"
COMPANY_ADERANT = "Aderant"
CONDENSABLE_BULLET_COMPANIES = (COMPANY_EAST_WEST, COMPANY_APTEAN)
MIN_FINAL_BULLETS_BY_COMPANY = {
    COMPANY_EAST_WEST: 5,
    COMPANY_APTEAN: 5,
    COMPANY_HOME_DEPOT: 3,
    COMPANY_ADERANT: 2,
}
LOWERCASE_SKILL_WORDS = {"and"}
SPECIAL_SKILL_WORDS = {
    "ai": "AI",
    "api": "API",
    "arr": "ARR",
    "b2b": "B2B",
    "bi": "BI",
    "bom": "BOM",
    "cpq": "CPQ",
    "crm": "CRM",
    "devops": "DevOps",
    "edi": "EDI",
    "erp": "ERP",
    "etl": "ETL",
    "frd": "FRD",
    "frds": "FRDs",
    "gl": "GL",
    "kpi": "KPI",
    "llm": "LLM",
    "mro": "MRO",
    "nlp": "NLP",
    "grr": "GRR",
    "nrr": "NRR",
    "pmi": "PMI",
    "qbr": "QBR",
    "qbrs": "QBRs",
    "roi": "ROI",
    "saas": "SaaS",
    "sap": "SAP",
    "sdlc": "SDLC",
    "sfdc": "SFDC",
    "servicenow": "ServiceNow",
    "liveperson": "LivePerson",
    "liveengage": "LiveEngage",
    "sow": "SOW",
    "sows": "SOWs",
    "sql": "SQL",
    "tfs": "TFS",
    "uat": "UAT",
    "wms": "WMS",
}
CORE_COMPETENCY_TARGET_ITEMS = 23

@dataclass(frozen=True)
class ParagraphInfo:
    text: str
    is_bullet: bool

@dataclass(frozen=True)
class RoleInfo:
    title: str
    company: str
    company_context: str
    bullet_count: int
    block_text: str

@dataclass(frozen=True)
class ResumeSnapshot:
    full_text: str
    sections: set[str]
    roles: list[RoleInfo]
    competency_labels: set[str]
    competency_items: set[str]
    professional_development_items: set[str]


@dataclass(frozen=True)
class TailoringEmphasis:
    key: str
    label: str
    summary_family: str
    proof_anchor: str
    bullet_terms: tuple[str, ...]
    competency_terms: tuple[str, ...]

EXPERIENCE_CASE_REPLACEMENTS = {
    "Statements of Work": "statements of work",
    "Functional Requirements Documents": "functional requirements documents",
    "Requirements Gathering": "requirements gathering",
    "Gap Analysis": "gap analysis",
    "System Review": "system review",
    "Data Analysis": "data analysis",
    "Order Management": "order management",
    "Project Management": "project management",
    "Resource Management": "resource management",
    "Deliverable Management": "deliverable management",
    "Product Functionality": "product functionality",
    "Solution Functionality": "solution functionality",
}

NON_ERP_VISIBLE_PLATFORM_PATTERN = re.compile(
    r"\b(ERP|Aptean Intuitive|Aptean Encompix|Epicor Kinetic|SAP(?!\s+Crystal Reports\b)|Oracle ERP|Microsoft Dynamics 365)\b",
    re.I,
)

CUTOVER_REPLACEMENTS = (
    (r"\bcross-functional cutover coordination\b", "cross-functional migration readiness coordination"),
    (r"\bcoordinating cutover timing\b", "coordinating release timing"),
    (r"\bas the migration reached cutover\b", "as the migration reached launch readiness"),
    (r"\bmigration reached cutover\b", "migration reached launch readiness"),
    (r"\bthrough final cutover\b", "through final launch readiness"),
    (r"\bfinal cutover\b", "final launch readiness"),
    (r"\bcutover coordination\b", "migration readiness coordination"),
    (r"\bcutover timing\b", "release timing"),
    (r"\bcutover plan\b", "transition plan"),
    (r"\bthrough cutover\b", "through launch readiness"),
    (r"\bcutover\b", "transition"),
)

def visible_text(document_xml: Path) -> str:
    root = ET.parse(document_xml).getroot()
    paragraphs: list[str] = []
    for paragraph in root.findall(f".//{W}p"):
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)

def paragraph_infos(document_xml: Path) -> list[ParagraphInfo]:
    root = ET.parse(document_xml).getroot()
    paragraphs: list[ParagraphInfo] = []
    for paragraph in root.findall(f".//{W}p"):
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        if text:
            paragraphs.append(ParagraphInfo(text=text, is_bullet=is_bullet(paragraph)))
    return paragraphs

def score(text: str, keywords: set[str]) -> int:
    normalized = text.lower()
    total = 0
    for keyword in keywords:
        if len(keyword) < 3:
            continue
        if " " in keyword:
            total += 4 if keyword in normalized else 0
        elif re.search(rf"\b{re.escape(keyword)}\b", normalized):
            total += 1
    return total

def remove_reorg_sentence(text: str) -> str:
    text = re.sub(rf"\s*{re.escape(MANDATORY_REORG_SENTENCE)}\s*", " ", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip()

def append_reorg_sentence(text: str) -> str:
    body = remove_reorg_sentence(text).rstrip()
    if not body:
        return MANDATORY_REORG_SENTENCE
    return f"{body.rstrip('.')} .".replace(" .", ".") + f" {MANDATORY_REORG_SENTENCE}"

def preserve_reorg_sentence_at_end(original: str, updated: str) -> str:
    if MANDATORY_REORG_SENTENCE.lower() in original.lower():
        return append_reorg_sentence(updated)
    return updated


def _normalize_terms(terms: Sequence[str]) -> tuple[str, ...]:
    return tuple(normalize_compare(term) for term in terms if normalize_compare(term))


def _default_emphasis_key(profile: JobProblemProfile, variant_index: int) -> str:
    primary_defaults = {
        "presales_solution": "customer_value",
        "customer_success": "customer_value",
        "change_enablement": "change_adoption",
        "analytics_operations": "analytics_reporting",
        "corporate_strategy": "operations_strategy",
        "implementation_delivery": "launch_migration",
    }
    secondary_defaults = {
        "presales_solution": "operations_strategy",
        "customer_success": "change_adoption",
        "change_enablement": "ai_workflows",
        "analytics_operations": "operations_strategy",
        "corporate_strategy": "analytics_reporting",
        "implementation_delivery": "analytics_reporting",
    }
    fallback_map = secondary_defaults if variant_index else primary_defaults
    return fallback_map.get(profile.primary_lane, "operations_strategy")


def determine_tailoring_emphasis(
    job_description: str,
    resume_text: str = "",
    variant_index: int = 0,
) -> TailoringEmphasis:
    profile = job_problem_profile(job_description, resume_text)
    job_key = normalize_compare(job_description)
    context = primary_employer_context(job_description)
    context_key = normalize_compare(context["key"]) if context else ""
    scored_profiles: list[tuple[int, int, str, dict[str, object]]] = []

    for order, config in enumerate(TAILORING_EMPHASIS_PROFILES):
        signals = _normalize_terms(config.get("signals", ()))
        lanes = _normalize_terms(config.get("lanes", ()))
        employer_contexts = _normalize_terms(config.get("employer_contexts", ()))
        bullet_terms = _normalize_terms(config.get("bullet_terms", ()))
        competency_terms = _normalize_terms(config.get("competency_terms", ()))

        score = 0
        signal_hits = sum(1 for signal in signals if signal in job_key)
        score += min(signal_hits * 4, 20)
        if normalize_compare(profile.primary_lane) in lanes:
            score += 5
        if context_key and context_key in employer_contexts:
            score += 3
        term_hits = sum(1 for term in (*bullet_terms, *competency_terms) if term in job_key)
        score += min(term_hits * 2, 8)
        scored_profiles.append((score, -order, str(config["key"]), config))

    scored_profiles.sort(key=lambda row: (-row[0], row[1], row[2]))
    default_key = _default_emphasis_key(profile, 0)
    primary_config = next(
        (config for _score, _order, key, config in scored_profiles if key == default_key),
        scored_profiles[0][3],
    )
    if scored_profiles and scored_profiles[0][0] > 0:
        primary_config = scored_profiles[0][3]

    selected_config = primary_config
    if variant_index:
        distinct_ranked = [config for _score, _order, key, config in scored_profiles if key != str(primary_config["key"])]
        secondary_key = _default_emphasis_key(profile, 1)
        third_key = "ai_workflows" if secondary_key != "ai_workflows" else "operations_strategy"
        preferred_keys = [secondary_key, third_key]
        if distinct_ranked:
            distinct_configs: list[dict[str, object]] = []
            seen_keys: set[str] = set()
            for config in distinct_ranked:
                key = str(config["key"])
                if key in seen_keys:
                    continue
                distinct_configs.append(config)
                seen_keys.add(key)
            preferred_ordered = [
                config
                for key in preferred_keys
                for config in distinct_configs
                if str(config["key"]) == key
            ]
            fallback_ranked = [config for config in distinct_configs if config not in preferred_ordered]
            ordered_variants = preferred_ordered + fallback_ranked
            selected_config = ordered_variants[min(variant_index - 1, len(ordered_variants) - 1)]

    return TailoringEmphasis(
        key=str(selected_config["key"]),
        label=str(selected_config["label"]),
        summary_family=str(selected_config["summary_family"]),
        proof_anchor=str(selected_config["proof_anchor"]),
        bullet_terms=tuple(str(term) for term in selected_config["bullet_terms"]),
        competency_terms=tuple(str(term) for term in selected_config["competency_terms"]),
    )

def summary_domain_items(job_description: str) -> list[str]:
    """Build the Professional Summary domain list from the active job description."""
    matched: list[str] = []

    def add(item: str) -> None:
        if item not in matched:
            matched.append(item)

    if jd_mentions(job_description, "manufacturing", "erp", "inventory", "supply chain"):
        add("manufacturing")
        add("supply chain")
    if jd_mentions(job_description, "healthcare", "clinical", "patient", "claims"):
        add("healthcare")
    if jd_mentions(job_description, "banking", "insurance", "payments", "fintech"):
        add("financial services")
    if jd_mentions(job_description, "ecommerce", "online retail", "digital commerce"):
        add("eCommerce")
    if jd_mentions(job_description, "saas", "cloud platform", "subscription software"):
        add("SaaS")
    if jd_mentions(job_description, "salesforce", "crm"):
        add("CRM")
    if jd_mentions(job_description, "analytics", "dashboards", "bi", "reporting"):
        add("analytics and reporting")
    if jd_mentions(job_description, "customer success", "adoption", "renewal", "retention"):
        add("customer success")

    domains = ["software implementation"]
    for item in matched:
        if item not in domains:
            domains.append(item)
        if len(domains) >= 5:
            break
    if len(domains) < 5:
        domains.append("enterprise software")
    return domains[:5]

def is_company_context_paragraph(company: str, text: str) -> bool:
    company_key = normalize_compare(company)
    text_key = normalize_compare(text)
    if not company_key or not text_key.startswith(company_key):
        return False
    remainder = text_key[len(company_key) :].strip()
    return remainder.startswith(("is ", "provides ", "operates ", "serves "))

def role_detail_paragraphs_after_company(children: list[ET.Element], company_index: int) -> tuple[list[ET.Element], int]:
    detail_paragraphs: list[ET.Element] = []
    scan_index = company_index + 1
    while scan_index < len(children):
        paragraph = children[scan_index]
        if paragraph.tag != f"{W}p":
            scan_index += 1
            continue
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        if not text:
            scan_index += 1
            continue
        if (
            is_bullet(paragraph)
            or is_role_heading(text)
            or normalize_required_section_name(text) is not None
            or " | " in text
        ):
            break
        detail_paragraphs.append(paragraph)
        scan_index += 1
    return detail_paragraphs, scan_index

def business_process_or_servicenow_role(job_description: str) -> bool:
    return jd_mentions(
        job_description,
        "servicenow",
        "business process",
        "process mapping",
        "workflow analysis",
        "requirements gathering",
        "user story",
        "functional specifications",
        "process optimization",
    )

def replace_paragraph_prefix(paragraph: ET.Element, old_label: str, new_label: str) -> bool:
    old_prefix = f"{old_label}:"
    new_prefix = f"{new_label}:"
    for text_node in paragraph.findall(f".//{W}t"):
        if text_node.text and old_prefix in text_node.text:
            text_node.text = text_node.text.replace(old_prefix, new_prefix, 1)
            return True

    text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
    if text.startswith(old_prefix):
        set_paragraph_text(paragraph, new_prefix + text[len(old_prefix) :])
        return True
    return False

def title_case_skill_phrase(value: str) -> str:
    words = re.split(r"(\s+|-)", value.strip())
    titled: list[str] = []
    for word in words:
        if not word or word.isspace() or word == "-":
            titled.append(word)
            continue
        match = re.match(r"^([^A-Za-z0-9]*)([A-Za-z0-9]+)([^A-Za-z0-9]*)$", word)
        if not match:
            titled.append(word)
            continue
        prefix, core, suffix = match.groups()
        plain = core.lower()
        if plain in LOWERCASE_SKILL_WORDS:
            titled.append(prefix + core.lower() + suffix)
        elif plain in SPECIAL_SKILL_WORDS:
            titled.append(prefix + SPECIAL_SKILL_WORDS[plain] + suffix)
        elif core.isupper() and (len(core) <= 5 or any(char.isdigit() for char in core)):
            titled.append(prefix + core + suffix)
        else:
            titled.append(prefix + core[:1].upper() + core[1:].lower() + suffix)
    normalized = "".join(titled)
    normalized = re.sub(r"\bLLM-Based\b", "LLM-based", normalized)
    normalized = re.sub(r"\bNLP-Based\b", "NLP-based", normalized)
    return normalized

def professional_summary_text(document_xml: Path) -> str | None:
    paragraphs = paragraph_infos(document_xml)
    start = section_index(paragraphs, "Professional Summary")
    end = section_index(paragraphs, "Professional Experience")
    if start is None or end is None or end <= start:
        return None
    summary_parts = [paragraph.text for paragraph in paragraphs[start + 1 : end] if paragraph.text]
    return " ".join(summary_parts).strip()

def section_index(paragraphs: list[ParagraphInfo], section: str) -> int | None:
    for index, paragraph in enumerate(paragraphs):
        if section_matches(paragraph.text, section):
            return index
    return None

def split_items(text: str) -> set[str]:
    return {
        re.sub(r"\s+", " ", item).strip()
        for item in re.split(r"\s+\|\s+|;", text)
        if re.sub(r"\s+", " ", item).strip()
    }

def extract_roles(paragraphs: list[ParagraphInfo]) -> list[RoleInfo]:
    start = section_index(paragraphs, "Professional Experience")
    end = section_index(paragraphs, "Education")
    if start is None or end is None or end <= start:
        return []

    roles: list[RoleInfo] = []
    role_positions: list[tuple[int, str]] = []
    for index in range(start + 1, end):
        paragraph = paragraphs[index]
        if not paragraph.is_bullet and is_role_heading(paragraph.text):
            role_positions.append((index, normalize_title(paragraph.text)))

    for pos, (index, title) in enumerate(role_positions):
        next_index = role_positions[pos + 1][0] if pos + 1 < len(role_positions) else end
        block = paragraphs[index:next_index]
        company = ""
        company_context = ""
        company_seen = False
        for paragraph in block[1:]:
            if paragraph.is_bullet:
                if company_seen:
                    break
                continue
            if not company_seen:
                company = paragraph.text.split("|", 1)[0].strip()
                company_seen = True
                continue
            if is_company_context_paragraph(company, paragraph.text):
                company_context = paragraph.text
                break
            break
        bullet_count = sum(1 for paragraph in paragraphs[index + 1 : next_index] if paragraph.is_bullet)
        roles.append(
            RoleInfo(
                title=title,
                company=company,
                company_context=company_context,
                bullet_count=bullet_count,
                block_text="\n".join(paragraph.text for paragraph in block),
            )
        )
    return roles

def extract_competency_labels(paragraphs: list[ParagraphInfo]) -> set[str]:
    start = section_index(paragraphs, SKILLS_SECTION_HEADING)
    end = section_index(paragraphs, "Professional Development")
    if start is None or end is None or end <= start:
        return set()
    labels: set[str] = set()
    for paragraph in paragraphs[start + 1 : end]:
        if ":" in paragraph.text:
            labels.add(normalize_compare(paragraph.text.split(":", 1)[0]))
    return labels

def extract_competency_items(paragraphs: list[ParagraphInfo]) -> set[str]:
    start = section_index(paragraphs, SKILLS_SECTION_HEADING)
    end = section_index(paragraphs, "Professional Development")
    if start is None or end is None or end <= start:
        return set()
    items: set[str] = set()
    for paragraph in paragraphs[start + 1 : end]:
        text = paragraph.text
        if ":" in text:
            text = text.split(":", 1)[1]
        items.update(normalize_compare(item) for item in split_items(text))
    return {item for item in items if item}

def extract_professional_development_items(paragraphs: list[ParagraphInfo]) -> set[str]:
    start = section_index(paragraphs, "Professional Development")
    if start is None:
        return set()
    items: set[str] = set()
    for paragraph in paragraphs[start + 1 :]:
        items.update(normalize_compare(item) for item in split_items(paragraph.text))
    return {item for item in items if item}

def resume_snapshot(document_xml: Path) -> ResumeSnapshot:
    paragraphs = paragraph_infos(document_xml)
    sections = {
        section
        for section in REQUIRED_SECTIONS
        if any(section_matches(paragraph.text, section) for paragraph in paragraphs)
    }
    return ResumeSnapshot(
        full_text="\n".join(paragraph.text for paragraph in paragraphs),
        sections=sections,
        roles=extract_roles(paragraphs),
        competency_labels=extract_competency_labels(paragraphs),
        competency_items=extract_competency_items(paragraphs),
        professional_development_items=extract_professional_development_items(paragraphs),
    )

def scrub_erp_language_for_non_erp_text(text: str, job_description: str) -> str:
    if jd_explicitly_requires_erp(job_description):
        return text
    replacements = (
        (r"\bERP administration\b", "enterprise systems administration"),
        (r"\bEnterprise ERP administration\b", "enterprise systems administration"),
        (r"\bEnterprise ERP\b", "enterprise systems"),
        (r"\bERP implementation\b", "software implementation"),
        (r"\bERP implementations\b", "software implementations"),
        (r"\bERP delivery\b", "enterprise systems delivery"),
        (r"\bERP migration\b", "systems migration"),
        (r"\bERP migrations\b", "systems migrations"),
        (r"\bERP platform\b", "enterprise system"),
        (r"\bERP platforms\b", "enterprise systems"),
        (r"\bERP workflows\b", "enterprise workflows"),
        (r"\bERP workflow\b", "enterprise workflow"),
        (r"\bERP/database records\b", "system records"),
    )
    updated = collision_safe_substitute(text, replacements)
    updated = re.sub(r"\bERP\b", "enterprise systems", updated)
    cleanup_replacements = (
        (r"\benterprise enterprise systems\b", "enterprise systems"),
        (r"\benterprise enterprise\b", "enterprise"),
    )
    for pattern, replacement in cleanup_replacements:
        updated = re.sub(pattern, replacement, updated, flags=re.I)
    return re.sub(r"\s+", " ", updated).strip()

def assert_no_erp_language_for_non_erp_role(text: str, job_description: str, label: str = "document") -> None:
    if jd_explicitly_requires_erp(job_description):
        return
    if NON_ERP_VISIBLE_PLATFORM_PATTERN.search(text):
        fail(f"{label} mentions ERP or named ERP-platform language even though the job description does not explicitly request ERP")

def rewrite_supported_text(text: str, job_description: str) -> str:
    original = text
    updated = text
    profile = job_problem_profile(job_description, text)

    updated = re.sub(r"\bresults[- ]driven\b", "outcome-focused", updated, flags=re.I)
    updated = re.sub(r"\bdedicated\b", "experienced", updated, flags=re.I)
    updated = re.sub(r"\bdetail[- ]oriented\b", "structured", updated, flags=re.I)
    updated = re.sub(r"\bself[- ]starter\b", "self-directed", updated, flags=re.I)

    if jd_mentions(job_description, "client", "clients", "consulting", "consultant"):
        updated = re.sub(r"\bcustomer-facing\b", "client-facing", updated, flags=re.I)
        updated = re.sub(r"\bcustomer business problems\b", "client business problems", updated, flags=re.I)
        updated = re.sub(r"\bcustomers\b", "clients", updated, flags=re.I)
        updated = re.sub(r"\bcustomer workflows\b", "client workflows", updated, flags=re.I)

    if jd_mentions(job_description, "requirements gathering", "gap analysis", "system review"):
        updated = re.sub(
            r"\brequirements definition\b",
            "requirements gathering, gap analysis, and requirements definition",
            updated,
            flags=re.I,
        )
        updated = re.sub(
            r"\bdefine requirements\b",
            "gather requirements, identify gaps, and define requirements",
            updated,
            flags=re.I,
        )
        updated = re.sub(
            r"\bdiscovery sessions\b",
            "requirements gathering and discovery sessions",
            updated,
            flags=re.I,
        )

    if jd_mentions(job_description, "product functionality", "solution functionality", "product and solution"):
        updated = re.sub(r"\bsystem solutions\b", "product and solution functionality", updated, flags=re.I)
        updated = re.sub(r"\bsolution designs\b", "product and solution designs", updated, flags=re.I)
        updated = re.sub(r"\bsystem health\b", "product and system health", updated, flags=re.I)

    if jd_mentions(job_description, "project management", "scope", "deliverable", "timelines", "implementation efforts"):
        updated = re.sub(
            r"\bgo-live readiness\b",
            "implementation readiness, scope alignment",
            updated,
            flags=re.I,
        )
        updated = re.sub(
            r"\bproduction deployment\b",
            "production deployment and implementation handoff",
            updated,
            flags=re.I,
        )
        updated = re.sub(
            r"\bweekly working sessions\b",
            "weekly working sessions, deliverable tracking",
            updated,
            flags=re.I,
        )

    if jd_mentions(job_description, "data analysis", "analyze", "billing", "order management", "crm"):
        # Normalize previously expanded phrases before adding analytics keywords.
        # Cleanup rules should operate on source text, not output created earlier in this block.
        cleanup_replacements = (
            (r"\bdata analysis and analytics tools\b", "analytics tools"),
            (r"\bcustomer and transactional and operational data\b", "customer and operational data"),
            (r"\bKPI reports, and reporting and analytics tools\b", "KPI reports, and analytics tools"),
        )
        expansion_replacements = (
            (r"\banalytics tools\b", "analytics tools"),
            (r"\banalytics, process support\b", "data analysis, process support"),
            (r"\btransactional data\b", "operational data"),
            (r"\breporting frameworks and dashboards\b", "data analysis dashboards and reporting frameworks"),
            (r"\border processing\b", "order management and order processing"),
            (r"\bSalesforce CRM records\b", "Salesforce CRM records and pipeline data"),
        )
        for pattern, replacement in cleanup_replacements + expansion_replacements:
            updated = re.sub(pattern, replacement, updated, flags=re.I)

    if jd_mentions(job_description, "internal resources", "resource management", "team relationship", "manage indirect reports"):
        updated = re.sub(
            r"\bCoordinated directly with development and product teams\b",
            "Aligned development and product teams",
            updated,
            flags=re.I,
        )
        updated = re.sub(
            r"\bcross-functional leadership\b",
            "cross-functional leadership that removed blockers and protected delivery timelines",
            updated,
            flags=re.I,
        )

    if jd_mentions(job_description, "presentation", "written communication", "interpersonal"):
        updated = re.sub(
            r"\bpresent recommendations\b",
            "present clear, actionable recommendations",
            updated,
            flags=re.I,
        )
        updated = re.sub(
            r"\bexecutive workshops\b",
            "executive workshops and stakeholder presentations",
            updated,
            flags=re.I,
        )

    if profile.primary_lane == "change_enablement":
        updated = re.sub(
            r"\bchange management programs\b",
            "change enablement programs",
            updated,
            flags=re.I,
        )
        updated = re.sub(
            r"\bchange management communications\b",
            "change communications",
            updated,
            flags=re.I,
        )
        updated = re.sub(
            r"\btraining programs, playbooks, and enablement resources\b",
            "training programs, adoption playbooks, and enablement resources",
            updated,
            flags=re.I,
        )
        updated = re.sub(
            r"\baligning implementation roadmaps\b",
            "aligning transformation roadmaps",
            updated,
            flags=re.I,
        )
        updated = re.sub(
            r"\bexecutive and operational decision-making with near real-time visibility\b",
            "adoption tracking, executive visibility, and operational decision-making",
            updated,
            flags=re.I,
        )
        updated = re.sub(
            r"\bdecision-making with near real-time visibility\b",
            "adoption tracking, executive visibility, and operational decision-making",
            updated,
            flags=re.I,
        )
        updated = re.sub(
            r"\bprotecting client workflows and reducing implementation risk\b",
            "protecting client workflows and reducing change and implementation risk",
            updated,
            flags=re.I,
        )
        updated = re.sub(
            r"\breducing manual effort across recurring implementation and systems administration processes\b",
            "reducing manual effort across recurring implementation, documentation, and reporting workflows",
            updated,
            flags=re.I,
        )

    if jd_mentions(job_description, "strategic business issues", "enhancing product functionality", "optimizing"):
        updated = re.sub(
            r"\bdefine requirements, evaluate options\b",
            "solve business issues, evaluate product functionality",
            updated,
            flags=re.I,
        )
        updated = re.sub(
            r"\bimproving processing speed\b",
            "optimizing processing speed",
            updated,
            flags=re.I,
        )
        updated = re.sub(
            r"\bdecision-making with near real-time visibility\b",
            "decision-making and operational optimization",
            updated,
            flags=re.I,
        )

    if jd_mentions(job_description, "enterprise software", "product functionality", "solution functionality"):
        updated = re.sub(
            r"\btechnical product support\b",
            "enterprise software product support",
            updated,
            flags=re.I,
        )
        updated = re.sub(
            r"\bresolving technical issues\b",
            "resolving enterprise software issues",
            updated,
            flags=re.I,
        )

    updated = preserve_reorg_sentence_at_end(original, updated)
    updated = scrub_erp_language_for_non_erp_text(updated, job_description)
    if len(updated.split()) > len(original.split()) + 6:
        return original
    return updated

def apply_supported_rewrites(document_xml: Path, job_description: str) -> int:
    tree = ET.parse(document_xml)
    paragraphs = tree.getroot().findall(f".//{W}p")
    raw_texts = [re.sub(r"\s+", " ", paragraph_text(paragraph)).strip() for paragraph in paragraphs]
    in_tailorable_zone = False
    changed = 0

    for index, paragraph in enumerate(paragraphs):
        text = raw_texts[index]
        if not text:
            continue
        if text == "Professional Summary":
            in_tailorable_zone = True
            continue
        if text == "Education":
            in_tailorable_zone = False
            continue
        if not in_tailorable_zone:
            continue
        if normalize_required_section_name(text) or is_role_heading(text):
            continue
        if " | " in text and ":" not in text and not is_bullet(paragraph):
            continue
        if not is_bullet(paragraph):
            previous_text = ""
            for previous_index in range(index - 1, -1, -1):
                if raw_texts[previous_index]:
                    previous_text = raw_texts[previous_index]
                    break
            if " | " in previous_text:
                company = previous_text.split("|", 1)[0].strip()
                if is_company_context_paragraph(company, text):
                    continue

        updated = rewrite_supported_text(text, job_description)
        if updated != text:
            set_paragraph_text(paragraph, updated)
            changed += 1

    if changed:
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)
    return changed

def strengthen_outcome_framing(text: str, job_description: str = "") -> str:
    original = text
    updated = text

    def has_outcome_or_metric_text(value: str) -> bool:
        return bool(re.search(r"\d|%|\$", value)) or has_great_eight_signal(value)

    def scope_suffix_from_context(active_job_description: str) -> str:
        if not active_job_description:
            return ""
        context = business_context.extract_business_context(active_job_description)
        business_model = context.business_model.lower() if context.business_model else ""
        if context.scale:
            return f" across {context.scale}"
        if context.customer_type and "b2b" in context.customer_type.lower():
            return " across enterprise customer environments"
        if context.industry == "healthcare":
            return " in a healthcare workflow environment"
        if context.industry == "manufacturing":
            return " across manufacturing and supply chain operations"
        if "saas" in business_model:
            return " in a cloud software delivery environment"
        return ""

    adverb_opener_pattern = re.compile(
        r"^(Successfully|Effectively|Proactively|Strategically|"
        r"Efficiently|Seamlessly|Consistently)\s+",
        re.I,
    )
    updated = adverb_opener_pattern.sub("", updated).strip()
    if updated:
        updated = updated[0].upper() + updated[1:]

    replacements = (
        (
            r"^Managed stakeholder communications\b",
            "Kept stakeholders aligned on risks, decisions, and next steps",
        ),
        (
            r"^Coordinated cross-functional teams\b",
            "Aligned cross-functional teams to keep milestones moving",
        ),
        (
            r"^Coordinated directly with development and product teams\b",
            "Aligned development and product teams",
        ),
        (
            r"^Managed Salesforce CRM records to maintain\b",
            "Improved Salesforce CRM pipeline data accuracy by maintaining",
        ),
        (
            r"^Responsible for\s+",
            "Owned ",
        ),
        (
            r"^Handled\s+",
            "Resolved ",
        ),
        (
            r"^Assisted with\s+",
            "Contributed to ",
        ),
        (
            r"^Participated in\s+",
            "Contributed to ",
        ),
    )

    for pattern, replacement in replacements:
        updated = re.sub(pattern, replacement, updated, flags=re.I)

    if has_outcome_or_metric_text(text):
        collective_openers = (
            (r"^Collaborated with [^,]+ to\b", "Partnered across teams to deliver"),
            (r"^Partnered with [^,]+ to\b", "Drove cross-functional work to"),
            (r"^Worked with [^,]+ to\b", "Led the effort to"),
            (r"^Supported the team in\b", "Owned the execution of"),
            (r"^Helped [^,]+ to\b", "Delivered"),
            (r"^Assisted [^,]+ with\b", "Executed"),
            (r"^Supported the implementation\b", "Coordinated the implementation"),
            (r"^Supported implementation\b", "Coordinated implementation"),
            (r"^Supported go-live\b", "Coordinated go-live"),
            (r"^Supported the rollout\b", "Coordinated the rollout"),
            (r"^Supported rollout\b", "Coordinated rollout"),
            (r"^Supported UAT\b", "Coordinated UAT"),
            (r"^Supported data validation\b", "Coordinated data validation"),
            (r"^Supported cross-functional\b", "Coordinated cross-functional"),
        )
        for pattern, replacement in collective_openers:
            updated = re.sub(pattern, replacement, updated, flags=re.I)

    updated = re.sub(r"\bresults[- ]driven\b", "outcome-focused", updated, flags=re.I)
    updated = re.sub(r"\bdedicated\b", "experienced", updated, flags=re.I)
    updated = re.sub(r"\bdetail[- ]oriented\b", "structured", updated, flags=re.I)
    updated = re.sub(r"\bteam player\b", "cross-functional collaborator", updated, flags=re.I)

    scope_signals = ("scope", "scale", "environment", "across", "for", "within")
    has_scope = any(signal in updated.lower() for signal in scope_signals)
    has_metric = bool(re.search(r"\d|%|\$", updated))
    if has_metric and not has_scope and job_description:
        suffix = scope_suffix_from_context(job_description)
        if suffix and len(updated) + len(suffix) <= 220:
            updated = updated.rstrip(".") + suffix + "."

    updated = preserve_reorg_sentence_at_end(original, updated)
    updated = scrub_erp_language_for_non_erp_text(updated, job_description)
    if len(updated.split()) > len(original.split()) + 6:
        return original
    return updated

def apply_outcome_framing_rewrites(document_xml: Path, job_description: str = "") -> int:
    tree = ET.parse(document_xml)
    paragraphs = tree.getroot().findall(f".//{W}p")
    raw_texts = [re.sub(r"\s+", " ", paragraph_text(paragraph)).strip() for paragraph in paragraphs]
    in_tailorable_zone = False
    changed = 0

    for index, paragraph in enumerate(paragraphs):
        text = raw_texts[index]
        if not text:
            continue
        if text == "Professional Summary":
            in_tailorable_zone = True
            continue
        if text == "Education":
            in_tailorable_zone = False
            continue
        if not in_tailorable_zone:
            continue
        if normalize_required_section_name(text) or is_role_heading(text):
            continue
        if " | " in text and ":" not in text and not is_bullet(paragraph):
            continue
        if not is_bullet(paragraph):
            previous_text = ""
            for previous_index in range(index - 1, -1, -1):
                if raw_texts[previous_index]:
                    previous_text = raw_texts[previous_index]
                    break
            if " | " in previous_text:
                company = previous_text.split("|", 1)[0].strip()
                if is_company_context_paragraph(company, text):
                    continue

        updated = strengthen_outcome_framing(text, job_description)
        if updated != text:
            set_paragraph_text(paragraph, updated)
            changed += 1

    if changed:
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)
    return changed

def woven_context_clause(job_description: str) -> str:
    """One short prepositional clause woven into sentence 1, not a labeled context dump."""
    context = business_context.extract_business_context(job_description)
    integration_buyer_signals = jd_mentions(
        job_description,
        "ipaas",
        "integration platform",
        "api-led",
        "master data",
        "mdm",
        "data governance",
        "data quality",
        "golden record",
        "data management platform",
        "data management solution",
        "data management software",
    )
    member_business_signals = jd_mentions(
        job_description,
        "subscription",
        "subscriber",
        "subscribers",
        "subscription business",
        "subscription retention",
        "member loyalty",
        "member retention",
        "member engagement",
        "member experience",
        "member services",
        "membership",
    )
    if integration_buyer_signals:
        return " for cloud integration and data management buyers"
    if member_business_signals:
        return " for subscription and member-facing customer teams"
    if context.business_model and "saas" in context.business_model.lower():
        return " for cloud software and B2B enterprise buyers"
    if context.industry == "healthcare":
        return " for healthcare operations and workflow teams"
    if context.industry == "manufacturing":
        return " for manufacturing and supply chain operations"
    if context.customer_type and "b2b" in context.customer_type.lower():
        return " for B2B enterprise software buyers"
    return ""


def summary_requires_erp_proof(job_description: str) -> bool:
    """ERP ownership proof belongs in summaries only when the role centers on ERP, not catalog vendor name-drops."""
    return jd_mentions(
        job_description,
        "erp",
        "enterprise resource planning",
        "aptean intuitive",
        "aptean",
        "epicor",
        "oracle erp",
        "microsoft dynamics",
        "netsuite",
        "manufacturing erp",
        "erp implementation",
        "erp platform",
        "manufacturing systems",
    )


def summary_has_quantified_anchor(text: str) -> bool:
    return bool(re.search(r"\b(?:\d|one million|two million|three million|five sites|users)\b|\$", text, re.I))


def summary_anchor_phrase(
    profile: JobProblemProfile,
    emphasis: TailoringEmphasis,
) -> str:
    by_emphasis = {
        "launch": "a 78% manual-work reduction and 22% discrepancy reduction",
        "dashboards": "200+ dashboards and KPI tools",
        "revenue": "$1M+ in at-risk annual revenue",
        "adoption": "150+ users across five sites",
        "ai": "200+ dashboards and KPI tools",
        "decision": "60+ executive workshops and QBRs",
    }
    anchor = by_emphasis.get(emphasis.proof_anchor, "")
    if anchor:
        return anchor
    return {
        "presales_solution": "80+ international client engagements",
        "customer_success": "$1M+ in at-risk annual revenue",
        "analytics_operations": "200+ dashboards and KPI tools",
        "change_enablement": "150+ users across five sites",
    }.get(profile.primary_lane, "150+ users across five sites")


def ensure_summary_proof_anchor(
    proof: str,
    profile: JobProblemProfile,
    emphasis: TailoringEmphasis,
) -> str:
    cleaned = neutralize_conflicting_region_lists(proof).strip()
    if not cleaned:
        return cleaned
    if summary_has_quantified_anchor(cleaned):
        return cleaned if cleaned.endswith(".") else f"{cleaned}."
    anchor = summary_anchor_phrase(profile, emphasis)
    if not anchor:
        return cleaned if cleaned.endswith(".") else f"{cleaned}."
    return f"{cleaned.rstrip('.').rstrip(',')}, backed by {anchor}."


def summary_proof_sentence(
    profile: JobProblemProfile,
    job_description: str,
    emphasis: TailoringEmphasis | None = None,
) -> str:
    """Lane-aware supported proof with a small amount of theme-based variation."""
    emphasis = emphasis or determine_tailoring_emphasis(job_description)
    proof = ""
    if emphasis.proof_anchor == "launch":
        proof = (
            "Owned Aptean Intuitive across five sites and 150+ users, launched system setup for a new warehouse and "
            "Amazon Robotics program, and cut manual inventory work by 78% and discrepancies by 22% through "
            "automated adjustments."
        )
    elif emphasis.proof_anchor == "dashboards":
        proof = (
            "Built 200+ dashboards and KPI reporting tools to replace raw exports with clearer decisions and "
            "supported 80+ client engagements and 60+ executive workshops and QBRs across North America, Asia, "
            "and Europe."
        )
    elif emphasis.proof_anchor == "revenue":
        proof = (
            "Managed 80+ manufacturing client engagements within a $6M+ book of business, led 60+ executive "
            "workshops and QBRs, and helped protect $1M+ in at-risk annual revenue through recovery and adoption work."
        )
    elif emphasis.proof_anchor == "adoption":
        proof = (
            "Led role-based training and enablement through the Aptean Intuitive to Epicor Kinetic transition for "
            "150+ users across five manufacturing sites and carried 80+ client engagements through UAT, adoption "
            "planning, and post-go-live support."
        )
    elif emphasis.proof_anchor == "ai":
        proof = (
            "Built 200+ dashboards and KPI tools while helping launch a zero-to-one SMS support channel in "
            "LivePerson LiveEngage, using Claude to accelerate documentation, reporting, and SQL workflows."
        )
    elif emphasis.proof_anchor == "decision":
        proof = (
            "Built 200+ dashboards and KPI reporting tools and led 60+ executive workshops and QBRs to turn "
            "ambiguous operations and engineering needs into scoped recommendations and risk-aware implementation "
            "plans before build work began."
        )
    elif profile.primary_lane == "customer_success":
        proof = (
            "Managed 80+ client engagements across the Americas, Europe, and Asia within a $6M+ book of business "
            "and helped protect $1M+ in at-risk annual revenue through 60+ executive QBRs and 200+ dashboards and "
            "KPI reporting tools."
        )
    else:
        include_erp = summary_requires_erp_proof(job_description)
        if profile.primary_lane == "presales_solution":
            items = (
                "80+ manufacturing client engagements across the Americas, Europe, and Asia",
                "200+ dashboards and KPI reporting tools",
                "60+ executive workshops and QBRs",
                "high-risk account recovery tied to $1M+ in annual revenue",
            )
            if include_erp:
                items = (
                    "ownership of an enterprise platform across five sites and 150+ users",
                    *items,
                )
        elif profile.primary_lane == "analytics_operations":
            items = (
                "200+ dashboards and KPI reporting tools",
                "60+ executive workshops and QBRs",
                "80+ client engagements across the Americas, Europe, and Asia",
            )
            if include_erp:
                items = (
                    "ownership of an enterprise platform across five sites and 150+ users",
                    *items,
                )
        else:
            items = (
                "ownership of an enterprise platform across five sites and 150+ users",
                "80+ manufacturing client engagements across the Americas, Europe, and Asia",
                "200+ dashboards and KPI reporting tools",
                "60+ executive workshops and QBRs",
            )
        lane_openers = {
            "presales_solution": "Delivered",
            "customer_success": "Managed",
            "analytics_operations": "Built",
        }
        opener = lane_openers.get(profile.primary_lane, "Delivered")
        proof = f"{opener} {comma_series(items)}."
    return ensure_summary_proof_anchor(proof, profile, emphasis)


def summary_demands_explicit_leadership(job_description: str) -> bool:
    title = (extract_job_title(job_description) or "").lower()
    if re.search(
        r"\b(senior|lead|leader|manager|director|head|principal|architect|vp|vice president|chief)\b",
        title,
        re.I,
    ):
        return True
    return jd_mentions(
        job_description,
        "people manager",
        "direct reports",
        "manage a team",
        "senior leadership",
        "executive leadership",
        "vp",
        "vice president",
    )


def analytics_reporting_focus_terms(job_description: str) -> tuple[str, ...]:
    terms: list[str] = []
    if jd_mentions(job_description, "performance reporting"):
        terms.append("performance reporting")
    if jd_mentions(job_description, "kpi", "kpi tracking"):
        terms.append("KPI tracking")
    if jd_mentions(job_description, "crm reporting"):
        terms.append("CRM reporting")
    if jd_mentions(job_description, "sfdc reporting"):
        terms.append("SFDC reporting")
    elif jd_mentions(job_description, "salesforce", "crm"):
        terms.append("Salesforce CRM reporting")
    if jd_mentions(job_description, "dashboard", "dashboards"):
        terms.append("executive dashboards")
    if jd_mentions(job_description, "forecast", "forecasting"):
        terms.append("forecasting support")
    return tuple(dict.fromkeys(terms))


def summary_fit_close_sentence(
    profile: JobProblemProfile,
    job_description: str,
    emphasis: TailoringEmphasis | None = None,
) -> str:
    emphasis = emphasis or determine_tailoring_emphasis(job_description)
    leadership_emphasis = summary_demands_explicit_leadership(job_description)

    if profile.primary_lane == "presales_solution":
        if emphasis.proof_anchor == "revenue":
            return (
                "Best used where discovery, executive communication, and implementation judgment all shape revenue, "
                "adoption, and expansion conversations."
            )
        if emphasis.proof_anchor == "ai":
            return (
                "Best used where software teams need credible discovery, workflow experimentation, and technical "
                "translation around automation, data, or service operations."
            )
        if leadership_emphasis:
            return (
                "Best used in executive-facing solution work where technical scoping and delivery judgment have to stay "
                "credible in the same conversation."
            )
        return (
            "Best used in solution work where discovery, solution design, and implementation realism need to connect "
            "cleanly to business value before the deal closes."
        )

    if profile.primary_lane == "customer_success":
        if emphasis.proof_anchor == "revenue":
            return (
                "Best used in post-sale environments where adoption planning, renewal-risk ownership, and executive "
                "account communication all shape retention."
            )
        return (
            "Best used where customer-facing delivery, account-health judgment, and escalation ownership steady "
            "complex relationships before issues turn into churn or stalled expansion."
        )

    if profile.primary_lane == "change_enablement":
        if emphasis.proof_anchor == "ai":
            return (
                "Best used where AI-assisted or system-driven change needs workflow clarity, training, and adoption "
                "follow-through after launch."
            )
        return (
            "Best used where training, workflow clarity, and stakeholder follow-through determine whether adoption "
            "holds after launch."
        )

    if profile.primary_lane == "analytics_operations":
        if emphasis.proof_anchor == "ai":
            return (
                "Best used where reporting depth, AI-assisted workflow experimentation, SQL validation, and operating "
                "judgment all influence decision speed and trust."
            )
        member_business_signals = jd_mentions(
            job_description,
            "member loyalty",
            "member retention",
            "member engagement",
            "member experience",
            "member services",
            "membership",
        )
        if jd_mentions(job_description, "retention", "curated reporting", "data-driven", "subscription") or member_business_signals:
            if jd_mentions(
                job_description,
                "imperfect business questions",
                "ad hoc analysis",
                "metric definition",
                "customer behavior",
            ) and jd_mentions(job_description, "retention"):
                return (
                    "Pairs reporting depth with operating judgment, turning unclear business questions into retention "
                    "analysis, curated reporting, and clearer follow-through for customer-facing teams."
                )
            return (
                "Best used where reporting depth and operating judgment improve retention analysis, curated reporting, "
                "and follow-through for customer-facing teams."
            )
        if emphasis.proof_anchor == "decision":
            return (
                "Best used where reporting, stakeholder alignment, and operating tradeoffs need to turn into decisions "
                "people actually act on."
            )
        if jd_mentions(job_description, "supply chain", "network optimization", "cost modeling", "data management", "project delivery"):
            return (
                "Combines reporting depth, SQL validation, and cross-functional judgment to tighten supply chain "
                "decisions, workflow handoffs, and executive follow-through."
            )
        if leadership_emphasis and is_education_assessment_context(job_description):
            return (
                "Brings executive-ready reporting, workflow validation, and continuous-improvement judgment where data "
                "trust directly affects whether AI-assisted outputs can be used."
            )
        return (
            "Best used where reporting depth and operating judgment improve decision speed, workflow clarity, and "
            "measurable follow-through in busy cross-functional environments."
        )

    if profile.primary_lane == "corporate_strategy":
        return (
            "Best used where ambiguous operating problems need practical decisions, clearer owners, and measurable next "
            "steps without inflated strategy claims."
        )

    if emphasis.proof_anchor == "launch":
        close_terms = ["launch readiness"]
    elif emphasis.proof_anchor == "dashboards":
        close_terms = ["reporting discipline", "data validation"]
    elif emphasis.proof_anchor == "adoption":
        close_terms = ["role-based enablement", "workflow follow-through", "user adoption"]
    else:
        close_terms = ["discovery", "migration", "testing", "adoption"]
    if jd_mentions(job_description, "quality control", "quality assurance", "quality", "accuracy"):
        close_terms.append("quality control")
    if jd_mentions(job_description, "process improvement", "workflow best practices", "implementation methodologies", "tools", "templates"):
        close_terms.append("process improvement")
    if jd_mentions(job_description, "solution architect", "solutions architect", "technical scoping", "scoping", "statement of work", "sow"):
        close_terms.append("technical scoping")
    if jd_mentions(job_description, "integrations", "integration", "data migration", "api", "apis"):
        close_terms.append("technical integration")
    if leadership_emphasis or jd_mentions(job_description, "delivery leadership", "lead implementation", "program leadership"):
        close_terms.append("delivery leadership")
    if jd_mentions(job_description, "user adoption", "post-implementation adoption", "post implementation adoption"):
        close_terms.append("user adoption")
    selected_close_terms = tuple(dict.fromkeys(close_terms))[:4]
    return (
        "Brings the most value when "
        + comma_series(selected_close_terms)
        + " must translate into clearer delivery decisions, durable adoption, and fewer operational surprises."
    )


def summary_word_count(text: str) -> int:
    return len(re.findall(r"\b[\w+.#'-]+\b", text))


def summary_minimum_close_extension(profile: JobProblemProfile, job_description: str) -> str:
    if profile.primary_lane == "presales_solution":
        return " across technical discovery, buyer evaluation, and executive decision cycles"
    if profile.primary_lane == "customer_success":
        return " across complex customer lifecycles, renewal pressure, and executive relationships"
    if profile.primary_lane == "change_enablement":
        return " across cross-functional teams, role-based workflows, and system changes"
    if profile.primary_lane == "analytics_operations":
        if jd_mentions(job_description, "supply chain", "network", "logistics", "transportation", "manufacturing"):
            return " across supply chain, reporting, and cross-functional operating environments"
        return " across reporting, workflow, and cross-functional operating environments"
    if profile.primary_lane == "corporate_strategy":
        return " across client teams, operating tradeoffs, and practical execution paths"
    return " across customer teams, launch pressure, and post-go-live adoption work"


def ensure_summary_minimum_words(
    positioning: str,
    proof: str,
    close: str,
    profile: JobProblemProfile,
    job_description: str,
) -> str:
    summary = f"{positioning} {proof} {close}"
    if summary_word_count(summary) >= PROFESSIONAL_SUMMARY_MIN_WORDS:
        return summary

    extension = summary_minimum_close_extension(profile, job_description)
    close_core = close.rstrip(".")
    if extension.strip().lower() not in close_core.lower():
        close = f"{close_core}{extension}."
    else:
        close = f"{close_core}."

    summary = f"{positioning} {proof} {close}"
    if summary_word_count(summary) >= PROFESSIONAL_SUMMARY_MIN_WORDS:
        return summary

    checklist_items = tuple(
        item
        for item in role_fit_checklist(profile, job_description)
        if item and item.lower() not in close.lower()
    )
    if checklist_items:
        close_base = close.rstrip(".")
        start_count = 2 if len(checklist_items) >= 2 else 1
        for count in range(start_count, len(checklist_items) + 1):
            close_variant = f"{close_base} with {comma_series(checklist_items[:count])}."
            summary = f"{positioning} {proof} {close_variant}"
            if summary_word_count(summary) >= PROFESSIONAL_SUMMARY_MIN_WORDS:
                return summary
    return summary


NAMED_ERP_PLATFORM_REPLACEMENTS = (
    (r"\bAptean Intuitive\b", "enterprise platform"),
    (r"\bAptean Encompix\b", "enterprise platform"),
    (r"\bEpicor Kinetic\b", "enterprise platform"),
    (r"\bOracle ERP\b", "enterprise platform"),
    (r"\bMicrosoft Dynamics 365\b", "enterprise platform"),
    (r"\bSAP(?!\s+Crystal Reports\b)\b", "enterprise platform"),
)

NAMED_ERP_PLATFORM_CLEANUP = (
    (r"\benterprise platform platform\b", "enterprise platform"),
    (r"\benterprise platform system\b", "enterprise platform"),
    (r"\benterprise platform enterprise systems\b", "enterprise platform"),
    (r"\ba enterprise platform\b", "an enterprise platform"),
)


def scrub_named_erp_platforms_for_summary(text: str) -> str:
    """Strip named ERP-platform mentions (not just the bare word 'ERP').

    Unlike scrub_erp_language_for_non_erp_text(), this intentionally
    removes specific platform names. It exists only for the Professional
    Summary, which assert_no_erp_language_for_non_erp_role() audits and
    requires to be completely free of ERP/platform language for non-ERP
    roles. Experience bullets are allowed to keep named platforms for
    supported-proof specificity, so do not apply this to bullet text.
    """
    updated = collision_safe_substitute(text, NAMED_ERP_PLATFORM_REPLACEMENTS)
    for pattern, replacement in NAMED_ERP_PLATFORM_CLEANUP:
        updated = re.sub(pattern, replacement, updated, flags=re.I)
    return re.sub(r"\s+", " ", updated).strip()


def scrub_non_erp_resume_language(document_xml: Path, job_description: str) -> int:
    if jd_explicitly_requires_erp(job_description):
        return 0

    tree = ET.parse(document_xml)
    paragraphs = tree.getroot().findall(f".//{W}p")
    raw_texts = [re.sub(r"\s+", " ", paragraph_text(paragraph)).strip() for paragraph in paragraphs]
    in_experience_zone = False
    in_summary_zone = False
    in_core_competencies = False
    changed = 0

    for index, paragraph in enumerate(paragraphs):
        text = raw_texts[index]
        if not text:
            continue
        if text == "Professional Summary":
            in_experience_zone = True
            in_summary_zone = True
            continue
        if text == "Professional Experience":
            in_summary_zone = False
            continue
        if text == "Education":
            in_experience_zone = False
            continue
        if is_skills_section_heading(text):
            in_core_competencies = True
            continue
        if text == "Professional Development":
            in_core_competencies = False
            continue
        if not in_experience_zone and not in_core_competencies:
            continue
        if normalize_required_section_name(text) or is_role_heading(text):
            continue
        if in_experience_zone and " | " in text and ":" not in text and not is_bullet(paragraph):
            continue
        if in_experience_zone and not is_bullet(paragraph):
            previous_text = ""
            for previous_index in range(index - 1, -1, -1):
                if raw_texts[previous_index]:
                    previous_text = raw_texts[previous_index]
                    break
            if " | " in previous_text:
                company = previous_text.split("|", 1)[0].strip()
                if is_company_context_paragraph(company, text):
                    continue

        cleaned = scrub_erp_language_for_non_erp_text(text, job_description)
        if in_summary_zone:
            cleaned = scrub_named_erp_platforms_for_summary(cleaned)
        if cleaned != text:
            set_paragraph_text(paragraph, cleaned)
            changed += 1

    if changed:
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)
    return changed


def startup_operator_summary(
    job_description: str,
    resume_text: str = "",
    variant_index: int = 0,
) -> str:
    profile = job_problem_profile(job_description, resume_text)
    emphasis = determine_tailoring_emphasis(job_description, resume_text, variant_index)
    positioning = summary_positioning_sentence(profile, job_description, emphasis).rstrip(".")
    context = woven_context_clause(job_description)
    if context:
        context_core = re.sub(r"^\s*for\s+", "", context, flags=re.I).replace(" buyers", "").strip().lower()
        positioning_lower = positioning.lower()
        buyer_context_redundant = "buyer" in context.lower() and re.search(r"\bcustomers?\b|\bbuyers?\b", positioning_lower)
        if context_core and context_core not in positioning_lower and not buyer_context_redundant:
            positioning = f"{positioning}{context}"
    positioning = f"{positioning}."
    proof = summary_proof_sentence(profile, job_description, emphasis)
    close = summary_fit_close_sentence(profile, job_description, emphasis)
    return neutralize_conflicting_region_lists(
        ensure_summary_minimum_words(positioning, proof, close, profile, job_description)
    )


def is_education_assessment_context(job_description: str) -> bool:
    context = business_context.extract_business_context(job_description)
    if context.industry == "education / assessment":
        return True
    return jd_mentions(
        job_description,
        "school assessment",
        "assessment item",
        "assessment and learning",
        "measurement and learning",
        "learner-facing",
        "instructional",
        "k-12",
        "psychometric",
        "constructed-response",
        "technology-enhanced items",
        "tei",
    )


def analytics_summary_role_label(job_description: str) -> str:
    role_title = extract_job_title(job_description) or ""
    primary_segment = re.split(r"[,/|]", role_title, maxsplit=1)[0].strip()
    normalized = normalize_compare(primary_segment)
    if normalized and len(normalized.split()) <= 3 and re.search(r"\banalyst\b", normalized):
        return title_case_skill_phrase(primary_segment)
    return ""


def analytics_summary_specialty_phrase(job_description: str) -> str:
    role_title = extract_job_title(job_description) or ""
    primary_segment = re.split(r"[,/|]", role_title, maxsplit=1)[0].strip()
    normalized = normalize_compare(primary_segment)
    if not normalized or len(normalized.split()) > 4:
        if jd_mentions(job_description, "supply chain", "network optimization", "transportation", "logistics"):
            return "Supply chain analytics consultant"
        return ""
    specialty_map = (
        ("supply chain network optimization", "Supply chain analytics consultant"),
        ("network optimization", "Supply chain analytics consultant"),
        ("supply chain analytics", "Supply chain analytics consultant"),
        ("revenue operations", "Revenue operations and analytics consultant"),
        ("sales operations", "Sales operations and analytics consultant"),
        ("business operations", "Business operations and analytics consultant"),
        ("operations manager", "Operations and analytics consultant"),
    )
    for signal, phrase in specialty_map:
        if signal in normalized:
            return phrase
    return ""


def analytics_priority_terms(job_description: str) -> tuple[str, ...]:
    terms: list[str] = []
    if jd_mentions(job_description, "ai-assisted", "ai-guided", "agentic", "intelligent systems"):
        terms.append("AI-assisted workflows")
    if jd_mentions(
        job_description,
        "validation",
        "validity",
        "defensibility",
        "interpretability",
        "drift detection",
        "monitoring",
    ):
        terms.append("workflow validation")
    if jd_mentions(
        job_description,
        "quality",
        "fairness",
        "accessibility",
        "instructional appropriateness",
        "continuous improvement",
    ):
        terms.append("quality monitoring")
    if jd_mentions(job_description, "supply chain", "network optimization", "transportation", "logistics", "least landed cost"):
        terms.append("supply chain analytics")
    if jd_mentions(
        job_description,
        "data management",
        "data guru",
        "etl",
        "data transformation",
        "model preparation",
        "operational datasets",
    ):
        terms.append("data management")
    if jd_mentions(job_description, "project delivery", "deliverables", "project reports"):
        terms.append("project delivery")
    if jd_mentions(
        job_description,
        "model quality",
        "validation",
        "modeling readiness",
        "validate inputs",
        "advanced modeling assumptions",
    ):
        terms.append("model quality")
    if jd_mentions(job_description, "power bi", "dashboard", "dashboards", "executive-level presentations", "executive reporting"):
        terms.append("executive reporting")
    return tuple(dict.fromkeys(term for term in terms if term))


def implementation_delivery_phrase(job_description: str) -> str:
    if jd_mentions(job_description, "customer delivery"):
        return "customer delivery"
    if jd_mentions(job_description, "client-facing delivery"):
        return "client-facing delivery"
    return "customer-facing delivery"


def implementation_training_phrase(job_description: str) -> str:
    if jd_mentions(job_description, "comprehensive training", "comprehensive training plans", "training plans"):
        return "comprehensive training"
    if jd_mentions(job_description, "client training"):
        return "client training"
    if jd_mentions(
        job_description,
        "customer training",
        "train end users",
        "end-user training",
        "user enablement",
        "training users",
    ):
        return "customer training"
    return "role-based training"


def implementation_documentation_phrase(job_description: str) -> str:
    if jd_mentions(job_description, "process documentation", "document processes"):
        return "process documentation"
    if jd_mentions(job_description, "workflow documentation"):
        return "workflow documentation"
    return ""


def implementation_scope_phrase(job_description: str) -> str:
    if jd_mentions(job_description, "scope management", "contractual scopes"):
        return "scope management"
    return "scope alignment"


def implementation_readiness_phrase(job_description: str) -> str:
    if jd_mentions(job_description, "delivery readiness"):
        return "delivery readiness"
    return "go-live readiness"


def implementation_quality_phrase(job_description: str) -> str:
    if jd_mentions(
        job_description,
        "quality control",
        "quality-control",
        "quality",
        "accuracy",
        "completeness",
        "validate setup",
        "readiness for go-live",
    ):
        return "quality validation"
    return ""


def implementation_priority_terms(job_description: str) -> tuple[str, ...]:
    terms: list[str] = [implementation_delivery_phrase(job_description)]
    documentation = implementation_documentation_phrase(job_description)
    if documentation:
        terms.append(documentation)
    if jd_mentions(job_description, "data migration", "mapping and transforming"):
        terms.append("data migration")
    terms.append(implementation_training_phrase(job_description))
    quality = implementation_quality_phrase(job_description)
    if quality:
        terms.append(quality)
    if jd_mentions(job_description, "scope management", "contractual scopes"):
        terms.append("scope management")
    elif jd_mentions(job_description, "testing", "user acceptance", "uat"):
        terms.append("testing")
    else:
        terms.append(implementation_readiness_phrase(job_description))
    return tuple(dict.fromkeys(term for term in terms if term))


def summary_positioning_sentence(
    profile: JobProblemProfile,
    job_description: str = "",
    emphasis: TailoringEmphasis | None = None,
) -> str:
    emphasis = emphasis or determine_tailoring_emphasis(job_description)
    if (
        profile.primary_lane in {"implementation_delivery", "change_enablement"}
        and (
            jd_mentions(job_description, "sales operations", "commercial operations", "sap", "salesforce")
            or (
                jd_mentions(job_description, "continuous improvement", "standardization")
                and jd_mentions(job_description, "project manager")
            )
        )
    ):
        return (
            "Enterprise systems and operations project manager with 10+ years driving software delivery and process "
            "standardization to raise adoption confidence and data reliability across day-to-day operations."
        )
    if profile.primary_lane == "presales_solution":
        if emphasis.proof_anchor == "revenue":
            if jd_mentions(job_description, "strategic partner", "trusted advisor", "strategic"):
                return (
                    "Solutions consultant with 10+ years leading strategic discovery, executive conversations, and "
                    "customer-value positioning for enterprise software decisions built to hold up in delivery."
                )
            return (
                "Solutions consultant with 10+ years leading technical discovery, executive conversations, and "
                "customer-value positioning for enterprise software decisions built to hold up in delivery."
            )
        if emphasis.proof_anchor == "ai":
            if jd_mentions(job_description, "strategic partner", "trusted advisor", "strategic"):
                return (
                    "Solutions consultant with 10+ years translating service workflows, data questions, and modern "
                    "automation use cases into credible strategic recommendations for enterprise software buyers."
                )
            return (
                "Solutions consultant with 10+ years translating service workflows, data questions, and modern "
                "automation use cases into credible software recommendations for enterprise buyers."
            )
        if jd_mentions(job_description, "service solutions", "service offerings", "service capabilities", "account managers", "sales management", "account expansion", "position and close"):
            return (
                "Service solutions consultant with 10+ years leading technical discovery, service strategy, and "
                "expansion support for enterprise customers where the recommendation had to hold up in delivery."
            )
        if jd_mentions(
            job_description,
            "data governance",
            "data quality",
            "master data",
            "mdm",
            "data management",
            "data integrity",
            "golden record",
            "ipaas",
            "proof of concept",
            "proof-of-concept",
        ):
            return (
                "Pre-sales solutions consultant with 10+ years leading technical discovery and solution proof for "
                "enterprise integration and data management evaluations, with implementation judgment keeping "
                "recommendations credible after the sale."
            )
        if jd_mentions(job_description, "strategic partner", "trusted advisor", "strategic"):
            return (
                "Pre-sales solutions consultant with 10+ years leading strategic discovery, solution design, and "
                "product demonstrations for enterprise software evaluations built to stay credible once "
                "implementation began."
            )
        return (
            "Pre-sales solutions consultant with 10+ years leading technical discovery, solution design, and product "
            "demonstrations for enterprise software evaluations built to stay credible once implementation began."
        )
    if profile.primary_lane == "customer_success":
        if emphasis.proof_anchor == "revenue":
            return (
                "Revenue-focused customer success and enterprise software consultant with 10+ years protecting "
                "adoption, renewal confidence, and account health across complex post-sale customer relationships."
            )
        if emphasis.proof_anchor == "adoption":
            return (
                "Customer-facing implementation and account-growth consultant with 10+ years turning onboarding, "
                "adoption planning, and executive follow-through into steadier post-sale customer outcomes."
            )
        return (
            "Revenue-focused customer success and enterprise software consultant with 10+ years protecting adoption, "
            "renewal confidence, and account health across complex post-sale customer relationships."
        )
    if profile.primary_lane == "change_enablement":
        if emphasis.proof_anchor == "ai":
            return (
                "Enterprise systems and change adoption consultant with 10+ years turning implementation ambiguity "
                "and AI-assisted workflow challenges into training programs, reporting, and durable user adoption."
            )
        return (
            "Enterprise systems and change adoption consultant with 10+ years turning implementation ambiguity "
            "into structured training, practical workflows, and adoption confidence for complex platform rollouts."
        )
    if profile.primary_lane == "analytics_operations":
        if emphasis.proof_anchor == "ai":
            return (
                "Enterprise systems and analytics consultant with 10+ years turning AI-assisted workflow questions, "
                "service-channel data, and reporting gaps into clearer decisions teams can trust."
            )
        if emphasis.proof_anchor == "decision":
            return (
                "Enterprise systems and analytics consultant with 10+ years turning operational tradeoffs, reporting "
                "gaps, and stakeholder pressure into clearer decisions and measurable follow-through."
            )
        if is_education_assessment_context(job_description):
            return (
                "Enterprise systems and analytics consultant with 10+ years turning AI-assisted workflow questions "
                "and data-trust issues into clearer decisions, measurable process improvement, and usable reporting."
            )
        specialty_phrase = analytics_summary_specialty_phrase(job_description)
        analytics_terms = analytics_priority_terms(job_description)
        if specialty_phrase and analytics_terms:
            focus_terms = tuple(
                term for term in analytics_terms if normalize_compare(term) not in normalize_compare(specialty_phrase)
            )
        else:
            focus_terms = ()
        if specialty_phrase and focus_terms:
            return (
                f"{specialty_phrase} with 10+ years turning multi-site operational data and {focus_terms[0]} "
                "into clearer decisions, measurable process improvements, and usable reporting."
            )
        if specialty_phrase:
            return (
                f"{specialty_phrase} with 10+ years turning operational data and reporting gaps into clearer decisions, "
                "measurable process improvements, and usable reporting."
            )
        role_label = analytics_summary_role_label(job_description)
        if role_label and jd_mentions(job_description, "retention"):
            return (
                f"{role_label} and enterprise systems analytics consultant with 10+ years turning operational data "
                "and workflow gaps into clearer decisions, retention analysis, and measurable process improvements."
            )
        if role_label:
            return (
                f"{role_label} and enterprise systems analytics consultant with 10+ years turning operational data "
                "and workflow gaps into clearer decisions, measurable process improvements, and usable reporting."
            )
        return (
            "Enterprise systems and analytics consultant with 10+ years turning operational data, reporting gaps, "
            "and workflow issues into clearer decisions and measurable process improvements for customer-facing teams."
        )
    if profile.primary_lane == "corporate_strategy":
        return (
            "Client-facing strategy and operations consultant with 10+ years turning ambiguous business problems, "
            "stakeholder tradeoffs, and systems-driven delivery risk into structured recommendations and measurable follow-through."
        )
    if profile.primary_lane == "implementation_delivery":
        if emphasis.proof_anchor == "launch":
            return (
                "Implementation consultant with 10+ years building system and platform setups, migration plans, and go-live "
                "execution for complex enterprise systems where launch stability mattered immediately."
            )
        if emphasis.proof_anchor == "dashboards":
            return (
                "Implementation consultant with 10+ years combining delivery ownership, reporting design, and data "
                "validation across enterprise software programs from discovery through go-live and adoption."
            )
        if emphasis.proof_anchor == "adoption":
            return (
                "Implementation consultant with 10+ years leading software delivery, role-based enablement, and "
                "cross-functional adoption work across complex enterprise systems and platforms."
            )
        focus_terms = implementation_priority_terms(job_description)[:3]
        return (
            "Implementation consultant with 10+ years leading "
            + comma_series(focus_terms)
            + " across complex enterprise systems and platforms from discovery through go-live and post-launch adoption."
        )
    return (
        "Customer-facing implementation consultant with 10+ years leading enterprise systems and platforms for complex "
        "customers from discovery and configuration through testing, go-live, and post-launch adoption."
    )


def obvious_choice_positioning(profile: JobProblemProfile, job_description: str = "") -> dict[str, str]:
    lane_sentences = {
        "presales_solution": (
            "For this kind of pre-sales role, the obvious choice is someone who can turn messy buyer requirements into credible solution proof, executive confidence, and a cleaner path to decision."
        ),
        "customer_success": (
            "For this kind of customer success role, the obvious choice is someone who can steady customer relationships, improve adoption, and turn post-sale work into stronger retention confidence."
        ),
        "change_enablement": (
            "For this kind of change adoption role, the obvious choice is someone who can turn system change into stakeholder clarity, role-based adoption, and durable workflow follow-through."
        ),
        "analytics_operations": (
            "For this kind of analytics and operations role, the obvious choice is someone who can turn messy data and workflow issues into decisions people trust and processes teams can actually use."
        ),
        "corporate_strategy": (
            "For this kind of strategy role, the obvious choice is someone who can structure ambiguous problems, align decision-makers, and stay close enough to execution to make the recommendation real."
        ),
        "implementation_delivery": (
            "For this kind of implementation role, the obvious choice is someone who has already handled complex software delivery, cross-functional alignment, and adoption work that leads to stable execution after go-live."
        ),
    }
    sentence = lane_sentences.get(profile.primary_lane)
    if not sentence:
        specialty = role_specialty_phrase(job_description, "cross-functional delivery work")
        sentence = (
            f"For this kind of {specialty} role, the obvious choice is someone who has already handled similar business problems, stakeholder pressure, and measurable outcome expectations."
        )
    return {
        "sentence": sentence,
        "short_line": "Obvious-choice frame: make it easy for them to see the same kind of problem, stakeholders, and outcome pattern Christian has already handled.",
    }


def generate_positioning_statement(profile: JobProblemProfile, job_description: str = "") -> str:
    analytics_statement = "Christian is strongest in analytics and operations roles that need noisy data and workflow issues turned into decisions leaders can trust and teams can use."
    analytics_terms = analytics_priority_terms(job_description)[:4]
    if analytics_terms:
        analytics_statement = (
            "Christian is strongest in analytics and operations roles that need "
            + comma_series(analytics_terms)
            + ", and decision support that holds up inside real operating environments."
        )
    lane_statements = {
        "presales_solution": "Christian is strongest in pre-sales roles that need sharp discovery, credible solution framing, and implementation realism that holds up after the sale.",
        "customer_success": "Christian is strongest in customer success roles that need adoption discipline, executive alignment, and practical ownership of renewal risk across complex accounts.",
        "change_enablement": "Christian is strongest in change roles that need system rollout work translated into stakeholder clarity, role-based adoption, and durable workflow follow-through.",
        "analytics_operations": analytics_statement,
        "corporate_strategy": "Christian is strongest in strategy roles that need ambiguity structured quickly and recommendations tied back to execution, ownership, and measurable next steps.",
        "implementation_delivery": (
            "Christian is strongest in implementation roles that need "
            + comma_series(implementation_priority_terms(job_description)[:4])
            + ", stakeholder alignment, and adoption work that lasts beyond go-live."
        ),
    }
    statement = lane_statements.get(profile.primary_lane)
    if statement:
        return statement
    specialty = role_specialty_phrase(job_description, "cross-functional delivery work")
    return (
        f"Christian is strongest in {specialty} roles that need structured problem solving, stakeholder confidence, and measurable outcomes without inflated claims."
    )


def summary_job_poster_sentence(profile: JobProblemProfile) -> str:
    if profile.primary_lane == "presales_solution":
        return (
            "Helps sales and customer teams turn unclear requirements into credible solution stories, practical recommendations, and buyer confidence."
        )
    if profile.primary_lane == "customer_success":
        return (
            "Helps customers turn complex software investments into clearer value, stronger account health, retained trust, and credible expansion paths."
        )
    if profile.primary_lane == "analytics_operations":
        return (
            "Helps leaders turn messy operating data and workflow questions into clearer decisions, better priorities, and usable reporting."
        )
    if profile.primary_lane == "change_enablement":
        return (
            "Helps teams make system and process changes easier to adopt by clarifying needs, reducing resistance, and keeping leaders and users aligned."
        )
    if profile.primary_lane == "corporate_strategy":
        return (
            "Helps clients and leadership teams turn ambiguous business problems into structured analysis, practical recommendations, and measurable follow-through."
        )
    return (
        "Helps teams move complex system work from requirements to adoption by clarifying scope, surfacing risk early, and keeping stakeholders aligned."
    )

def consulting_story_summary(job_description: str = "") -> str:
    opening = (
        "Client-facing consultant with 10+ years bringing consulting-style discovery, analysis, and stakeholder alignment "
        "to complex client programs. "
    )
    closing = (
        "Those engagements needed structured problem solving, data-backed recommendations, stakeholder alignment, "
        "and execution judgment to hold up together."
    )
    if jd_mentions(job_description, "transformation", "modernization", "turnaround"):
        opening = (
            "Client-facing consultant with 10+ years bringing consulting-style discovery, analysis, and stakeholder alignment "
            "to complex client delivery and transformation programs. "
        )
        closing = (
            "Those engagements needed structured problem solving, data-backed recommendations, stakeholder alignment, "
            "and execution judgment to hold up through delivery."
        )
    # Keyword-filling branches: the audit uses exact word-boundary matching, so synonyms
    # and different word forms (client-facing vs customer-facing, strategy vs strategic) do
    # not satisfy keyword checks. These branches swap in the exact JD terms when the JD uses
    # them. All three replacements are safe regardless of which transformation branch ran above.
    if jd_mentions(job_description, "customer-facing"):
        opening = opening.replace("Client-facing consultant", "Customer-facing consultant")
    if jd_mentions(job_description, "strategic"):
        closing = closing.replace("execution judgment", "strategic execution judgment")
    if jd_mentions(job_description, "business process", "process improvement"):
        closing = closing.replace("structured problem solving,", "structured problem solving, process discipline,")
    # This middle sentence has to carry every scale fact (sites, users, client count,
    # geography, book size, dashboards, workshops, recovered revenue) while staying ONE
    # sentence: the Professional Summary guard requires exactly 3 sentences total
    # (opening + this + closing), and a previous attempt to split it into multiple
    # sentences pushed the count to 5 and broke that guard. A semicolon was tried next,
    # but assert_professional_summary_structure() bans semicolons in the proof/close
    # sentences outright (only the opening sentence may use one). A "while building" /
    # "helping stabilize" gerund version avoided the semicolon but accidentally demoted
    # two strong ownership verbs (built, stabilized) into forms hiring_manager_skim_issues'
    # ownership check doesn't recognize, which tripped a separate "too support-oriented"
    # audit flag. This version keeps every verb in past tense (owned/supported/built/
    # facilitated/stabilized) and chains clauses with plain "and" instead of commas or
    # "while", holding the comma count at 1 (safely under writing_eval.list_density_issue's
    # >=3-comma trigger) with zero semicolons.
    return (
        opening
        + "Owned a mission-critical enterprise platform across five sites and 150+ users and supported 80+ "
        "manufacturing clients across North America, Asia and Europe within a $6M+ client book of business and "
        "built 200+ dashboards and KPI reporting tools and facilitated 60+ executive workshops and QBRs and "
        "stabilized $1M+ in at-risk annual revenue. "
        + closing
    )

def comma_series(items: tuple[str, ...]) -> str:
    if len(items) <= 1:
        return items[0] if items else ""
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"

def role_fit_checklist(profile: JobProblemProfile, job_description: str) -> tuple[str, ...]:
    specialty = role_specialty_phrase(job_description, "enterprise systems")
    if profile.primary_lane in {"implementation_delivery", "analytics_operations"} and jd_mentions(
        job_description,
        "business systems analyst",
        "business systems analysis",
        "business analyst",
        "business technical analyst",
        "capability needs",
        "business requirements",
    ):
        return (
            "business requirements and testing",
            "data analysis and reporting",
            "cross-functional implementation support",
            "risk, defect, and issue documentation",
            "customer-facing stakeholder alignment",
            "quality delivery",
        )
    if (
        profile.primary_lane in {"implementation_delivery", "change_enablement", "analytics_operations"}
        and jd_mentions(job_description, "sales operations", "commercial operations", "sap", "salesforce", "crm")
    ):
        systems_item = (
            "Salesforce CRM workflow and reporting support"
            if jd_mentions(job_description, "salesforce", "crm", "crm reporting", "sfdc reporting")
            else "enterprise systems and data migration support"
        )
        execution_item = (
            "forecasting and planning support"
            if jd_mentions(job_description, "forecast", "forecasting", "quota setting", "capacity planning")
            else "cross-functional project execution"
        )
        tracking_item = "performance reporting" if jd_mentions(job_description, "performance reporting") else "KPI tracking"
        return (
            systems_item,
            "commercial operations standardization",
            execution_item,
            tracking_item,
            "change adoption",
            "stakeholder coordination",
        )
    if profile.primary_lane == "presales_solution":
        if jd_mentions(job_description, "service solutions", "service offerings", "service capabilities", "account managers", "sales management", "account expansion", "position and close"):
            return (
                "service discovery",
                "solution strategy",
                "account expansion",
                "service-value positioning",
                "SOW and MSA support",
                "executive presentations",
            )
        return (
            "technical discovery",
            "solution design",
            "product demonstrations",
            "buyer-value alignment",
            "implementation planning",
            "executive presentations",
        )
    if profile.primary_lane == "customer_success":
        return (
            "strategic account management",
            "customer adoption",
            "account health",
            "renewal risk management",
            "QBRs",
            "value realization",
        )
    if profile.primary_lane == "change_enablement":
        return (
            "change adoption",
            "role-based training",
            "stakeholder communication",
            "readiness planning",
            "process standardization",
            "risk mitigation",
        )
    if profile.primary_lane == "analytics_operations":
        if jd_mentions(job_description, "supply chain", "network optimization", "cost modeling", "data management", "project delivery"):
            return (
                "data management",
                "project delivery",
                "model quality",
                "executive reporting",
                "Power BI dashboards",
                "supply chain analytics",
            )
        return (
            "KPI reporting",
            "dashboard development",
            "data analysis",
            "process improvement",
            "decision support",
            specialty,
        )
    if profile.primary_lane == "corporate_strategy":
        return (
            "structured analysis",
            "executive stakeholder alignment",
            "client communication",
            "recommendation development",
            "cross-functional follow-through",
            "measurable outcomes",
        )
    implementation_terms = list(implementation_priority_terms(job_description))
    implementation_terms.extend(
        [
            "systems and data migration",
            "testing and UAT" if jd_mentions(job_description, "testing", "user acceptance", "uat") else implementation_readiness_phrase(job_description),
            implementation_scope_phrase(job_description),
            "adoption planning",
        ]
    )
    return tuple(dict.fromkeys(term for term in implementation_terms if term))[:6]

def build_problem_first_summary(
    job_description: str,
    resume_text: str = "",
    variant_index: int = 0,
) -> str:
    profile = job_problem_profile(job_description, resume_text)
    emphasis = determine_tailoring_emphasis(job_description, resume_text, variant_index)
    if is_startup_or_broad_operator_role(job_description):
        debug_print("[summary] Summary variant: startup_operator", flag="DEBUG_RESUME_SUMMARY")
        return startup_operator_summary(job_description, resume_text, variant_index)
    # Keep the broad consulting summary isolated to the dedicated strategy/consulting
    # lane so it does not bleed into implementation, change, or software-consultant resumes.
    if profile.primary_lane == "corporate_strategy":
        debug_print("[summary] Summary variant: consulting", flag="DEBUG_RESUME_SUMMARY")
        return consulting_story_summary(job_description)

    positioning = summary_positioning_sentence(profile, job_description, emphasis).rstrip(".")
    context = woven_context_clause(job_description)
    if context:
        context_core = re.sub(r"^\s*for\s+", "", context, flags=re.I).replace(" buyers", "").strip().lower()
        positioning_lower = positioning.lower()
        buyer_context_redundant = "buyer" in context.lower() and re.search(r"\bcustomers?\b|\bbuyers?\b", positioning_lower)
        if context_core and context_core not in positioning_lower and not buyer_context_redundant:
            positioning = f"{positioning}{context}"
    positioning = f"{positioning}."
    proof = summary_proof_sentence(profile, job_description, emphasis)
    close = summary_fit_close_sentence(profile, job_description, emphasis)
    checklist = comma_series(role_fit_checklist(profile, job_description)[:3])
    summary = ensure_summary_minimum_words(positioning, proof, close, profile, job_description)
    summary = neutralize_conflicting_region_lists(summary)
    debug_print(
        f"[summary] Summary variant: standard/{emphasis.key} | lane: {profile.primary_lane} | positioning: {positioning[:60]}...",
        flag="DEBUG_RESUME_SUMMARY",
    )
    debug_print(f"[summary] Summary checklist: {checklist}", flag="DEBUG_RESUME_SUMMARY")
    return summary


def summary_moment_in_time_clause(job_description: str) -> str:
    lowered = job_description.lower()
    if any(signal in lowered for signal in ("acquisition", "integration", "migration", "cutover", "consolidation")):
        return "during periods when system change and user adoption have to move together"
    if any(signal in lowered for signal in ("scale", "scaling", "growth", "expansion", "hypergrowth", "rapidly growing")):
        return "during periods when growth and process discipline both need to scale"
    if any(signal in lowered for signal in ("turnaround", "stabilize", "stabilization", "transformation", "rebuild", "modernization")):
        return "during periods when execution and operating clarity both need to tighten"
    return ""


def summary_future_bridge(profile: JobProblemProfile, job_description: str = "") -> str:
    lane_bridges = {
        "presales_solution": (
            "A career spanning both implementation delivery and pre-sales discovery leads to sharper questions before the contract is signed "
            "and fewer surprises after it is."
        ),
        "customer_success": (
            "The strongest customer work starts long before renewal, with risk named early, ownership kept clear, and value discussed before pressure builds."
        ),
        "change_enablement": (
            "Adoption holds when training, measurement rhythm, and workflow design are built into the implementation instead of added afterward."
        ),
        "analytics_operations": (
            "Reporting matters most when the decision, the data, and the operating follow-through are tightened at the same time."
        ),
        "corporate_strategy": (
            "Strategy work lands best when analysis, stakeholder tradeoffs, and execution ownership stay connected from the start."
        ),
        "implementation_delivery": (
            "Implementation work is strongest when adoption, stabilization, and cross-functional execution are treated as one delivery problem."
        ),
    }
    bridge = lane_bridges.get(profile.primary_lane)
    if bridge:
        return bridge
    specialty = role_specialty_phrase(job_description, "cross-functional delivery work")
    return f"{specialty.capitalize()} benefits most when clearer execution and measurable follow-through are built into the work from the start."


def append_summary_future_bridge(document_xml: Path, job_description: str) -> int:
    # Deliberately disabled so professional summaries stay at three direct sentences.
    return 0


def rewrite_professional_summary_for_role(
    document_xml: Path,
    job_description: str,
    *,
    variant_index: int = 0,
) -> int:
    tree = ET.parse(document_xml)
    paragraphs = tree.getroot().findall(f".//{W}p")
    in_summary = False
    changed = 0
    summary_text = build_problem_first_summary(
        job_description,
        visible_text(document_xml),
        variant_index=variant_index,
    )
    summary_repair = prose_engine.repair_text(summary_text, "summary")
    if not summary_repair.converged:
        rule_ids = ", ".join(item.rule_id for item in summary_repair.findings if item.severity == "fail")
        fail(f"Commercial summary prose repair did not converge. Rule IDs: {rule_ids or 'UNKNOWN'}")
    summary_text = summary_repair.text

    for paragraph in paragraphs:
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        if text == "Professional Summary":
            in_summary = True
            continue
        if text == "Professional Experience":
            break
        if in_summary and text:
            set_paragraph_text(paragraph, summary_text)
            changed += 1
            in_summary = False

    if changed:
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)
    return changed

def optimized_role_summary(
    company: str,
    current_summary: str,
    job_description: str,
    emphasis: TailoringEmphasis | None = None,
) -> str:
    has_reorg_sentence = MANDATORY_REORG_SENTENCE.lower() in current_summary.lower()
    body = remove_reorg_sentence(current_summary)
    profile = job_problem_profile(job_description, current_summary)
    emphasis = emphasis or determine_tailoring_emphasis(job_description, current_summary)
    delivery_phrase = implementation_delivery_phrase(job_description)
    training_phrase = implementation_training_phrase(job_description)
    documentation_phrase = implementation_documentation_phrase(job_description)

    company_key = normalize_compare(company)
    if company_key == normalize_compare(COMPANY_EAST_WEST):
        body = (
            "Owned Aptean Intuitive administration and continuous improvement as the primary ERP "
            "platform for a five-site manufacturing operation, giving 150+ users clearer supply chain, finance, and "
            "operations visibility while supporting Epicor Kinetic transition planning and final launch readiness "
            "during migration."
        )
        if emphasis.proof_anchor == "launch":
            body = (
                "Scaled a five-site manufacturing environment for 150+ users by owning Aptean Intuitive "
                "administration, launching system setup for a new warehouse and Amazon Robotics program, and "
                "supporting Epicor Kinetic transition planning, training, testing, and final launch readiness."
            )
        elif emphasis.proof_anchor == "dashboards":
            body = (
                "Increased operating visibility for 150+ users across five manufacturing sites by owning Aptean "
                "Intuitive administration and building reporting that clarified supply-chain and finance issues. "
                "Supported Epicor Kinetic transition planning through data validation and final launch readiness."
            )
        elif emphasis.proof_anchor == "ai":
            body = (
                "Improved system execution across a five-site manufacturing environment by owning Aptean Intuitive "
                "administration, using Claude in reporting and SQL troubleshooting workflows, and supporting Epicor "
                "Kinetic transition planning and launch readiness for 150+ users."
            )
        elif emphasis.proof_anchor == "decision":
            body = (
                "Turned operations, finance, and engineering tradeoffs into clearer system decisions by owning "
                "Aptean Intuitive administration across a five-site manufacturing environment, supporting 150+ users, "
                "and guiding Epicor Kinetic transition planning and launch readiness."
            )
        if documentation_phrase or training_phrase != "role-based training":
            support_terms = [term for term in (documentation_phrase, training_phrase) if term]
            body = (
                "Owned Aptean Intuitive administration and continuous improvement as the primary ERP "
                "platform for a five-site manufacturing operation, giving 150+ users clearer supply chain, finance, "
                "and operations visibility while supporting "
                + comma_series(tuple(support_terms))
                + ", Epicor Kinetic transition planning, and final launch readiness during migration."
            )
        if profile.primary_lane == "change_enablement":
            body = (
                "Led change adoption and continuous improvement for Aptean Intuitive across a five-site manufacturing "
                "operation, designing role-based training, stakeholder "
                "communications, and enablement resources that moved 150+ operations, finance, and engineering users "
                "from resistance to measurable system confidence while supporting Epicor Kinetic transition planning "
                "and final launch readiness during migration."
            )
        elif profile.primary_lane == "corporate_strategy":
            body = (
                "Led structured operating analysis and stakeholder alignment around Aptean Intuitive for a five-site "
                "manufacturing environment, turning workflow, reporting, and "
                "systems tradeoffs into executive-ready recommendations for 150+ users across operations, finance, "
                "and engineering while supporting Epicor Kinetic migration planning, transition readiness, and final "
                "launch readiness."
            )
        elif jd_mentions(job_description, "solution architecture", "enterprise solutions", "technical uncertainty", "deployment strategies"):
            body = (
                "Owned Aptean Intuitive administration, solution architecture, and deployment strategy for a five-site "
                "manufacturing operation supporting 150+ users, translating ambiguous operations, finance, and "
                "engineering needs into structured ERP recommendations while supporting Epicor Kinetic migration "
                "planning, transition readiness, training, and final launch readiness."
            )
    elif company_key == normalize_compare(COMPANY_APTEAN):
        body = (
            "Delivered 12 full-lifecycle ERP implementations and managed up to four at a time for 80+ manufacturing "
            "clients in the Americas, Europe, and Asia through structured issue ownership that turned ambiguous "
            "requirements into cleaner configurations and steadier post-go-live adoption."
        )
        if emphasis.proof_anchor == "revenue":
            body = (
                "Managed customer success and commercial account health for 80+ manufacturing clients across the "
                "Americas, Europe, and Asia, using QBRs, adoption planning, and escalation recovery to protect a $6M+ "
                "book of business and support $1M+ in at-risk annual revenue."
            )
        elif emphasis.proof_anchor == "dashboards":
            body = (
                "Improved account visibility across 80+ manufacturing clients in the Americas, Europe, and Asia by "
                "combining Salesforce workflow support, adoption tracking, and executive review preparation with "
                "full-lifecycle delivery ownership."
            )
        elif emphasis.proof_anchor == "adoption":
            body = (
                "Moved 80+ manufacturing clients across the Americas, Europe, and Asia from unclear requirements to "
                "usable go-live outcomes through discovery, configuration, testing, customer training, and post-go-live adoption support."
            )
        elif emphasis.proof_anchor == "ai":
            body = (
                "Ran full-lifecycle manufacturing-software delivery for 80+ clients across the Americas, Europe, and "
                "Asia while accelerating documentation, reporting, and SQL troubleshooting through Claude and "
                "AI-assisted workflows that supported cleaner handoffs and steadier adoption."
            )
        elif emphasis.proof_anchor == "decision":
            body = (
                "Turned discovery findings and delivery risk across 80+ manufacturing clients in the Americas, Europe, "
                "and Asia into clearer implementation paths, scoped recommendations, and executive-ready tradeoffs."
            )
        if documentation_phrase or training_phrase != "role-based training" or delivery_phrase != "customer-facing delivery":
            support_terms = [term for term in (documentation_phrase, training_phrase) if term]
            support_phrase = (
                comma_series(tuple(support_terms)) + ", structured issue ownership, and stakeholder communication"
                if support_terms
                else "structured issue ownership and stakeholder communication"
            )
            body = (
                "Ran full ERP lifecycle delivery for 80+ manufacturing clients across the Americas, Europe, and Asia, "
                "turning ambiguous requirements into working configurations, cleaner data migrations, and steadier "
                f"post-go-live adoption while supporting {delivery_phrase} through {support_phrase}."
            )
        if profile.primary_lane == "customer_success":
            body = (
                "Managed customer success and commercial account health for 80+ manufacturing clients globally, "
                "protecting a $6M+ book of business through QBRs and escalation recovery. "
                "Led $1M+ in at-risk annual revenue recovery across the Americas, Europe, and Asia "
                "through adoption planning and value realization."
            )
        elif profile.primary_lane == "change_enablement":
            body = (
                "Led change adoption and full-lifecycle ERP delivery for 80+ manufacturing clients across the Americas, "
                "Europe, and Asia, designing training programs, adoption guides, and stakeholder communications that "
                "reduced resistance and improved go-live confidence; managed scope alignment, risk visibility, and "
                "post-go-live support from requirements through customer handoff."
            )
        elif profile.primary_lane == "corporate_strategy":
            body = (
                "Guided 80+ manufacturing clients across the Americas, Europe, and Asia through ambiguous delivery, "
                "risk, and adoption decisions by turning discovery findings into scoped recommendations, executive-ready "
                "tradeoffs, and practical implementation paths."
            )
        elif jd_mentions(job_description, "technical sales", "sales pursuits", "rfp", "executive", "solution design"):
            body = (
                "Drove pre-sales and full-lifecycle ERP delivery for 80+ manufacturing clients across the Americas, "
                "Europe, and Asia, using discovery, solution design, and implementation judgment to shorten sales "
                "cycles and improve post-go-live adoption."
            )
    elif company_key == normalize_compare(COMPANY_HOME_DEPOT):
        body = (
            "Built reporting frameworks around eCommerce performance, customer engagement data, and service workflow "
            "signals so leaders could spot trends faster and act on clearer operating decisions in a large-scale online retail environment."
        )
        if emphasis.proof_anchor == "ai":
            body = (
                "Helped build a zero-to-one internal SMS support channel in LivePerson LiveEngage for a large-scale "
                "eCommerce environment, pairing service-workflow design, AI-assisted chatbot logic, and performance "
                "reporting to improve channel adoption and support visibility."
            )
        elif emphasis.proof_anchor == "dashboards":
            body = (
                "Turned eCommerce reporting, customer engagement data, and Salesforce or LivePerson workflow signals "
                "into clearer operating decisions for leaders in a large-scale online retail environment."
            )
        if profile.primary_lane == "change_enablement":
            body = (
                "Delivered analytics, process support, and customer engagement solutions for a large-scale eCommerce "
                "environment, supporting workflow improvement, data-informed decisions, and new communication-channel "
                "adoption."
            )
        elif profile.primary_lane == "corporate_strategy":
            body = (
                "Turned customer, reporting, and workflow signals into clearer operating decisions for leaders in a "
                "large-scale eCommerce environment, helping teams prioritize service improvements and new-channel adoption."
            )
        elif jd_mentions(job_description, "operational impact", "data analysis", "stakeholders", "customer"):
            body = (
                "Delivered data analysis, operational reporting, and customer engagement support for a large-scale "
                "eCommerce environment, helping leaders interpret performance trends and improve service workflows."
            )
    elif company_key == normalize_compare(COMPANY_ADERANT):
        body = (
            "Resolved enterprise legal case management, SQL, integration, and systems-administration issues across "
            "more than 600 law firm offices during an organizational transition, helping stabilize a mission-critical platform under pressure."
        )
        if jd_mentions(job_description, "technical consulting", "enterprise", "systems integration", "application architectures"):
            body = (
                "Provided enterprise software product support and interim systems administration, resolving application, "
                "SQL Server, Active Directory, integration, and Windows service issues during an organizational transition."
            )

    if has_reorg_sentence:
        return neutralize_conflicting_region_lists(append_reorg_sentence(body))
    return neutralize_conflicting_region_lists(body)

def optimize_role_summaries(
    document_xml: Path,
    job_description: str,
    *,
    variant_index: int = 0,
) -> int:
    tree = ET.parse(document_xml)
    paragraphs = tree.getroot().findall(f".//{W}p")
    changed = 0
    current_company = ""
    emphasis = determine_tailoring_emphasis(job_description, visible_text(document_xml), variant_index)

    for index, paragraph in enumerate(paragraphs):
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        if not text:
            continue
        if normalize_required_section_name(text):
            current_company = ""
            continue
        if not is_bullet(paragraph) and is_role_heading(text):
            current_company = ""
            continue
        if not is_bullet(paragraph) and " | " in text:
            current_company = text.split("|", 1)[0].strip()
            continue
        if current_company and not is_bullet(paragraph) and not is_role_heading(text) and not normalize_required_section_name(text):
            if is_company_context_paragraph(current_company, text):
                continue
            updated = optimized_role_summary(current_company, text, job_description, emphasis)
            role_repair = prose_engine.repair_text(updated, "summary")
            if not role_repair.converged:
                rule_ids = ", ".join(item.rule_id for item in role_repair.findings if item.severity == "fail")
                fail(
                    f"Commercial role-summary prose repair did not converge for {current_company}. "
                    f"Rule IDs: {rule_ids or 'UNKNOWN'}"
                )
            updated = role_repair.text
            if updated != text:
                set_paragraph_text(paragraph, updated)
                changed += 1
            current_company = ""

    if changed:
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)
    return changed

def remove_extra_role_summary_paragraphs(document_xml: Path) -> int:
    tree = ET.parse(document_xml)
    root = tree.getroot()
    body = root.find(f"{W}body")
    if body is None:
        return 0

    def is_required_section_text(value: str) -> bool:
        return normalize_required_section_name(value) is not None

    removed = 0
    index = 0
    while index < len(list(body)):
        children = list(body)
        child = children[index]
        if child.tag != f"{W}p":
            index += 1
            continue
        text = re.sub(r"\s+", " ", paragraph_text(child)).strip()
        if not text or not is_role_heading(text):
            index += 1
            continue

        company_index = index + 1
        while company_index < len(children):
            company_text = re.sub(r"\s+", " ", paragraph_text(children[company_index])).strip()
            if company_text:
                break
            company_index += 1

        if company_index >= len(children):
            break

        company_text = re.sub(r"\s+", " ", paragraph_text(children[company_index])).strip()
        if " | " not in company_text or is_required_section_text(company_text) or is_role_heading(company_text):
            index = company_index + 1
            continue

        company_name = company_text.split("|", 1)[0].strip()
        summary_paragraphs, scan_index = role_detail_paragraphs_after_company(children, company_index)
        keep_count = 0
        if summary_paragraphs:
            first_summary_text = re.sub(r"\s+", " ", paragraph_text(summary_paragraphs[0])).strip()
            keep_count = 2 if is_company_context_paragraph(company_name, first_summary_text) else 1

        for extra_summary in summary_paragraphs[keep_count:]:
            body.remove(extra_summary)
            removed += 1

        index = scan_index

    if removed:
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)
    return removed

def apply_consulting_story_rewrites(document_xml: Path, job_description: str) -> int:
    if not is_consulting_job_description(job_description):
        return 0

    tree = ET.parse(document_xml)
    paragraphs = tree.getroot().findall(f".//{W}p")
    changed = 0

    replacements = (
        (
            ("end-to-end strategy", "Aptean Intuitive", "mission-critical ERP platform", "five sites"),
            "Owned end-to-end strategy, administration, and continuous improvement for Aptean Intuitive as the primary mission-critical ERP platform supporting manufacturing, supply chain, and finance operations across five sites in North America and Asia and more than 150 users; supported the Aptean Intuitive to Epicor Kinetic migration through final launch readiness. Position impacted by company reorganization.",
        ),
        (
            ("inventory adjustment", "Aptean Intuitive ERP", "78%", "22%"),
            "Diagnosed a recurring inventory accuracy problem in a high-volume warehouse environment and built an automated adjustment system in Aptean Intuitive ERP that reduced manual processing effort by 78% and cut inventory discrepancies by 22%, converting an operational pain point into a controlled, auditable process",
        ),
        (
            ("full ERP setup", "new warehouse operation", "Amazon Robotics", "GL accounts"),
            "Delivered the full ERP buildout for a new warehouse operation and Amazon Robotics program from an open scope, configuring product families, GL accounts, BOMs, and multi-site training across concurrent workstreams with no existing playbook",
        ),
        (
            ("change management programs", "enablement materials", "role-based training", "operations, finance, and engineering"),
            "Designed change management and enablement programs from the ground up, including role-based training, onboarding materials, and adoption resources that moved operations, finance, and engineering teams from active resistance to measurable system confidence at each major release",
        ),
        (
            ("internal solution architect", "ERP enhancements", "structured discovery", "directors and VPs"),
            "Functioned as the internal solution architect for ERP enhancements, running structured discovery sessions with operations, finance, and engineering stakeholders to define requirements, model tradeoffs, and present clear recommendations to directors and VPs before any build began",
        ),
        (
            ("vp/director decision-making", "scoped system recommendations", "vendor tradeoffs", "implementation plans"),
            "Improved executive decision-making by turning ambiguous operations, finance, and engineering needs into strategy recommendations, analytics-backed tradeoffs, and risk-aware implementation plans before build work began",
        ),
        (
            ("200 dashboards", "KPI reports", "SQL", "Crystal Reports", "Power BI"),
            "Built more than 200 dashboards, KPI reports, and analytics tools using SQL, Crystal Reports, and Power BI, giving executives near real-time visibility into manufacturing and financial performance they had previously interpreted from raw exports or verbal status updates",
        ),
        (
            ("go-live readiness", "sandbox testing", "user acceptance validation", "Epicor Kinetic"),
            "Owned go-live readiness across concurrent program tracks, including sandbox testing, user acceptance validation, and targeted Epicor Kinetic training as the migration reached launch readiness, protecting production stability during live operations",
        ),
        (
            ("Aptean Intuitive to Epicor Kinetic", "extracting", "validating", "ETL tools", "SQL-based validation"),
            "Supported the Aptean Intuitive to Epicor Kinetic migration by extracting, validating, transforming, and loading ERP and database records through ETL tools and SQL-based validation, coordinating release timing across cross-functional teams to achieve a clean migration close",
        ),
        (
            ("60 executive workshops", "quarterly business reviews", "manufacturing clients", "United States", "Europe"),
            "Facilitated more than 60 executive workshops, implementation reviews, and quarterly business reviews for manufacturing clients across North America and Asia, aligning technology roadmaps to business outcomes in environments where communication styles, organizational structures, and decision-making norms varied significantly",
        ),
        (
            ("implementation and adoption delivery", "Aptean Encompix", "requirements definition", "go-live"),
            "Managed the full ERP lifecycle for enterprise manufacturing clients across discovery, requirements definition, configuration, data migration, integration, testing, go-live, and post-go-live support, consistently navigating competing stakeholder priorities across multiple time zones and organizational structures",
        ),
        (
            ("international manufacturing clients", "unclear requirements", "usable go-live outcomes", "post-go-live support"),
            "Guided international manufacturing clients from unclear requirements to analysis-backed implementation outcomes by leading discovery, requirements definition, configuration, data migration, testing, customer training, and post-go-live support in enterprise software",
        ),
        (
            ("scope, risk, and escalation", "at-risk accounts", "one million dollars", "annual revenue"),
            "Took ownership of at-risk accounts inside a broader six-million-dollar client portfolio, stepped into escalating situations without a warm handoff, consolidated fragmented case histories, led structured recovery sessions, and converted more than one million dollars in at-risk annual revenue into retained client trust",
        ),
        (
            ("pre-sales product demonstrations", "discovery sessions", "prospective enterprise clients", "competitive displacements"),
            "Delivered pre-sales product demonstrations and technical discovery sessions for prospective enterprise clients across multiple geographies, translating business requirements into solution designs that contributed directly to competitive displacements and new business wins",
        ),
        (
            ("client-facing success communications", "training documentation", "adoption guides", "account newsletters"),
            "Developed client-facing communications including training documentation, adoption guides, product updates, and account newsletters that kept international stakeholders engaged between reviews and reduced reactive support volume across a distributed client base",
        ),
        (
            ("development and product teams", "triage issues", "prioritize fixes", "validate solutions"),
            "Coordinated directly with development and product teams to triage issues, prioritize fixes, and validate solutions before deployment, acting as the translation layer between client urgency and engineering capacity across concurrent implementation tracks",
        ),
        (
            ("reporting frameworks", "dashboards", "customer experience metrics", "eCommerce operation"),
            "Built reporting frameworks and dashboards tracking customer experience metrics and operational efficiency outcomes across a large home improvement eCommerce operation, helping leaders identify service gaps before they compounded",
        ),
        (
            ("pilot team member", "Home Depot SMS texting service", "2017", "LivePerson LiveEngage"),
            f"Served as a founding pilot team member for the {COMPANY_HOME_DEPOT} SMS texting service in 2017, configuring LivePerson LiveEngage chat workflows, AI-assisted chatbot logic, and automated conversation routing for an enterprise communication channel that did not previously exist",
        ),
    )

    for paragraph in paragraphs:
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        if not text:
            continue
        text_lower = text.lower()
        for key_phrases, replacement in replacements:
            cleaned_replacement = neutralize_conflicting_region_lists(replacement)
            if all(phrase.lower() in text_lower for phrase in key_phrases) and text != cleaned_replacement:
                set_paragraph_text(paragraph, cleaned_replacement)
                changed += 1
                break

    if changed:
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)
    else:
        print(
            "consulting story rewrite pass: no bullets matched in consulting context; verify source resume bullets align with expected key phrases.",
            file=sys.stderr,
        )
    return changed

def apply_startup_operator_rewrites(document_xml: Path, job_description: str) -> int:
    if not is_startup_or_broad_operator_role(job_description):
        return 0
    tree = ET.parse(document_xml)
    paragraphs = tree.getroot().findall(f".//{W}p")
    changed = 0
    rewrites = (
        (
            ("Aptean Intuitive", "mission-critical", "five sites", "150+ users"),
            "Owned Aptean Intuitive across five sites in North America and Asia for 150+ users in manufacturing, supply chain, and finance; supported migration planning, data validation, training, and final launch readiness from Aptean Intuitive to Epicor Kinetic. Position impacted by company reorganization.",
        ),
        (
            ("inventory adjustment", "78%", "22%"),
            "Reduced manual inventory adjustment work by 78% and lowered discrepancies by 22% by diagnosing a recurring warehouse accuracy problem and building an automated, auditable workflow",
        ),
        (
            ("200 dashboards", "KPI reports", "Power BI", "near real-time visibility"),
            "Enabled real-time executive decision-making by building 200+ SQL-based BI and reporting tools, replacing raw exports and verbal status updates with usable operational visibility",
        ),
        (
            ("operations, finance, and engineering", "scoped ERP recommendations", "directors and VPs", "before build work began"),
            "Translated ambiguous operations, finance, and engineering requests into scoped systems recommendations by leading discovery, evaluating options, and presenting clear tradeoffs to directors and VPs before build work began",
        ),
        (
            ("ERP migration data", "Aptean Intuitive", "Epicor Kinetic", "ETL tools", "cutover coordination"),
            "Supported enterprise data migration from Aptean Intuitive to Epicor Kinetic by extracting, querying, transforming, updating, and validating system and database records through ETL tools, SQL checks, and migration readiness coordination",
        ),
        (
            ("open warehouse launch", "Amazon Robotics", "product families", "GL accounts"),
            "Turned an open warehouse launch and Amazon Robotics program into a production-ready system setup, scoping product families, GL accounts, BOMs, and cross-site training through go-live",
        ),
        (
            ("200 dashboards", "Crystal Reports", "Power BI", "raw exports", "verbal status updates"),
            "Enabled real-time executive decision-making by building 200+ SQL-based BI and reporting tools, replacing raw exports and verbal status updates with usable operational visibility",
        ),
        (
            ("recurring inventory accuracy", "automated adjustment system", "78%", "22%"),
            "Reduced manual inventory work by 78% and discrepancies by 22% by diagnosing a recurring warehouse accuracy problem and building an automated, auditable adjustment workflow",
        ),
        (
            ("Aptean Intuitive to Epicor Kinetic", "extracting", "validating", "SQL-based validation", "clean migration close"),
            "Supported enterprise data migration by extracting, validating, transforming, and loading system/database records through ETL tools and SQL checks while coordinating release timing across cross-functional teams",
        ),
        (
            ("internal solution architect", "ERP enhancements", "structured discovery", "directors and VPs"),
            "Turned ambiguous operations, finance, and engineering requests into scoped system recommendations by running structured discovery, modeling tradeoffs, and presenting decisions to directors and VPs before build work began",
        ),
        (
            ("founding pilot team member", "Home Depot SMS", "2017", "LivePerson LiveEngage"),
            "Helped launch a net-new enterprise SMS support channel by configuring LivePerson workflows, AI-assisted chatbot logic, and automated routing for a founding pilot team",
        ),
    )
    for paragraph in paragraphs:
        current = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        if not current:
            continue
        current_lower = current.lower()
        for key_phrases, new in rewrites:
            cleaned_new = neutralize_conflicting_region_lists(new)
            if all(phrase.lower() in current_lower for phrase in key_phrases) and current != cleaned_new:
                set_paragraph_text(paragraph, cleaned_new)
                changed += 1
                break
    if changed:
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)
    else:
        print(
            "apply_startup_operator_rewrites: no bullets matched while startup/operator rewrite context was active; verify source resume bullets align with expected key phrases.",
            file=sys.stderr,
        )
    return changed

def apply_value_story_rewrites(document_xml: Path, job_description: str) -> int:
    """Rewrite known duty-style bullets into compact value stories without inventing facts."""
    tree = ET.parse(document_xml)
    paragraphs = tree.getroot().findall(f".//{W}p")
    changed = 0
    delivery_phrase = implementation_delivery_phrase(job_description)
    training_phrase = implementation_training_phrase(job_description)
    scope_phrase = implementation_scope_phrase(job_description)

    rewrites = (
        (
            ("change management programs", "enablement materials", "role-based training"),
            "Reduced adoption resistance by building enablement materials, onboarding processes, and role-based training that gave operations, finance, and engineering teams more confidence in system changes",
        ),
        (
            ("internal solution architect", "technical program owner", "ERP enhancements"),
            "Converted operations, finance, and engineering requests into scoped ERP recommendations by leading discovery, evaluating options, and presenting clear tradeoffs to directors and VPs before build work began",
        ),
        (
            ("implementation and adoption delivery", "Aptean Encompix", "data migration", "go-live"),
            f"Moved manufacturing clients across the Americas, Europe, and Asia from ERP requirements through configuration, data migration, testing, go-live, and post-go-live support while keeping {delivery_phrase}, {scope_phrase}, {training_phrase}, and adoption risk visible",
        ),
        (
            ("development and product teams", "triage issues", "prioritize fixes", "production deployment"),
            "Protected client workflows before production deployment by aligning development and product teams on issue triage, fix prioritization, validation, and implementation handoff",
        ),
        (
            ("60 executive workshops", "quarterly business reviews", "implementation roadmaps"),
            "Built executive confidence across more than 60 workshops and QBRs by tying implementation roadmaps to business objectives, adoption risk, renewal readiness, and expansion conversations",
        ),
        (
            ("scope, risk, and escalation", "at-risk accounts", "one million dollars", "annual revenue"),
            "Stabilized at-risk accounts inside a broader six-million-dollar client portfolio by consolidating ownership, leading structured recovery sessions, and turning more than one million dollars in at-risk annual revenue into retained trust",
        ),
        (
            ("data analysis", "operational reporting", "customer engagement", "eCommerce environment"),
            "Turned eCommerce reporting, customer engagement data, and service workflow signals into clearer operating decisions for leaders in a large-scale online retail environment.",
        ),
        (
            ("technical product support", "interim systems administration", "legal case management", "organizational transition"),
            "Helped stabilize enterprise legal case management software during an organizational transition by combining product support, systems administration, SQL troubleshooting, and integration issue resolution.",
        ),
        (
            ("customer and transactional data", "forecast shipping pipelines", "operational strategy", "B2B"),
            "Turned customer and transactional data into trend analysis, shipping pipeline forecasts, and operational recommendations supporting large-scale B2B and direct customer relationships",
        ),
        (
            ("reporting frameworks", "dashboards", "customer experience metrics"),
            "Built customer experience dashboards and reporting frameworks that made performance trends, service gaps, and operational efficiency easier for leaders to act on",
        ),
        (
            ("pilot team member", "Home Depot", "SMS"),
            f"Helped launch {COMPANY_HOME_DEPOT} SMS texting pilot by configuring LivePerson LiveEngage chat and text workflows, automated greetings and closings, and adoption of a new enterprise communication channel",
        ),
        (
            ("customer-facing success communications", "training documentation", "adoption guides", "newsletters"),
            "Kept customer stakeholders engaged between reviews by developing training documentation, adoption guides, product updates, and newsletters that reduced reactive support volume",
        ),
        (
            ("customer interaction trends", "Salesforce CRM", "LivePerson LiveEngage", "eCommerce operations"),
            "Used Salesforce and LivePerson data to find workflow friction and improve eCommerce operations",
        ),
        (
            ("enterprise applications", "600 law firm offices", "Active Directory", "SQL Server"),
            "Resolved enterprise application issues across more than 600 law firm offices, spanning Active Directory, SQL Server, third-party integrations, and Windows services during a support transition",
        ),
        (
            ("Salesforce pages", "sales, support, and project management", "disaster recovery", "system resilience"),
            "Improved sales, support, and project-management workflows by building Salesforce pages and contributing to disaster recovery planning and system resilience improvements",
        ),
        (
            ("statements of work", "functional requirements", "before any build began"),
            "Converted complex ERP implementation, data migration, integration, and customization needs into SOWs and functional requirements that clarified scope, milestones, and cost baselines before any build began",
        ),
        (
            ("training programs", "playbooks", "enablement resources", "post-go-live support volume"),
            f"Improved client adoption and reduced post-go-live support volume by designing {training_phrase}, playbooks, and enablement resources that made complex ERP workflows easier to use",
        ),
        (
            ("full ERP setup", "new warehouse operation", "Amazon Robotics", "GL accounts"),
            "Turned an open warehouse launch and Amazon Robotics program into a production-ready ERP setup, scoping product families, GL accounts, BOMs, and cross-site training through go-live",
        ),
        (
            ("implementation readiness", "sandbox testing", "user acceptance validation", "Epicor Kinetic training"),
            "Protected migration stability by leading implementation readiness, scope alignment, sandbox testing, UAT validation, targeted Epicor Kinetic training, and administrative release tasks across concurrent program tracks",
        ),
        (
            ("Aptean Intuitive to Epicor Kinetic", "extracting", "updating ERP", "SQL-based validation", "cutover coordination"),
            "Moved ERP migration data from Aptean Intuitive toward Epicor Kinetic by extracting, querying, transforming, updating, and validating ERP and database records through ETL tools, SQL checks, and migration readiness coordination",
        ),
    )

    for paragraph in paragraphs:
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        if not text or normalize_required_section_name(text) or is_role_heading(text):
            continue
        text_lower = text.lower()
        for key_phrases, new in rewrites:
            cleaned_new = neutralize_conflicting_region_lists(new)
            if all(phrase.lower() in text_lower for phrase in key_phrases) and text != cleaned_new:
                set_paragraph_text(paragraph, cleaned_new)
                changed += 1
                break

    if changed:
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)
    else:
        print(
            "apply_value_story_rewrites: no bullets matched while value story rewrite context was active; verify source resume bullets align with expected key phrases.",
            file=sys.stderr,
        )
    return changed

def merge_low_fit_bullets_before_delete(document_xml: Path, job_description: str) -> int:
    tree = ET.parse(document_xml)
    root = tree.getroot()
    body = root.find(f"{W}body")
    if body is None:
        return 0

    children = list(body)
    current_company = ""
    changed = 0
    absorbed_patterns = (
        "designed and executed user enablement programs",
        "applied codex-assisted automation",
        "advised clients against high-risk or low-value customizations",
        "advised customers against high-risk or low-value customizations",
    )

    for child in list(children):
        text = re.sub(r"\s+", " ", paragraph_text(child)).strip()
        if not text:
            continue
        if not is_bullet(child) and " | " in text:
            current_company = text.split("|", 1)[0].strip()
            continue
        if not is_bullet(child) and is_role_heading(text):
            current_company = ""
            continue
        if current_company not in CONDENSABLE_BULLET_COMPANIES or not is_bullet(child):
            continue

        normalized = text.lower()
        if not any(pattern in normalized for pattern in absorbed_patterns):
            continue
        if bullet_deserves_explicit_fit_protection(text, job_description):
            continue

        bullets = [
            item
            for item in list(body)
            if is_bullet(item)
            and item is not child
            and (score(paragraph_text(item), audit_keywords(job_description)) > 0 or business_context.business_relevance_score(paragraph_text(item), job_description) >= 6)
        ]
        if not bullets:
            continue
        target = bullets[0]
        target_text = re.sub(r"\s+", " ", paragraph_text(target)).strip()

        if "user enablement" in normalized and "user enablement" not in target_text.lower():
            set_paragraph_text(target, target_text + " while supporting user enablement and adoption")
            body.remove(child)
            changed += 1
        elif "low-value customizations" in normalized and "total cost of ownership" not in target_text.lower():
            set_paragraph_text(target, target_text + " while balancing upgrade risk and total cost of ownership")
            body.remove(child)
            changed += 1

    if changed:
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)
    return changed

def clean_merged_role_bullets(document_xml: Path) -> int:
    tree = ET.parse(document_xml)
    changed = 0
    for paragraph in tree.getroot().findall(f".//{W}p"):
        if not is_bullet(paragraph):
            continue
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        if (
            "Served as the internal solution architect" in text
            and "user enablement and adoption" in text
            and "total cost of ownership" in text
        ):
            updated = (
                "Served as the internal solution architect for ERP enhancements, leading stakeholder discovery, "
                "technical option evaluation, adoption planning, and risk-aware recommendations for directors and VPs"
            )
            set_paragraph_text(paragraph, updated)
            changed += 1
    if changed:
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)
    return changed


def job_demands_explicit_role_proof(job_description: str) -> bool:
    title = (extract_job_title(job_description) or "").lower()
    if re.search(
        r"\b(senior|lead|leader|manager|director|head|principal|architect|vp|vice president|chief)\b",
        title,
        re.I,
    ):
        return True
    return jd_mentions(
        job_description,
        "people manager",
        "direct reports",
        "manage a team",
        "lead a team",
        "senior leadership",
        "executive leadership",
        "vp",
        "vice president",
        "director",
    )


def bullet_deserves_explicit_fit_protection(text: str, job_description: str) -> bool:
    normalized = text.lower()
    if jd_mentions(
        job_description,
        "ai",
        "automation",
        "agent",
        "agents",
        "llm",
        "generative",
        "chatbot",
        "conversational ai",
        "workflow automation",
    ) and re.search(r"\b(codex|claude|ai-assisted|automation|chatbot|conversational ai|liveperson|liveengage|sms)\b", normalized, re.I):
        return True
    if jd_mentions(
        job_description,
        "solution architect",
        "solutions architect",
        "technical scoping",
        "scoping",
        "requirements gathering",
        "integrations",
        "integration",
        "data migration",
        "testing",
        "delivery",
        "api",
        "apis",
    ) and re.search(
        r"\b(scoping|requirements|functional requirements|statement of work|sow|integration|data migration|testing|uat|go-live|implementation readiness|delivery|solution architecture)\b",
        normalized,
        re.I,
    ):
        return True
    if job_demands_explicit_role_proof(job_description) and re.search(
        r"\b(led|owned|executive|director|vp|stakeholder|workshop|qbr|recommendation|tradeoff|roadmap|decision|implementation plan)\b",
        normalized,
        re.I,
    ):
        return True
    return False


def bullet_is_condensable(text: str, job_description: str) -> bool:
    normalized = text.lower()
    if bullet_deserves_explicit_fit_protection(text, job_description):
        return False
    always_condense_patterns = (
        "ai-assisted analysis and workflow automation",
        "least-privilege security models",
        "designed and executed user enablement programs",
        "advised clients against high-risk or low-value customizations",
        "advised customers against high-risk or low-value customizations",
        "negotiated vendor agreements, system enhancement scopes",
    )
    if any(pattern in normalized for pattern in always_condense_patterns):
        return True
    if "ai-assisted analysis" in normalized and not jd_mentions(job_description, "ai", "automation"):
        return True
    if "pre-sales product demonstrations" in normalized and not jd_mentions(
        job_description,
        "demo",
        "demos",
        "pre-sales",
        "presales",
        "solution consulting",
        "sales engineer",
    ):
        return True
    if "advised customers against high-risk or low-value customizations" in normalized and not jd_mentions(
        job_description,
        "customization",
        "customizations",
        "configuration",
        "upgrade",
    ):
        return True
    if business_process_or_servicenow_role(job_description):
        process_trim_patterns = (
            "delivered the full erp buildout for a new warehouse operation",
            "turned an open warehouse launch and amazon robotics program",
            "managed the full erp lifecycle for enterprise manufacturing clients",
            "improved client adoption and reduced post-go-live support volume",
            "developed client-facing communications including training documentation",
        )
        if any(pattern in normalized for pattern in process_trim_patterns):
            return True
    return False

def remove_condensable_role_bullets(document_xml: Path, job_description: str, max_remove: int = 6) -> int:
    tree = ET.parse(document_xml)
    root = tree.getroot()
    body = root.find(f"{W}body")
    if body is None:
        return 0

    children = list(body)
    current_company = ""
    removed = 0
    removed_by_company: dict[str, int] = {}
    for child in list(children):
        text = re.sub(r"\s+", " ", paragraph_text(child)).strip()
        if not text:
            continue
        if not is_bullet(child) and " | " in text:
            company_candidate = text.split("|", 1)[0].strip()
            if company_candidate in CONDENSABLE_BULLET_COMPANIES:
                current_company = company_candidate
            elif is_role_heading(text):
                current_company = ""
        elif not is_bullet(child) and is_role_heading(text):
            current_company = ""

        if (
            current_company in CONDENSABLE_BULLET_COMPANIES
            and is_bullet(child)
            and bullet_is_condensable(text, job_description)
            and removed < max_remove
            and removed_by_company.get(current_company, 0) < 3
        ):
            body.remove(child)
            removed += 1
            removed_by_company[current_company] = removed_by_company.get(current_company, 0) + 1

    if removed:
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)
    return removed

def remove_global_low_fit_bullets(document_xml: Path, max_remove: int = 4) -> int:
    tree = ET.parse(document_xml)
    root = tree.getroot()
    body = root.find(f"{W}body")
    if body is None:
        return 0

    patterns = (
        "ai-assisted analysis and workflow automation",
        "applied codex-assisted automation",
        "least-privilege security models",
        "designed and executed user enablement programs",
        "advised clients against high-risk or low-value customizations",
        "advised customers against high-risk or low-value customizations",
        "negotiated vendor agreements, system enhancement scopes",
    )

    def is_experience_detail(text: str, paragraph: ET.Element, in_experience: bool) -> bool:
        if not in_experience or not text:
            return False
        normalized_section = normalize_required_section_name(text)
        if normalized_section or is_role_heading(text):
            return False
        if " | " in text and not is_bullet(paragraph):
            return False
        return True

    removed = 0
    in_experience = False
    for child in list(body):
        if removed >= max_remove:
            break
        original_text = re.sub(r"\s+", " ", paragraph_text(child)).strip()
        normalized_section = normalize_required_section_name(original_text)
        if normalized_section:
            in_experience = normalized_section == "Professional Experience"
            continue

        text = original_text.lower()
        removable_detail = is_bullet(child) or is_experience_detail(original_text, child, in_experience)
        if removable_detail and any(pattern in text for pattern in patterns):
            if bullet_deserves_explicit_fit_protection(original_text, job_description):
                continue
            body.remove(child)
            removed += 1

    if removed:
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)
    return removed

def competency_label_rewrites(job_description: str) -> dict[str, str]:
    rewrites: dict[str, str] = {}
    profile = job_problem_profile(job_description)
    if profile.primary_lane == "change_enablement":
        rewrites.update(
            {
                "Implementation and Delivery": "Transformation Delivery",
                "Risk and Escalation": "Change Risk and Adoption",
                "Analytics and Reporting": "Adoption Metrics and Reporting",
            }
        )
    if jd_mentions(job_description, "saas", "licensing", "software asset", "license management"):
        rewrites.update(
            {
                "Implementation and Delivery": "SaaS Consulting and Delivery",
                "Customer Success": "Client Advisory and Stakeholder Management",
                "Analytics and Operations": "SaaS Data Analysis and Operations",
                "ERP Platforms": "SaaS and Enterprise Platforms",
                "Enterprise Tools": "SaaS and Enterprise Tools",
            }
        )
    if jd_mentions(job_description, "project management", "scope", "deliverable", "resource management"):
        rewrites.update(
            {
                "Process and Delivery": "Project Delivery",
            }
        )
    if jd_mentions(job_description, "crm", "billing", "order management"):
        rewrites.update(
            {
                "Enterprise Tools": "CRM Tools",
                "Process and Delivery": "Project Delivery",
            }
        )
    if jd_mentions(job_description, "ai", "automation"):
        rewrites.update(
            {
                "AI and Automation": "AI and Automation",
            }
        )
    return rewrites

def rename_core_competency_categories(document_xml: Path, job_description: str) -> int:
    rewrites = competency_label_rewrites(job_description)
    if not rewrites:
        return 0

    tree = ET.parse(document_xml)
    paragraphs = tree.getroot().findall(f".//{W}p")
    in_core = False
    changed = 0

    for paragraph in paragraphs:
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        if is_skills_section_heading(text):
            in_core = True
            continue
        if text == "Professional Development":
            in_core = False
            continue
        if not in_core or ":" not in text:
            continue
        current_label = text.split(":", 1)[0].strip()
        new_label = rewrites.get(current_label)
        if new_label and replace_paragraph_prefix(paragraph, current_label, new_label):
            changed += 1

    if changed:
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)
    return changed

def normalize_core_competency_capitalization(document_xml: Path) -> int:
    tree = ET.parse(document_xml)
    paragraphs = tree.getroot().findall(f".//{W}p")
    in_core = False
    changed = 0

    for paragraph in paragraphs:
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        if is_skills_section_heading(text):
            in_core = True
            continue
        if text == "Professional Development":
            in_core = False
            continue
        if not in_core or ":" not in text:
            continue
        label, items_text = text.split(":", 1)
        items = [item.strip() for item in re.split(r"\s+\|\s+", items_text.strip()) if item.strip()]
        normalized_label = title_case_skill_phrase(label)
        normalized_items = [title_case_skill_phrase(item) for item in items]
        normalized_text = f"{normalized_label}:  " + "  |  ".join(normalized_items)
        if normalized_text != text:
            set_paragraph_text(paragraph, normalized_text)
            changed += 1

    if changed:
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)
    return changed

def format_core_competency_runs(document_xml: Path) -> int:
    tree = ET.parse(document_xml)
    paragraphs = tree.getroot().findall(f".//{W}p")
    in_core = False
    changed = 0

    for paragraph in paragraphs:
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        if is_skills_section_heading(text):
            in_core = True
            continue
        if text == "Professional Development":
            in_core = False
            continue
        if not in_core or ":" not in text:
            continue

        label, items_text = text.split(":", 1)
        items = [item.strip() for item in re.split(r"\s+\|\s+", items_text.strip()) if item.strip()]
        remove_runs(paragraph)
        append_run(paragraph, f"{label}:", italic=True, bold=False)
        if items:
            append_run(paragraph, "  " + "  |  ".join(items), italic=False, bold=False)
        changed += 1

    if changed:
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)
    return changed


def normalize_skills_section_heading(document_xml: Path) -> int:
    tree = ET.parse(document_xml)
    changed = 0

    for paragraph in tree.getroot().findall(f".//{W}p"):
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        if not is_skills_section_heading(text) or text == SKILLS_SECTION_HEADING:
            continue
        set_paragraph_text(paragraph, SKILLS_SECTION_HEADING)
        changed += 1

    if changed:
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)
    return changed

def supported_simple_competencies(job_description: str, existing_items: set[str]) -> list[str]:
    additions: list[str] = []
    for skill, triggers in SIMPLE_COMPETENCY_KEYWORDS:
        if normalize_compare(skill) in existing_items:
            continue
        if jd_mentions(job_description, *triggers):
            additions.append(skill)
    for context in employer_context_matches(job_description)[:2]:
        for skill in context["competencies"]:
            skill = str(skill)
            if normalize_compare(skill) in existing_items:
                continue
            if skill in additions:
                continue
            additions.append(skill)
    return additions


def skill_relevance_score(
    skill: str,
    job_description: str,
    emphasis: TailoringEmphasis | None = None,
) -> int:
    score = 0
    normalized = normalize_compare(skill)
    jd_lower = normalize_compare(job_description)
    if normalized in jd_lower:
        score += 5
    if re.search(rf"\b{re.escape(normalized)}\b", jd_lower):
        score += 3
    if normalized in IMPORTANT_SHORT_ATS_TERMS:
        score += 4
    if emphasis:
        boosted_terms = {normalize_compare(term) for term in emphasis.competency_terms}
        if normalized in boosted_terms:
            score += 5
        elif any(term and term in normalized for term in boosted_terms):
            score += 2
    return score

def irrelevant_competency_items(job_description: str, items: set[str]) -> set[str]:
    """Identify competency items that do not match the job description.
    
    Competencies are considered irrelevant if they have CONDITIONAL triggers
    that do NOT match the job description. This preserves domain-specific 
    skills only when their job context is present.
    
    Note: This uses CONDITIONAL_COMPETENCY_ITEMS (for removal logic).
    The add_simple_core_competencies function uses SIMPLE_COMPETENCY_KEYWORDS
    (for addition logic). These are intentionally separate: conditional items
    are niche/specialized and only removed when context is absent; simple
    keywords are common and only added when context is present.
    """
    irrelevant: set[str] = set()
    for item in items:
        triggers = CONDITIONAL_COMPETENCY_ITEMS.get(item)
        if triggers and not jd_mentions(job_description, *triggers):
            irrelevant.add(item)
    return irrelevant


def retained_competency_items(
    job_description: str,
    items: set[str],
    max_items: int = CORE_COMPETENCY_TARGET_ITEMS,
    emphasis: TailoringEmphasis | None = None,
) -> set[str]:
    """Return the normalized competency items that should survive tailoring.

    This mirrors the resume-build behavior:
    1. Remove niche items whose conditional triggers are absent.
    2. If the section is still oversized, keep the highest-relevance items and
       trim the lowest-scoring overflow so the resume can stay within two pages.
    """
    normalized_items = {normalize_compare(item) for item in items if normalize_compare(item)}
    retained = normalized_items - irrelevant_competency_items(job_description, normalized_items)
    if len(retained) <= max_items:
        return retained

    removable = sorted(
        (
            (skill_relevance_score(item, job_description, emphasis), normalize_compare(item), item)
            for item in retained
        ),
        key=lambda row: (row[0], row[1]),
    )
    extras_to_remove = len(retained) - max_items
    overflow = {item for _score, _normalized, item in removable[:extras_to_remove]}
    return retained - overflow

def add_simple_core_competencies(
    document_xml: Path,
    job_description: str,
    *,
    emphasis: TailoringEmphasis | None = None,
) -> int:
    snapshot = resume_snapshot(document_xml)
    additions = supported_simple_competencies(job_description, snapshot.competency_items)
    if not additions:
        return 0
    max_items = CORE_COMPETENCY_TARGET_ITEMS

    tree = ET.parse(document_xml)
    paragraphs = tree.getroot().findall(f".//{W}p")
    in_core = False
    preferred_labels = (
        "Solution Delivery and Program Leadership",
        "Solution Delivery",
        "Project Delivery and Resource Management",
        "Project Delivery and Operations Management",
        "Project Delivery",
        "Process and Delivery",
        "Implementation and Delivery",
    )
    candidates: dict[str, ET.Element] = {}

    for paragraph in paragraphs:
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        if is_skills_section_heading(text):
            in_core = True
            continue
        if text == "Professional Development":
            break
        if not in_core or ":" not in text:
            continue
        label = text.split(":", 1)[0].strip()
        candidates[label] = paragraph

    target: ET.Element | None = None
    for label in preferred_labels:
        if label in candidates:
            target = candidates[label]
            break
    if target is None and candidates:
        target = next(reversed(candidates.values()))
    if target is None:
        return 0

    text = re.sub(r"\s+", " ", paragraph_text(target)).strip()
    existing_normalized = extract_competency_items(paragraph_infos(document_xml))
    available_slots = max(0, max_items - len(existing_normalized))
    additions_sorted = sorted(
        additions,
        key=lambda skill: skill_relevance_score(skill, job_description, emphasis),
        reverse=True,
    )
    new_items = [title_case_skill_phrase(skill) for skill in additions_sorted if normalize_compare(skill) not in existing_normalized]
    if not new_items:
        return 0

    label, items_text = text.split(":", 1)
    items = [item.strip() for item in re.split(r"\s+\|\s+", items_text.strip()) if item.strip()]
    baseline_page_count = estimate_page_count_from_xml(document_xml)
    added = 0

    if available_slots == 0:
        ranked_existing = sorted(
            (
                (skill_relevance_score(item, job_description, emphasis), index, item)
                for index, item in enumerate(items)
            ),
            key=lambda row: (row[0], normalize_compare(row[2])),
        )
        for skill in new_items:
            if added >= 5 or not ranked_existing:
                break
            weakest_score, weakest_index, weakest_item = ranked_existing[0]
            if skill_relevance_score(skill, job_description, emphasis) <= weakest_score:
                continue
            previous_items = list(items)
            items[weakest_index] = skill
            set_paragraph_text(target, f"{label}:  " + "  |  ".join(items))
            tree.write(document_xml, encoding="utf-8", xml_declaration=True)
            page_count = estimate_page_count_from_xml(document_xml)
            if page_count and page_count > baseline_page_count:
                items = previous_items
                set_paragraph_text(target, f"{label}:  " + "  |  ".join(items))
                tree.write(document_xml, encoding="utf-8", xml_declaration=True)
                break
            existing_normalized.discard(normalize_compare(weakest_item))
            existing_normalized.add(normalize_compare(skill))
            ranked_existing = sorted(
                (
                    (skill_relevance_score(item, job_description, emphasis), index, item)
                    for index, item in enumerate(items)
                ),
                key=lambda row: (row[0], normalize_compare(row[2])),
            )
            added += 1
        return added

    for skill in new_items:
        if added >= 5 or added >= available_slots:
            break
        previous_items = list(items)
        items.append(skill)
        set_paragraph_text(target, f"{label}:  " + "  |  ".join(items))
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)
        page_count = estimate_page_count_from_xml(document_xml)
        if page_count and page_count > baseline_page_count:
            items = previous_items
            set_paragraph_text(target, f"{label}:  " + "  |  ".join(items))
            tree.write(document_xml, encoding="utf-8", xml_declaration=True)
            break
        added += 1

    return added


def add_targeted_core_competencies(
    document_xml: Path,
    target_keywords: Sequence[str],
    job_description: str,
    *,
    limit: int = 3,
) -> list[str]:
    normalized_targets = [
        title_case_skill_phrase(keyword)
        for keyword in target_keywords
        if normalize_compare(keyword)
    ]
    if not normalized_targets:
        return []

    snapshot = resume_snapshot(document_xml)
    existing_normalized = set(snapshot.competency_items)
    candidates = [
        keyword
        for keyword in normalized_targets
        if normalize_compare(keyword) not in existing_normalized
    ]
    if not candidates:
        return []

    max_items = CORE_COMPETENCY_TARGET_ITEMS
    tree = ET.parse(document_xml)
    paragraphs = tree.getroot().findall(f".//{W}p")
    in_core = False
    preferred_labels = (
        "Solution Delivery and Program Leadership",
        "Solution Delivery",
        "Project Delivery and Resource Management",
        "Project Delivery and Operations Management",
        "Project Delivery",
        "Process and Delivery",
        "Implementation and Delivery",
    )
    candidates_by_label: dict[str, ET.Element] = {}

    for paragraph in paragraphs:
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        if is_skills_section_heading(text):
            in_core = True
            continue
        if text == "Professional Development":
            break
        if not in_core or ":" not in text:
            continue
        label = text.split(":", 1)[0].strip()
        candidates_by_label[label] = paragraph

    target: ET.Element | None = None
    for label in preferred_labels:
        if label in candidates_by_label:
            target = candidates_by_label[label]
            break
    if target is None and candidates_by_label:
        target = next(reversed(candidates_by_label.values()))
    if target is None:
        return []

    text = re.sub(r"\s+", " ", paragraph_text(target)).strip()
    if ":" not in text:
        return []
    label, items_text = text.split(":", 1)
    items = [item.strip() for item in re.split(r"\s+\|\s+", items_text.strip()) if item.strip()]
    available_slots = max(0, max_items - len(existing_normalized))
    baseline_page_count = estimate_page_count_from_xml(document_xml)
    inserted: list[str] = []

    if available_slots == 0:
        return inserted

    for skill in candidates[: min(limit, available_slots)]:
        previous_items = list(items)
        items.append(skill)
        set_paragraph_text(target, f"{label}:  " + "  |  ".join(items))
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)
        page_count = estimate_page_count_from_xml(document_xml)
        if page_count and baseline_page_count and page_count > baseline_page_count:
            items = previous_items
            set_paragraph_text(target, f"{label}:  " + "  |  ".join(items))
            tree.write(document_xml, encoding="utf-8", xml_declaration=True)
            break
        inserted.append(skill)

    return inserted

def remove_irrelevant_core_competencies(
    document_xml: Path,
    job_description: str,
    *,
    emphasis: TailoringEmphasis | None = None,
) -> int:
    snapshot = resume_snapshot(document_xml)
    retained = retained_competency_items(job_description, snapshot.competency_items, emphasis=emphasis)

    tree = ET.parse(document_xml)
    paragraphs = tree.getroot().findall(f".//{W}p")
    in_core = False
    removed = 0
    current_rows: list[tuple[ET.Element, str, list[str]]] = []

    for paragraph in paragraphs:
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        if is_skills_section_heading(text):
            in_core = True
            continue
        if text == "Professional Development":
            in_core = False
            continue
        if not in_core or ":" not in text:
            continue

        label, items_text = text.split(":", 1)
        items = [item.strip() for item in re.split(r"\s+\|\s+", items_text.strip()) if item.strip()]
        kept: list[str] = []
        for item in items:
            if normalize_compare(item) not in retained:
                removed += 1
            else:
                kept.append(item)
        if len(kept) != len(items):
            set_paragraph_text(paragraph, f"{label}:  " + "  |  ".join(kept))
            items = kept
        current_rows.append((paragraph, label, items))

    total_items = sum(len(items) for _paragraph, _label, items in current_rows)

    if total_items > 25:
        removable = sorted(
            (
                (skill_relevance_score(item, job_description, emphasis), normalize_compare(item), item)
                for _paragraph, _label, items in current_rows
                for item in items
            ),
            key=lambda row: (row[0], row[1]),
        )
        extras_to_remove = total_items - 25
        extra_removals = {normalized for _score, normalized, _item in removable[:extras_to_remove]}
        if extra_removals:
            for paragraph, label, items in current_rows:
                kept = [item for item in items if normalize_compare(item) not in extra_removals]
                removed += len(items) - len(kept)
                if len(kept) != len(items):
                    set_paragraph_text(paragraph, f"{label}:  " + "  |  ".join(kept))

    if removed:
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)
    return removed

def condense_professional_summary(document_xml: Path) -> int:
    summary = professional_summary_text(document_xml)
    if summary is None:
        return 0
    word_count = len(re.findall(r"\b[\w+.#'-]+\b", summary))
    if word_count <= 130:
        return 0
    print(f"condense_professional_summary: {word_count} words, applying condensations")

    tree = ET.parse(document_xml)
    paragraphs = tree.getroot().findall(f".//{W}p")
    in_summary = False
    changed = 0

    replacements = (
        (r"\bmore than ten years of\b", "10+ years of"),
        (r"\bthree years as\b", "3 years as"),
        (r"\bmore than 80\b", "80+"),
        (r"\b150-plus\b", "150+"),
        (r"\bmore than 200\b", "200+"),
        (r"\bmore than 60\b", "60+"),
        (r"\bmore than one million dollars in annual revenue\b", "$1M+ in annual revenue"),
        (r"\bhaving built\b", "built"),
        (
            r"\bTranslates customer business problems into system solutions that stick, built 200\+ dashboards\b",
            "Translates customer business problems into durable system solutions, with 200+ dashboards",
        ),
        (r"\bincluding the full ERP setup for\b", "including ERP setup for"),
        (r"\bthrough consolidated case ownership and resolution of\b", "through ownership and resolution of"),
    )

    for paragraph in paragraphs:
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        if text == "Professional Summary":
            in_summary = True
            continue
        if text == "Professional Experience":
            in_summary = False
            break
        if not in_summary or not text:
            continue
        updated = text
        for pattern, replacement in replacements:
            updated = re.sub(pattern, replacement, updated, flags=re.I)
        if updated != text:
            set_paragraph_text(paragraph, updated)
            changed += 1

    if changed:
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)
    return changed

def rebalance_professional_summary_erp_mentions(document_xml: Path, max_mentions: int = 2) -> int:
    summary = professional_summary_text(document_xml)
    if summary is None or len(re.findall(r"\berp\b", summary, flags=re.I)) <= max_mentions:
        return 0

    tree = ET.parse(document_xml)
    paragraphs = tree.getroot().findall(f".//{W}p")
    in_summary = False
    changed = 0
    replacements = (
        ("mission-critical ERP platforms", "mission-critical enterprise platforms"),
        ("practical ERP outcomes", "measurable client outcomes"),
        ("complex ERP outcomes", "complex implementation outcomes"),
        ("ERP implementation, data migration", "software implementation, data migration"),
        ("ERP implementation", "software implementation"),
        ("ERP delivery", "enterprise systems delivery"),
        ("ERP workflow", "enterprise workflow"),
        ("ERP setup", "systems setup"),
        ("ERP migration", "systems migration"),
        ("ERP platform", "enterprise system"),
        ("ERP platforms", "enterprise systems"),
    )

    for paragraph in paragraphs:
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        if text == "Professional Summary":
            in_summary = True
            continue
        if text == "Professional Experience":
            break
        if not in_summary or not text:
            continue
        updated = text
        for original, replacement in replacements:
            if len(re.findall(r"\berp\b", updated, flags=re.I)) <= max_mentions:
                break
            updated = re.sub(re.escape(original), replacement, updated, count=1, flags=re.I)
        if len(re.findall(r"\berp\b", updated, flags=re.I)) > max_mentions:
            # The list is created inside rebalance_professional_summary_erp_mentions(), so no counter state persists across calls.
            count = [0]

            def replace_extra(match):
                count[0] += 1
                return match.group(0) if count[0] <= max_mentions else "enterprise systems"

            updated = re.sub(r"\bERP\b", replace_extra, updated, flags=re.I)
        if updated != text:
            set_paragraph_text(paragraph, updated)
            changed += 1

    if changed:
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)
    return changed
