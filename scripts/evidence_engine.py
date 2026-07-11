"""Provenance-bearing evidence catalog, matching, and safe terminology injection."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from requirement_engine import RequirementElement, RequirementStatus, canonical_terms, normalize_key, normalize_text
from config.paths import FEDERAL_RESUME_SOURCE


@dataclass(frozen=True)
class EvidenceRecord:
    record_id: str
    source_path: str
    employer: str
    role: str
    text: str
    capability_tags: tuple[str, ...]
    allowed_terminology: tuple[str, ...]
    adjacent_terminology: tuple[str, ...]
    ownership_ceiling: str
    rewrite_templates: tuple[str, ...]
    confirmed_on: str = ""
    provenance: str = "approved-source"
    never_claim: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvidenceMatch:
    element_id: str
    status: RequirementStatus
    evidence_ids: tuple[str, ...]
    rationale: str
    required_terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class CoverageReport:
    matches: tuple[EvidenceMatch, ...]
    visible_hits: tuple[str, ...]
    missing_direct: tuple[str, ...]
    never_claim_hits: tuple[str, ...]
    competency_hits: tuple[str, ...] = ()
    competency_misses: tuple[str, ...] = ()
    intake_questions: tuple[str, ...] = ()


@dataclass(frozen=True)
class CanonicalEvidence:
    id: str
    employer: str
    role: str
    source_text: str
    claim: str
    metrics: tuple[str, ...]
    lane_signals: tuple[str, ...]
    authorized: bool = True
    support_terms: tuple[str, ...] = ()


CANONICAL_EVIDENCE: tuple[CanonicalEvidence, ...] = (
    CanonicalEvidence(
        id="inv_automation",
        employer="East West Manufacturing",
        role="Enterprise Systems Manager",
        source_text="Reduced manual inventory adjustment work by 78% and lowered discrepancies by 22% by diagnosing a recurring warehouse accuracy problem and building an automated, auditable workflow in Aptean Intuitive.",
        claim="reduced manual inventory work by 78% and discrepancies by 22% by building an automated, auditable workflow",
        metrics=("78%", "22%"),
        lane_signals=("process improvement", "operations", "automation", "implementation"),
        support_terms=("78%", "22%", "inventory adjustment"),
    ),
    CanonicalEvidence(
        id="bi_tools",
        employer="East West Manufacturing",
        role="Enterprise Systems Manager",
        source_text="Increased operational visibility for leadership by building 200+ SQL-based KPI dashboards, Crystal Reports, and Power BI tools that replaced raw exports and verbal status updates with clearer operating decisions.",
        claim="built 200+ SQL-based KPI dashboards and reporting tools that replaced raw exports with clearer operating decisions",
        metrics=("200+", "SQL"),
        lane_signals=("analytics", "reporting", "kpi", "dashboard"),
        support_terms=("200+", "dashboards"),
    ),
    CanonicalEvidence(
        id="client_side_owner",
        employer="East West Manufacturing",
        role="Enterprise Systems Manager",
        source_text="Partnered directly with plant controllers, accounting managers, and the CFO on month-end and year-end close, inventory adjustment, and audit readiness across five sites, owning ERP data integrity for finance and operations.",
        claim="owned the client-side ERP for 150+ users across five sites, partnering with the CFO and plant controllers on financial close",
        metrics=("150+", "five sites"),
        lane_signals=("erp", "implementation", "finance", "client side"),
        support_terms=("plant controllers", "cfo"),
    ),
    CanonicalEvidence(
        id="amazon_cert",
        employer="East West Manufacturing",
        role="Enterprise Systems Manager",
        source_text="Passed Amazon Robotics certification before go-live during a six-month warehouse setup, configuring every product family, bill of materials, and component structure while coordinating with the CFO, plant controllers, vendors, and Amazon's compliance team.",
        claim="stood up a new warehouse in the ERP and passed Amazon Robotics certification before go-live over a six-month process",
        metrics=("Amazon Robotics", "six-month"),
        lane_signals=("go-live", "compliance", "configuration", "rollout", "implementation"),
        support_terms=("Amazon Robotics",),
    ),
    CanonicalEvidence(
        id="migration_readiness",
        employer="East West Manufacturing",
        role="Enterprise Systems Manager",
        source_text="Reduced migration and audit risk from Aptean Intuitive to Epicor Kinetic by extracting, querying, transforming, updating, and validating system/database records through ETL tools, SQL checks, user access reviews, control validation, and cutover coordination.",
        claim="protected migration readiness during the Epicor Kinetic transition through ETL validation and SQL checks",
        metrics=("ETL", "SQL"),
        lane_signals=("data migration", "testing", "validation", "implementation"),
        support_terms=("ETL", "SQL"),
    ),
    CanonicalEvidence(
        id="aptean_portfolio",
        employer="Aptean",
        role="Customer Success Consultant",
        source_text="Protected delivery quality and customer trust across 80+ international manufacturing clients in a $6M+ book of business by running full-lifecycle Aptean Encompix delivery from discovery and configuration through data migration, testing, training, and post-go-live adoption, partnering with Product Management and Product Ownership on an Agile development team throughout.",
        claim="carried 80+ international ERP client engagements from discovery through go-live and post-go-live support",
        metrics=("80+", "$6M+"),
        lane_signals=("implementation", "client", "go-live", "requirements", "customer success"),
        support_terms=("80+", "post-go-live support"),
    ),
    CanonicalEvidence(
        id="account_recovery",
        employer="Aptean",
        role="Customer Success Consultant",
        source_text="Stabilized at-risk accounts within a $6M+ client book of business, protecting $1M+ in at-risk annual revenue by consolidating case ownership, leading structured recovery sessions, and converting complex integration and customization failures into retained customer trust.",
        claim="stabilized at-risk accounts and protected $1M+ in annual revenue by consolidating ownership and leading recovery",
        metrics=("$1M+",),
        lane_signals=("risk", "retention", "revenue", "customer success"),
        support_terms=("$1M+", "at-risk"),
    ),
    CanonicalEvidence(
        id="executive_workshops",
        employer="Aptean",
        role="Customer Success Consultant",
        source_text="Strengthened renewal and expansion confidence by facilitating 60+ executive workshops and QBRs that aligned implementation roadmaps to business objectives, adoption progress, and measurable outcomes.",
        claim="facilitated 60+ executive workshops and QBRs that aligned implementation roadmaps to business objectives and measurable outcomes",
        metrics=("60+", "QBRs"),
        lane_signals=("executive", "stakeholder", "qbr", "alignment", "customer success"),
        support_terms=("60+", "QBR"),
    ),
    CanonicalEvidence(
        id="salesforce_release_coordination",
        employer="Aptean",
        role="Customer Success Consultant",
        source_text="Partnered with Product Management and Product Ownership on an Agile development team while supporting Salesforce Service Cloud, Marketing Cloud, AppExchange, and development tools, translating business needs into backlog-ready requirements and user stories that helped drive adoption across customer-facing teams.",
        claim="translated business needs into backlog-ready requirements and user stories across Salesforce customer workflows",
        metrics=("Salesforce",),
        lane_signals=("product", "agile", "salesforce", "requirements", "prioritization"),
        support_terms=("Salesforce",),
    ),
    CanonicalEvidence(
        id="livengage_workflows",
        employer="The Home Depot",
        role="Business Analyst",
        source_text="Configured LivePerson LiveEngage chat and text workflows, automated greetings and closings, and customer-facing messaging improvements during an enterprise SMS pilot.",
        claim="configured LivePerson LiveEngage workflows, automated greetings and closings, and customer messaging improvements during an enterprise SMS pilot",
        metrics=("LivePerson LiveEngage",),
        lane_signals=("automation", "ai", "chatbot", "messaging", "workflow"),
        support_terms=("LivePerson LiveEngage", "automated greetings and closings", "SMS pilot"),
    ),
    CanonicalEvidence(
        id="modernization_13mo",
        employer="Aptean",
        role="Customer Success Consultant",
        source_text="Led a full ERP modernization engagement where requirements gathering revealed infrastructure too outdated to run the software, tens of thousands in hardware upgrades were required before implementation could begin, and a project scoped for four to seven months ran about thirteen while keeping the client satisfied and opening billable customization work.",
        claim="kept a client confident through a 13-month modernization after surfacing infrastructure too outdated to run the software",
        metrics=("13-month",),
        lane_signals=("expectation management", "risk", "hardware", "resistance", "implementation"),
        support_terms=("13-month",),
    ),
)


NEVER_CLAIM_PATTERNS: tuple[tuple[str, str], ...] = (
    ("SQL_SERVER_INSTANCE_ADMIN", r"\b(?:administered|configured|monitored|tuned|maintained)\s+(?:enterprise\s+)?(?:microsoft\s+)?sql server(?:\s+(?:instances|environments))?\b"),
    ("SQL_HA_ADMIN", r"\b(?:owned|administered|designed|managed)\b[^.]{0,80}\b(?:clustering|replication|failover|high availability)\b"),
    ("CICD_OWNERSHIP", r"\b(?:owned|administered|led|designed)\b[^.]{0,80}\b(?:ci/cd|continuous integration|devsecops)\b"),
    ("WORKFORCE_MANAGEMENT_OWNERSHIP", r"\b(?:owned|administered|led|managed)\s+workforce management\b"),
    ("ADERANT_RECOVERY_OWNERSHIP", r"\b(?:owned|administered|led)\b[^.]{0,80}\b(?:backup|restore|recovery)\b"),
)

COMPETENCY_VARIANTS: dict[str, tuple[str, ...]] = {
    "attention to detail": ("data quality", "validation", "accuracy", "quality control"),
    "customer service": ("customer", "client", "service quality"),
    "decision making": ("decision", "recommendation", "tradeoff"),
    "information management": ("reporting", "documentation", "data governance"),
    "interpersonal skills": ("stakeholder", "cross-functional", "workshop"),
    "oral communication": ("workshop", "presentation", "training"),
    "problem solving": ("troubleshooting", "root cause", "resolved"),
    "team work": ("cross-functional", "team"),
    "teamwork": ("cross-functional", "team"),
    "technical competence": ("technical", "sql", "enterprise systems"),
    "flexibility": ("migration", "transition", "change"),
    "influencing/negotiating": ("stakeholder alignment", "vendor tradeoffs", "advisory"),
    "integrity/honesty": ("audit readiness", "internal control", "compliance"),
    "learning": ("training", "professional development", "adoption"),
    "reading comprehension": ("requirements", "documentation"),
    "reasoning": ("analysis", "recommendations", "risk"),
    "self-management": ("independently", "ownership", "concurrent workstreams"),
    "stress tolerance": ("high-risk", "operational continuity", "launch readiness"),
    "accountability": ("ownership", "accountability", "responsible"),
}


CONFIRMED_BULLET_TEMPLATES: dict[str, str] = {
    "east-west-sql-reporting-objects": (
        "Designed and deployed 200+ SQL-based reporting and business-intelligence tools, personally creating views, "
        "stored procedures, functions, and reporting data models that improved operational visibility for manufacturing, "
        "supply chain, finance, and engineering leaders."
    ),
    "aderant-backup-recovery": (
        "Supported backup and restore tasks and performed recovery testing alongside disaster-recovery planning, "
        "documenting dependencies and operational risks without owning backup or high-availability infrastructure."
    ),
    "aptean-version-control": (
        "Used Azure DevOps/TFS and Git/GitHub directly for work items, repositories, release tracking, and delivery "
        "change-management practices across customer implementation work."
    ),
    "home-depot-contact-center": (
        "Analyzed LivePerson chat and SMS customer interaction data for contact center operations, producing service "
        "level reporting, interaction-volume trend analysis, and forecasting that supported workload and staffing decisions."
    ),
}


def load_evidence_catalog(source_json: Path) -> tuple[EvidenceRecord, ...]:
    payload = json.loads(source_json.read_text(encoding="utf-8"))
    records: list[EvidenceRecord] = []
    for role_index, role in enumerate(payload.get("roles", ())):
        for bullet_index, bullet in enumerate(role.get("bullets", ())):
            record_id = f"federal-role-{role_index}-bullet-{bullet_index}"
            records.append(
                EvidenceRecord(
                    record_id=record_id,
                    source_path=str(source_json),
                    employer=role.get("company", ""),
                    role=role.get("title", ""),
                    text=normalize_text(bullet),
                    capability_tags=canonical_terms(bullet),
                    allowed_terminology=canonical_terms(bullet),
                    adjacent_terminology=(),
                    ownership_ceiling="source-text",
                    rewrite_templates=(normalize_text(bullet),),
                )
            )
    for item in payload.get("confirmed_evidence", ()):
        record_id = str(item["id"])
        records.append(
            EvidenceRecord(
                record_id=record_id,
                source_path=str(source_json),
                employer=str(item["employer"]),
                role=str(item["role"]),
                text=normalize_text(item["claim"]),
                capability_tags=tuple(
                    dict.fromkeys(
                        (*canonical_terms(item["claim"]), *(str(value).lower() for value in item.get("allowed_terminology", ())))
                    )
                ),
                allowed_terminology=tuple(item.get("allowed_terminology", ())),
                adjacent_terminology=tuple(item.get("adjacent_terminology", ())),
                ownership_ceiling=str(item.get("ownership_ceiling", "supported")),
                rewrite_templates=tuple(
                    item.get("rewrite_templates")
                    or (CONFIRMED_BULLET_TEMPLATES.get(record_id, normalize_text(item["claim"])),)
                ),
                confirmed_on=str(item.get("confirmed_on", "")),
                provenance=str(item.get("provenance", "")),
                never_claim=tuple(item.get("never_claim", ())),
            )
        )
    return tuple(records)


def commercial_canonical_evidence(*, authorized_only: bool = True) -> tuple[CanonicalEvidence, ...]:
    if not authorized_only:
        return CANONICAL_EVIDENCE
    return tuple(item for item in CANONICAL_EVIDENCE if item.authorized)


def canonical_evidence_support_terms(item: CanonicalEvidence) -> tuple[str, ...]:
    if item.support_terms:
        return item.support_terms
    return item.metrics or tuple(
        word
        for word in re.findall(r"[A-Za-z0-9][A-Za-z0-9+./-]{2,}", item.source_text)
        if len(word) >= 3
    )


def confirmed_bullets_by_role(source_json: Path) -> dict[tuple[str, str], tuple[str, ...]]:
    grouped: dict[tuple[str, str], list[str]] = {}
    for record in load_evidence_catalog(source_json):
        if record.provenance != "christian-direct-confirmation":
            continue
        grouped.setdefault((record.employer, record.role), []).append(record.rewrite_templates[0])
    return {key: tuple(values) for key, values in grouped.items()}


def _term_hit(text: str, term: str) -> bool:
    normalized_text = normalize_key(text)
    normalized_term = normalize_key(term)
    return bool(normalized_term and normalized_term in normalized_text)


def match_requirement(element: RequirementElement, records: tuple[EvidenceRecord, ...]) -> EvidenceMatch:
    lowered_element = normalize_key(element.text)
    if "sql server" in lowered_element and re.search(r"\b(administering|configuring|monitoring|tuning|maintaining)\b", lowered_element):
        return EvidenceMatch(element.element_id, RequirementStatus.UNSUPPORTED, (), "SQL Server instance administration was not confirmed.", element.canonical_terms)
    if "database administration" in lowered_element and re.search(r"\b(leadership|guidance|administering|administration)\b", lowered_element):
        return EvidenceMatch(element.element_id, RequirementStatus.UNSUPPORTED, (), "Database-administration leadership was not confirmed.", element.canonical_terms)
    if re.search(r"\b(clustering|replication|failover|high availability)\b", lowered_element):
        recovery_ids = tuple(record.record_id for record in records if record.record_id == "aderant-backup-recovery")
        return EvidenceMatch(element.element_id, RequirementStatus.ADJACENT, recovery_ids, "Backup, restore, and recovery testing are supported; HA/DR administration is not.", element.canonical_terms)
    if "workforce management" in lowered_element or "workforce management" in element.canonical_terms:
        contact_ids = tuple(record.record_id for record in records if record.record_id == "home-depot-contact-center")
        return EvidenceMatch(element.element_id, RequirementStatus.ADJACENT, contact_ids, "Contact-center analytics supported staffing and workload decisions; workforce management remains bridge-only.", element.canonical_terms)
    if "devsecops" in lowered_element or "automated deployment" in lowered_element:
        version_ids = tuple(record.record_id for record in records if record.record_id == "aptean-version-control")
        return EvidenceMatch(element.element_id, RequirementStatus.ADJACENT, version_ids, "Direct version-control use is supported; CI/CD and DevSecOps ownership are not.", element.canonical_terms)

    direct: list[str] = []
    adjacent: list[str] = []
    transferable: list[str] = []
    element_terms = set(element.canonical_terms)
    element_tokens = {token for token in normalize_key(element.text).split() if len(token) >= 5}

    for record in records:
        allowed = set(record.capability_tags) | {term.lower() for term in record.allowed_terminology}
        if element_terms and any(term in allowed or any(_term_hit(term, candidate) for candidate in allowed) for term in element_terms):
            direct.append(record.record_id)
            continue
        if any(_term_hit(element.text, term) for term in record.allowed_terminology):
            direct.append(record.record_id)
            continue
        if any(_term_hit(element.text, term) for term in record.adjacent_terminology):
            adjacent.append(record.record_id)
            continue
        record_tokens = {token for token in normalize_key(record.text).split() if len(token) >= 5}
        overlap = element_tokens & record_tokens
        if len(overlap) >= 3:
            transferable.append(record.record_id)

    if direct:
        return EvidenceMatch(element.element_id, RequirementStatus.DIRECT, tuple(dict.fromkeys(direct)), "Allowed terminology and source capability align.", element.canonical_terms)
    if adjacent:
        return EvidenceMatch(element.element_id, RequirementStatus.ADJACENT, tuple(dict.fromkeys(adjacent)), "A neighboring capability is supported; bridge language is required.", element.canonical_terms)
    if transferable:
        return EvidenceMatch(element.element_id, RequirementStatus.TRANSFERABLE, tuple(dict.fromkeys(transferable[:3])), "Transferable source evidence overlaps but does not establish the named capability.", element.canonical_terms)
    return EvidenceMatch(element.element_id, RequirementStatus.UNSUPPORTED, (), "No approved evidence record supports this capability.", element.canonical_terms)


def match_requirements(elements: tuple[RequirementElement, ...], records: tuple[EvidenceRecord, ...]) -> tuple[EvidenceMatch, ...]:
    return tuple(match_requirement(element, records) for element in elements)


def inject_direct_evidence(
    role_bullets: tuple[str, ...],
    employer: str,
    role: str,
    matches: tuple[EvidenceMatch, ...],
    records: tuple[EvidenceRecord, ...],
) -> tuple[str, ...]:
    matched_ids = {evidence_id for match in matches if match.status == RequirementStatus.DIRECT for evidence_id in match.evidence_ids}
    additions: list[str] = []
    for record in records:
        if record.record_id not in matched_ids or record.employer != employer or record.role != role:
            continue
        if record.provenance != "christian-direct-confirmation":
            continue
        additions.extend(record.rewrite_templates)
    return tuple(dict.fromkeys((*role_bullets, *additions)))


def never_claim_hits(text: str) -> tuple[str, ...]:
    hits = [rule_id for rule_id, pattern in NEVER_CLAIM_PATTERNS if re.search(pattern, text, re.I)]
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
    for record in load_evidence_catalog(FEDERAL_RESUME_SOURCE):
        for phrase in record.never_claim:
            normalized_phrase = normalize_key(phrase)
            if not normalized_phrase:
                continue
            matched_sentences = [sentence for sentence in sentences if normalized_phrase in normalize_key(sentence)]
            if normalized_phrase in {"clustering", "replication", "failover"}:
                matched_sentences = [
                    sentence
                    for sentence in matched_sentences
                    if re.search(r"\b(?:sql|server|database|backup|recovery|ha|dr|infrastructure|instance)\b", sentence, re.I)
                ]
            if matched_sentences:
                hits.append(f"RECORD_NEVER_CLAIM:{record.record_id}:{normalized_phrase}")
    return tuple(dict.fromkeys(hits))


def build_coverage_report(
    elements: tuple[RequirementElement, ...],
    matches: tuple[EvidenceMatch, ...],
    visible_work_text: str,
    *,
    competencies: tuple[str, ...] = (),
) -> CoverageReport:
    by_id = {element.element_id: element for element in elements}
    visible_hits: list[str] = []
    missing_direct: list[str] = []
    questions: list[str] = []
    for match in matches:
        element = by_id[match.element_id]
        terms = match.required_terms or element.canonical_terms
        visible = not terms or any(_term_hit(visible_work_text, term) for term in terms)
        if match.status == RequirementStatus.DIRECT and visible:
            visible_hits.append(match.element_id)
        elif match.status == RequirementStatus.DIRECT:
            missing_direct.append(match.element_id)
        elif match.status == RequirementStatus.UNSUPPORTED and not (
            match.rationale.startswith("SQL Server instance administration was not confirmed")
            or match.rationale.startswith("Database-administration leadership was not confirmed")
        ):
            capability = terms[0] if terms else normalize_text(element.text)[:120]
            questions.append(f"Did your work involve {capability}? If confirmed, identify the employer, role, and scope so it can become claimable.")
    competency_hits = tuple(
        item
        for item in competencies
        if _term_hit(visible_work_text, item)
        or any(_term_hit(visible_work_text, variant) for variant in COMPETENCY_VARIANTS.get(item.lower(), ()))
    )
    competency_misses = tuple(item for item in competencies if item not in competency_hits)
    return CoverageReport(
        matches=matches,
        visible_hits=tuple(visible_hits),
        missing_direct=tuple(missing_direct),
        never_claim_hits=never_claim_hits(visible_work_text),
        competency_hits=competency_hits,
        competency_misses=competency_misses,
        intake_questions=tuple(dict.fromkeys(questions)),
    )
