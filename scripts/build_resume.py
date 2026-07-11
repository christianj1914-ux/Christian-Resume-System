#!/usr/bin/env python3
"""
Build Christian Estrada's tailored DOCX resume.

Rules enforced from AGENTS.md:
- use only files in /source
- default to Implementation resume
- use Pre-Sales/CSM only when the job clearly focuses on that lane
- use EdFix as the visual formatting base
- preserve role identity, required sections, metrics, and factual meaning
- always preserve the East West and Aptean reorganization fact
- apply ATS keyword alignment through supported reframes and bullet ordering
- save DOCX only to /output
- never create placeholders or PDFs
- never use LinkedIn page content as source material
- enforce single spacing and hyphenated date ranges
"""

from __future__ import annotations

import _bootstrap

_bootstrap.ensure_script_path()

import argparse
import difflib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile
from dataclasses import dataclass, replace
from pathlib import Path
from xml.etree import ElementTree as ET

import render_checks
import business_context
import commercial_resume_model
import prose_engine
import requirement_engine
from config.job_profiles import (
    BRIDGE_EVIDENCE_AREAS,
    CONDITIONAL_COMPETENCY_ITEMS,
    EMPLOYER_CONTEXTS,
    POOR_FIT_REQUIREMENT_AREAS,
    PRESALES_SIGNALS,
    SAME_COMPANY_OUTPUT_LOOKBACK,
    SAME_COMPANY_VARIABLE_OVERLAP_THRESHOLD,
    SIMPLE_COMPETENCY_KEYWORDS,
    SPECIALTY_GAP_AREAS,
    STORY_LENSES,
    TAILORING_EMPHASIS_PROFILES,
    TARGETING_LANES,
    UNSUPPORTED_REQUIREMENT_PATTERNS,
)
from config.language_rules import (
    ACRONYM_TEXT_REPLACEMENTS,
    AI_WRITING_PATTERNS,
    CLICHE_PATTERNS,
    DUTY_ONLY_OPENERS,
    FIRST_PERSON_PATTERNS,
    GENERIC_SOFT_KEYWORDS,
    contains_reorg_fact,
    MANDATORY_REORG_COMPANIES,
    MANDATORY_REORG_SENTENCE,
    PLACEHOLDER_PATTERNS,
    PROFESSIONAL_SUMMARY_MAX_WORDS,
    PROFESSIONAL_SUMMARY_MIN_WORDS,
    PROMPT_LEAK_PATTERNS,
    reorg_fact_count,
    SUBJECTIVE_JOB_AD_PATTERNS,
)
from config.paths import (
    JOB_DESCRIPTION,
    OUTPUT_DIR,
    PROJECT_ROOT,
    SCRATCH_DIR,
    SOURCE_DIR,
)
from utils import (
    GREAT_EIGHT_OUTCOMES,
    clean_source_text,
    fail,
    has_great_eight_signal,
    optional_text,
    read_text,
    remove_linkedin_hyperlinks,
)
from text_safety import dedupe_header_segments, normalize_bullet_ending, substitution_safety_issues

from resume_analysis import (
    audit_keyword_sort_key,
    BOILERPLATE_LINE_RE,
    BOILERPLATE_SECTION_RE,
    BLOCKED_FILENAME_NAMES,
    COLOR_AUDIT_BLOCKED_KEYWORDS,
    COLOR_AUDIT_PRIORITY_TERMS,
    CORPORATE_STRATEGY_PROFILE,
    IMPORTANT_SHORT_ATS_TERMS,
    JobProblemProfile,
    OWNERSHIP_ACTION_RE,
    ROLE_REQUIREMENT_SECTION_RE,
    STOP_WORDS,
    SUMMARY_PLACEMENT_TERMS,
    UNSUPPORTED_OWNERSHIP_LABELS,
    audit_keywords,
    choose_resume,
    clean_company_name,
    clean_job_title,
    detect_company_profile,
    employer_context_matches,
    employer_context_sentence,
    extract_company_name,
    extract_display_job_title,
    extract_job_title,
    extract_output_name,
    extract_output_target_name,
    fit_status,
    is_consulting_job_description,
    is_generic_soft_keyword,
    is_keyword_color_candidate,
    is_startup_or_broad_operator_role,
    is_valid_company_name,
    is_valid_filename_piece,
    jd_color_priority_terms,
    jd_explicitly_requires_erp,
    jd_mentions,
    jd_priority_phrases,
    job_problem_profile,
    keyword_hits,
    keyword_regex,
    keyword_set,
    natural_problem_phrase,
    looks_like_job_title,
    looks_like_sentence_fragment,
    matching_output_files,
    normalize_compare,
    normalize_title,
    objective_business_context_sentence,
    is_unsupported_do_not_insert,
    poor_fit_requirements,
    primary_employer_context,
    primary_story_lens,
    role_requirement_text,
    role_specialty_phrase,
    should_deemphasize_erp_for_role,
    signal_hits,
    story_lens_business_problem,
    story_lens_candidate_story,
    story_lens_identity,
    story_lens_interview_lens,
    story_lens_matches,
    story_lens_sentence,
    text_mentions,
    unsupported_requirement_hit,
    visible_company_values,
    visible_role_specialties,
    visible_values_phrase,
    output_name_candidates,
)

from resume_content import (
    add_targeted_core_competencies,
    add_simple_core_competencies,
    apply_consulting_story_rewrites,
    apply_outcome_framing_rewrites,
    apply_startup_operator_rewrites,
    apply_supported_rewrites,
    apply_value_story_rewrites,
    append_summary_future_bridge,
    assert_no_erp_language_for_non_erp_role,
    build_problem_first_summary,
    bullet_is_condensable,
    clean_merged_role_bullets,
    comma_series,
    competency_label_rewrites,
    condense_professional_summary,
    determine_tailoring_emphasis,
    format_core_competency_runs,
    generate_positioning_statement,
    merge_low_fit_bullets_before_delete,
    normalize_core_competency_capitalization,
    normalize_skills_section_heading,
    obvious_choice_positioning,
    optimize_role_summaries,
    optimized_role_summary,
    rebalance_professional_summary_erp_mentions,
    remove_condensable_role_bullets,
    remove_extra_role_summary_paragraphs,
    remove_global_low_fit_bullets,
    remove_irrelevant_core_competencies,
    retained_competency_items,
    rename_core_competency_categories,
    rewrite_professional_summary_for_role,
    rewrite_supported_text,
    role_fit_checklist,
    scrub_non_erp_resume_language,
    skill_relevance_score,
    scrub_erp_language_for_non_erp_text,
    scrub_named_erp_platforms_for_summary,
    startup_operator_summary,
    strengthen_outcome_framing,
    summary_future_bridge,
    summary_job_poster_sentence,
    summary_positioning_sentence,
    supported_simple_competencies,
    TailoringEmphasis,
)

from resume_format import (
    REQUIRED_SECTIONS,
    SKILLS_SECTION_HEADING,
    W,
    append_run,
    apply_core_competency_row_spacing,
    apply_dense_font_sizing,
    apply_fit_font_sizing,
    apply_font_and_size_pass,
    apply_resume_alignment,
    apply_resume_spacing_rhythm,
    apply_section_layout,
    apply_spacing_and_layout_pass,
    copy_visual_parts,
    ensure_child,
    ensure_header_gap_after_contact,
    force_document_font,
    force_paragraph_single_spacing,
    force_resume_visual_branding,
    force_style_single_spacing,
    force_styles_font,
    estimate_page_count_from_xml,
    is_blank_paragraph,
    is_bullet,
    make_separator_paragraph,
    normalize_linkedin_hyperlink_targets,
    normalize_required_section_name,
    normalize_separator_paragraph,
    pack_docx,
    pack_docx_with_page_fit,
    paragraph_text,
    remove_runs,
    section_matches,
    set_bool_prop,
    set_paragraph_alignment,
    set_paragraph_spacing_values,
    set_paragraph_text,
    set_run_color,
    set_run_font,
    set_run_size,
    set_single_spacing,
    is_skills_section_heading,
    unpack_docx,
    w_attr,
)

COMPANY_EAST_WEST = "East West Manufacturing"
COMPANY_APTEAN = "Aptean"
COMPANY_HOME_DEPOT = "The Home Depot"
COMPANY_ADERANT = "Aderant"
APTEAN_COMPANY_CONTEXT_SENTENCE_ONE = (
    "Aptean is a global provider of mission-critical, industry-specific software solutions for manufacturers, distributors, and other specialized organizations."
)
APTEAN_COMPANY_CONTEXT_SENTENCE_TWO = (
    "More than 10,000 organizations across 20-plus industries and 80 countries rely on Aptean's purpose-built ERP, supply chain, and compliance platforms to streamline daily operations."
)
APTEAN_COMPANY_CONTEXT_REQUIRED_PHRASES = (
    "mission-critical, industry-specific software solutions",
    "10,000 organizations",
    "20-plus industries",
    "80 countries",
)
RESPONSIBILITY_SOFTENING_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\blight system administration\b", "light system administration"),
    (r"\blight administration\b", "light administration"),
    (r"\bhelped with\b", "helped with"),
    (r"\bwas involved in\b", "was involved in"),
    (r"\bparticipated in\b", "participated in"),
    (r"\bsort of\b", "sort of"),
    (r"\bpretty much\b", "pretty much"),
    (r"\bthings of that nature\b", "things of that nature"),
)
OWNERSHIP_VERB_LADDER: tuple[str, ...] = ("owned", "led", "was responsible for", "coordinated", "supported")
TOP_THIRD_OWNERSHIP_SOFTENERS: tuple[tuple[str, str], ...] = (
    (r"\bsupported\b", "supported"),
    (r"\bworked with\b", "worked with"),
    (r"\bhelped\b", "helped"),
    (r"(?<![a-zA-Z-])assisted\b", "assisted"),  # exclude compound adjectives like "AI-assisted"
    (r"\binvolved in\b", "involved in"),
)
TOP_THIRD_STRONG_OWNERSHIP_RE = re.compile(
    r"\b(?:owned|led|was responsible for|coordinated|drove|delivered|built|implemented|aligned|validated|stabilized|resolved|managed)\b",
    re.I,
)

IMPLEMENTATION_RESUME = SOURCE_DIR / "Estrada_Resume_Implementation.docx"
PRESALES_CSM_RESUME = SOURCE_DIR / "Estrada_Resume_PreSales_CSM.docx"
AUDIT_TOP_ROLE_TITLES = (
    "Enterprise Systems Manager",
    "ERP Systems Manager",
    "Customer Success Consultant",
    "Customer Success Manager",
    "Solutions Consultant",
    "Implementation Consultant",
)
EDFIX_RESUME = SOURCE_DIR / "Christian_Estrada_KPMG_Final_Tightened_EdFix.docx"
IMPLEMENTATION_MASTER_TITLE = (
    "Software Implementation Manager  |  Pre-Sales and Solution Consulting"
    "  |  Enterprise Systems  |  Customer Success"
)
PRESALES_MASTER_TITLE = (
    "Solutions Consultant  |  Pre-Sales  |  Customer Success"
    "  |  Revenue Retention and Expansion"
)

WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"
RELS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
ET.register_namespace("w", WORD_NS)
W = f"{{{WORD_NS}}}"
R_PKG = f"{{{RELS_NS}}}"
XML_SPACE = f"{{{XML_NS}}}space"

STYLE_PARTS = (
    "word/styles.xml",
    "word/stylesWithEffects.xml",
    "word/theme/theme1.xml",
    "word/fontTable.xml",
    "word/settings.xml",
    "word/webSettings.xml",
)

SECTION_LAYOUT_TAGS = {
    f"{W}pgSz",
    f"{W}pgMar",
    f"{W}cols",
    f"{W}docGrid",
}

SINGLE_LINE_SPACING = "240"
ZERO_SPACING = "0"
RESUME_FONT = "Calibri"
BRAND_BLUE = "1F4E79"
BODY_GRAY = "595959"
LINK_BLUE = "0563C1"
CONTACT_EMAIL = "christianj1914@gmail.com"
LINKEDIN_URL = "https://www.linkedin.com/in/cjne/"
BODY_FONT_SIZE_HP = "20"
SECTION_SEPARATOR_FONT_SIZE_HP = "20"
CORE_COMPETENCY_ROW_SEPARATOR_FONT_SIZE_HP = "6"
SECTION_FONT_SIZE_HP = "21"
NAME_FONT_SIZE_HP = "44"
ALIGNMENT_MAX_SCORE = 115
ALIGNMENT_FAIL_FLOOR = 86
ALIGNMENT_TARGET_SCORE = 98
# Ordered to try the most common two-page fits before progressively tighter fallbacks.
FIT_PROFILES = (
    ("20", "21", "20"),
    ("19.6", "21", "20"),
    ("19.6", "21", "19.6"),
    ("20", "21", "19"),
    ("19.6", "21", "19"),
    ("19.2", "20", "19.2"),
    ("20", "21", "18"),
    ("19.6", "21", "18"),
    ("19.2", "20", "18"),
    ("20", "21", "16"),
    ("19.6", "21", "16"),
    ("19.2", "20", "16"),
    ("20", "21", "14"),
    ("19.6", "21", "14"),
    ("19.2", "20", "14"),
    ("19.2", "20", "12"),
)
TARGET_PAGE_COUNT = 2
CONDENSABLE_BULLET_COMPANIES = (COMPANY_EAST_WEST, COMPANY_APTEAN)
MIN_FINAL_BULLETS_BY_COMPANY = {
    COMPANY_EAST_WEST: 5,
    COMPANY_APTEAN: 5,
    COMPANY_HOME_DEPOT: 3,
    COMPANY_ADERANT: 2,
}


def validate_config_integrity() -> None:
    job_profile_configs = (
        "TARGETING_LANES",
        "BRIDGE_EVIDENCE_AREAS",
        "SPECIALTY_GAP_AREAS",
        "UNSUPPORTED_REQUIREMENT_PATTERNS",
        "STORY_LENSES",
        "EMPLOYER_CONTEXTS",
        "TAILORING_EMPHASIS_PROFILES",
    )
    language_rule_configs = (
        "CLICHE_PATTERNS",
        "AI_WRITING_PATTERNS",
        "PLACEHOLDER_PATTERNS",
        "FIRST_PERSON_PATTERNS",
        "DUTY_ONLY_OPENERS",
    )

    counts: list[str] = []
    for key in job_profile_configs:
        value = globals().get(key)
        if not isinstance(value, (list, tuple)) or not value:
            fail(
                f"config integrity failed: config/job_profiles.py {key} is missing or empty; "
                "expected a non-empty list or tuple"
            )
        counts.append(f"{key}={len(value)}")

    for key in language_rule_configs:
        value = globals().get(key)
        if not isinstance(value, tuple) or not value:
            fail(
                f"config integrity failed: config/language_rules.py {key} is missing or empty; "
                "expected a non-empty tuple"
            )
        counts.append(f"{key}={len(value)}")

    # Cross-reference validation: each lane should have supporting bridge evidence
    targeting_lanes = globals().get("TARGETING_LANES", ())
    bridge_evidence = globals().get("BRIDGE_EVIDENCE_AREAS", ())
    
    if targeting_lanes and bridge_evidence:
        lane_keys = {lane.get("key") for lane in targeting_lanes if isinstance(lane, dict)}
        # Bridge evidence doesn't map 1:1 with lanes, so just verify both exist
        # This prevents silent failures where configs are empty
        if not lane_keys:
            fail("config integrity failed: TARGETING_LANES contains no entries with 'key' field")
        if not isinstance(bridge_evidence, (list, tuple)) or not bridge_evidence:
            fail("config integrity failed: BRIDGE_EVIDENCE_AREAS is empty or missing")

    print("Config integrity OK: " + ", ".join(counts))


OBJECTIVE_CONTEXT_PATTERNS = (
    r"\$",
    r"\d",
    r"%",
    r"\b(?:b2b|b2c|saas|crm|erp|sql|power bi|tableau|salesforce|liveperson|serviceNow|jira|azure devops)\b",
    r"\b(?:manufacturing|supply chain|finance|ecommerce|operations|warehouse|implementation|go-live|uat|migration|integration|renewal|retention|forecast|churn|mitigation|onboarding)\b",
    r"\b(?:education(?:al)?|school|k-12|assessment|learning|learner(?:-facing)?|student|measurement|validation|accessibility|fairness|standards)\b",
    r"\b(?:clients|accounts|users|sites|dashboards|reports|workshops|qbrs|revenue|portfolio|platform|systems|global|international)\b",
)

OUTCOME_SIGNAL_RE = re.compile(
    r"(\$|\d|%|\b(?:reduced|reducing|increased|increasing|improved|improving|accelerated|accelerating|"
    r"stabilized|stabilizing|delivered|delivering|built|building|launched|launching|implemented|implementing|"
    r"enabled|enabling|eliminated|eliminating|optimized|optimizing|protected|protecting|converted|converting|"
    r"resolved|resolving|prevented|preventing|saved|saving|streamlined|streamlining|expanded|expanding|"
    r"retained|retaining|grew|growing|cut|minimized|minimizing|decreased|decreasing|strengthened|strengthening|"
    r"established|establishing|created|creating|designed|designing|drove|driving|produced|producing|"
    r"facilitated|facilitating|negotiated|negotiating|aligned|aligning|validated|validating)\b)",
    re.I,
)

SCOPE_PROOF_RE = re.compile(
    r"\b(?:director|directors|vp|vps|executive|executives|stakeholder|stakeholders|cross-functional|"
    r"cross-site|multi-site|global|enterprise|portfolio|workstream|workstreams|go-live|post-go-live|"
    r"uat|user acceptance|production|defect|defects|risk|escalation|adoption|readiness|scope|"
    r"cost|timeline|roadmap|roadmaps|users|clients|accounts|sites|annual revenue|support volume|"
    r"implementation phases|customer experience|pipeline|audit readiness)\b",
    re.I,
)

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


