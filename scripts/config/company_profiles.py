"""Verified company profile registry for tailored positioning.

This file is intentionally conservative: profiles should be added only when the
company context is verified from Christian's own research notes, interview notes,
or a visible job posting.
"""

from __future__ import annotations

import os
import sys
from typing import Literal, TypedDict


CoverStyle = Literal[
    "default_pyramid",
    "consulting_practice",
    "customer_outcomes",
    "mission_context",
    "operator_builder",
]


class CompanyProfile(TypedDict):
    key: str
    name_patterns: tuple[str, ...]
    industry: str
    cover_style: CoverStyle
    interview_emphasis: str
    proof_emphasis: str
    avoid: str


COMPANY_PROFILES: tuple[CompanyProfile, ...] = (
    {
        "key": "bain",
        "name_patterns": ("bain", "bain & company", "bain and company"),
        "industry": "management consulting",
        "cover_style": "consulting_practice",
        "interview_emphasis": "structured problem solving, client-service judgment, executive alignment, and measurable recommendations",
        "proof_emphasis": "global client delivery, executive workshops, analytics, stakeholder alignment, and implementation credibility",
        "avoid": "Do not imply formal strategy-consulting employment or unsupported MBA-style case depth.",
    },
    {
        "key": "state_farm",
        "name_patterns": ("state farm",),
        "industry": "insurance and financial services",
        "cover_style": "mission_context",
        "interview_emphasis": "risk-aware delivery, claims workflow clarity, controls, service quality, and trustworthy reporting",
        "proof_emphasis": "workflow improvement, stakeholder governance, reporting quality, and practical adoption support",
        "avoid": "Do not claim insurance-specific operations ownership beyond transferable workflow and analytics evidence.",
    },
    {
        "key": "kpmg",
        "name_patterns": ("kpmg",),
        "industry": "professional services and advisory",
        "cover_style": "consulting_practice",
        "interview_emphasis": "client credibility, structured discovery, practical recommendations, and implementation risk control",
        "proof_emphasis": "enterprise systems, executive communication, analytics, and cross-functional implementation delivery",
        "avoid": "Do not imply audit, tax, or formal advisory employment unless directly supported.",
    },
    {
        "key": "liveperson",
        "name_patterns": ("liveperson", "liveperson liveengage"),
        "industry": "customer experience and conversational AI",
        "cover_style": "customer_outcomes",
        "interview_emphasis": "messaging workflow design, customer engagement, analytics, adoption, and automation judgment",
        "proof_emphasis": "LiveEngage online chat/text workflows, greeting and closing scripts, SMS pilot support, and interaction trend monitoring",
        "avoid": "Do not claim production AI model ownership or unsupported machine-learning engineering.",
    },
    {
        "key": "aptean",
        "name_patterns": ("aptean",),
        "industry": "enterprise software and ERP",
        "cover_style": "customer_outcomes",
        "interview_emphasis": "implementation quality, customer adoption, renewal risk, value realization, and post-go-live support",
        "proof_emphasis": "Encompix implementation, configuration, data migration, testing, go-live support, QBRs, and at-risk account recovery",
        "avoid": "Do not tie Aptean Intuitive ownership to the Aptean Customer Success role; Intuitive belongs to East West Manufacturing.",
    },
)


def match_company_profile(company_name: str, job_description: str = "") -> CompanyProfile | None:
    haystack = f"{company_name}\n{job_description}".lower()
    debug = os.environ.get("DEBUG_COMPANY_PROFILE") == "1"
    
    if debug:
        print(f"[DEBUG] Matching company profile for: {company_name}", file=sys.stderr)
    
    for profile in COMPANY_PROFILES:
        if any(pattern in haystack for pattern in profile["name_patterns"]):
            if debug:
                print(f"[DEBUG] ✓ Matched profile '{profile['key']}' via patterns: {profile['name_patterns']}", file=sys.stderr)
            return profile
    
    if debug:
        print(f"[DEBUG] ✗ No profile matched. Checked {len(COMPANY_PROFILES)} profiles.", file=sys.stderr)
    
    return None
