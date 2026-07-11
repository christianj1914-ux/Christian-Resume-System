"""Declarative language validation rules."""

import re

# Mandatory resume text for roles impacted by reorganization
MANDATORY_REORG_SENTENCE = "Position impacted by company reorganization."
MANDATORY_REORG_COMPANIES = ("East West Manufacturing", "Aptean")
PROFESSIONAL_SUMMARY_MIN_WORDS = 50
PROFESSIONAL_SUMMARY_MAX_WORDS = 110

PLACEHOLDER_PATTERNS = (
    r"\bplaceholder\b",
    r"\btbd\b",
    r"\bto be determined\b",
    r"\blorem ipsum\b",
    r"\binsert (company|job|role|text|content)\b",
    r"\bcompany name\b",
    r"\[+[^\]]+\]+",
    r"\{\{[^}]+\}\}",
)

CLICHE_PATTERNS = (
    r"\bdedicated\b",
    r"\bresults[- ]driven\b",
    r"\bdetail[- ]oriented\b",
    r"\bself[- ]starter\b",
    r"\bhard[- ]working\b",
    r"\bteam player\b",
    r"\bgo[- ]getter\b",
    r"\bwork like this only sticks when\b",
    r"\bthe work only matters when it changes a decision\b",
    r"\bwould be valuable\b",
    r"\bwould be beneficial\b",
)

SUBJECTIVE_JOB_AD_PATTERNS = (
    r"\bstrong (?:in|at|with)\b",
    r"\bexcels? in\b",
    r"\bexcellent (?:communication|interpersonal|relationship|organizational|problem[- ]solving)\b",
    r"\boutstanding (?:communication|listening|training|organizational|problem[- ]solving)\b",
    r"\bhighly organized\b",
    r"\bproactive\b",
    r"\bcreative problem[- ]solver\b",
    r"\bresourceful\b",
    r"\bconfident under pressure\b",
    r"\bcomfortable (?:with|in) ambiguity\b",
    r"\bambiguous environments\b",
)

GENERIC_SOFT_KEYWORDS = {
    "adaptable",
    "ambiguity",
    "ambiguous",
    "collaborative",
    "communication",
    "communication skills",
    "confident",
    "creative",
    "creative problem solver",
    "excellent",
    "excellent communication",
    "highly",
    "highly organized",
    "interpersonal",
    "listening skills",
    "organized",
    "passion",
    "passionate",
    "presentation",
    "presentation skills",
    "proactive",
    "problem-solver",
    "problem solver",
    "problem solving",
    "resourceful",
    "self motivated",
    "skills",
    "strategic planning",
    "strong communication",
    "stakeholder communication",
}

AI_WRITING_PATTERNS = (
    r"\bspearheaded\b",
    r"\bpioneered\b",
    r"\bchampioned\b",
    r"\bmeticulously\b",
    r"\brobust\b",
    r"\bleveraged extensively\b",
    r"\bseamlessly\b",
    r"\bthought leader\b",
    r"\bcutting[- ]edge\b",
    r"\bgame[- ]changer\b",
    r"\bsynergy\b",
    r"\bmove the needle\b",
    r"\bvalue[- ]add\b",
    r"\bparadigm\b",
    r"\bholistic\b",
    r"\bworld[- ]class\b",
    r"\bbest[- ]in[- ]class\b",
    r"\bsolution[- ]oriented\b",
    r"\bforward[- ]thinking\b",
    r"\binnovative solutions\b",
    r"\bembrace change\b",
    r"\bdrive success\b",
    r"\bpassionate about\b",
    r"\bseek to\b",
)

PROMPT_LEAK_PATTERNS = (
    r"\bmost relevant to this role\b",
    r"\brelevant to this role\b",
    r"\btailored to this role\b",
    r"\btarget(?:ed)? role\b",
    r"\btarget(?:ed)? job\b",
    r"\bthis job description\b",
    r"\bTarget context:\b",
    r"\bStrong fit for roles\b",
    r"\bBackground includes\b",
    r"\bExperience spans\b",
    r"\bBackground spans\b",
    r"\bThis background fits\b",
    r"\bThis background is strongest\b",
    r"\bThe same pattern fits\b",
    r"\bRecent work has included\b",
    r"\bPrior work includes\b",
    r"\bmaps directly to\b",
    r"\bmaps to this role\b",
    r"\bwhich is exactly the kind of\b",
    r"\bspeaks directly to\b",
    r"\baligns directly with\b",
    r"\baligns directly to\b",
)

FIRST_PERSON_PATTERNS = (
    r"\bI\b",
    r"\bme\b",
    r"\bmy\b",
    r"\bmine\b",
    r"\bwe\b",
    r"\bour\b",
    r"\bours\b",
    r"\bus\b",
)

DUTY_ONLY_OPENERS = (
    "managed",
    "coordinated",
    "supported",
    "handled",
    "assisted",
    "participated",
    "responsible",
)

ACRONYM_TEXT_REPLACEMENTS = {
    "uat": "UAT",
    "sow": "SOW",
    "sows": "SOWs",
    "frd": "FRD",
    "frds": "FRDs",
    "qbr": "QBR",
    "qbrs": "QBRs",
    "ebr": "EBR",
    "ebrs": "EBRs",
    "etl": "ETL",
    "cpq": "CPQ",
    "arr": "ARR",
    "grr": "GRR",
    "nrr": "NRR",
    "roi": "ROI",
    "mro": "MRO",
    "nlp": "NLP",
    "pmi": "PMI",
    "sdlc": "SDLC",
    "sfdc": "SFDC",
    "liveperson": "LivePerson",
    "liveengage": "LiveEngage",
}


for _name in (
    "CLICHE_PATTERNS",
    "AI_WRITING_PATTERNS",
    "PLACEHOLDER_PATTERNS",
    "FIRST_PERSON_PATTERNS",
    "DUTY_ONLY_OPENERS",
    "PROMPT_LEAK_PATTERNS",
    "SUBJECTIVE_JOB_AD_PATTERNS",
):
    _value = globals()[_name]
    assert isinstance(_value, tuple) and _value, f"{_name} must be a non-empty tuple"

assert isinstance(GENERIC_SOFT_KEYWORDS, set) and GENERIC_SOFT_KEYWORDS, (
    "GENERIC_SOFT_KEYWORDS must be a non-empty set"
)

APPROVED_BRACKETED_METADATA_PATTERNS = (
    r"POST-INTERVIEW NOTE \[[^\]]+\]:",
)


def contains_reorg_fact(text: str) -> bool:
    return bool(re.search(r"\breorgani[sz]ation\b", text, re.I))


def reorg_fact_count(text: str) -> int:
    return len(re.findall(r"\breorgani[sz]ation\b", text, re.I))


def remove_approved_bracketed_metadata(text: str) -> str:
    """Remove system-owned bracket metadata before placeholder checks."""
    cleaned = text
    for pattern in APPROVED_BRACKETED_METADATA_PATTERNS:
        cleaned = re.sub(pattern, "POST-INTERVIEW NOTE:", cleaned, flags=re.I)
    return cleaned
assert isinstance(ACRONYM_TEXT_REPLACEMENTS, dict) and ACRONYM_TEXT_REPLACEMENTS, (
    "ACRONYM_TEXT_REPLACEMENTS must be a non-empty dict"
)