@dataclass(frozen=True)
class BuildResult:
    source_resume: Path
    output_docx: Path
    company_name: str
    paragraphs_rewritten: int
    competency_categories_renamed: int
    competency_items_added: int
    competency_items_removed: int
    role_bullets_removed: int
    bullet_groups_reordered: int
    visual_parts_applied: int
    audit_status: str
    audit_notes: list[str]
    readiness: "ResumeReadiness | None" = None
    build_warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResumeGap:
    label: str
    issue: str
    support_level: str
    priority: int
    blocker: bool = False


@dataclass(frozen=True)
class ResumeReadiness:
    audit_status: str
    prioritized_unresolved_gaps: tuple[ResumeGap, ...]
    auto_closed_gaps: tuple[ResumeGap, ...]
    hard_blockers: tuple[ResumeGap, ...]


@dataclass(frozen=True)
class ResumeVariationSnapshot:
    headline: str
    summary: str
    role_summaries: tuple[str, ...]
    bullets: tuple[str, ...]
    competency_labels: tuple[str, ...]
    competency_items: tuple[str, ...]


@dataclass(frozen=True)
class ResumeAssemblyResult:
    work_dir: Path
    document_xml: Path
    source_snapshot: "ResumeSnapshot"
    final_snapshot: "ResumeSnapshot"
    emphasis: TailoringEmphasis
    paragraphs_rewritten: int
    competency_categories_renamed: int
    competency_items_added: int
    competency_items_removed: int
    role_bullets_removed: int
    bullet_groups_reordered: int
    visual_parts_applied: int
    audit_status: str
    audit_notes: list[str]
    readiness: "ResumeReadiness | None"
    auto_closed_keywords: tuple[str, ...]
    variable_snapshot: ResumeVariationSnapshot


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




def require_file(path: Path, label: str) -> None:
    if not path.is_file():
        fail(f"{label} not found: {path}")


def validate_inputs(job_description_text: str | None = None) -> str:
    require_file(PROJECT_ROOT / "AGENTS.md", "AGENTS.md")
    if job_description_text is None:
        require_file(JOB_DESCRIPTION, "job description")
    require_file(IMPLEMENTATION_RESUME, "Implementation resume")
    require_file(PRESALES_CSM_RESUME, "Pre-Sales/CSM resume")
    require_file(EDFIX_RESUME, "EdFix visual base")

    raw_job_description = read_text(JOB_DESCRIPTION) if job_description_text is None else job_description_text.strip()
    if not raw_job_description:
        fail("jobs/job_description.txt is empty; refusing to create a placeholder or partial resume")
    warning_count = _check_job_description_quality(raw_job_description)
    print(f"JD quality check: {warning_count} warning(s).")
    job_description, removed_lines = strip_linkedin_job_board_boilerplate(raw_job_description)
    if removed_lines:
        print(f"JD NOTE: removed {removed_lines} LinkedIn/job-board boilerplate line(s) before targeting.")
    return job_description


def _check_job_description_quality(job_description: str) -> int:
    warnings = 0

    words = re.findall(r"\b[\w+.#'-]+\b", job_description)
    if len(words) < 150:
        warnings += 1
        print(
            f"JD WARNING: job description is only {len(words)} words; a full posting typically has 300 or more. "
            "Keyword coverage and lane detection may be weak.",
            file=sys.stderr,
        )

    if extract_company_name(job_description) is None:
        warnings += 1
        print(
            "JD WARNING: no company name detected; output filename will use the job title instead. "
            "Add a 'Company: [Name]' line at the top of the job description to set the filename explicitly.",
            file=sys.stderr,
        )

    about_matches = re.findall(r"\bAbout\s+[A-Z][A-Za-z0-9&.'-]+", job_description[:500])
    if len(about_matches) > 2:
        warnings += 1
        print(
            "JD WARNING: job description may contain multiple postings; use only one posting per run to keep "
            "targeting, keywords, and output names clean.",
            file=sys.stderr,
        )

    if re.search(r"\bEasy Apply\b|See who (?:applied|you know)", job_description, re.I):
        warnings += 1
        print(
            "JD WARNING: job description appears to be a LinkedIn snippet rather than a full posting; paste the "
            "full job description text for better keyword coverage.",
            file=sys.stderr,
        )

    return warnings


LINKEDIN_JOB_BOARD_NOISE_PATTERNS = (
    re.compile(r"\bInterested in applying\?.*\bEasy Apply\b", re.I),
    re.compile(r"\bSee who\b", re.I),
    # Only strip applicant COUNT lines (e.g. "123 applicants"); bare "applicants"
    # appears in legitimate EEO and company-values language and should not be stripped.
    re.compile(r"\b\d[\d,]*\+?\s+applicants?\b", re.I),
    # Only strip LinkedIn "promoted" UI indicators, not uses of "promoted" in job text.
    re.compile(r"\bpromoted\b.*\bLinkedIn\b|\bLinkedIn\b.*\bpromoted\b|promoted\s*[•·]\s*\d", re.I),
    re.compile(r"\bvisit our website\b.*\bfollow\b.*\bLinkedIn\b", re.I),
    re.compile(r"\brecruitment firm\b.*\bLinkedIn page\b", re.I),
)


def strip_linkedin_job_board_boilerplate(job_description: str) -> tuple[str, int]:
    cleaned_lines: list[str] = []
    removed_lines = 0

    for raw_line in job_description.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            cleaned_lines.append("")
            continue
        if any(pattern.search(line) for pattern in LINKEDIN_JOB_BOARD_NOISE_PATTERNS):
            removed_lines += 1
            continue
        cleaned_lines.append(raw_line.rstrip())

    cleaned = "\n".join(cleaned_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned, removed_lines


HEADER_TITLE_MAX_PARTS = 4
HEADER_TITLE_MAX_CHARS = 110
HEADER_TITLE_ROLE_NOUNS = {
    "administrator",
    "analyst",
    "architect",
    "consultant",
    "coordinator",
    "delivery",
    "developer",
    "director",
    "engineer",
    "lead",
    "manager",
    "officer",
    "owner",
    "partner",
    "specialist",
    "strategist",
}
HEADER_TITLE_SIGNAL_WORDS = {
    "adoption",
    "change",
    "consulting",
    "customer",
    "delivery",
    "enterprise",
    "implementation",
    "integration",
    "operations",
    "onboarding",
    "program",
    "reporting",
    "solution",
    "technical",
    "transformation",
    "workflow",
}
HEADER_TITLE_SENIORITY_WORDS = {
    "associate",
    "assistant",
    "chief",
    "junior",
    "jr",
    "principal",
    "senior",
    "sr",
    "staff",
    "vp",
}
HEADER_TITLE_ORG_SUFFIXES = ("office", "team", "department", "function", "group", "practice")
HEADER_TITLE_SKIP_LINES = {
    "about the job",
    "about this job",
    "about the role",
    "about this role",
    "responsibilities",
    "requirements",
    "qualifications",
    "skills",
    "experience",
    "education",
}
HEADER_TITLE_NOISE_SECTION_RE = re.compile(
    r"^\s*(?:why apply\??|what we offer|benefits|compensation|salary|pay range|perks)\s*:?\s*$",
    re.I,
)
HEADER_TITLE_NOISE_LINE_RE = re.compile(
    r"\b(?:easy apply|salary|equity|insurance(?:\s+plan)?|benefits|platinum health|"
    r"recruitment firm|linkedin page|visit our website|interested in applying|"
    r"equal opportunity|remote only|united states,\s*remote)\b",
    re.I,
)
HEADER_SIGNAL_PHRASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Healthcare AI", ("healthcare ai",)),
    ("Customer Onboarding", ("customer onboarding", "onboard customers", "onboard clients")),
    ("API-Led Integrations", ("api-led integrations", "api led integrations", "api integration", "api integrations")),
    ("Clinical Workflows", ("clinical workflows", "clinical requirements", "healthcare operations")),
    ("Technical Implementation", ("technical implementation", "technical implementations")),
    ("Implementation Delivery", ("implementation delivery", "delivery of workflows", "go-live", "launch readiness")),
    ("Change Delivery", ("change delivery",)),
    ("Enterprise Program", ("enterprise program office", "enterprise program")),
    ("Workflow Automation", ("workflow automation", "ai workflow")),
)


def industry_label_for_header(job_description: str) -> str:
    context = business_context.extract_business_context(job_description)
    business_model = context.business_model.lower() if context.business_model else ""
    if context.industry == "healthcare":
        return "Healthcare Technology"
    if context.industry == "manufacturing":
        return "Manufacturing and Supply Chain"
    if context.industry == "software" or "saas" in business_model:
        return "Enterprise SaaS"
    if context.industry == "financial services":
        return "Financial Services"
    if context.industry == "customer experience":
        return "Customer Experience Technology"
    return "Enterprise Software"


def header_signal_text(job_description: str) -> str:
    cleaned = role_requirement_text(job_description)
    kept: list[str] = []
    skipping_noise = False

    for raw_line in cleaned.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        normalized = line.lower().rstrip(":")

        if normalized in HEADER_TITLE_SKIP_LINES:
            if normalized in {"responsibilities", "requirements", "qualifications", "skills", "experience", "education"}:
                skipping_noise = False
            continue
        if re.match(r"^(?:company|job\s+title|title|role\s+title|role|position)\b", normalized):
            continue
        if HEADER_TITLE_NOISE_SECTION_RE.match(line):
            skipping_noise = True
            continue
        if skipping_noise:
            continue
        if HEADER_TITLE_NOISE_LINE_RE.search(line):
            continue
        kept.append(line)

    return "\n".join(kept) if kept else cleaned


def split_header_title_segments(role_title: str) -> list[str]:
    return [
        clean_job_title(segment)
        for segment in re.split(r"\s+(?:\||-|/|:)\s+", role_title)
        if clean_job_title(segment)
    ]


def header_title_segment_score(segment: str, index: int) -> tuple[int, int]:
    words = re.findall(r"[A-Za-z0-9]+", segment.lower())
    role_noun_hits = sum(1 for word in words if word in HEADER_TITLE_ROLE_NOUNS)
    signal_hits = sum(1 for word in words if word in HEADER_TITLE_SIGNAL_WORDS)
    trailing_org_penalty = 3 if words and words[-1] in HEADER_TITLE_ORG_SUFFIXES and role_noun_hits == 0 else 0
    score = len(words) + (role_noun_hits * 5) + (signal_hits * 2) - trailing_org_penalty
    return score, index


def primary_header_title(role_title: str) -> str:
    segments = split_header_title_segments(role_title)
    if not segments:
        return clean_job_title(role_title)
    role_segments = [
        segment
        for segment in segments
        if normalize_compare(segment.split()[-1]) not in HEADER_TITLE_ORG_SUFFIXES
    ]
    if role_segments:
        segments = role_segments
    return max(
        segments,
        key=lambda segment: header_title_segment_score(segment, segments.index(segment)),
    )


def normalize_header_org_segment(segment: str) -> str:
    shortened = re.sub(r"\s+(?:Office|Team|Department|Function|Group|Practice)\b$", "", segment, flags=re.I).strip()
    if len(shortened.split()) >= 2:
        return shortened
    return segment


def remove_header_title_seniority(title: str) -> str:
    words = title.split()
    filtered = [word for word in words if normalize_compare(word) not in HEADER_TITLE_SENIORITY_WORDS]
    return " ".join(filtered).strip() or title


def remove_header_role_noun(title: str) -> str:
    words = title.split()
    if len(words) < 3:
        return ""
    if normalize_compare(words[-1]) not in HEADER_TITLE_ROLE_NOUNS:
        return ""
    return " ".join(words[:-1]).strip()


def header_candidate_words(value: str) -> set[str]:
    return {
        normalize_compare(word)
        for word in re.findall(r"[A-Za-z0-9]+", value)
        if normalize_compare(word)
    }


def header_candidate_has_role_noun(value: str) -> bool:
    return any(word in HEADER_TITLE_ROLE_NOUNS for word in header_candidate_words(value))


def header_candidate_is_redundant(candidate: str, primary: str, existing_parts: list[str]) -> bool:
    candidate_key = normalize_compare(candidate)
    if any(candidate_key == normalize_compare(part) for part in existing_parts):
        return True

    candidate_without_seniority = normalize_compare(remove_header_title_seniority(candidate))
    primary_without_seniority = normalize_compare(remove_header_title_seniority(primary))
    if candidate_without_seniority and candidate_without_seniority == primary_without_seniority:
        return True

    candidate_without_role = normalize_compare(remove_header_role_noun(remove_header_title_seniority(candidate)))
    primary_without_role = normalize_compare(remove_header_role_noun(remove_header_title_seniority(primary)))
    if candidate_without_role and candidate_without_role == primary_without_role:
        return True

    candidate_words = header_candidate_words(candidate)
    primary_words = header_candidate_words(primary)
    if candidate_words and candidate_words.issubset(primary_words) and not header_candidate_has_role_noun(candidate):
        return True

    for part in existing_parts:
        part_words = header_candidate_words(part)
        if candidate_words and candidate_words == part_words:
            return True

    # Stemmed-root check: catches singular/plural and noun/gerund variants where exact
    # word comparison fails (e.g. "solution consulting" vs "Solutions Consultant").
    # Use the first 5 chars of each word as a rough shared-root proxy.
    def _root5(word: str) -> str:
        return word[:5]

    all_existing_roots: set[str] = set()
    for part in existing_parts:
        all_existing_roots |= {_root5(w) for w in header_candidate_words(part)}
    candidate_roots = {_root5(w) for w in candidate_words}
    if candidate_roots and candidate_roots.issubset(all_existing_roots) and not header_candidate_has_role_noun(candidate):
        return True

    return False


def title_variants_for_header(role_title: str) -> tuple[str, list[str]]:
    segments = split_header_title_segments(role_title)
    primary = primary_header_title(role_title)
    primary_key = normalize_compare(primary)
    variants: list[str] = []

    for segment in segments:
        if normalize_compare(segment) == primary_key:
            continue
        normalized_segment = normalize_header_org_segment(segment)
        if normalize_compare(normalized_segment) != primary_key:
            variants.append(title_case_skill_phrase(normalized_segment))

    without_seniority = remove_header_title_seniority(primary)
    if normalize_compare(without_seniority) != primary_key:
        variants.append(title_case_skill_phrase(without_seniority))

    without_role_noun = remove_header_role_noun(without_seniority)
    if without_role_noun and normalize_compare(without_role_noun) not in {
        primary_key,
        normalize_compare(without_seniority),
    }:
        variants.append(title_case_skill_phrase(without_role_noun))

    return title_case_skill_phrase(primary), variants


def header_phrase_candidates(job_description: str) -> list[str]:
    text = normalize_compare(header_signal_text(job_description))
    found: list[str] = []
    for label, signals in HEADER_SIGNAL_PHRASES:
        if any(signal in text for signal in signals):
            found.append(label)

    specialty_text = header_signal_text(job_description)
    for specialty in visible_role_specialties(specialty_text):
        found.append(title_case_skill_phrase(specialty))

    industry = industry_label_for_header(specialty_text)
    if industry and industry != "Enterprise Software":
        if "healthcare" not in normalize_compare(industry) or not any("healthcare" in normalize_compare(item) for item in found):
            found.append(industry)

    return found


def master_header_fallback_parts(master: str) -> list[str]:
    return [part.strip() for part in master.split("|") if part.strip()]


def fit_header_parts(primary: str, candidates: list[str], max_parts: int = HEADER_TITLE_MAX_PARTS, max_chars: int = HEADER_TITLE_MAX_CHARS) -> str:
    parts = [primary]

    for candidate in candidates:
        if not candidate or header_candidate_is_redundant(candidate, primary, parts):
            continue
        proposal = "  |  ".join(parts + [candidate])
        if len(proposal) > max_chars:
            continue
        parts.append(candidate)
        if len(parts) >= max_parts:
            break

    return "  |  ".join(dedupe_header_segments(parts))


def dynamic_header_title_line(job_description: str) -> str:
    selected = choose_resume(job_description)
    master = PRESALES_MASTER_TITLE if selected == PRESALES_CSM_RESUME else IMPLEMENTATION_MASTER_TITLE
    official_title = extract_job_title(job_description)
    if not official_title:
        return master
    from requirement_engine import _display_title, commercial_requirement_sections

    requirement_text = "\n".join(body for _heading, body in commercial_requirement_sections(job_description))
    role_title = _display_title(official_title, requirement_text) or official_title

    primary_title, title_variants = title_variants_for_header(role_title)
    profile = job_problem_profile(job_description)
    if profile.primary_lane == "corporate_strategy":
        consulting_candidates = [
            "Client Delivery",
            "Strategy and Analytics",
            "Executive Stakeholder Alignment",
        ]
        line = fit_header_parts(primary_title, consulting_candidates + title_variants + header_phrase_candidates(job_description))
        return line if len(line) <= HEADER_TITLE_MAX_CHARS else master

    candidates = title_variants + header_phrase_candidates(job_description) + master_header_fallback_parts(master)
    line = fit_header_parts(primary_title, candidates)
    return line if len(line) <= HEADER_TITLE_MAX_CHARS else master


















def is_valid_job_title(value: str) -> bool:
    return is_valid_filename_piece(value) and not looks_like_sentence_fragment(value)






















ATS_ADMIN_KEYWORD_PATTERNS = (
    "minimum", "requirement", "requirements", "preferred", "salary", "range", "exempt", "non exempt",
    "location", "start date", "background check", "benefits", "equal opportunity", "application",
    "job title", "reports to", "department", "employment", "full time", "part time",
)










NON_ERP_VISIBLE_PLATFORM_PATTERN = re.compile(
    r"\b(ERP|Aptean Intuitive|Aptean Encompix|Epicor Kinetic|SAP(?!\s+Crystal Reports\b)|Oracle ERP|Microsoft Dynamics 365)\b",
    re.I,
)
















def paragraph_text(element: ET.Element) -> str:
    return "".join(node.text or "" for node in element.findall(f".//{W}t"))


