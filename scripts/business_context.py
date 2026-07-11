#!/usr/bin/env python3
"""Business-context extraction, audits, scoring, and interview questions."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class BusinessContext:
    business_model: str = ""
    product_or_service: str = ""
    customer_type: str = ""
    industry: str = ""
    geography: str = ""
    scale: str = ""
    revenue_or_account_size: str = ""
    growth_stage: str = ""
    operational_complexity: str = ""
    technical_stack: tuple[str, ...] = ()
    compliance_signals: tuple[str, ...] = ()
    role_success_outcomes: tuple[str, ...] = ()


@dataclass(frozen=True)
class BusinessInterviewQuestion:
    question: str
    hidden_concern: str
    answer_angle: str
    ask_back: str
    signal: str


GENERIC_FLUFF_PATTERNS: tuple[str, ...] = (
    r"\bstrategic\b",
    r"\bresults[- ]driven\b",
    r"\bproven ability\b",
    r"\bexcellent communication\b",
    r"\btrusted advisor\b",
    r"\bcollaborative\b",
    r"\bfast[- ]paced environment\b",
    r"\bcomfortable with ambiguity\b",
    r"\bstakeholders? at all levels\b",
)

HEALTHCARE_CONTEXT_RE = r"\b(?:healthcare|clinical|patient|medical|lab|laboratory|hipaa|phi)\b"
FINANCIAL_SERVICES_CONTEXT_RE = r"\b(?:financial services|banking|insurance|claims|risk control)\b"
EDUCATION_AUDIENCE_RE = r"\b(?:schools?|districts?|educators?|teachers?|students?)\b"
EDUCATION_ASSESSMENT_CONTEXT_RE = (
    r"\b(?:education(?:al)?|school assessment|assessment items?|assessment systems?|k-12|"
    r"instructional|psychometric|psychometrics|constructed-response|technology-enhanced items?|"
    r"educational measurement|measurement and learning|learning systems?|learner-facing)\b"
)


BUSINESS_FACT_PATTERNS: tuple[str, ...] = (
    r"\bB2B\b|\bB2C\b|\bSaaS\b|\bcloud\b|\bplatform\b|\bproduct\b",
    r"\bhealthcare\b|\bmanufacturing\b|\bfinancial services\b|\blogistics\b|\bsoftware\b",
    r"\beducation(?:al)?\b|\bschool\b|\bk-12\b|\bassessment\b|\blearning\b|\blearner(?:-facing)?\b|\bstudents?\b|\bmeasurement\b",
    r"\bclients?\b|\bcustomers?\b|\baccounts?\b|\busers?\b|\bpatients?\b|\bsites?\b|\beducators?\b|\blearners?\b|\bstudents?\b",
    r"\b\d{2,6}\+?\s+(?:employees|users|customers|clients|accounts|sites|locations|projects)\b",
    r"\$\s?\d+(?:\.\d+)?\s?(?:M|MM|million|B|billion)\+?",
    r"\bimplementation\b|\badoption\b|\bgo-live\b|\bdata migration\b|\bintegration\b|\brisk\b|\bquality\b|\bvalidation\b|\bfairness\b|\baccessibility\b",
)


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def normalize_geography_label(raw: str) -> str:
    """Avoid bare US tokens that read like pronouns in generated prose."""
    stripped = clean_text(raw)
    if not stripped:
        return ""
    if re.fullmatch(r"U\.?S\.?", stripped, re.I):
        return "North America"
    return stripped


def detect_first(text: str, patterns: tuple[tuple[str, str], ...]) -> str:
    lowered = text.lower()
    for label, pattern in patterns:
        if re.search(pattern, lowered, re.I):
            return label
    return ""


def detect_terms(text: str, terms: tuple[tuple[str, str], ...]) -> tuple[str, ...]:
    found: list[str] = []
    lowered = text.lower()
    for label, pattern in terms:
        if re.search(pattern, lowered, re.I) and label not in found:
            found.append(label)
    return tuple(found)


def extract_business_context(source_text: str) -> BusinessContext:
    text = clean_text(source_text)
    lowered = text.lower()
    business_model = detect_first(
        lowered,
        (
            ("education / assessment systems", EDUCATION_ASSESSMENT_CONTEXT_RE),
            ("supply chain / logistics operations", r"\bsupply chain|logistics|transportation|warehousing|warehouse|trade compliance|order management\b"),
            ("cloud software / SaaS", r"\bsaas\b|software-as-a-service|cloud-based|cloud based"),
            ("consulting / client service", r"\bconsulting\b|client service|advisory"),
            ("manufacturing / operations", r"\bmanufacturer|manufacturing|supply chain|inventory\b"),
            ("healthcare / regulated operations", HEALTHCARE_CONTEXT_RE),
            ("financial services / controls", FINANCIAL_SERVICES_CONTEXT_RE),
        ),
    )
    product_or_service = detect_first(
        lowered,
        (
            ("assessment and learning systems", r"\b(?:assessment and learning|measurement and learning|learning systems?|assessment systems?|assessment item development|instructional guidance)\b"),
            ("educational content and learning materials", r"\b(?:educational content|learning materials|practice items?|instructional supports?)\b"),
            ("cloud-based platform", r"cloud-based platform|cloud based platform|proprietary cloud-based platform"),
            ("software platform", r"\bplatform\b|\bsoftware\b|\bsolution\b|\bsystem\b"),
            ("professional services", r"\bservices\b|\bconsulting\b|\badvisory\b"),
        ),
    )
    # EDUCATION_AUDIENCE_RE alone is too broad to use as a standalone customer_type
    # signal: bare nouns like "schools" or "districts" also show up in non-education
    # postings (e.g. a consumer brand statement like "in every corner of homes,
    # schools, and offices"). Require it to co-occur with a genuine education-domain
    # signal (EDUCATION_ASSESSMENT_CONTEXT_RE), the same gate business_model and
    # industry already use, before labeling the audience as education-sector.
    customer_type = ""
    if re.search(EDUCATION_ASSESSMENT_CONTEXT_RE, lowered, re.I) and (
        re.search(EDUCATION_AUDIENCE_RE, lowered, re.I) or re.search(r"\blearner-facing\b", lowered, re.I)
    ):
        customer_type = "schools, educators, and learners"
    if not customer_type:
        customer_type = detect_first(
            lowered,
            (
                ("B2B customers or client accounts", r"\bb2b\b|business[- ]to[- ]business|clients?|customer accounts?"),
                ("consumer, patient, or member users", r"\bb2c\b|consumer|patients?|members?"),
            ),
        )
    industry = detect_first(
        lowered,
        (
            ("education / assessment", EDUCATION_ASSESSMENT_CONTEXT_RE),
            ("supply chain / logistics", r"\bsupply chain|logistics|transportation|warehousing|warehouse|trade compliance|order management\b"),
            ("healthcare", HEALTHCARE_CONTEXT_RE),
            ("manufacturing", r"\bmanufacturing|inventory|oem\b"),
            ("software", r"\bsoftware|saas|cloud-based|platform\b"),
            ("financial services", r"\b(?:financial services|banking|insurance|claims)\b"),
            ("customer experience", r"\bcustomer experience|contact center|messaging|chat\b"),
        ),
    )
    geography_match = re.search(
        r"\b(?:United States|U\.S\.|Canada|North America|Atlanta|remote|hybrid|onsite|on-site|global|international)\b",
        text,
        re.I,
    )
    if geography_match is None:
        geography_match = re.search(
            r"\b(?:North American|AMER)\b",
            text,
            re.I,
        )
    scale_match = re.search(
        r"\b(?:\d{1,6}\+?\s+(?:employees|users|customers|clients|accounts|sites|locations|implementations|projects)|"
        r"\d+\s*-\s*\d+\s+(?:employees|users|customers|clients|accounts|projects|implementations))\b",
        text,
        re.I,
    )
    revenue_match = re.search(r"\$\s?\d+(?:\.\d+)?\s?(?:M|MM|million|B|billion)\+?", text, re.I)
    growth_stage = detect_first(
        lowered,
        (
            ("early-stage", r"\bearly[- ]stage|seed|series a|series b|startup\b"),
            ("high-growth", r"\bhigh[- ]growth|scaling|scale-up|rapid growth\b"),
            ("enterprise / mature", r"\benterprise|global|publicly traded|fortune\b"),
        ),
    )
    operational_complexity = detect_first(
        lowered,
        (
            ("multi-project implementation load", r"5\s*[-–]\s*10 implementation|multiple implementation|portfolio"),
            ("cross-functional research and content workflows", r"measurement|content development|learning science|psychometric|ai science|instructional|standards"),
            ("cross-functional delivery", r"cross-functional|engineering|qa|product|support|sales|customer success"),
            ("workflow/data complexity", r"workflow|data migration|integration|api|file transfer|database|validation"),
        ),
    )
    technical_stack = detect_terms(
        lowered,
        (
            ("Jira", r"\bjira\b"),
            ("Azure", r"\bazure\b"),
            ("SQL", r"\bsql\b"),
            ("API", r"\bapi\b|\bapis\b"),
            ("automated file transfers", r"automated file transfer|sftp|file transfer"),
            ("Excel", r"\bexcel\b"),
            ("ERP", r"\berp\b|epicor|aptean"),
        ),
    )
    compliance_signals = detect_terms(
        lowered,
        (
            ("HIPAA", r"\bhipaa\b"),
            ("PHI", r"\bphi\b|protected health information"),
            ("accessibility", r"\baccessibility\b"),
            ("fairness", r"\bfairness\b"),
            ("validity", r"\bvalidity\b"),
            ("regulated data", r"\bcompliance|regulated|audit|access control\b"),
        ),
    )
    role_success_outcomes = detect_terms(
        lowered,
        (
            ("implementation success", r"implementation|go-live|configuration|migration"),
            ("customer adoption", r"adoption|training|enablement|usage"),
            ("customer trust", r"relationship|trusted advisor|communication|partnership"),
            ("delivery quality", r"quality|validation|testing|issue tracking"),
            ("assessment quality", r"assessment quality|instructional appropriateness|accuracy|fact checking|distractor rationale"),
            ("validation quality", r"validity|defensibility|interpretability|monitoring|drift detection"),
            ("instructional alignment", r"learning goals|standards|instructional intent|instructionally aligned"),
            ("risk reduction", r"risk|escalation|compliance|security"),
            ("decision quality", r"dashboard|reporting|analytics|kpi|insight"),
        ),
    )
    return BusinessContext(
        business_model=business_model,
        product_or_service=product_or_service,
        customer_type=customer_type,
        industry=industry,
        geography=normalize_geography_label(geography_match.group(0)) if geography_match else "",
        scale=scale_match.group(0) if scale_match else "",
        revenue_or_account_size=revenue_match.group(0) if revenue_match else "",
        growth_stage=growth_stage,
        operational_complexity=operational_complexity,
        technical_stack=technical_stack,
        compliance_signals=compliance_signals,
        role_success_outcomes=role_success_outcomes,
    )


def context_items(context: BusinessContext) -> list[str]:
    low_signal_items = {"B2B customers or client accounts", "software platform", "professional services"}
    geography = normalize_geography_label(context.geography)
    items = [
        context.business_model,
        context.product_or_service,
        context.customer_type,
        context.industry,
        geography,
        context.scale,
        context.revenue_or_account_size,
        context.growth_stage,
        context.operational_complexity,
    ]
    items.extend(context.technical_stack[:3])
    items.extend(context.compliance_signals[:2])
    items.extend(context.role_success_outcomes[:3])
    out: list[str] = []
    for item in items:
        if item and item not in out:
            out.append(item)
    filtered = [item for item in out if item not in low_signal_items]
    return filtered or out


def business_context_sentence(source_text: str, limit: int = 5) -> str:
    items = context_items(extract_business_context(source_text))
    if not items:
        return ""
    return "Objective business context: " + "; ".join(items[:limit]) + "."


def missing_business_context_fields(source_text: str) -> list[str]:
    context = extract_business_context(source_text)
    required = {
        "business model": context.business_model,
        "product/service": context.product_or_service,
        "customer type": context.customer_type,
        "industry/domain": context.industry,
        "scale": context.scale or context.revenue_or_account_size,
        "success outcomes": ", ".join(context.role_success_outcomes),
    }
    return [label for label, value in required.items() if not value]


def has_generic_fluff(text: str) -> bool:
    return any(re.search(pattern, text, re.I) for pattern in GENERIC_FLUFF_PATTERNS)


def business_fact_count(text: str) -> int:
    return sum(1 for pattern in BUSINESS_FACT_PATTERNS if re.search(pattern, text, re.I))


def business_relevance_score(text: str, job_description: str = "") -> int:
    score = business_fact_count(text) * 3
    if re.search(r"\b\d+(?:\+|%)?\b|\$\s?\d", text):
        score += 5
    if re.search(r"\b(?:reduced|improved|increased|stabilized|launched|built|delivered|enabled|protected|accelerated)\b", text, re.I):
        score += 4
    for item in context_items(extract_business_context(job_description)):
        if item and item.lower() in text.lower():
            score += 3
    if has_generic_fluff(text):
        score -= 5
    return score


def business_context_audit(text: str, job_description: str, label: str = "output") -> list[str]:
    warnings: list[str] = []
    context = extract_business_context(job_description)
    missing = missing_business_context_fields(job_description)
    if len(missing) >= 4:
        warnings.append(f"{label}: job description lacks business context fields worth researching: {', '.join(missing[:4])}.")
    if context_items(context) and business_fact_count(text) < 2:
        warnings.append(f"{label}: output uses too little objective business context from the posting.")
    if has_generic_fluff(text) and business_fact_count(text) < 3:
        warnings.append(f"{label}: generic job-ad language appears without enough business facts, scope, or outcomes.")
    if not re.search(r"\b(?:customer|client|user|patient|account|business|workflow|revenue|risk|quality|adoption|decision)\b", text, re.I):
        warnings.append(f"{label}: output does not clearly connect Christian's work to a business/customer outcome.")
    return warnings


def unsupported_target_context_warnings(text: str, job_description: str, label: str = "output") -> list[str]:
    warnings: list[str] = []
    job_context = extract_business_context(job_description)
    if job_context.industry != "education / assessment" and re.search(
        r"\b(?:schools?|districts?|educators?|teachers?|students?|learners?|assessment and learning|measurement and learning|learning systems?)\b",
        text,
        re.I,
    ):
        warnings.append(f"{label}: introduces education/assessment audience language not supported by the job description.")
    if job_context.industry != "healthcare" and re.search(r"\b(?:patient|patients|clinical|hipaa|phi)\b", text, re.I):
        warnings.append(f"{label}: introduces healthcare language not supported by the job description.")
    if job_context.industry != "financial services" and re.search(r"\b(?:insurance|banking|claims|policyholder)\b", text, re.I):
        warnings.append(f"{label}: introduces financial-services language not supported by the job description.")
    return warnings


def business_context_check_lines(job_description: str) -> list[str]:
    context = extract_business_context(job_description)
    lines = ["Detected Business Context"]
    for label, value in (
        ("Business model", context.business_model),
        ("Product/service", context.product_or_service),
        ("Customer type", context.customer_type),
        ("Industry/domain", context.industry),
        ("Geography", context.geography),
        ("Scale", context.scale),
        ("Revenue/account size", context.revenue_or_account_size),
        ("Growth stage", context.growth_stage),
        ("Operational complexity", context.operational_complexity),
        ("Technical stack", ", ".join(context.technical_stack)),
        ("Compliance signals", ", ".join(context.compliance_signals)),
        ("Role success outcomes", ", ".join(context.role_success_outcomes)),
    ):
        lines.append(f"{label}: {value or 'not detected'}")
    missing = missing_business_context_fields(job_description)
    lines.append("Missing/research before writing: " + (", ".join(missing) if missing else "none obvious"))
    return lines


def business_interview_questions(job_description: str, supplied_context: str = "", limit: int = 10) -> list[BusinessInterviewQuestion]:
    combined = f"{job_description}\n{supplied_context}"
    context = extract_business_context(combined)
    questions: list[BusinessInterviewQuestion] = []
    if context.product_or_service or context.business_model:
        questions.append(BusinessInterviewQuestion(
            "Where does this product or service usually create the most value for customers after implementation?",
            "They need to know whether Christian thinks beyond launch into customer value.",
            "Connect implementation discipline to adoption, workflow clarity, and measurable customer outcomes.",
            "What customer outcome is most important for this team to improve this year?",
            "product/customer value",
        ))
    if context.customer_type:
        questions.append(BusinessInterviewQuestion(
            "Which customer segment creates the most complex implementation or support pattern?",
            "They are testing whether Christian understands customer variation, not just generic project delivery.",
            "Use client portfolio, account health, and workflow discovery examples.",
            "Are customer differences mostly driven by workflow, data, integrations, user training, or account maturity?",
            "customer type",
        ))
    if context.operational_complexity:
        questions.append(BusinessInterviewQuestion(
            "Where do implementations usually lose momentum: scope, data quality, integrations, testing, training, or customer ownership?",
            "The business concern is hidden delivery risk.",
            "Answer with visible risks, named owners, issue tracking, and go-live readiness.",
            "Which blocker would you want the new hire to make more visible in the first 60 days?",
            "implementation risk",
        ))
    if context.technical_stack:
        questions.append(BusinessInterviewQuestion(
            f"How does the team use {', '.join(context.technical_stack[:3])} to manage customer issues and implementation work?",
            "They are checking technical collaboration without needing unsupported tool ownership.",
            "Bridge to documentation, ticket ownership, validation, handoffs, and customer-facing updates.",
            "What information makes a ticket or technical handoff genuinely useful to Engineering, QA, or Support?",
            "technical stack",
        ))
    if context.compliance_signals:
        questions.append(BusinessInterviewQuestion(
            f"How does the team manage {', '.join(context.compliance_signals)} risk during implementation and customer support?",
            "The concern is judgment around regulated data and risk control.",
            "Do not overclaim. Emphasize documentation, validation, access awareness, escalation, and workflow discipline.",
            "Where does compliance risk most often show up in the customer workflow?",
            "compliance",
        ))
    if context.industry == "education / assessment":
        questions.append(BusinessInterviewQuestion(
            "Where does the team draw the line between AI speed and human review when validity, fairness, or accessibility is at stake?",
            "They are testing judgment around quality guardrails, not just enthusiasm for AI.",
            "Bridge to validation habits, stakeholder alignment, documented criteria, and practical escalation when output quality is uncertain.",
            "Which quality signal would you want this hire to make more visible first: validity, fairness, accessibility, or instructional alignment?",
            "education quality",
        ))
    if "customer adoption" in context.role_success_outcomes:
        questions.append(BusinessInterviewQuestion(
            "How do you know customers are actually adopting the platform after training?",
            "They need practical adoption thinking, not feature training.",
            "Use role-based training, customer questions, usage behavior, QBRs, and post-go-live stabilization.",
            "What adoption signal does the team trust most today?",
            "adoption",
        ))
    if "decision quality" in context.role_success_outcomes:
        questions.append(BusinessInterviewQuestion(
            "Which decisions should reporting or analytics help the customer make faster?",
            "The hidden concern is whether reports support decisions or just activity.",
            "Use dashboard/reporting examples and start with the decision behind the data.",
            "Which metric is most trusted today, and which one still gets debated?",
            "decision quality",
        ))
    questions.extend([
        BusinessInterviewQuestion(
            "What would make this hire clearly successful one year from now from the customer's perspective?",
            "They are testing whether Christian can define success in business terms.",
            "Summarize customer outcome, delivery quality, trust, adoption, and risk reduction.",
            "Which customer-facing outcome would you want improved first?",
            "success outcomes",
        ),
        BusinessInterviewQuestion(
            "What usually creates rework for this team?",
            "The business concern is preventable cost, delay, and customer frustration.",
            "Answer with current-state mapping, validation, stakeholder alignment, and root-cause discipline.",
            "Where does rework usually start: requirements, data, integrations, testing, or training?",
            "rework",
        ),
    ])
    unique: list[BusinessInterviewQuestion] = []
    seen: set[str] = set()
    for question in questions:
        if question.question.lower() in seen:
            continue
        unique.append(question)
        seen.add(question.question.lower())
        if len(unique) >= limit:
            break
    return unique


def business_question_lines(job_description: str, supplied_context: str = "", limit: int = 8) -> list[str]:
    lines: list[str] = []
    for item in business_interview_questions(job_description, supplied_context, limit):
        lines.append(
            f"{item.question} Hidden concern: {item.hidden_concern} Answer angle: {item.answer_angle} Ask back: {item.ask_back}"
        )
    return lines


def post_round_business_questions(notes_text: str) -> list[BusinessInterviewQuestion]:
    return business_interview_questions(notes_text, notes_text, limit=8)


def question_quality_warnings(questions: list[str]) -> list[str]:
    warnings: list[str] = []
    weak = re.compile(r"\b(culture like|day in the life|work-life balance|team dynamic|what do you like)\b", re.I)
    strong = re.compile(r"\b(customer|client|workflow|risk|implementation|data|quality|adoption|metric|success|handoff|support|rework|value)\b", re.I)
    for question in questions:
        if weak.search(question) and not strong.search(question):
            warnings.append(f"Weak question should be reframed around contribution or business outcome: {question}")
    return warnings