def visible_text(document_xml: Path) -> str:
    root = ET.parse(document_xml).getroot()
    paragraphs: list[str] = []
    for paragraph in root.findall(f".//{W}p"):
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def docx_visible_text_from_path(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    paragraphs: list[str] = []
    for paragraph in root.findall(f".//{W}p"):
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def ats_plain_text_validation(docx_path: Path) -> dict[str, object]:
    text = docx_visible_text_from_path(docx_path)
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]
    blockers: list[str] = []
    warnings: list[str] = []

    missing_sections = [
        section
        for section in REQUIRED_SECTIONS
        if not any(section_matches(line, section) for line in lines)
    ]
    if missing_sections:
        blockers.append("Missing required section(s) in ATS plain text: " + ", ".join(missing_sections) + ".")

    if not re.search(r"\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b", text, re.I):
        blockers.append("No email address detected in ATS plain text.")

    month_pattern = "|".join(MONTHS)
    date_pattern = rf"\b(?:{month_pattern})\s+\d{{4}}\s*-\s*(?:Present|(?:{month_pattern})\s+\d{{4}})\b"
    text_for_date_scan = re.sub(
        rf"(?<=[A-Za-z])(?=(?:{month_pattern})\s+\d{{4}}\s*-\s*(?:Present|(?:{month_pattern})\s+\d{{4}}))",
        " ",
        text,
        flags=re.I,
    )
    if not re.search(date_pattern, text_for_date_scan, re.I):
        blockers.append("No role date ranges detected in ATS plain text.")

    if "\ufffd" in text or "Ã" in text:
        warnings.append("Potential encoding artifacts detected in ATS plain text.")

    word_count = len(re.findall(r"\b[\w+.#'-]+\b", text))
    if word_count < 350 or word_count > 1600:
        warnings.append(f"ATS plain-text word count looks unusual ({word_count} words). Review for parser loss or overlong output.")

    return {"blockers": blockers, "warnings": warnings, "word_count": word_count}


def paragraph_infos(document_xml: Path) -> list[ParagraphInfo]:
    root = ET.parse(document_xml).getroot()
    paragraphs: list[ParagraphInfo] = []
    for paragraph in root.findall(f".//{W}p"):
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        if text:
            paragraphs.append(ParagraphInfo(text=text, is_bullet=is_bullet(paragraph)))
    return paragraphs


def is_bullet(paragraph: ET.Element) -> bool:
    return paragraph.find(f"{W}pPr/{W}numPr") is not None


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


def natural_top_bullet_score(
    text: str,
    keywords: set[str],
    profile: "JobProblemProfile | None" = None,
    job_description: str = "",
    emphasis: TailoringEmphasis | None = None,
) -> int:
    total = 0
    total += min(business_context.business_relevance_score(text), 12)
    if has_outcome_or_metric(text):
        total += 8
    total += min(objective_context_signal_count(text), 6) * 2
    if profile is not None:
        # Lane-specific business problem alignment bonus — ensures the bullets that
        # best match the employer's core need float to positions 1-2 under every role.
        lane_bonus_signals: dict[str, tuple[str, ...]] = {
            "presales_solution": (
                "discovery", "demo", "solution design", "buyer", "pre-sales", "presales",
                "executive workshop", "qbr", "requirements", "80+", "solution consulting",
            ),
            "customer_success": (
                "adoption", "retention", "renewal", "account", "customer", "1m+", "risk",
                "executive", "qbr", "workshop", "health", "churn", "expansion",
            ),
            "implementation_delivery": (
                "implementation", "go-live", "migration", "configuration", "data migration",
                "requirements", "uat", "testing", "readiness", "launch", "onboarding",
                "scoping", "technical scoping", "statement of work", "sow", "delivery",
                "customer delivery", "client-facing delivery", "process documentation",
                "comprehensive training", "customer training", "scope management",
                "technical integration", "integration", "cross-functional", "stakeholder",
                "solution architecture", "solution design", "project management",
            ),
            "analytics_operations": (
                "dashboard", "kpi", "reporting", "sql", "analytics", "decision", "visibility",
                "200+", "crystal reports", "power bi", "bi", "insight",
            ),
            "change_enablement": (
                "change", "adoption", "training", "enablement", "stakeholder", "resistance",
                "role-based", "communications", "transformation", "readiness",
            ),
            "corporate_strategy": (
                "client", "clients", "executive", "decision", "analysis", "recommendation",
                "tradeoff", "risk", "discovery", "workshop", "stakeholder",
            ),
            "process_improvement": (
                "process", "root cause", "efficiency", "lean", "cycle time", "waste",
                "78%", "22%", "workflow", "discrepancy", "improvement", "standardization",
            ),
        }
        signals = lane_bonus_signals.get(profile.primary_lane, ())
        text_lower = text.lower()
        lane_hits = sum(1 for s in signals if s in text_lower)
        total += min(lane_hits * 5, 20)
        if job_description and higher_level_private_sector_role(job_description):
            leadership_terms = (
                "led", "owned", "facilitated", "executive", "vp", "director", "stakeholder",
                "cross-functional", "workshop", "qbr", "presented", "recommendations",
                "tradeoffs", "scope", "scoping", "requirements", "solution architecture",
                "implementation plans", "decision-making", "roadmap", "aligned", "owners",
            )
            leadership_hits = sum(1 for term in leadership_terms if term in text_lower)
            total += min(leadership_hits * 3, 14)
        if job_description and jd_mentions(
            job_description,
            "integration",
            "integrations",
            "data migration",
            "testing",
            "delivery",
            "statement of work",
            "sow",
            "requirements gathering",
            "scoping",
            "technical scoping",
        ):
            bridge_terms = (
                "integration", "data migration", "testing", "uat", "delivery", "sow",
                "requirements", "scope", "scoping", "go-live", "validation", "handoff",
            )
            bridge_hits = sum(1 for term in bridge_terms if term in text_lower)
            total += min(bridge_hits * 2, 10)
        if job_description and jd_mentions(
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
        ):
            ai_bridge_terms = (
                "codex", "claude", "ai-assisted", "automation", "chatbot",
                "conversational ai", "liveperson", "liveengage", "sms",
            )
            ai_hits = sum(1 for term in ai_bridge_terms if term in text_lower)
            total += min(ai_hits * 3, 12)
        if job_description:
            explicit_hits = sum(1 for term in explicit_private_sector_terms(profile, job_description) if term in text_lower)
            total += min(explicit_hits * 2, 12)
        if emphasis is not None:
            emphasis_hits = sum(1 for term in emphasis.bullet_terms if term.lower() in text_lower)
            total += min(emphasis_hits * 4, 16)
    if re.search(r"\b(?:owned|built|delivered|reduced|stabilized|facilitated|led|designed|aligned|protected|enabled)\b", text, re.I):
        total += 3
    if re.search(r"\b(?:clients|users|sites|dashboards|workshops|revenue|go-live|implementation|ERP|Power BI|SQL)\b", text, re.I):
        total += 3
    if starts_with_duty_only_language(text):
        total -= 4
    if re.search(r"\ba pattern that\b", text, re.I):
        total -= 10
    if contains_subjective_job_ad_claim(text) or contains_cliche(text):
        total -= 8
    keyword_cap = 5
    if profile is not None and (
        profile.primary_lane == "implementation_delivery"
        or len(profile.direct_matches) < 4
        or profile.adjacent_matches
    ):
        keyword_cap = 8
    return total + min(score(text, keywords), keyword_cap)


def bullet_groups(body: ET.Element) -> list[tuple[int, int]]:
    children = list(body)
    groups: list[tuple[int, int]] = []
    start: int | None = None
    for index, child in enumerate(children):
        bullet = child.tag == f"{W}p" and is_bullet(child)
        if bullet and start is None:
            start = index
        elif not bullet and start is not None:
            if index - start > 1:
                groups.append((start, index))
            start = None
    if start is not None and len(children) - start > 1:
        groups.append((start, len(children)))
    return groups


def reorder_bullets(
    document_xml: Path,
    keywords: set[str],
    profile: "JobProblemProfile | None" = None,
    job_description: str = "",
    emphasis: TailoringEmphasis | None = None,
) -> int:
    tree = ET.parse(document_xml)
    root = tree.getroot()
    body = root.find(f"{W}body")
    if body is None:
        return 0

    children = list(body)
    changed = 0
    for start, end in reversed(bullet_groups(body)):
        group = children[start:end]
        top_count = min(2, len(group))
        top_items = [
            item
            for _, _, item in sorted(
                (
                    (
                        natural_top_bullet_score(
                            paragraph_text(item),
                            keywords,
                            profile,
                            job_description,
                            emphasis,
                        ),
                        index,
                        item,
                    )
                    for index, item in enumerate(group)
                ),
                key=lambda row: (-row[0], row[1]),
            )[:top_count]
        ]
        top_ids = {id(item) for item in top_items}
        remaining = [item for item in group if id(item) not in top_ids]
        keyword_items = [
            item
            for _, _, item in sorted(
                ((score(paragraph_text(item), keywords), index, item) for index, item in enumerate(remaining)),
                key=lambda row: (-row[0], row[1]),
            )
        ]
        ordered = top_items + keyword_items
        if ordered == group:
            continue
        for item in group:
            body.remove(item)
        for offset, item in enumerate(ordered):
            body.insert(start + offset, item)
        changed += 1

    if changed:
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)
    return changed


def role_bullet_budget(
    company: str,
    title: str,
    job_description: str,
    emphasis: TailoringEmphasis | None = None,
) -> int:
    company_key = normalize_compare(company)
    title_key = normalize_compare(title)
    profile = job_problem_profile(job_description)

    if company_key == normalize_compare(COMPANY_EAST_WEST):
        if emphasis and emphasis.proof_anchor in {"launch", "dashboards", "adoption", "decision", "ai"}:
            return 7
        if jd_explicitly_requires_erp(job_description) or jd_mentions(
            job_description,
            "manufacturing",
            "supply chain",
            "inventory",
            "data migration",
            "systems administrator",
            "erp admin",
            "erp manager",
            "epicor",
        ):
            return 7
        if profile.primary_lane in {"implementation_delivery", "analytics_operations", "change_enablement"}:
            return 6
        return 5

    if company_key == normalize_compare(COMPANY_APTEAN):
        if emphasis and emphasis.proof_anchor in {"revenue", "adoption", "ai"}:
            return 6
        if profile.primary_lane in {"customer_success", "presales_solution", "implementation_delivery"}:
            return 6
        if jd_mentions(job_description, "client", "customer", "implementation", "onboarding", "adoption"):
            return 6
        return 5

    if company_key == normalize_compare(COMPANY_HOME_DEPOT):
        if emphasis and emphasis.proof_anchor in {"ai", "dashboards", "revenue"}:
            return 5
        if profile.primary_lane in {"analytics_operations", "customer_success"} or jd_mentions(
            job_description,
            "analytics",
            "reporting",
            "dashboard",
            "customer experience",
            "contact center",
            "crm",
            "liveperson",
            "chat",
            "sms",
            "ecommerce",
        ):
            return 5
        return 3

    if company_key == normalize_compare(COMPANY_ADERANT):
        if "support" in title_key or jd_mentions(
            job_description,
            "technical support",
            "systems administration",
            "active directory",
            "sql server",
            "windows service",
            "application support",
        ):
            return 3
        return 2

    return 4


def select_experience_bullets_for_two_page_resume(
    document_xml: Path,
    job_description: str,
    emphasis: TailoringEmphasis | None = None,
) -> int:
    tree = ET.parse(document_xml)
    root = tree.getroot()
    body = root.find(f"{W}body")
    if body is None:
        return 0

    def is_required_section_text(value: str) -> bool:
        return normalize_required_section_name(value) is not None

    children = list(body)
    roles: list[tuple[str, str, list[ET.Element]]] = []
    in_experience = False
    current_title = ""
    current_company = ""
    current_bullets: list[ET.Element] = []
    awaiting_company = False

    def flush_role() -> None:
        nonlocal current_title, current_company, current_bullets
        if current_title and current_company and current_bullets:
            roles.append((current_title, current_company, current_bullets))
        current_title = ""
        current_company = ""
        current_bullets = []

    for child in children:
        if child.tag != f"{W}p":
            continue
        text = re.sub(r"\s+", " ", paragraph_text(child)).strip()
        if not text:
            continue

        normalized_section = normalize_required_section_name(text)
        if normalized_section:
            if in_experience and normalized_section != "Professional Experience":
                flush_role()
            in_experience = normalized_section == "Professional Experience"
            awaiting_company = False
            continue
        if not in_experience:
            continue

        if not is_bullet(child) and is_role_heading(text):
            flush_role()
            current_title = text
            current_company = ""
            current_bullets = []
            awaiting_company = True
            continue
        if awaiting_company and not is_bullet(child) and " | " in text and not is_required_section_text(text):
            current_company = text.split("|", 1)[0].strip()
            awaiting_company = False
            continue
        if current_title and current_company and is_bullet(child):
            current_bullets.append(child)

    if in_experience:
        flush_role()

    removed = 0
    for title, company, bullets in roles:
        budget = role_bullet_budget(company, title, job_description, emphasis)
        minimum_required = min(MIN_FINAL_BULLETS_BY_COMPANY.get(company, 2), len(bullets))
        remaining_count = len(bullets) - max(0, len(bullets) - budget)
        effective_budget = budget
        if remaining_count < minimum_required:
            print(
                f"WARNING: {company} has {remaining_count} bullet(s) after budget trim against a minimum of {minimum_required}; "
                f"validate_resume_integrity will catch this but review role_bullet_budget for {company}.",
                file=sys.stderr,
            )
            effective_budget = minimum_required
        if budget < minimum_required:
            print(
                f"WARNING: {company} role_bullet_budget returned {budget}, below the minimum of {minimum_required}; "
                f"using {minimum_required} for this role so bullet trimming cannot violate resume integrity.",
                file=sys.stderr,
            )
            effective_budget = minimum_required
        if len(bullets) <= effective_budget:
            continue
        for bullet in bullets[effective_budget:]:
            body.remove(bullet)
            removed += 1

    if removed:
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)
    return removed


















def normalize_date_ranges(document_xml: Path) -> int:
    month_pattern = "|".join(MONTHS)
    date_range = re.compile(
        rf"\b({month_pattern})\s+(\d{{4}})\s+to\s+({month_pattern})\s+(\d{{4}})\b",
        re.I,
    )
    typo_fixes = {
        "Janurary": "January",
        "Feburary": "February",
        "Novemeber": "November",
        "Septemeber": "September",
    }

    tree = ET.parse(document_xml)
    changed = 0
    for text_node in tree.getroot().findall(f".//{W}t"):
        original = text_node.text or ""
        updated = original
        for typo, correction in typo_fixes.items():
            updated = re.sub(typo, correction, updated, flags=re.I)
        updated = date_range.sub(lambda match: f"{match.group(1)} {match.group(2)} - {match.group(3)} {match.group(4)}", updated)
        if updated != original:
            text_node.text = updated
            changed += 1
    if changed:
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)
    return changed
























def normalize_supported_acronyms(document_xml: Path) -> int:
    tree = ET.parse(document_xml)
    changed = 0
    for text_node in tree.getroot().findall(f".//{W}t"):
        if not text_node.text:
            continue
        original = text_node.text
        updated = original
        for plain, replacement in ACRONYM_TEXT_REPLACEMENTS.items():
            updated = re.sub(rf"\b{re.escape(plain)}\b", replacement, updated, flags=re.I)
        if updated != original:
            text_node.text = updated
            changed += 1
    if changed:
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)
    return changed


























def restore_mandatory_reorg_summaries(document_xml: Path) -> int:
    tree = ET.parse(document_xml)
    paragraphs = tree.getroot().findall(f".//{W}p")
    changed = 0

    for index, paragraph in enumerate(paragraphs):
        company_line = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        company_name = company_line.split("|", 1)[0].strip()
        if company_name not in MANDATORY_REORG_COMPANIES:
            continue

        for summary in paragraphs[index + 1 :]:
            summary_text = re.sub(r"\s+", " ", paragraph_text(summary)).strip()
            if not summary_text:
                continue
            if is_bullet(summary) or is_role_heading(summary_text):
                break
            if is_company_context_paragraph(company_name, summary_text):
                continue
            updated = preserve_reorg_sentence_at_end(summary_text, summary_text)
            if not contains_reorg_fact(summary_text):
                updated = append_reorg_sentence(summary_text)
            if updated != summary_text:
                set_paragraph_text(summary, updated)
                changed += 1
            break

    if changed:
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)
    return changed


def contains_search_term(text: str, term: str) -> bool:
    normalized = text.lower()
    parts = term.lower().strip().split()
    if not parts:
        return False

    last = parts[-1]
    variants = [" ".join(parts)]
    if last.endswith("ies") and len(last) > 4:
        variants.append(" ".join(parts[:-1] + [last[:-3] + "y"]))
    elif last.endswith("s") and len(last) > 4 and not last.endswith(("ss", "ics")):
        variants.append(" ".join(parts[:-1] + [last[:-1]]))
    elif not last.endswith("s") and not last.endswith("ing"):
        variants.append(" ".join(parts[:-1] + [last + "s"]))

    return any(
        re.search(rf"(?<![a-z0-9]){re.escape(variant)}(?![a-z0-9])", normalized) is not None
        for variant in dict.fromkeys(variants)
    )



















def effective_lane_key(role_title: str, job_description: str, profile: JobProblemProfile) -> str:
    role_lower = role_title.lower()
    role_and_jd = f"{role_title}\n{job_description}".lower()
    change_signals = (
        r"\b(change enablement|change management|change adoption|organiz(?:ation|ational) development|"
        r"org development|organiz(?:ation|ational) design|leadership development|team effectiveness|"
        r"workforce transformation)\b"
    )
    strategy_consulting_signals = (
        r"\b(strategy|transformation|recommendations?|business case|gap analysis|root cause|"
        r"process flows?|standard operating procedures)\b"
    )

    if re.search(r"\b(strategy|transformation|operating model)\b", role_lower):
        return "corporate_strategy"
    if profile.primary_lane == "implementation_delivery" and (
        re.search(r"\b(project manager|program manager|implementation|go-live|migration|scrum)\b", role_lower)
        or re.search(r"\b(sdlc|software development lifecycle|workstreams?|delivery|implementation|uat|training|rollout|milestones|risk registers?)\b", role_and_jd)
    ):
        return "implementation_delivery"
    if re.search(change_signals, role_and_jd):
        return "change_enablement"
    if (
        profile.primary_lane == "corporate_strategy"
        and re.search(r"\b(consultant|consulting|advisory|advisor)\b", role_lower)
        and re.search(strategy_consulting_signals, role_and_jd)
        and not re.search(change_signals, role_and_jd)
    ):
        return "corporate_strategy"
    if re.search(r"\b(data analyst|analytics analyst|business analyst|reporting analyst|analytics|reporting|insights|measurement)\b", role_lower):
        return "analytics_operations"
    if re.search(r"\b(process engineer|process improvement|continuous improvement|lean six sigma|root cause)\b", role_lower):
        return "process_improvement"
    if re.search(r"\b(implementation|implementation project manager|technical implementation manager|go-live|configuration|migration)\b", role_lower):
        return "implementation_delivery"
    if re.search(r"\b(customer success|partner success|csm|renewal|retention manager|account manager)\b", role_lower):
        return "customer_success"
    support_title_signal = re.search(
        r"\b(customer experience|customer support|support specialist|support agent|member services|member support|cx)\b",
        role_lower,
    )
    support_jd_signal = re.search(
        r"\b(customer experience|customer support|support specialist|support agent|member services|member support|cx)\b",
        role_and_jd,
    )
    support_pain_signal = re.search(
        r"\b(escalation|retention|billing|membership|zendesk|phone|email|vip|human touch)\b",
        role_and_jd,
    )
    stronger_non_cs_title_signal = re.search(
        r"\b(implementation|consultant|consulting|project manager|program manager|analyst|strategy|transformation|"
        r"change|process|data|reporting|solution|solutions|architect|product owner|scrum master)\b",
        role_lower,
    )
    if support_title_signal:
        return "customer_success"
    if (
        support_jd_signal
        and support_pain_signal
        and profile.primary_lane == "customer_success"
        and not stronger_non_cs_title_signal
    ):
        return "customer_success"
    if re.search(r"\b(solutions engineer|solution engineer|solution consultant|solution consulting|pre-sales|presales|sales engineer)\b", role_lower):
        return "presales_solution"

    if profile.primary_lane == "analytics_operations":
        return profile.primary_lane
    if profile.primary_lane == "implementation_delivery" and re.search(
        r"\b(implementation|integration|integrations|data migration|data migrations|migration|migrations|requirements|testing|delivery|go-live|api|apis)\b",
        role_and_jd,
    ):
        return profile.primary_lane
    if re.search(r"\b(solutions engineer|solution engineer|solution consultant|solution consulting|pre-sales|presales|demo)\b", role_and_jd):
        return "presales_solution"
    if re.search(r"\b(process improvement|process engineer|lean six sigma|root cause|standard work|cost[- ]benefit|service quality|workflow redesign|continuous improvement)\b", role_and_jd):
        return "process_improvement"
    if re.search(r"\b(customer success|csm|account manager|renewal|expansion)\b", role_and_jd):
        return "customer_success"
    if re.search(r"\b(change adoption|change management|change enablement|ways of working)\b", role_and_jd):
        return "change_enablement"
    return profile.primary_lane


def adjust_profile_for_lane(profile: JobProblemProfile, lane_key: str) -> JobProblemProfile:
    if lane_key == profile.primary_lane:
        return profile
    lane = next((item for item in TARGETING_LANES if item["key"] == lane_key), None)
    if lane is None and lane_key == str(CORPORATE_STRATEGY_PROFILE["key"]):
        lane = CORPORATE_STRATEGY_PROFILE
    if not lane:
        return profile
    return replace(
        profile,
        primary_lane=str(lane["key"]),
        lane_label=str(lane["label"]),
        core_problem=str(lane["problem"]),
        audience=str(lane["audience"]),
        outcomes=tuple(str(item) for item in lane["outcomes"]),
    )


def has_outcome_or_metric(text: str) -> bool:
    return OUTCOME_SIGNAL_RE.search(text) is not None or SCOPE_PROOF_RE.search(text) is not None


def starts_with_duty_only_language(text: str) -> bool:
    normalized = text.strip().lower()
    if normalized.startswith("responsible for"):
        return True
    first_word = re.split(r"\W+", normalized, maxsplit=1)[0]
    return first_word in DUTY_ONLY_OPENERS and not has_outcome_or_metric(text)


def contains_cliche(text: str) -> bool:
    return any(re.search(pattern, text, flags=re.I) for pattern in CLICHE_PATTERNS)


def contains_subjective_job_ad_claim(text: str) -> bool:
    return any(re.search(pattern, text, flags=re.I) for pattern in SUBJECTIVE_JOB_AD_PATTERNS)


def unsupported_platform_action_claims(text: str) -> list[str]:
    unsupported_patterns = (
        ("Salesforce migration", r"\bSalesforce(?:\s+CRM)?\s+(?:data\s+)?migration\b|\bmigration\s+(?:to|from|in|within)\s+Salesforce\b"),
        ("CRM migration", r"\bCRM\s+(?:data\s+)?migration\b|\bmigration\s+(?:to|from|in|within)\s+(?:the\s+)?CRM\b"),
        ("LivePerson migration", r"\bLivePerson(?:\s+LiveEngage)?\s+(?:data\s+)?migration\b|\bmigration\s+(?:to|from|in|within)\s+LivePerson\b"),
    )
    return [label for label, pattern in unsupported_patterns if re.search(pattern, text, re.I)]


def assert_no_unsupported_platform_action_claims(text: str, context: str) -> None:
    claims = unsupported_platform_action_claims(text)
    if claims:
        fail(
            f"{context} contains unsupported blended platform/action claim(s): "
            + ", ".join(dict.fromkeys(claims))
        )


def subjective_job_ad_claims_without_proof(text: str) -> list[str]:
    flagged: list[str] = []
    for paragraph in re.split(r"[\r\n]+", text):
        cleaned = re.sub(r"\s+", " ", paragraph).strip()
        if not cleaned:
            continue
        if not contains_subjective_job_ad_claim(cleaned):
            continue
        if has_outcome_or_metric(cleaned) or objective_context_signal_count(cleaned) >= 2:
            continue
        flagged.append(cleaned)
    return flagged


def objective_context_signal_count(text: str) -> int:
    return sum(1 for pattern in OBJECTIVE_CONTEXT_PATTERNS if re.search(pattern, text, flags=re.I))


def contains_ai_writing_word(text: str) -> bool:
    return any(re.search(pattern, text, flags=re.I) for pattern in AI_WRITING_PATTERNS)


def naturalness_score(text: str) -> dict[str, object]:
    """Score how templated or AI-signaled a text sample feels."""
    issues: list[str] = []
    score = 0

    ai_hits = sum(1 for pattern in AI_WRITING_PATTERNS if re.search(pattern, text, re.I))
    if ai_hits > 0:
        score += ai_hits * 3
        issues.append(f"{ai_hits} AI-writing word(s) detected")

    pipe_count = text.count("|")
    if pipe_count > 6:
        score += (pipe_count - 6) * 2
        issues.append(f"Pipe-list density: {pipe_count} pipes")

    specificity = re.findall(r"\d|%|\$|\b\d+\+\b", text)
    score -= min(len(specificity) * 2, 10)

    adverb_openers = (
        "successfully",
        "effectively",
        "proactively",
        "strategically",
        "efficiently",
        "seamlessly",
        "consistently",
    )
    for adverb in adverb_openers:
        if re.search(rf"(?:^|(?<=\. )){adverb}\b", text, re.I):
            score += 2
            issues.append(f"Adverb opener: '{adverb}'")

    return {"score": max(0, score), "issues": issues}


def contains_prompt_leak(text: str) -> bool:
    return any(re.search(pattern, text, flags=re.I) for pattern in PROMPT_LEAK_PATTERNS)


def contains_first_person(text: str) -> bool:
    normalized = text.replace("’", "'")
    patterns: list[str] = []
    for pattern in FIRST_PERSON_PATTERNS:
        if pattern == r"\bI\b":
            patterns.extend((r"\bI\s+[A-Za-z]", r"\bI'(?:m|ve|d|ll)\b"))
            continue
        patterns.append(pattern)
    return any(re.search(pattern, normalized) for pattern in patterns)


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










def normalize_summary_experience_case(document_xml: Path) -> int:
    tree = ET.parse(document_xml)
    paragraphs = tree.getroot().findall(f".//{W}p")
    in_target = False
    changed = 0

    for paragraph in paragraphs:
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        if text == "Professional Summary":
            in_target = True
            continue
        if text == "Education":
            in_target = False
            continue
        if not in_target or not text:
            continue
        if normalize_required_section_name(text) or is_role_heading(text):
            continue

        updated = text
        for original, replacement in EXPERIENCE_CASE_REPLACEMENTS.items():
            updated = re.sub(rf"\b{re.escape(original)}\b", replacement, updated)
        if updated != text:
            set_paragraph_text(paragraph, updated)
            changed += 1

    if changed:
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)
    return changed
















































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


def replace_cutover_terms(text: str) -> str:
    updated = text
    for pattern, replacement in CUTOVER_REPLACEMENTS:
        updated = re.sub(pattern, replacement, updated, flags=re.I)
    return updated


def limit_cutover_mentions(document_xml: Path, max_mentions: int = 1) -> int:
    tree = ET.parse(document_xml)
    changed = 0
    seen = 0

    for paragraph in tree.getroot().findall(f".//{W}p"):
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        if not text or not re.search(r"\bcutover\b", text, re.I):
            continue

        if seen >= max_mentions:
            updated = replace_cutover_terms(text)
        else:
            match = re.search(r"\bcutover\b", text, re.I)
            if match is None:
                continue
            seen += 1
            before = text[: match.end()]
            after = text[match.end() :]
            updated = before + replace_cutover_terms(after)

        if updated != text:
            set_paragraph_text(paragraph, updated)
            changed += 1

    if changed:
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)
    return changed


def normalize_role_bullet_endings(document_xml: Path) -> int:
    """Apply one punctuation convention to every visible resume bullet."""

    tree = ET.parse(document_xml)
    changed = 0
    for paragraph in tree.getroot().findall(f".//{W}p"):
        if not is_bullet(paragraph):
            continue
        current = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        normalized = normalize_bullet_ending(current)
        if normalized and normalized != current:
            set_paragraph_text(paragraph, normalized)
            changed += 1
    if changed:
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)
    return changed


def assert_substitution_safety(text: str, label: str = "generated output") -> None:
    issues = substitution_safety_issues(text)
    if issues:
        fail(f"{label} contains unsafe generic-term substitution: {', '.join(issues)}")


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














def assert_single_spacing(document_xml: Path) -> None:
    tree = ET.parse(document_xml)
    problems = []
    for index, paragraph in enumerate(tree.getroot().findall(f".//{W}p"), start=1):
        spacing = paragraph.find(f"{W}pPr/{W}spacing")
        if spacing is None:
            problems.append(f"paragraph {index} has no explicit spacing")
            continue
        line = spacing.get(w_attr("line"))
        line_rule = spacing.get(w_attr("lineRule"))
        if line != SINGLE_LINE_SPACING or line_rule != "auto":
            problems.append(f"paragraph {index} has non-single spacing")
    if problems:
        fail("single-spacing validation failed:\n  " + "\n  ".join(problems))


def assert_date_range_format(snapshot: ResumeSnapshot) -> None:
    month_pattern = "|".join(MONTHS)
    if re.search(rf"\b(?:{month_pattern})\s+\d{{4}}\s+to\s+(?:{month_pattern})\s+\d{{4}}\b", snapshot.full_text, re.I):
        fail('date range validation failed: use "Month YYYY - Month YYYY", not "Month YYYY to Month YYYY"')


def professional_summary_text(document_xml: Path) -> str | None:
    paragraphs = paragraph_infos(document_xml)
    start = section_index(paragraphs, "Professional Summary")
    end = section_index(paragraphs, "Professional Experience")
    if start is None or end is None or end <= start:
        return None
    summary_parts = [paragraph.text for paragraph in paragraphs[start + 1 : end] if paragraph.text]
    return " ".join(summary_parts).strip()


def resume_variable_snapshot(document_xml: Path) -> ResumeVariationSnapshot:
    paragraphs = paragraph_infos(document_xml)
    summary_start = section_index(paragraphs, "Professional Summary")
    experience_start = section_index(paragraphs, "Professional Experience")
    education_start = section_index(paragraphs, "Education")

    header_paragraphs = [paragraph.text for paragraph in paragraphs[: summary_start or 0] if paragraph.text]
    headline = ""
    if len(header_paragraphs) >= 3:
        headline = header_paragraphs[1]
    elif len(header_paragraphs) >= 2:
        headline = header_paragraphs[-1]

    role_summaries: list[str] = []
    bullets: list[str] = []
    if experience_start is not None and education_start is not None and education_start > experience_start:
        current_company = ""
        for paragraph in paragraphs[experience_start + 1 : education_start]:
            text = paragraph.text
            if not text:
                continue
            if not paragraph.is_bullet and is_role_heading(text):
                current_company = ""
                continue
            if not paragraph.is_bullet and " | " in text:
                current_company = text.split("|", 1)[0].strip()
                continue
            if paragraph.is_bullet:
                bullets.append(text)
                continue
            if current_company:
                if is_company_context_paragraph(current_company, text):
                    continue
                role_summaries.append(text)
                current_company = ""

    return ResumeVariationSnapshot(
        headline=headline,
        summary=professional_summary_text(document_xml) or "",
        role_summaries=tuple(role_summaries),
        bullets=tuple(bullets),
        competency_labels=tuple(sorted(extract_competency_labels(paragraphs))),
        competency_items=tuple(sorted(extract_competency_items(paragraphs))),
    )


def resume_variable_snapshot_from_docx(docx_path: Path) -> ResumeVariationSnapshot:
    with tempfile.TemporaryDirectory(prefix="resume_overlap_") as temp_dir:
        unpack_dir = Path(temp_dir)
        unpack_docx(docx_path, unpack_dir)
        return resume_variable_snapshot(unpack_dir / "word" / "document.xml")


def _resume_overlap_ratio(left: str, right: str) -> float:
    left_key = normalize_compare(left)
    right_key = normalize_compare(right)
    if not left_key and not right_key:
        return 1.0
    if not left_key or not right_key:
        return 0.0
    return difflib.SequenceMatcher(None, left_key, right_key).ratio()


def resume_variable_overlap_score(current: ResumeVariationSnapshot, other: ResumeVariationSnapshot) -> float:
    weighted_sections = (
        (_resume_overlap_ratio(current.headline, other.headline), 0.10),
        (_resume_overlap_ratio(current.summary, other.summary), 0.24),
        (_resume_overlap_ratio("\n".join(current.role_summaries), "\n".join(other.role_summaries)), 0.24),
        (_resume_overlap_ratio("\n".join(current.bullets), "\n".join(other.bullets)), 0.32),
        (
            _resume_overlap_ratio(
                "\n".join(current.competency_labels + current.competency_items),
                "\n".join(other.competency_labels + other.competency_items),
            ),
            0.10,
        ),
    )
    return sum(score * weight for score, weight in weighted_sections)


def output_resume_company_name(path: Path) -> str:
    prefix = "Christian Estrada - "
    suffix = " Resume"
    stem = path.stem
    if not stem.startswith(prefix):
        return ""
    remainder = stem[len(prefix) :]
    if remainder.endswith(suffix):
        remainder = remainder[: -len(suffix)]
    status_suffixes = (" BRIDGE", " FAIL", " POOR")
    for status_suffix in status_suffixes:
        if remainder.endswith(status_suffix):
            remainder = remainder[: -len(status_suffix)]
            break
    parts = [part.strip() for part in remainder.split(" - ") if part.strip()]
    return parts[0] if len(parts) >= 2 else ""


def same_company_resume_outputs(output_dir: Path, company_name: str) -> list[Path]:
    if not output_dir.exists():
        return []

    target_company = normalize_compare(company_name)
    if not target_company:
        return []

    matches: list[Path] = []
    for candidate in output_dir.glob("Christian Estrada - *Resume.docx"):
        company = normalize_compare(output_resume_company_name(candidate))
        if not company:
            continue
        if company == target_company or company in target_company or target_company in company:
            matches.append(candidate)
    matches.sort(key=lambda path: (-path.stat().st_mtime, path.name.lower()))
    return matches[:SAME_COMPANY_OUTPUT_LOOKBACK]


def highest_same_company_overlap(
    current: ResumeVariationSnapshot,
    company_name: str,
    output_dir: Path,
) -> tuple[float, Path | None]:
    best_score = 0.0
    best_match: Path | None = None
    for candidate in same_company_resume_outputs(output_dir, company_name):
        try:
            candidate_snapshot = resume_variable_snapshot_from_docx(candidate)
        except Exception:  # noqa: BLE001
            continue
        overlap = resume_variable_overlap_score(current, candidate_snapshot)
        if overlap > best_score:
            best_score = overlap
            best_match = candidate
    return best_score, best_match






def summary_sentences(summary: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", summary.strip()) if part.strip()]


def resume_text_for_non_erp_audit(document_xml: Path) -> str:
    paragraphs = paragraph_infos(document_xml)
    summary_start = section_index(paragraphs, "Professional Summary")
    experience_start = section_index(paragraphs, "Professional Experience")

    audit_segments: list[str] = []
    if summary_start is not None and experience_start is not None and experience_start > summary_start:
        audit_segments.extend(
            paragraph.text
            for paragraph in paragraphs[summary_start + 1 : experience_start]
            if paragraph.text
        )
    return "\n".join(audit_segments)


def assert_professional_summary_length(document_xml: Path) -> None:
    summary = professional_summary_text(document_xml)
    if summary is None:
        fail("Professional Summary text could not be located")
    words = re.findall(r"\b[\w+.#'-]+\b", summary)
    if len(words) < PROFESSIONAL_SUMMARY_MIN_WORDS:
        fail(
            f"Professional Summary is too short: "
            f"{len(words)} words vs {PROFESSIONAL_SUMMARY_MIN_WORDS} minimum"
        )
    if len(words) > PROFESSIONAL_SUMMARY_MAX_WORDS:
        fail(
            f"Professional Summary is too long: "
            f"{len(words)} words vs {PROFESSIONAL_SUMMARY_MAX_WORDS} maximum"
        )
    if len(re.findall(r"\berp\b", summary, flags=re.I)) > 2:
        fail("Professional Summary uses ERP more than twice; use enterprise systems, software, or systems migration instead")


def assert_professional_summary_structure(document_xml: Path) -> None:
    summary = professional_summary_text(document_xml)
    if summary is None:
        fail("Professional Summary text could not be located")
    sentences = summary_sentences(summary)
    if len(sentences) != 3:
        fail(
            f"Professional Summary must use exactly 3 recruiter-friendly sentences; found {len(sentences)}: {summary}"
        )
    if summary.count(";") > 1:
        fail(
            f"Professional Summary has too many semicolons ({summary.count(';')}); "
            "use commas and and instead of semicolon lists"
        )
    if contains_prompt_leak(summary):
        fail("Professional Summary contains prompt-like tailoring language")
    opening = sentences[0]
    comma_items = [item.strip() for item in opening.split(",") if item.strip()]
    if len(comma_items) > 4:
        fail(
            "Professional Summary opening sentence has more than four comma-separated segments: "
            f"{opening}"
        )
    for sentence in sentences[1:]:
        if sentence.count(";") > 0:
            fail(f"Professional Summary proof or close sentences must not use semicolons: {sentence}")
    if any(sentence.startswith("That") for sentence in sentences):
        fail("Professional Summary sentences must not start with That")


def assert_core_competency_capitalization(document_xml: Path) -> None:
    paragraphs = paragraph_infos(document_xml)
    start = section_index(paragraphs, SKILLS_SECTION_HEADING)
    end = section_index(paragraphs, "Professional Development")
    if start is None or end is None or end <= start:
        return
    problems: list[str] = []
    for paragraph in paragraphs[start + 1 : end]:
        text = paragraph.text
        if ":" in text:
            text = text.split(":", 1)[1]
        for item in split_items(text):
            for word in re.findall(r"[A-Za-z][A-Za-z0-9]*", item):
                if word.lower() == "and":
                    continue
                if word.lower() == "based" and re.search(r"\b(?:NLP|LLM)-based\b", item):
                    continue
                if not (word[:1].isupper() or word.isupper()):
                    problems.append(item)
                    break
    if problems:
        fail("Skills section capitalization validation failed:\n  " + "\n  ".join(problems[:10]))


def bool_prop_enabled(r_pr: ET.Element | None, tag: str) -> bool | None:
    if r_pr is None:
        return None
    prop = r_pr.find(tag)
    if prop is None:
        return None
    value = prop.get(w_attr("val"))
    return value not in {"0", "false", "False", "off"}


def assert_core_competency_run_format(document_xml: Path) -> None:
    tree = ET.parse(document_xml)
    paragraphs = tree.getroot().findall(f".//{W}p")
    in_core = False
    problems: list[str] = []

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

        runs = paragraph.findall(f"{W}r")
        if len(runs) < 2:
            problems.append(f"Skills line was not split into label/items runs: {text}")
            continue

        label_r_pr = runs[0].find(f"{W}rPr")
        if bool_prop_enabled(label_r_pr, f"{W}b") is not False or bool_prop_enabled(label_r_pr, f"{W}i") is not True:
            problems.append(f"category label is not italic-only: {text.split(':', 1)[0]}")

        for run in runs[1:]:
            r_pr = run.find(f"{W}rPr")
            if bool_prop_enabled(r_pr, f"{W}b") is not False or bool_prop_enabled(r_pr, f"{W}i") is not False:
                problems.append(f"competency item run is not regular text: {text}")
                break

    if problems:
        fail("Skills section formatting validation failed:\n  " + "\n  ".join(problems[:10]))


def assert_experience_emphasis_format(document_xml: Path) -> None:
    tree = ET.parse(document_xml)
    paragraphs = tree.getroot().findall(f".//{W}p")
    in_experience = False
    next_company_line = False
    next_summary_line = False
    summary_company = ""
    month_pattern = "|".join(MONTHS)
    problems: list[str] = []

    def visible_runs(paragraph: ET.Element) -> list[tuple[str, ET.Element | None]]:
        runs: list[tuple[str, ET.Element | None]] = []
        for run in paragraph.findall(f"{W}r"):
            run_text = re.sub(r"\s+", " ", paragraph_text(run)).strip()
            if run_text:
                runs.append((run_text, run.find(f"{W}rPr")))
        return runs

    def run_is_italic(r_pr: ET.Element | None) -> bool:
        return any(
            value is True
            for value in (
                bool_prop_enabled(r_pr, f"{W}i"),
                bool_prop_enabled(r_pr, f"{W}iCs"),
            )
        )

    for paragraph in paragraphs:
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        if not text:
            continue

        section = normalize_required_section_name(text)
        if section:
            in_experience = section == "Professional Experience"
            next_company_line = False
            next_summary_line = False
            summary_company = ""
            continue
        if text == "Education":
            break
        if not in_experience:
            continue

        runs = visible_runs(paragraph)
        if is_role_heading(text):
            for run_text, r_pr in runs:
                if re.search(rf"(?:{month_pattern})\s+\d{{4}}|present", run_text, re.I):
                    continue
                if run_is_italic(r_pr):
                    problems.append(f"role heading should not be italic: {text}")
                    break
            next_company_line = True
            next_summary_line = False
            summary_company = ""
            continue

        if next_company_line:
            if any(run_is_italic(r_pr) for _, r_pr in runs):
                problems.append(f"company line should not be italic: {text}")
            summary_company = text.split("|", 1)[0].strip()
            next_company_line = False
            next_summary_line = True
            continue

        if next_summary_line:
            if is_bullet(paragraph):
                next_summary_line = False
                summary_company = ""
                continue
            is_company_context = bool(summary_company and is_company_context_paragraph(summary_company, text))
            if is_company_context:
                if not any(run_is_italic(r_pr) for _, r_pr in runs):
                    problems.append(f"company context line should remain italic: {text}")
                continue
            if any(run_is_italic(r_pr) for _, r_pr in runs):
                problems.append(f"role summary should not be italic: {text}")
            next_summary_line = False
            summary_company = ""

    if problems:
        fail("Experience formatting validation failed:\n  " + "\n  ".join(problems[:10]))


def assert_document_font(document_xml: Path, font_name: str = RESUME_FONT) -> None:
    tree = ET.parse(document_xml)
    problems: list[str] = []
    for index, run in enumerate(tree.getroot().findall(f".//{W}r"), start=1):
        text = paragraph_text(run).strip()
        if not text:
            continue
        fonts = run.find(f"{W}rPr/{W}rFonts")
        if fonts is None:
            problems.append(f"run {index} has no explicit font")
            continue
        for attr in ("ascii", "hAnsi"):
            if fonts.get(w_attr(attr)) != font_name:
                problems.append(f"run {index} is not {font_name}: {text[:40]}")
                break
    if problems:
        fail("font validation failed:\n  " + "\n  ".join(problems[:10]))


def assert_resume_language_rules(document_xml: Path, job_description: str = "") -> None:
    text = "\n".join(paragraph.text for paragraph in paragraph_infos(document_xml) if paragraph.text)
    problems: list[str] = []
    if "--" in text:
        problems.append("visible resume text contains double dashes")
    if contains_first_person(text):
        problems.append("visible resume text contains first-person pronouns")
    if contains_ai_writing_word(text):
        problems.append("visible resume text contains banned AI-writing words")
    if contains_prompt_leak(text):
        problems.append("visible resume text contains prompt-like tailoring language")
    if contains_cliche(text):
        problems.append("visible resume text contains generic cliché language")
    if re.search(r"\ba pattern that\b", text, re.I):
        problems.append("visible resume text contains forward-looking meta-commentary ('a pattern that')")
    cutover_count = len(re.findall(r"\bcutover\b", text, re.I))
    if cutover_count > 1:
        problems.append(f"visible resume text repeats cutover {cutover_count} times; limit to one mention")
    unsupported_claims = unsupported_platform_action_claims(text)
    if unsupported_claims:
        problems.append(
            "visible resume text contains unsupported blended platform/action claim(s): "
            + ", ".join(dict.fromkeys(unsupported_claims))
        )
    unproved_subjective_claims = subjective_job_ad_claims_without_proof(text)
    if unproved_subjective_claims:
        examples = "; ".join(claim[:120] for claim in unproved_subjective_claims[:3])
        problems.append("visible resume text contains subjective job-ad claim language without objective proof: " + examples)
    if problems:
        fail("resume language validation failed:\n  " + "\n  ".join(problems))


def role_top_bullet_texts(document_xml: Path, role_titles: tuple[str, ...], limit: int = 3) -> list[str]:
    paragraphs = paragraph_infos(document_xml)
    texts: list[str] = []
    active = False
    collected = 0
    normalized_titles = {normalize_compare(title) for title in role_titles}
    for paragraph in paragraphs:
        if paragraph.text.startswith(role_titles) or normalize_compare(normalize_title(paragraph.text)) in normalized_titles:
            active = True
            collected = 0
            continue
        if active and is_role_heading(paragraph.text):
            active = False
        if active and paragraph.is_bullet:
            texts.append(paragraph.text)
            collected += 1
            if collected >= limit:
                active = False
    return texts


def experience_bullet_texts(document_xml: Path) -> list[str]:
    paragraphs = paragraph_infos(document_xml)
    start = section_index(paragraphs, "Professional Experience")
    end = section_index(paragraphs, "Education")
    if start is None or end is None or end <= start:
        return []
    return [paragraph.text for paragraph in paragraphs[start + 1 : end] if paragraph.is_bullet]


def experience_bullet_texts_from_text(resume_text: str) -> list[str]:
    lines = [re.sub(r"\s+", " ", line).strip() for line in resume_text.splitlines() if line.strip()]
    bullets: list[str] = []
    in_experience = False
    for line in lines:
        normalized = line.lower()
        if normalized == "professional experience":
            in_experience = True
            continue
        if normalized == "education":
            break
        if not in_experience:
            continue
        if normalize_required_section_name(line):
            continue
        if is_role_heading(line):
            continue
        if " | " in line and not re.search(r"\d", line):
            continue
        if len(line.split()) < 5:
            continue
        bullets.append(line)
    return bullets


def section_text_from_visible_text(resume_text: str, start_label: str, end_label: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in resume_text.splitlines() if line.strip()]
    collected: list[str] = []
    in_section = False
    for line in lines:
        if section_matches(line, start_label):
            in_section = True
            continue
        if in_section and section_matches(line, end_label):
            break
        if in_section:
            collected.append(line)
    return " ".join(collected).strip()


def professional_summary_text_from_text(resume_text: str) -> str:
    return section_text_from_visible_text(resume_text, "Professional Summary", "Professional Experience")


def core_competencies_text_from_text(resume_text: str) -> str:
    return section_text_from_visible_text(resume_text, SKILLS_SECTION_HEADING, "Professional Development")


def keyword_occurrence_count(text: str, keyword: str) -> int:
    normalized = keyword.strip()
    if not normalized:
        return 0
    if " " in normalized:
        return len(re.findall(re.escape(normalized), text, flags=re.I))
    return len(re.findall(rf"\b{re.escape(normalized)}\b", text, flags=re.I))


def keyword_placement_audit(job_description: str, resume_text: str, limit: int = 5) -> dict[str, object]:
    keywords = audit_keywords(job_description)
    summary = professional_summary_text_from_text(resume_text)
    top_bullets = experience_bullet_texts_from_text(resume_text)[:5]
    core_text = core_competencies_text_from_text(resume_text)
    ranked_keywords = sorted(
        (
            keyword
            for keyword in keywords
            if len(keyword.strip()) >= 3 and not is_generic_soft_keyword(keyword)
        ),
        key=lambda keyword: audit_keyword_sort_key(job_description, keyword),
        reverse=True,
    )

    gaps: list[dict[str, object]] = []
    for keyword in ranked_keywords:
        overall_hit = contains_search_term(resume_text, keyword)
        summary_hit = contains_search_term(summary, keyword)
        top_bullet_hit = any(contains_search_term(bullet, keyword) for bullet in top_bullets)
        core_hit = contains_search_term(core_text, keyword)
        if not overall_hit:
            gaps.append(
                {
                    "keyword": keyword,
                    "issue": "missing from the resume",
                    "priority": 3,
                    "jd_hits": keyword_occurrence_count(job_description, keyword),
                }
            )
        elif core_hit and not summary_hit and not top_bullet_hit:
            gaps.append(
                {
                    "keyword": keyword,
                    "issue": "buried in Skills only; move it into the summary or an early bullet",
                    "priority": 2,
                    "jd_hits": keyword_occurrence_count(job_description, keyword),
                }
            )
        elif not summary_hit and not top_bullet_hit:
            gaps.append(
                {
                    "keyword": keyword,
                    "issue": "not visible in the summary or early bullets",
                    "priority": 1,
                    "jd_hits": keyword_occurrence_count(job_description, keyword),
                }
            )

    gaps.sort(
        key=lambda gap: (
            int(gap.get("priority", 0)),
            *audit_keyword_sort_key(job_description, str(gap.get("keyword", ""))),
        ),
        reverse=True,
    )
    return {
        "gaps": gaps[:limit],
        "summary_text": summary,
        "top_bullets": top_bullets,
        "core_text": core_text,
    }


UNSUPPORTED_FINANCE_GAP_RE = re.compile(
    r"\b(?:budget|budgets|budgeting|eac|etc|earned value|forecast ownership|financial ownership|p&l|profit and loss)\b",
    re.I,
)
ROLE_DEFINING_FINANCE_TERMS = (
    "budget",
    "EAC",
    "ETC",
    "earned value",
    "financial forecasting",
    "financial ownership",
    "P&L",
)


def finance_ownership_gap(keyword: str) -> bool:
    return bool(UNSUPPORTED_FINANCE_GAP_RE.search(keyword))


def role_defining_finance_requirement(job_description: str) -> bool:
    strong_terms = (
        "project financials",
        "budget management",
        "budget ownership",
        "monthly cost projections",
        "cost projections",
        "financial forecasting",
        "forecast ownership",
        "financial ownership",
        "estimate at completion",
        "estimate to complete",
        "earned value",
        "EAC",
        "ETC",
        "P&L",
        "profit and loss",
    )
    strong_hits = sum(1 for term in strong_terms if contains_search_term(job_description, term))
    if strong_hits >= 2:
        return True
    return re.search(
        r"\b(?:manage|manages|managed|own|owns|owned|oversee|oversees|overseeing|responsible for)\b[^.\n]{0,80}\b(?:budget|budgets|financials|forecast|forecasting|cost projections?|eac|etc|earned value|p&l)\b",
        job_description,
        re.I,
    ) is not None


HARD_BLOCK_UNSUPPORTED_REQUIREMENTS = {
    *UNSUPPORTED_OWNERSHIP_LABELS,
    "Direct People Leadership",
}


def unsupported_requirement_is_blocker(
    requirement: str,
    job_description: str,
    profile: JobProblemProfile,
) -> bool:
    if requirement in HARD_BLOCK_UNSUPPORTED_REQUIREMENTS:
        return True
    if requirement == "People Manager Enablement":
        return higher_level_private_sector_role(job_description)
    if len(profile.unsupported_requirements) >= 2 and higher_level_private_sector_role(job_description):
        return True
    return False


def role_defining_keyword(keyword: str, job_description: str, profile: JobProblemProfile) -> bool:
    if finance_ownership_gap(keyword):
        return role_defining_finance_requirement(job_description)
    if keyword_occurrence_count(job_description, keyword) >= 2:
        return True
    return any(
        normalize_compare(keyword) == normalize_compare(term)
        or normalize_compare(keyword) in normalize_compare(term)
        or normalize_compare(term) in normalize_compare(keyword)
        for term in explicit_private_sector_terms(profile, job_description)
    )


def classify_keyword_gap_support(keyword: str, source_resume_text: str, profile: JobProblemProfile) -> str:
    if finance_ownership_gap(keyword):
        return "unsupported-do-not-insert"
    if source_resume_text and contains_search_term(source_resume_text, keyword):
        return "supported-direct-unresolved"

    normalized_keyword = normalize_compare(keyword)
    if "delivery" in normalized_keyword and profile.primary_lane in {"implementation_delivery", "corporate_strategy"}:
        return "supported-adjacent"
    if "cross-functional" in normalized_keyword and source_resume_text and any(
        contains_search_term(source_resume_text, term)
        for term in ("stakeholder", "stakeholders", "executive", "workshops", "coordination")
    ):
        return "supported-adjacent"

    keyword_tokens = [
        token
        for token in re.findall(r"[A-Za-z][A-Za-z0-9-]+", keyword)
        if len(token) >= 4 and token.lower() not in {"with", "from", "through", "across", "role", "team"}
    ]
    if source_resume_text and keyword_tokens:
        token_hits = sum(1 for token in keyword_tokens if contains_search_term(source_resume_text, token))
        required_hits = len(keyword_tokens) if len(keyword_tokens) <= 2 else len(keyword_tokens) - 1
        if token_hits >= required_hits:
            return "supported-adjacent"
    adjacent_terms = tuple(profile.adjacent_matches) + tuple(profile.safe_terms) + tuple(profile.direct_matches)
    for term in adjacent_terms:
        normalized_term = normalize_compare(term)
        if not normalized_term:
            continue
        if normalized_keyword == normalized_term or normalized_keyword in normalized_term or normalized_term in normalized_keyword:
            return "supported-adjacent"
    return "unsupported-do-not-insert"


def aggressively_close_supported_keyword_gaps(
    document_xml: Path,
    job_description: str,
    source_resume_text: str,
    *,
    limit: int = 3,
) -> list[str]:
    current_text = visible_text(document_xml)
    placement_report = keyword_placement_audit(job_description, current_text, limit=8)
    profile = job_problem_profile(job_description, source_resume_text or current_text)
    candidates: list[str] = []
    for gap in placement_report.get("gaps", []):
        if not isinstance(gap, dict):
            continue
        keyword = str(gap.get("keyword", "")).strip()
        issue = str(gap.get("issue", "")).strip().lower()
        if not keyword or issue != "missing from the resume":
            continue
        if classify_keyword_gap_support(keyword, source_resume_text, profile) != "supported-direct-unresolved":
            continue
        candidates.append(keyword)
    if not candidates:
        return []
    return add_targeted_core_competencies(document_xml, candidates, job_description, limit=limit)


def resume_readiness_report(
    job_description: str,
    resume_text: str,
    *,
    source_resume_text: str = "",
    audit_status: str = "PASS",
    auto_closed_keywords: tuple[str, ...] = (),
) -> ResumeReadiness:
    profile = job_problem_profile(job_description, resume_text or source_resume_text)
    placement_report = keyword_placement_audit(job_description, resume_text, limit=8)
    auto_closed_normalized = {normalize_compare(keyword) for keyword in auto_closed_keywords if normalize_compare(keyword)}
    unresolved: list[ResumeGap] = []
    auto_closed: list[ResumeGap] = []
    blockers: list[ResumeGap] = []
    seen_labels: set[str] = set()

    for gap in placement_report.get("gaps", []):
        if not isinstance(gap, dict):
            continue
        keyword = str(gap.get("keyword", "")).strip()
        issue = str(gap.get("issue", "")).strip() or "keyword gap remains unresolved"
        if not keyword or normalize_compare(keyword) in seen_labels:
            continue
        normalized_keyword = normalize_compare(keyword)
        if normalized_keyword in auto_closed_normalized:
            gap_obj = ResumeGap(keyword, "gap auto-closed before final audit", "auto_closed", int(gap.get("priority", 0)))
            auto_closed.append(gap_obj)
            seen_labels.add(normalized_keyword)
            continue
        support_level = classify_keyword_gap_support(keyword, source_resume_text, profile)
        blocker = (
            role_defining_keyword(keyword, job_description, profile)
            and support_level == "unsupported-do-not-insert"
        )
        gap_obj = ResumeGap(keyword, issue, support_level, int(gap.get("priority", 0)), blocker)
        unresolved.append(gap_obj)
        if blocker:
            blockers.append(gap_obj)
        seen_labels.add(normalized_keyword)

    for requirement in profile.unsupported_requirements:
        normalized_requirement = normalize_compare(requirement)
        if not normalized_requirement or normalized_requirement in seen_labels:
            continue
        blocker = unsupported_requirement_is_blocker(requirement, job_description, profile)
        gap_obj = ResumeGap(
            requirement,
            "unsupported requirement remains unresolved",
            "unsupported-do-not-insert",
            4,
            blocker,
        )
        unresolved.append(gap_obj)
        if blocker:
            blockers.append(gap_obj)
        seen_labels.add(normalized_requirement)

    for term in ROLE_DEFINING_FINANCE_TERMS:
        normalized_term = normalize_compare(term)
        if not normalized_term or normalized_term in seen_labels:
            continue
        if not contains_search_term(job_description, term):
            continue
        if not role_defining_finance_requirement(job_description):
            continue
        if contains_search_term(source_resume_text or resume_text, term):
            continue
        gap_obj = ResumeGap(
            term,
            "role-defining finance ownership term remains unresolved",
            "unsupported-do-not-insert",
            5,
            True,
        )
        unresolved.append(gap_obj)
        blockers.append(gap_obj)
        seen_labels.add(normalized_term)

    unresolved.sort(key=lambda item: (item.blocker, item.priority, item.label.lower()), reverse=True)
    auto_closed.sort(key=lambda item: (item.priority, item.label.lower()), reverse=True)
    blockers.sort(key=lambda item: (item.priority, item.label.lower()), reverse=True)
    return ResumeReadiness(
        audit_status=audit_status,
        prioritized_unresolved_gaps=tuple(unresolved),
        auto_closed_gaps=tuple(auto_closed),
        hard_blockers=tuple(blockers),
    )


def resume_readiness_for_output(
    job_description: str,
    resume_docx: Path,
    *,
    source_resume_text: str = "",
    audit_status: str = "PASS",
) -> ResumeReadiness:
    return resume_readiness_report(
        job_description,
        docx_visible_text_from_path(resume_docx),
        source_resume_text=source_resume_text,
        audit_status=audit_status,
    )


def resume_gap_summary_line(gap: ResumeGap) -> str:
    suffix = f" [{gap.support_level}]" if gap.support_level else ""
    return f"{gap.label}: {gap.issue}{suffix}"


def resume_gap_blocker_message(readiness: ResumeReadiness, *, limit: int = 3) -> str:
    lines = [resume_gap_summary_line(gap) for gap in readiness.hard_blockers[:limit]]
    if not lines:
        return ""
    return "; ".join(lines)


def first_sentence(text: str) -> str:
    match = re.search(r"(.+?[.!?])(?:\s|$)", text.strip())
    return match.group(1).strip() if match else text.strip()


def higher_level_private_sector_role(job_description: str) -> bool:
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


def explicit_private_sector_terms(profile: JobProblemProfile, job_description: str) -> tuple[str, ...]:
    terms: list[str] = []
    if higher_level_private_sector_role(job_description):
        terms.extend(
            [
                "led",
                "owned",
                "executive",
                "director",
                "vp",
                "stakeholder",
                "recommendation",
                "tradeoff",
                "roadmap",
                "decision",
            ]
        )
    if profile.primary_lane == "implementation_delivery" or jd_mentions(
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
    ):
        terms.extend(
            [
                "technical scoping",
                "requirements",
                "integration",
                "data migration",
                "testing",
                "uat",
                "delivery",
                "go-live",
                "solution architecture",
            ]
        )
        if jd_mentions(job_description, "customer delivery", "customer-facing delivery", "client-facing delivery"):
            terms.extend(["customer delivery", "delivery"])
        if jd_mentions(
            job_description,
            "comprehensive training",
            "comprehensive training plans",
            "training plans",
            "train end users",
            "user enablement",
        ):
            terms.extend(["comprehensive training", "training"])
        if jd_mentions(job_description, "process documentation", "document processes", "workflow documentation"):
            terms.append("process documentation")
        if jd_mentions(job_description, "scope management", "contractual scopes"):
            terms.append("scope management")
    elif profile.primary_lane == "presales_solution":
        terms.extend(["discovery", "solution design", "executive", "demo", "recommendation"])
    elif profile.primary_lane == "customer_success":
        terms.extend(["adoption", "renewal", "executive", "risk", "retention"])
    elif profile.primary_lane == "analytics_operations":
        terms.extend(["dashboard", "reporting", "decision", "executive", "analytics"])
        if jd_mentions(job_description, "data management", "data guru", "etl"):
            terms.append("data management")
        if jd_mentions(job_description, "project delivery", "deliverables", "delivery timeliness"):
            terms.append("project delivery")
        if jd_mentions(job_description, "model quality", "validation", "modeling readiness"):
            terms.append("model quality")
        if jd_mentions(job_description, "power bi"):
            terms.append("power bi")
    return tuple(dict.fromkeys(term for term in terms if term))


def visible_term_hits(text: str, terms: tuple[str, ...]) -> int:
    lowered = text.lower()
    return sum(1 for term in terms if term and term.lower() in lowered)


def top_third_ownership_issues(summary: str, top_bullets: list[str]) -> list[str]:
    issues: list[str] = []
    top_text = " ".join([summary, *top_bullets]).strip()
    lowered = top_text.lower()
    if not lowered:
        return issues
    strong_hits = len(TOP_THIRD_STRONG_OWNERSHIP_RE.findall(top_text))
    soft_hits = sum(1 for pattern, _label in TOP_THIRD_OWNERSHIP_SOFTENERS if re.search(pattern, lowered, re.I))
    if strong_hits == 0:
        issues.append(
            "Top-third skim still lacks a clear ownership line; the summary or first bullets should make Christian's role explicit."
        )
    if soft_hits >= 2 and strong_hits <= soft_hits:
        issues.append(
            "Top-third wording still leans too support-oriented; prefer the strongest truthful ownership verb over soft phrases like supported or worked with."
        )
    return issues


def hiring_manager_skim_issues(
    summary: str,
    top_bullets: list[str],
    profile: JobProblemProfile,
    job_description: str = "",
) -> list[str]:
    issues: list[str] = []
    sentences = summary_sentences(summary)
    if len(sentences) != 3:
        issues.append("Professional Summary should use exactly three recruiter-friendly sentences.")
    if summary.count(";") > 1:
        issues.append("Professional Summary uses semicolon-heavy template phrasing; keep to at most one semicolon.")
    if len(sentences) >= 2 and not has_outcome_or_metric(sentences[1]) and (not top_bullets or not has_outcome_or_metric(top_bullets[0])):
        issues.append("Top-third skim does not surface proof fast enough; the second summary sentence or first bullet should carry a metric, scope marker, or clear outcome.")
    if re.search(
        r"Target context:|Strong fit for roles|Experience spans|Background includes|Background spans|The same pattern fits|This background fits|This background is strongest|Recent work has included|Prior work includes",
        summary,
        re.I,
    ):
        issues.append(
            "Professional Summary contains labeled template phrasing instead of natural recruiter prose."
        )
    opening = first_sentence(summary)
    opening_lower = opening.lower()
    if opening_lower.startswith("turns "):
        issues.append("Professional Summary opens with a constructed problem phrase instead of a direct role-fit sentence.")

    role_terms_by_lane = {
        "presales_solution": ("solutions consultant", "solution consulting", "pre-sales", "product demonstrations", "discovery"),
        "customer_success": ("customer success", "adoption", "renewal", "account", "post-go-live"),
        "implementation_delivery": (
            "implementation",
            "project manager",
            "project management",
            "erp",
            "crm",
            "migration",
            "standardization",
            "go-live",
            "configuration",
            "testing",
            "launch",
            "scoping",
            "integration",
            "delivery",
            "customer delivery",
            "process documentation",
            "training",
            "scope management",
            "requirements",
        ),
        "change_enablement": ("change", "adoption", "training", "stakeholder"),
        "analytics_operations": (
            "analytics",
            "reporting",
            "data",
            "process",
            "supply chain",
            "data management",
            "project delivery",
            "model quality",
            "power bi",
            "revenue operations",
            "sales operations",
            "business operations",
            "operations manager",
            "dashboard",
        ),
        "process_improvement": (
            "process improvement",
            "process engineer",
            "lean",
            "six sigma",
            "root cause",
            "workflow",
            "efficiency",
            "continuous improvement",
            "standard work",
            "operational metrics",
        ),
        "corporate_strategy": (
            "consulting",
            "consultant",
            "client",
            "analysis",
            "analyses",
            "strategy",
            "strategic",
            "analyst",
            "recommendations",
            "operating model",
            "transformation",
            "initiative",
            "business case",
            "stakeholder alignment",
            "decision",
        ),
    }
    role_terms = role_terms_by_lane.get(profile.primary_lane, ())
    if not role_terms:
        print(
            f"hiring_manager_skim_issues: no role terms defined for lane '{profile.primary_lane}'; skipping lane-name check.",
            file=sys.stderr,
        )
    elif not any(term in opening_lower for term in role_terms):
        issues.append("Professional Summary opening sentence does not clearly name the target role lane.")

    top_text = " ".join([summary] + top_bullets)
    proof_markers = ("10+", "80+", "150+", "200+", "60+", "$1M+", "five sites")
    if not any(marker.lower() in top_text.lower() for marker in proof_markers):
        issues.append("Top-third skim lacks fast proof of scale, scope, or measurable outcome.")
    if objective_context_signal_count(top_text) < 3:
        issues.append("Top-third skim lacks enough objective business context for a six-second recruiter scan.")
    if subjective_job_ad_claims_without_proof(top_text):
        issues.append("Top-third skim contains subjective job-ad claim language instead of objective evidence.")
    if keyword_hits(top_text, audit_keywords(profile.core_problem)) < 1:
        issues.append("Top-third skim does not clearly echo the role's core business problem.")
    issues.extend(top_third_ownership_issues(summary, top_bullets))
    if job_description:
        explicit_terms = explicit_private_sector_terms(profile, job_description)
        visible_hits = visible_term_hits(top_text, explicit_terms)
        if higher_level_private_sector_role(job_description) and visible_hits < 2:
            issues.append(
                "Higher-level private-sector fit is still too implicit; the summary and first bullets should explicitly show leadership, ownership, executive audience, or decision-making scope."
            )
        elif explicit_terms and visible_hits < (3 if profile.primary_lane == "implementation_delivery" else 2):
            issues.append(
                "Core requirement proof is still too implicit in the top third; the summary and first bullets should name the role's main experience areas directly instead of leaving them inferred."
            )
    return issues


def final_fit_audit(
    document_xml: Path,
    job_description: str,
    *,
    source_resume_text: str = "",
    auto_closed_keywords: tuple[str, ...] = (),
    alignment_grade: str | None = None,
) -> tuple[str, list[str]]:
    keywords = audit_keywords(job_description)
    notes: list[str] = []
    status = "PASS"
    document_text = visible_text(document_xml)
    profile = job_problem_profile(job_description, document_text)
    poor_requirements = poor_fit_requirements(job_description, document_text)
    hard_fail_reasons = 0
    bridge_candidate = False

    def add_fail(note: str) -> None:
        nonlocal status, hard_fail_reasons
        status = fit_status(status, "FAIL")
        hard_fail_reasons += 1
        notes.append(note)

    if poor_requirements:
        status = fit_status(status, "POOR")
        notes.append(
            "Role appears to require experience that is not strongly supported by the resume: "
            + ", ".join(poor_requirements)
            + "."
        )

    summary = professional_summary_text(document_xml) or ""
    if contains_cliche(summary):
        add_fail("Professional Summary still contains generic cliché language.")

    if not has_outcome_or_metric(summary):
        add_fail("Professional Summary lacks a metric, scope marker, or clear outcome signal.")

    summary_keywords = {
        keyword
        for keyword in keywords
        if not is_unsupported_do_not_insert(keyword, document_text, job_description)
    }
    summary_hits = keyword_hits(summary, summary_keywords)
    if summary_hits < 3:
        add_fail(f"Professional Summary has weak job-language alignment ({summary_hits} keyword hits).")

    nat = naturalness_score(summary)
    nat_score = int(nat.get("score", 0))
    nat_issues = [str(issue) for issue in nat.get("issues", [])]
    if nat_score > 10:
        notes.append(
            f"Naturalness: summary has a high AI-writing signal score ({nat_score}). "
            f"Issues: {', '.join(nat_issues[:3])}. Rewrite flagged phrases to sound more direct and human."
        )

    for warning in business_context.business_context_audit(summary, job_description, "Professional Summary"):
        notes.append(warning)

    if len(profile.direct_matches) < 2 and alignment_grade in ("Stretch Fit", "Poor Fit"):
        add_fail(
            f"Targeting bridge is weak for {profile.lane_label}: "
            f"{len(profile.direct_matches)} direct evidence areas found."
        )

    if profile.unsupported_requirements:
        if len(profile.direct_matches) < 2 or len(profile.unsupported_requirements) >= 2:
            status = fit_status(status, "POOR")
        else:
            status = fit_status(status, "FAIL")
            bridge_candidate = True
        notes.append(
            "Role includes unsupported or human-review requirements: "
            + ", ".join(profile.unsupported_requirements)
            + "."
        )

    if profile.specialty_gaps:
        notes.append(
            "Domain specialty gap: implementation fit is stronger than direct domain evidence for "
            + ", ".join(profile.specialty_gaps)
            + ". Use the cover letter and interview to address the learning curve honestly."
        )

    top_bullets = role_top_bullet_texts(
        document_xml,
        AUDIT_TOP_ROLE_TITLES,
        limit=2,
    )
    keyword_support_bullets = role_top_bullet_texts(
        document_xml,
        AUDIT_TOP_ROLE_TITLES,
        limit=5,
    )
    support_bullet_hits = keyword_hits(" ".join(keyword_support_bullets), keywords)
    if support_bullet_hits < 6:
        add_fail(f"Top experience section has weak job-language support ({support_bullet_hits} keyword hits across early bullets).")

    if not top_bullets:
        add_fail("Could not locate top role bullets for audit; verify role heading matches a known source title.")
    else:
        for warning in business_context.business_context_audit(" ".join(top_bullets), job_description, "Top-third bullets"):
            notes.append(warning)
        skim_issues = hiring_manager_skim_issues(summary, top_bullets, profile, job_description)
        if skim_issues:
            hard_fail_reasons += len(skim_issues)
            status = fit_status(status, "FAIL")
            notes.extend(skim_issues)
        top_without_proof = [bullet for bullet in top_bullets if not has_outcome_or_metric(bullet)]
        if len(top_without_proof) > 1:
            add_fail("Too many top experience bullets lack a metric, scope marker, or clear outcome signal.")

    all_bullets = experience_bullet_texts(document_xml)
    cliche_bullets = [bullet for bullet in all_bullets if contains_cliche(bullet)]
    if cliche_bullets:
        add_fail("Experience bullets still contain generic cliché language.")

    duty_only_bullets = [bullet for bullet in all_bullets if starts_with_duty_only_language(bullet)]
    if len(duty_only_bullets) > 2:
        add_fail(f"{len(duty_only_bullets)} experience bullets still read like duties without clear impact.")

    if all_bullets:
        great_eight_bullets = [bullet for bullet in all_bullets if has_great_eight_signal(bullet)]
        if len(great_eight_bullets) / len(all_bullets) < 0.60:
            notes.append(
                "Resume bullets may be too activity-focused. Fewer than 60 percent connect explicitly to a business outcome. Prioritize bullets that answer: what changed because Christian was there?"
            )

    placement_report = keyword_placement_audit(job_description, document_text)
    placement_gaps = placement_report.get("gaps", [])
    if isinstance(placement_gaps, list):
        for gap in placement_gaps[:3]:
            if not isinstance(gap, dict):
                continue
            keyword = str(gap.get("keyword", "")).strip()
            issue = str(gap.get("issue", "")).strip()
            if keyword and issue:
                notes.append(f"Keyword placement gap: {keyword} is {issue}.")

    competency_count = len(extract_competency_items(paragraph_infos(document_xml)))
    if competency_count < 15:
        notes.append(
            f"Skills section currently lists {competency_count} items. Optimal range is 15-25; consider adding only supported keyword coverage."
        )
    elif competency_count > 25:
        notes.append(
            f"Skills section currently lists {competency_count} items. Over 25 items can dilute signal and weaken ATS targeting."
        )

    alignment_report = alignment_score_report(job_description, document_text)
    total_score = int(alignment_report.get("total_score", 0))
    if total_score < ALIGNMENT_FAIL_FLOOR:
        add_fail(
            f"Alignment score is {total_score}/{ALIGNMENT_MAX_SCORE}, below the automatic fail floor of {ALIGNMENT_FAIL_FLOOR}."
        )
    elif total_score < ALIGNMENT_TARGET_SCORE:
        notes.append(
            f"Alignment score is {total_score}/{ALIGNMENT_MAX_SCORE}. This clears the fail floor, but the preferred target is {ALIGNMENT_TARGET_SCORE}+."
        )

    if (
        bridge_candidate
        and status == "FAIL"
        and hard_fail_reasons == 0
        and not poor_requirements
        and total_score >= ALIGNMENT_FAIL_FLOOR
    ):
        status = "BRIDGE"
        notes.append(
            "Overall fit is strong enough to pursue, but one requirement still needs honest bridge language instead of direct-claim wording."
        )

    readiness = resume_readiness_report(
        job_description,
        document_text,
        source_resume_text=source_resume_text,
        audit_status=status,
        auto_closed_keywords=auto_closed_keywords,
    )
    if readiness.hard_blockers:
        blocker_summary = "; ".join(resume_gap_summary_line(gap) for gap in readiness.hard_blockers[:3])
        if status != "POOR" and (
            status in {"PASS", "BRIDGE"}
            or (status == "FAIL" and hard_fail_reasons == 0 and total_score >= ALIGNMENT_FAIL_FLOOR)
        ):
            status = "BRIDGE"
        notes.append(
            "Bridge gaps remain for this role: "
            + blocker_summary
            + ". Address them directly in the cover letter and interview without overstating direct ownership."
        )

    return status, notes


def write_resume_audit_notes(
    output_target_name: str,
    company_name: str,
    role_title: str,
    status: str,
    notes: list[str],
    job_description: str,
    document_text: str,
) -> Path | None:
    profile = job_problem_profile(job_description, document_text)
    status_meaning = {
        "PASS": "PASS means the visible resume provides strong supported coverage without a hard evidence blocker.",
        "BRIDGE": "BRIDGE means the role is worth pursuing, but one requirement still needs explicit bridge language rather than a direct claim.",
        "FAIL": "FAIL means the resume needs human review before submission because targeting, evidence, or quality checks found fixable issues.",
        "POOR": "POOR means the role appears to be a weak strategic fit or includes important requirements the resume cannot honestly support.",
    }.get(status, f"{status} means the build needs human review.")
    status_suffix = "" if status == "PASS" else f" {status}"
    output_path = OUTPUT_DIR / f"Christian Estrada - {output_target_name}{status_suffix} Resume Notes.txt"
    lines = [
        f"Company: {company_name}",
        f"Role: {role_title or 'Unknown role'}",
        f"Fit status: {status}",
        status_meaning,
        "",
        "Audit Notes:",
    ]
    lines.extend(f"- {note}" for note in (notes or ["No detailed audit notes were returned."]))
    lines.extend(
        [
            "",
            "Evidence Map:",
            f"- Lane: {profile.lane_label}",
            f"- Direct evidence: {', '.join(profile.direct_matches) if profile.direct_matches else 'No direct evidence detected'}",
            f"- Adjacent evidence: {', '.join(profile.adjacent_matches) if profile.adjacent_matches else 'No adjacent evidence detected'}",
            f"- Domain specialty matches: {', '.join(profile.specialty_matches) if profile.specialty_matches else 'No domain specialty matches detected'}",
            f"- Domain specialty gaps: {', '.join(profile.specialty_gaps) if profile.specialty_gaps else 'No domain specialty gaps detected'}",
            f"- Unsupported requirements: {', '.join(profile.unsupported_requirements) if profile.unsupported_requirements else 'No unsupported requirements detected'}",
        ]
    )
    requirement_coverage = requirement_engine.commercial_requirement_coverage(job_description, document_text)
    if requirement_coverage:
        lines.extend(["", "Requirement Coverage:"])
        for item in requirement_coverage:
            evidence = ", ".join(item.matched_terms) or "honest non-claim"
            lines.append(
                f"- {item.element.element_id} [{item.status.value}] {item.element.text} -> {evidence}"
            )
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Audit notes file: {output_path}")
    return output_path


def alignment_score_report(job_description: str, resume_text: str) -> dict[str, object]:
    """Score pre-build alignment across keywords, lane fit, domain specialty, business context, and outcome density."""
    profile = job_problem_profile(job_description, resume_text)
    keywords = audit_keywords(job_description)

    covered = 0
    total_kw = len(keywords) if keywords else 1
    covered_weight = 0
    total_weight = 0
    for keyword in keywords:
        if is_unsupported_do_not_insert(keyword, resume_text, job_description):
            continue
        sort_key = audit_keyword_sort_key(job_description, keyword)
        if len(sort_key) < 7:
            raise ValueError(
                f"audit_keyword_sort_key returned {len(sort_key)} elements for {keyword!r}; expected at least 7."
            )
        title_flag, phrase_flag, priority_flag, _clean_edge, color_flag, summary_flag, jd_hits = sort_key[:7]
        weight = 1 + (title_flag * 4) + (phrase_flag * 2) + priority_flag + color_flag + summary_flag + min(2, int(jd_hits) // 2)
        total_weight += weight
        if contains_search_term(resume_text, keyword):
            covered += 1
            covered_weight += weight
    total_weight = total_weight or 1
    kw_score = min(15, int((covered_weight / total_weight) * 15))

    direct = len(profile.direct_matches)
    unsupported = len(profile.unsupported_requirements)
    lane_score = min(15, direct * 3) - (unsupported * 3)
    lane_score = max(0, lane_score)

    specialty_matches = len(profile.specialty_matches)
    specialty_gaps = len(profile.specialty_gaps)
    required_specialties = specialty_matches + specialty_gaps
    if required_specialties == 0:
        specialty_score = 15
        specialty_status = "No specialty domain requirement detected"
    elif specialty_gaps == 0:
        specialty_score = 15
        specialty_status = "Supported domain specialty"
    else:
        specialty_score = min(15, int((specialty_matches / required_specialties) * 15))
        specialty_status = "Domain specialty gap detected"

    context_score = min(15, business_context.business_relevance_score(resume_text, job_description) // 3)

    bullets = experience_bullet_texts_from_text(resume_text)
    if bullets:
        outcome_bullets = sum(1 for bullet in bullets if has_outcome_or_metric(bullet))
        density = outcome_bullets / len(bullets)
        outcome_score = min(15, int(density * 15))
    else:
        outcome_score = 7

    requirement_coverage = requirement_engine.commercial_requirement_coverage(job_description, resume_text)
    required_items = [item for item in requirement_coverage if item.element.required]
    if required_items:
        direct_coverage = sum(1 for item in required_items if item.status == requirement_engine.RequirementStatus.DIRECT)
        adjacent_coverage = sum(1 for item in required_items if item.status == requirement_engine.RequirementStatus.ADJACENT)
        requirement_score = min(40, int(((direct_coverage + (adjacent_coverage * 0.5)) / len(required_items)) * 40))
    else:
        direct_coverage = 0
        adjacent_coverage = 0
        requirement_score = 20

    total = requirement_score + kw_score + lane_score + specialty_score + context_score + outcome_score
    grade = (
        "Strong Fit" if total >= ALIGNMENT_TARGET_SCORE else
        "Adjacent Fit" if total >= ALIGNMENT_FAIL_FLOOR else
        "Stretch Fit" if total >= 35 else
        "Poor Fit"
    )
    return {
        "total_score": total,
        "keyword_coverage": {
            "score": kw_score,
            "covered": covered,
            "total_keywords": total_kw,
            "covered_weight": covered_weight,
            "total_weight": total_weight,
        },
        "requirement_coverage": {
            "score": requirement_score,
            "required": len(required_items),
            "direct": direct_coverage,
            "adjacent": adjacent_coverage,
            "unsupported": sum(1 for item in required_items if item.status == requirement_engine.RequirementStatus.UNSUPPORTED),
        },
        "lane_fit": {
            "score": lane_score,
            "direct": direct,
            "unsupported": unsupported,
        },
        "specialty_fit": {
            "score": specialty_score,
            "required": required_specialties,
            "matched": specialty_matches,
            "gaps": specialty_gaps,
            "matched_labels": profile.specialty_matches,
            "gap_labels": profile.specialty_gaps,
            "status": specialty_status,
        },
        "business_context": {
            "score": context_score,
        },
        "outcome_density": {
            "score": outcome_score,
        },
        "grade": grade,
        "score_scale_max": ALIGNMENT_MAX_SCORE,
        "minimum_pass_score": ALIGNMENT_FAIL_FLOOR,
        "preferred_target_score": ALIGNMENT_TARGET_SCORE,
        "minimum_pass_met": total >= ALIGNMENT_FAIL_FLOOR,
        "preferred_target_met": total >= ALIGNMENT_TARGET_SCORE,
    }


def alignment_gate_decision(
    total_score: int,
    report: dict[str, object],
    job_description: str,
    company_name: str,
) -> tuple[str, list[str]]:
    profile = job_problem_profile(job_description)
    specialty_fit = report.get("specialty_fit", {})
    specialty_gaps = (
        list(specialty_fit.get("gap_labels", ()))
        if isinstance(specialty_fit, dict)
        else []
    )
    if total_score >= ALIGNMENT_TARGET_SCORE:
        decision = "STRONG FIT - apply now"
        actions = [
            "Build resume and cover letter immediately.",
            f"Alignment is already above the preferred {ALIGNMENT_TARGET_SCORE}+ target, so interview preparation should now matter more than keyword refinement.",
            "Use remaining time on company research and interview stories instead of further resume tuning.",
        ]
        if specialty_gaps:
            actions.append(
                "Implementation fit is stronger than named domain-specialty fit ("
                + ", ".join(specialty_gaps[:3])
                + "). Address that learning curve directly in the cover letter and interview."
            )
    elif total_score >= ALIGNMENT_FAIL_FLOOR:
        decision = "ADJACENT FIT - make targeted edits first"
        keyword_coverage = report.get("keyword_coverage", {})
        if isinstance(keyword_coverage, dict):
            keyword_gap = int(keyword_coverage.get("total_keywords", 0)) - int(keyword_coverage.get("covered", 0))
        else:
            keyword_gap = 0
        actions = [
            f"Raise the score toward the preferred {ALIGNMENT_TARGET_SCORE}+ target by adding the top {min(keyword_gap, 5)} missing keywords to the summary, Skills, and top experience bullets.",
            "Rerun python tasks.py check to verify coverage improved.",
            "Apply within 48 hours - do not over-refine and miss the window.",
        ]
        if specialty_gaps:
            actions.insert(
                1,
                "Implementation fit is stronger than named domain-specialty fit ("
                + ", ".join(specialty_gaps[:3])
                + "). Use the cover letter to bridge the domain jump honestly rather than implying direct specialty depth."
            )
        lane_fit = report.get("lane_fit", {})
        unsupported = int(lane_fit.get("unsupported", 0)) if isinstance(lane_fit, dict) else 0
        if unsupported >= 2:
            actions.append(
                "Use gap_address_paragraph() in the cover letter to address the largest unsupported requirement directly."
            )
    else:
        decision = "STRETCH FIT - evaluate before applying"
        actions = [
            f"Raise the score above the automatic fail floor of {ALIGNMENT_FAIL_FLOOR} before submitting; below that threshold the resume should be treated as FAIL.",
            "Identify whether the gap is a keyword gap (solvable in 30 minutes) or a skill gap (requires a bridge story). Keyword gaps are fixable. Skill gaps require a cover letter.",
            "Write the cover letter first rather than last. The cover letter is where stretch candidates make their case.",
            f"Consider whether better-fit roles exist at {company_name} or similar companies where alignment is {ALIGNMENT_FAIL_FLOOR}+ before investing full preparation time here.",
            "If you apply, run python tasks.py cover-check to verify the specificity score is passing before submitting.",
        ]
        if specialty_gaps:
            actions.insert(
                2,
                "Implementation fit is clearer than named domain-specialty fit ("
                + ", ".join(specialty_gaps[:3])
                + "). Treat this as a bridge application and explain the domain learning curve directly."
            )
    return decision, actions


def section_index(paragraphs: list[ParagraphInfo], section: str) -> int | None:
    for index, paragraph in enumerate(paragraphs):
        if section_matches(paragraph.text, section):
            return index
    return None






def is_role_heading(text: str) -> bool:
    month_pattern = "|".join(MONTHS)
    role_date_pattern = re.compile(
        rf"(?<!\bin\s)(?<!\bsince\s)(?<!\bfrom\s)(?<!\bby\s)(?<!\bduring\s)(?<!\buntil\s)(?<!\bthrough\s)(?:{month_pattern})\s+\d{{4}}",
        re.I,
    )
    date_match = role_date_pattern.search(text)
    return bool(date_match and date_match.start() >= 15)


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


def validate_selected_resume_source_truth(source: ResumeSnapshot) -> None:
    problems: list[str] = []
    roles_by_company = {normalize_compare(role.company): role for role in source.roles}

    east_west = roles_by_company.get(normalize_compare(COMPANY_EAST_WEST))
    if east_west:
        context = east_west.company_context.strip()
        if not context:
            problems.append("East West source role is missing its company context paragraph")
        else:
            if re.search(r"\bindia\b", context, re.I):
                problems.append(
                    "East West company context incorrectly references India; use the neutralized global footprint wording instead"
                )
            if not (
                re.search(r"\bglobal(?:ly)?\b", context, re.I)
                or re.search(r"\binternational(?:ly)?\b", context, re.I)
                or (re.search(r"\bnorth america\b", context, re.I) and re.search(r"\basia\b", context, re.I))
            ):
                problems.append(
                    "East West company context must preserve the approved global or international footprint wording"
                )

    aptean = roles_by_company.get(normalize_compare(COMPANY_APTEAN))
    if aptean:
        context = re.sub(r"\s+", " ", aptean.company_context.strip())
        if not context:
            problems.append("Aptean source role is missing its company context paragraph")
        else:
            for phrase in APTEAN_COMPANY_CONTEXT_REQUIRED_PHRASES:
                if phrase.lower() not in context.lower():
                    problems.append(
                        f"Aptean company context is missing the approved phrase '{phrase}'"
                    )
            if re.search(r"\b3,000\+\b|\b12 countries\b", context, re.I):
                problems.append(
                    "Aptean company context still uses the outdated 3,000+/12 countries summary; replace it with the approved 10,000 organizations / 80 countries version"
                )
        if re.search(r"\bAptean Intuitive\b", aptean.block_text, re.I):
            problems.append(
                "Aptean source role incorrectly references Aptean Intuitive; keep Aptean Intuitive scoped to East West work"
            )

    if problems:
        fail("source resume truth validation failed:\n  " + "\n  ".join(problems))


def validate_resume_integrity(
    source: ResumeSnapshot,
    final: ResumeSnapshot,
    job_description: str,
    emphasis: TailoringEmphasis | None = None,
) -> None:
    problems: list[str] = []

    for section in REQUIRED_SECTIONS:
        if section not in final.sections:
            problems.append(f"missing section: {section}")

    final_text_lower = final.full_text.lower()
    final_text_key = normalize_compare(final.full_text)
    for pattern in PLACEHOLDER_PATTERNS:
        if re.search(pattern, final_text_lower, re.I):
            problems.append(f"placeholder text detected: {pattern}")
    for pattern, label in RESPONSIBILITY_SOFTENING_PATTERNS:
        if re.search(pattern, final_text_lower, re.I):
            problems.append(
                f"responsibility-softening phrase detected in generated resume text: {label}"
            )

    source_roles = {normalize_compare(role.title): role for role in source.roles}
    final_roles = {normalize_compare(role.title): role for role in final.roles}
    for key, source_role in source_roles.items():
        final_role = final_roles.get(key)
        if final_role is None:
            problems.append(f"missing role/job title: {source_role.title}")
            continue
        minimum_final_bullets = MIN_FINAL_BULLETS_BY_COMPANY.get(source_role.company, 2)
        minimum_final_bullets = min(minimum_final_bullets, source_role.bullet_count)
        if final_role.bullet_count < minimum_final_bullets:
            problems.append(
                f"too few bullets retained for {source_role.title}: "
                f"{final_role.bullet_count} final vs {minimum_final_bullets} required"
            )
        if source_role.company_context and normalize_compare(source_role.company_context) not in final_text_key:
            problems.append(f"missing company context for {source_role.company}: {source_role.company_context}")

    final_roles_by_company = {normalize_compare(role.company): role for role in final.roles}
    for company in MANDATORY_REORG_COMPANIES:
        role = final_roles_by_company.get(normalize_compare(company))
        if role is None:
            problems.append(f"missing role/company block for mandatory summary text: {company}")
            continue
        fact_count = reorg_fact_count(role.block_text)
        if fact_count == 0:
            problems.append(f"missing reorganization fact for {company}")
        elif fact_count > 1:
            problems.append(f"reorganization fact repeated more than once for {company}")

    required_competency_items = retained_competency_items(
        job_description,
        source.competency_items,
        emphasis=emphasis,
    )
    if not jd_explicitly_requires_erp(job_description):
        scrubbed_competency_items: set[str] = set()
        for item in required_competency_items:
            cleaned_item = normalize_compare(scrub_erp_language_for_non_erp_text(item, job_description))
            if cleaned_item:
                scrubbed_competency_items.add(cleaned_item)
        required_competency_items = scrubbed_competency_items
    missing_competency_items = required_competency_items - final.competency_items
    if missing_competency_items:
        supported_additions = {
            normalize_compare(skill)
            for skill in supported_simple_competencies(job_description, source.competency_items)
            if normalize_compare(skill)
        }
        added_competency_items = {
            item
            for item in (final.competency_items - source.competency_items)
            if item in supported_additions
        }
        unresolved_missing = set(missing_competency_items)
        if added_competency_items:
            removable_missing = sorted(
                unresolved_missing,
                key=lambda item: (skill_relevance_score(item, job_description, emphasis), item),
            )
            for added_item in sorted(
                added_competency_items,
                key=lambda item: (skill_relevance_score(item, job_description, emphasis), item),
                reverse=True,
            ):
                added_score = skill_relevance_score(added_item, job_description, emphasis)
                for missing_item in list(removable_missing):
                    if added_score > skill_relevance_score(missing_item, job_description, emphasis):
                        unresolved_missing.discard(missing_item)
                        removable_missing.remove(missing_item)
                        break
        if unresolved_missing:
            problems.append("missing Skills item(s): " + ", ".join(sorted(unresolved_missing)))

    missing_pd = source.professional_development_items - final.professional_development_items
    if missing_pd:
        problems.append("missing Professional Development item(s): " + ", ".join(sorted(missing_pd)))

    if problems:
        fail("resume integrity validation failed:\n  " + "\n  ".join(problems))






def build_resume() -> BuildResult:
    validate_config_integrity()
    job_description = validate_inputs()
    company_name = extract_output_name(job_description)
    overlap_company_name = extract_company_name(job_description) or company_name
    output_target_name = extract_output_target_name(job_description)
    selected_resume = choose_resume(job_description)
    selected_resume_text = docx_visible_text_from_path(selected_resume)
    output_docx = OUTPUT_DIR / f"Christian Estrada - {output_target_name} Resume.docx"
    keywords = keyword_set(job_description)
    profile = job_problem_profile(job_description, selected_resume_text)
    header_title_line = dynamic_header_title_line(job_description)
    alignment_report = alignment_score_report(job_description, selected_resume_text)
    gate_decision, gate_actions = alignment_gate_decision(
        int(alignment_report["total_score"]),
        alignment_report,
        job_description,
        company_name,
    )
    positioning_statement = generate_positioning_statement(profile, job_description)

    specialty_fit = alignment_report.get("specialty_fit", {})
    if isinstance(specialty_fit, dict):
        required_specialties = int(specialty_fit.get("required", 0))
        if required_specialties > 0:
            print(f"\nDomain Specialty: {specialty_fit.get('score', 0)}/15 - {specialty_fit.get('status', 'Domain specialty gap detected')}")
            matched_labels = specialty_fit.get("matched_labels", ())
            gap_labels = specialty_fit.get("gap_labels", ())
            if matched_labels:
                print(f"  Supported areas: {', '.join(str(label) for label in matched_labels)}")
            if gap_labels:
                print(f"  Gap areas: {', '.join(str(label) for label in gap_labels)}")
            print()
        else:
            print("\nDomain Specialty: not a major differentiator in this posting.\n")
    print(
        f"Alignment Score: {alignment_report['total_score']}/{alignment_report['score_scale_max']} - "
        f"{alignment_report['grade']}"
    )
    print(f"  Requirement coverage: {alignment_report['requirement_coverage']['score']}/40")
    print(f"  Keyword coverage: {alignment_report['keyword_coverage']['score']}/15")
    print(f"  Lane fit: {alignment_report['lane_fit']['score']}/15")
    print(f"  Business context: {alignment_report['business_context']['score']}/15")
    print(f"  Outcome density: {alignment_report['outcome_density']['score']}/15\n")
    print(f"Alignment Gate: {gate_decision}")
    for action in gate_actions:
        print(f"  Gate action: {action}")
    print(f"Positioning Statement: {positioning_statement}")
    print()

    OUTPUT_DIR.mkdir(exist_ok=True)
    SCRATCH_DIR.mkdir(exist_ok=True)

    temp_root = SCRATCH_DIR / f"christian_resume_{uuid.uuid4().hex}"
    build_warnings: list[str] = []
    try:
        temp_root.mkdir(parents=True, exist_ok=False)
        def assemble_variant(variant_index: int) -> ResumeAssemblyResult:
            variant_root = temp_root / f"variant_{variant_index}"
            work_dir = variant_root / "work"
            visual_dir = variant_root / "visual"
            work_dir.mkdir(parents=True, exist_ok=False)
            visual_dir.mkdir(parents=True, exist_ok=False)
            unpack_docx(selected_resume, work_dir)
            unpack_docx(EDFIX_RESUME, visual_dir)

            document_xml = work_dir / "word" / "document.xml"
            visual_document_xml = visual_dir / "word" / "document.xml"
            emphasis = determine_tailoring_emphasis(job_description, selected_resume_text, variant_index)

            restore_mandatory_reorg_summaries(document_xml)
            source_snapshot = resume_snapshot(document_xml)
            validate_selected_resume_source_truth(source_snapshot)
            provenance_source_xml = variant_root / "approved_source_document.xml"
            shutil.copy2(document_xml, provenance_source_xml)

            visual_parts = copy_visual_parts(work_dir, visual_dir)
            if apply_section_layout(document_xml, visual_document_xml):
                visual_parts += 1
            force_styles_font(work_dir / "word" / "styles.xml")
            force_styles_font(work_dir / "word" / "stylesWithEffects.xml")
            force_style_single_spacing(work_dir / "word" / "styles.xml")
            force_style_single_spacing(work_dir / "word" / "stylesWithEffects.xml")
            normalize_date_ranges(document_xml)
            paragraphs_rewritten = apply_supported_rewrites(document_xml, job_description)
            paragraphs_rewritten += apply_outcome_framing_rewrites(document_xml, job_description)
            paragraphs_rewritten += apply_consulting_story_rewrites(document_xml, job_description)
            paragraphs_rewritten += apply_value_story_rewrites(document_xml, job_description)
            paragraphs_rewritten += apply_startup_operator_rewrites(document_xml, job_description)
            normalize_summary_experience_case(document_xml)
            normalize_supported_acronyms(document_xml)
            paragraphs_rewritten += merge_low_fit_bullets_before_delete(document_xml, job_description)
            paragraphs_rewritten += clean_merged_role_bullets(document_xml)
            role_bullets_removed = remove_condensable_role_bullets(document_xml, job_description)
            role_bullets_removed += remove_global_low_fit_bullets(document_xml)
            competency_categories_renamed = rename_core_competency_categories(document_xml, job_description)
            competency_items_removed = remove_irrelevant_core_competencies(
                document_xml,
                job_description,
                emphasis=emphasis,
            )
            competency_items_added = add_simple_core_competencies(
                document_xml,
                job_description,
                emphasis=emphasis,
            )
            auto_closed_keywords = tuple(
                aggressively_close_supported_keyword_gaps(document_xml, job_description, selected_resume_text)
            )
            competency_items_added += len(auto_closed_keywords)
            normalize_core_competency_capitalization(document_xml)
            normalize_supported_acronyms(document_xml)
            format_core_competency_runs(document_xml)
            reordered = reorder_bullets(document_xml, keywords, profile, job_description, emphasis)
            role_bullets_removed += select_experience_bullets_for_two_page_resume(
                document_xml,
                job_description,
                emphasis,
            )
            paragraphs_rewritten += apply_value_story_rewrites(document_xml, job_description)
            paragraphs_rewritten += apply_startup_operator_rewrites(document_xml, job_description)
            paragraphs_rewritten += remove_extra_role_summary_paragraphs(document_xml)
            paragraphs_rewritten += limit_cutover_mentions(document_xml)
            paragraphs_rewritten += scrub_non_erp_resume_language(document_xml, job_description)
            paragraphs_rewritten += normalize_role_bullet_endings(document_xml)

            # Phase 6 content boundary: candidate mutations stop here. Summary,
            # role-summary, and bullet content becomes a provenance-bearing
            # model and is rendered once before formatting-only passes.
            content_model = commercial_resume_model.build_content_model(
                selected_resume,
                provenance_source_xml,
                document_xml,
            )
            composed_summary = build_problem_first_summary(
                job_description,
                selected_resume_text,
                variant_index=variant_index,
            )
            summary_outcome = prose_engine.repair_text(composed_summary, "summary")
            if not summary_outcome.converged:
                rule_ids = ", ".join(
                    finding.rule_id for finding in summary_outcome.findings if finding.severity == "fail"
                )
                fail(f"Commercial model summary repair did not converge. Rule IDs: {rule_ids or 'UNKNOWN'}")
            composed_summary = scrub_erp_language_for_non_erp_text(summary_outcome.text, job_description)
            if not jd_explicitly_requires_erp(job_description):
                composed_summary = scrub_named_erp_platforms_for_summary(composed_summary)
            role_summary_map: dict[str, str] = {}
            for role_model in content_model.roles:
                if not role_model.summaries:
                    continue
                role_text = optimized_role_summary(
                    role_model.employer,
                    role_model.summaries[0].text,
                    job_description,
                    emphasis,
                )
                role_outcome = prose_engine.repair_text(role_text, "summary")
                if not role_outcome.converged:
                    rule_ids = ", ".join(
                        finding.rule_id for finding in role_outcome.findings if finding.severity == "fail"
                    )
                    fail(
                        f"Commercial model role-summary repair did not converge for {role_model.employer}. "
                        f"Rule IDs: {rule_ids or 'UNKNOWN'}"
                    )
                role_summary_map[role_model.employer] = scrub_erp_language_for_non_erp_text(
                    role_outcome.text,
                    job_description,
                )
            content_model = commercial_resume_model.with_composed_summaries(
                content_model,
                composed_summary,
                role_summary_map,
            )
            paragraphs_rewritten += 1 + len(role_summary_map)
            commercial_resume_model.render_content_model(document_xml, content_model)
            manifest_name = re.sub(r"[^A-Za-z0-9._-]+", "_", output_target_name).strip("_")
            commercial_resume_model.write_manifest(
                content_model,
                SCRATCH_DIR / "provenance_models" / f"{manifest_name}_variant_{variant_index}.json",
            )

            apply_font_and_size_pass(document_xml, header_title_line=header_title_line)
            normalize_core_competency_capitalization(document_xml)
            normalize_supported_acronyms(document_xml)
            format_core_competency_runs(document_xml)
            normalize_skills_section_heading(document_xml)
            force_resume_visual_branding(document_xml, header_title_line=header_title_line)
            ensure_header_gap_after_contact(document_xml)
            apply_spacing_and_layout_pass(document_xml)
            remove_linkedin_hyperlinks(work_dir)

            final_snapshot = resume_snapshot(document_xml)
            validate_resume_integrity(source_snapshot, final_snapshot, job_description, emphasis)
            assert_professional_summary_length(document_xml)
            assert_professional_summary_structure(document_xml)
            assert_date_range_format(final_snapshot)
            assert_core_competency_capitalization(document_xml)
            assert_core_competency_run_format(document_xml)
            assert_experience_emphasis_format(document_xml)
            assert_document_font(document_xml)
            assert_single_spacing(document_xml)
            assert_resume_language_rules(document_xml, job_description)
            assert_substitution_safety(visible_text(document_xml), "resume")
            assert_no_erp_language_for_non_erp_role(
                resume_text_for_non_erp_audit(document_xml),
                job_description,
                label="resume summary",
            )

            alignment_report = alignment_score_report(job_description, visible_text(document_xml))
            audit_status, audit_notes = final_fit_audit(
                document_xml,
                job_description,
                source_resume_text=selected_resume_text,
                auto_closed_keywords=auto_closed_keywords,
                alignment_grade=str(alignment_report.get("grade", "")).strip() or None,
            )
            audit_document_text = visible_text(document_xml)
            readiness = resume_readiness_report(
                job_description,
                audit_document_text,
                source_resume_text=selected_resume_text,
                audit_status=audit_status,
                auto_closed_keywords=auto_closed_keywords,
            )
            return ResumeAssemblyResult(
                work_dir=work_dir,
                document_xml=document_xml,
                source_snapshot=source_snapshot,
                final_snapshot=final_snapshot,
                emphasis=emphasis,
                paragraphs_rewritten=paragraphs_rewritten,
                competency_categories_renamed=competency_categories_renamed,
                competency_items_added=competency_items_added,
                competency_items_removed=competency_items_removed,
                role_bullets_removed=role_bullets_removed,
                bullet_groups_reordered=reordered,
                visual_parts_applied=visual_parts,
                audit_status=audit_status,
                audit_notes=audit_notes,
                readiness=readiness,
                auto_closed_keywords=auto_closed_keywords,
                variable_snapshot=resume_variable_snapshot(document_xml),
            )

        assembled = assemble_variant(0)
        overlap_score, overlap_match = highest_same_company_overlap(
            assembled.variable_snapshot,
            overlap_company_name,
            OUTPUT_DIR,
        )
        if overlap_match:
            print(
                f"Same-company overlap check: {overlap_score:.2f} against {overlap_match.name} "
                f"using emphasis {assembled.emphasis.key}."
            )
        if overlap_score > SAME_COMPANY_VARIABLE_OVERLAP_THRESHOLD:
            alternates: list[tuple[ResumeAssemblyResult, float, Path | None]] = []
            for variant_index in (1, 2):
                try:
                    alternate = assemble_variant(variant_index)
                except SystemExit as error:
                    build_warnings.append(
                        "Skipped a same-company alternate emphasis pass because it did not assemble cleanly: "
                        f"variant {variant_index} ({error})"
                    )
                    continue
                alternate_score, alternate_match = highest_same_company_overlap(
                    alternate.variable_snapshot,
                    overlap_company_name,
                    OUTPUT_DIR,
                )
                alternates.append((alternate, alternate_score, alternate_match))
                if alternate_match:
                    print(
                        f"Alternate same-company overlap: {alternate_score:.2f} against {alternate_match.name} "
                        f"using emphasis {alternate.emphasis.key}."
                    )
            best_alternate = min(alternates, key=lambda item: item[1]) if alternates else None
            if best_alternate and best_alternate[1] < overlap_score:
                assembled = best_alternate[0]
                overlap_score = best_alternate[1]
                overlap_match = best_alternate[2]
            if overlap_score > SAME_COMPANY_VARIABLE_OVERLAP_THRESHOLD:
                warning_target = overlap_match.name if overlap_match else "recent same-company resume output"
                build_warnings.append(
                    f"Same-company variable-section overlap remained {overlap_score:.2f} against {warning_target} after alternate emphasis passes."
                )

        final_snapshot = assembled.final_snapshot
        role_title = extract_job_title(job_description) or ""
        if assembled.audit_status == "POOR":
            output_docx = OUTPUT_DIR / f"Christian Estrada - {output_target_name} POOR Resume.docx"
        elif assembled.audit_status == "BRIDGE":
            output_docx = OUTPUT_DIR / f"Christian Estrada - {output_target_name} BRIDGE Resume.docx"
        elif assembled.audit_status == "FAIL":
            output_docx = OUTPUT_DIR / f"Christian Estrada - {output_target_name} FAIL Resume.docx"
        write_resume_audit_notes(
            output_target_name,
            company_name,
            role_title,
            assembled.audit_status,
            assembled.audit_notes,
            job_description,
            visible_text(assembled.document_xml),
        )

        pack_docx_with_page_fit(assembled.work_dir, output_docx, assembled.document_xml, temp_root)
        ats_report = ats_plain_text_validation(output_docx)
        for warning in ats_report["warnings"]:
            print(f"ATS WARNING: {warning}")
        for warning in build_warnings:
            print(f"BUILD WARNING: {warning}")
        if ats_report["blockers"]:
            fail("ATS plain-text validation failed:\n  " + "\n  ".join(str(item) for item in ats_report["blockers"]))
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    print(f"Skills: {len(final_snapshot.competency_items)} items after build.")

    started = time.monotonic()
    render_checks.render_docx(output_docx)
    print(f"Final render check elapsed: {time.monotonic() - started:.1f}s")

    return BuildResult(
        selected_resume,
        output_docx,
        company_name,
        assembled.paragraphs_rewritten,
        assembled.competency_categories_renamed,
        assembled.competency_items_added,
        assembled.competency_items_removed,
        assembled.role_bullets_removed,
        assembled.bullet_groups_reordered,
        assembled.visual_parts_applied,
        assembled.audit_status,
        assembled.audit_notes,
        assembled.readiness,
        tuple(build_warnings),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Christian Estrada's tailored DOCX resume.")
    parser.add_argument("--no-pdf", action="store_true", help="Accepted for clarity; PDFs are never created.")
    return parser.parse_args()


def main() -> None:
    parse_args()
    result = build_resume()
    print(f"Company: {result.company_name}")
    print(f"Source resume: {result.source_resume}")
    print(f"Output DOCX: {result.output_docx}")
    print(f"Visual formatting parts applied: {result.visual_parts_applied}")
    print(f"Paragraphs rewritten: {result.paragraphs_rewritten}")
    print(f"Competency categories renamed: {result.competency_categories_renamed}")
    print(f"Competency items added: {result.competency_items_added}")
    print(f"Competency items removed: {result.competency_items_removed}")
    print(f"Role bullets removed: {result.role_bullets_removed}")
    print(f"Bullet groups reordered: {result.bullet_groups_reordered}")
    print(f"Final audit: {result.audit_status}")
    if result.readiness and result.readiness.auto_closed_gaps:
        print(
            "Readiness auto-closed: "
            + ", ".join(gap.label for gap in result.readiness.auto_closed_gaps[:5])
        )
    if result.readiness and result.readiness.hard_blockers:
        print(
            "Resume bridge gaps: "
            + "; ".join(resume_gap_summary_line(gap) for gap in result.readiness.hard_blockers[:3])
        )
    for warning in result.build_warnings:
        print(f"Build warning: {warning}")
    for note in result.audit_notes:
        print(f"Audit note: {note}")


if __name__ == "__main__":
    main()
