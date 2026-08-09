"""Neutral shared interview-story logic used by interview and qualifications builders."""
from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Sequence

import proof_text
import prose_engine
import question_prep
import resume_analysis
from config.job_profiles import TARGETING_LANES
from resume_analysis import CORPORATE_STRATEGY_PROFILE, JobProblemProfile
from text_safety import neutralize_conflicting_region_lists
from utils import fail, join_answer_sentences

COMPANY_EAST_WEST = "East West Manufacturing"
COMPANY_APTEAN = "Aptean"
COMPANY_HOME_DEPOT = "The Home Depot"

def effective_lane_key(role_title: str, job_description: str, profile: JobProblemProfile) -> str:
    role_lower = role_title.lower(); role_and_jd = f"{role_title}\n{job_description}".lower()
    change_signals = r"\b(change enablement|change management|change adoption|organiz(?:ation|ational) development|org development|organiz(?:ation|ational) design|leadership development|team effectiveness|workforce transformation)\b"
    strategy_signals = r"\b(strategy|transformation|recommendations?|business case|gap analysis|root cause|process flows?|standard operating procedures)\b"
    if re.search(r"\b(strategy|transformation|operating model)\b", role_lower): return "corporate_strategy"
    if profile.primary_lane == "implementation_delivery" and (re.search(r"\b(project manager|program manager|implementation|go-live|migration|scrum)\b", role_lower) or re.search(r"\b(sdlc|software development lifecycle|workstreams?|delivery|implementation|uat|training|rollout|milestones|risk registers?)\b", role_and_jd)): return "implementation_delivery"
    if re.search(change_signals, role_and_jd): return "change_enablement"
    if profile.primary_lane == "corporate_strategy" and re.search(r"\b(consultant|consulting|advisory|advisor)\b", role_lower) and re.search(strategy_signals, role_and_jd) and not re.search(change_signals, role_and_jd): return "corporate_strategy"
    if re.search(r"\b(data analyst|analytics analyst|business analyst|reporting analyst|analytics|reporting|insights|measurement)\b", role_lower): return "analytics_operations"
    if re.search(r"\b(process engineer|process improvement|continuous improvement|lean six sigma|root cause)\b", role_lower): return "process_improvement"
    if re.search(r"\b(implementation|implementation project manager|technical implementation manager|go-live|configuration|migration)\b", role_lower): return "implementation_delivery"
    if re.search(r"\b(customer success|client success|partner success|csm|renewal|retention manager|account manager)\b", role_lower): return "customer_success"
    support_title_signal = re.search(r"\b(customer experience|customer support|support specialist|support agent|member services|member support|cx)\b", role_lower)
    support_jd_signal = re.search(r"\b(customer experience|customer support|support specialist|support agent|member services|member support|cx)\b", role_and_jd)
    support_pain_signal = re.search(r"\b(escalation|retention|billing|membership|zendesk|phone|email|vip|human touch)\b", role_and_jd)
    stronger_non_cs_title_signal = re.search(r"\b(implementation|consultant|consulting|project manager|program manager|analyst|strategy|transformation|change|process|data|reporting|solution|solutions|architect|product owner|scrum master)\b", role_lower)
    if support_title_signal: return "customer_success"
    if support_jd_signal and support_pain_signal and profile.primary_lane == "customer_success" and not stronger_non_cs_title_signal: return "customer_success"
    if re.search(r"\b(solutions engineer|solution engineer|solution consultant|solution consulting|pre-sales|presales|sales engineer)\b", role_lower): return "presales_solution"
    if profile.primary_lane == "analytics_operations": return profile.primary_lane
    if profile.primary_lane == "implementation_delivery" and re.search(r"\b(implementation|integration|integrations|data migration|data migrations|migration|migrations|requirements|testing|delivery|go-live|api|apis)\b", role_and_jd): return profile.primary_lane
    if re.search(r"\b(solutions engineer|solution engineer|solution consultant|solution consulting|pre-sales|presales|demo)\b", role_and_jd): return "presales_solution"
    if re.search(r"\b(process improvement|process engineer|lean six sigma|root cause|standard work|cost[- ]benefit|service quality|workflow redesign|continuous improvement)\b", role_and_jd): return "process_improvement"
    if re.search(r"\b(customer success|client success|csm|account manager|renewal|expansion)\b", role_and_jd): return "customer_success"
    if re.search(r"\b(change adoption|change management|change enablement|ways of working)\b", role_and_jd): return "change_enablement"
    return profile.primary_lane

def adjust_profile_for_lane(profile: JobProblemProfile, lane_key: str) -> JobProblemProfile:
    if lane_key == profile.primary_lane: return profile
    lane = next((item for item in TARGETING_LANES if item["key"] == lane_key), None)
    if lane is None and lane_key == str(CORPORATE_STRATEGY_PROFILE["key"]): lane = CORPORATE_STRATEGY_PROFILE
    if not lane: return profile
    return replace(profile, primary_lane=str(lane["key"]), lane_label=str(lane["label"]), core_problem=str(lane["problem"]), audience=str(lane["audience"]), outcomes=tuple(str(item) for item in lane["outcomes"]))

@dataclass(frozen=True)
class StoryCard:
    title: str
    story_types: tuple[str, ...]
    hook: str
    takeaways: tuple[str, str, str]
    evidence: str
    level3_trait: str
    result: str
    outcome: str
    evidence_terms: tuple[str, ...]
    signals: tuple[str, ...]
    boost_key: str = ""
    sensitive_note: str = ""
@dataclass(frozen=True)
class InterviewQuestion:
    question: str
    angle: str
def lower_clause(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip().rstrip(".")
    if not cleaned:
        return ""
    return cleaned[:1].lower() + cleaned[1:] if cleaned[:1].isupper() else cleaned
_ACTION_FRAGMENT_STARTS = {
    "built",
    "configured",
    "coordinated",
    "created",
    "delivered",
    "developed",
    "drove",
    "enabled",
    "facilitated",
    "improved",
    "increased",
    "kept",
    "launched",
    "led",
    "maintained",
    "managed",
    "mapped",
    "negotiated",
    "owned",
    "protected",
    "reduced",
    "stabilized",
    "supported",
    "tracked",
    "translated",
    "turned",
    "used",
    "validated",
}
def starts_with_action_fragment(text: str) -> bool:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return False
    first = re.sub(r"[^A-Za-z'-]", "", cleaned.split()[0]).lower()
    return bool(first) and (first in _ACTION_FRAGMENT_STARTS or first.endswith("ed"))
def story_evidence_sentence(text: str) -> str:
    cleaned = neutralize_conflicting_region_lists(re.sub(r"\s+", " ", text).strip().rstrip("."))
    if not cleaned:
        return ""
    if spoken_word_count(cleaned) > 28 and ":" in cleaned:
        lead, detail = (part.strip() for part in cleaned.split(":", 1))
        lead_sentence = story_evidence_sentence(lead)
        detail = re.sub(r"^a\s+", "It was a ", detail, flags=re.I)
        if re.search(r"\s+across coordination with\s+", detail, re.I):
            work, partners = re.split(r"\s+across coordination with\s+", detail, maxsplit=1, flags=re.I)
            return interview_join(lead_sentence, work, f"I coordinated with {partners}")
        return interview_join(lead_sentence, detail)
    lowered = cleaned.lower()
    if lowered.startswith("i "):
        return cleaned
    if lowered.startswith("at "):
        return cleaned
    if starts_with_action_fragment(cleaned):
        return f"I {lower_clause(cleaned)}"
    return f"My role was to {lower_clause(cleaned)}"
def tighten_story_result_text(text: str) -> str:
    cleaned = proof_text.rewrite_dense_proof_patterns(
        neutralize_conflicting_region_lists(re.sub(r"\s+", " ", text).strip().rstrip("."))
    )
    replacements = (
        (
            r"\bkept core manufacturing and finance operations running across North America and Asia while improving the ERP system through training, testing, and release readiness\b",
            "kept core operations and finance workflows stable across North America and Asia during ERP improvement work",
        ),
        (
            r"\bimproved post-go-live follow-through, clearer issue ownership, and more reliable coordination across customer-facing teams\b",
            "improved post-go-live ownership and coordination across customer-facing teams",
        ),
        (
            r"\bhelped manufacturing clients across the Americas, Europe, and Asia move through full lifecycle ERP implementation with clearer scope and lower delivery risk\b",
            "helped international manufacturing clients move through ERP implementation with clearer scope and lower delivery risk",
        ),
    )
    for pattern, replacement in replacements:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.I)
    return cleaned
def story_result_sentence(text: str) -> str:
    cleaned = tighten_story_result_text(text)
    if not cleaned:
        return ""
    lowered = cleaned.lower()
    if lowered.startswith(("the result was ", "the work ", "it ", "this ")):
        return cleaned
    if starts_with_action_fragment(cleaned):
        return f"The work {lower_clause(cleaned)}"
    return f"The result was {lower_clause(cleaned)}"
def story_company_hint(card: StoryCard, fallback: str = "") -> str:
    searchable = f"{card.title} {card.hook} {card.evidence} {card.result}"
    if re.search(r"\bEast West\b", searchable, re.I):
        return COMPANY_EAST_WEST
    if re.search(r"\bAptean\b", searchable, re.I):
        return COMPANY_APTEAN
    if re.search(r"\bHome Depot\b", searchable, re.I):
        return COMPANY_HOME_DEPOT
    return fallback
def concrete_story_opening(card: StoryCard, company: str = "") -> str:
    company_name = story_company_hint(card, company)
    hook = re.sub(r"\s+", " ", card.hook).strip().rstrip(".")
    if company_name and not re.match(r"^at\s+", hook, re.I) and not re.search(re.escape(company_name), hook, re.I):
        hook = f"At {company_name}, {lower_clause(hook)}"
    elif not company_name:
        hook = hook[:1].upper() + hook[1:]
    return hook
def spoken_level3_trait_sentence(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip().rstrip(".")
    if not cleaned:
        return ""
    lowered = cleaned.lower()
    if lowered.startswith("show what was noticed:"):
        detail = cleaned.split(":", 1)[1].strip()
        segments = re.split(r"\.\s*show what was done:\s*", detail, maxsplit=1, flags=re.I)
        noticed = segments[0]
        noticed_sentence = f"The key early signal was that {lower_clause(noticed)}"
        if len(segments) == 2 and segments[1]:
            return interview_join(noticed_sentence, story_evidence_sentence(segments[1]))
        return noticed_sentence
    if lowered.startswith("show what was noticed in the room:"):
        detail = lower_clause(cleaned.split(":", 1)[1].strip())
        return f"The key early signal was that {detail}"
    if lowered.startswith("show the constraint that made this hard:"):
        detail = cleaned.split(":", 1)[1].strip()
        detail = re.sub(r"\s+[—–]\s+", ". ", detail)
        detail = re.sub(r"\.\s+([a-z])", lambda match: f". {match.group(1).upper()}", detail)
        return interview_join("The constraint was clear", detail)
    if lowered.startswith("show how "):
        detail = lower_clause(cleaned[9:].strip())
        return f"The key early signal was that {detail}"
    if lowered.startswith("show the changed behavior:"):
        detail = lower_clause(cleaned.split(":", 1)[1].strip())
        return f"What changed afterward was {detail}"
    if lowered.startswith("show what was done:"):
        detail = cleaned.split(":", 1)[1].strip()
        return story_evidence_sentence(detail)
    if lowered.startswith("show "):
        detail = lower_clause(cleaned[5:].strip())
        return f"The key early signal was that {detail}"
    return f"The key early signal was {lower_clause(cleaned)}"
STANDARD_SPOKEN_WORD_RANGE = (95, 140)
def interview_join(*parts: str) -> str:
    """Join deliberately ordered interview sentences without changing shared prose helpers."""
    return join_answer_sentences(*parts)
def candidate_problem_phrase(profile: resume_analysis.JobProblemProfile) -> str:
    return question_prep.candidate_problem_phrase(profile)
INSTRUCTIONAL_OPENING_RE = re.compile(
    r"^(?:use|choose|answer like|lead with|do not|when asked|this is the same question)\b",
    re.I,
)
def spoken_word_count(text: str) -> int:
    return len(re.findall(r"\b[\w+.#'-]+\b", text))
def assert_full_spoken_answer(label: str, text: str, *, min_words: int = 35) -> None:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if spoken_word_count(cleaned) < min_words:
        fail(f"{label} is too short to sound like a full spoken answer")
    if INSTRUCTIONAL_OPENING_RE.search(cleaned):
        fail(f"{label} still reads like coaching instructions instead of a spoken answer")
def safe_evidence_term_matches(text: str, term: str) -> bool:
    """Match a source-backed evidence phrase without unsafe substring leakage."""
    normalized = re.sub(r"\s+", " ", term.strip().lower())
    if len(normalized) < 5:
        return False
    if not normalized:
        return False
    escaped = re.escape(normalized)
    prefix = r"(?<![a-z0-9])" if normalized[0].isalnum() else ""
    suffix = r"(?![a-z0-9])" if normalized[-1].isalnum() else ""
    return re.search(prefix + escaped + suffix, text.lower()) is not None
def contains_all(text: str, fragments: tuple[str, ...], *, safe: bool = False) -> bool:
    if safe:
        return all(safe_evidence_term_matches(text, fragment) for fragment in fragments)
    lowered = text.lower()
    return all(fragment.lower() in lowered for fragment in fragments)
def signal_score(job_description: str, signals: tuple[str, ...]) -> int:
    lowered = job_description.lower()
    return sum(1 for signal in signals if signal.lower() in lowered)
def adjusted_profile_for_role(
    profile: resume_analysis.JobProblemProfile,
    role_title: str,
    job_description: str,
) -> resume_analysis.JobProblemProfile:
    lane_key = effective_lane_key(role_title, job_description, profile)
    return adjust_profile_for_lane(profile, lane_key)
def expanded_story_bank() -> list[StoryCard]:
    cards = [
        StoryCard(
            title="EFT/ACH payment integration replacement",
            story_types=("Managing and Leading", "Teamwork", "Ambiguous Problem", "Analysis and Decision"),
            hook="At East West Manufacturing, a five-month EFT/ACH payment integration replacement had to restore reliable, compliant payments across IT, finance, Aptean, and Truist Bank.",
            takeaways=("Mapped the full payment chain", "Aligned four parties without direct authority", "Kept compliance and auditability visible from the start"),
            evidence="At East West, I owned the scope, milestones, and cross-functional coordination for an EFT/ACH replacement involving internal IT, global finance, Aptean, and Truist Bank.",
            level3_trait="Show what was noticed: the issue was not only technical; ownership was split across four parties, so the work needed one end-to-end delivery path.",
            result="Replaced a fragile payment setup with a compliant, auditable workflow that restored payment process integrity.",
            outcome="Use this for cross-functional project delivery, data or integration risk, banking/payment workflow, and influence without authority.",
            evidence_terms=("payment", "integration"),
            signals=("payment", "integration", "bank", "compliance", "finance", "delivery", "risk", "stakeholder"),
        ),
        StoryCard(
            title="High-volume inventory automation",
            story_types=("Individual Achievement", "Analysis and Decision", "Ambiguous Problem"),
            hook="At East West Manufacturing, high-volume inventory adjustments were manual and error-prone, and Approved Manufacturer List maintenance needed the same controlled audit trail.",
            takeaways=("Structured the messy workflow before building", "Validated the fix against operational reality", "Turned the work into measurable business improvement"),
            evidence="At East West, built automated, auditable workflows for high-volume inventory adjustments and Approved Manufacturer List maintenance.",
            level3_trait="Show what was noticed: repeated manual touches were creating delay and discrepancy risk, so the workflow was mapped, tested, and tightened before broader use.",
            result="Reduced manual work for the adjustment process by 78% and lowered inventory adjustment discrepancies by 22%.",
            outcome="Use this for process improvement, structured problem solving, and practical systems execution.",
            evidence_terms=("inventory adjustment",),
            signals=("inventory", "process", "optimization", "efficiency", "operations", "analysis"),
        ),
        StoryCard(
            title="Aptean rapid product learning",
            story_types=("Rapid Learning", "Challenge and Failure", "Individual Achievement"),
            hook="At Aptean, 80+ international client engagements required fast credibility across a complex ERP product and varied manufacturing workflows.",
            takeaways=("Learned through client problems, not abstract study", "Built a repeatable discovery rhythm", "Converted product complexity into clearer customer decisions"),
            evidence="Managed 80+ international client engagements through 12 full-lifecycle ERP implementations, carrying up to four concurrent deliveries from discovery through data migration, UAT, and post-go-live support.",
            level3_trait="Show how unfamiliar workflows were broken into requirements, risks, decision owners, and next actions until the client could move forward.",
            result="Delivered 12 full-lifecycle ERP implementations and managed up to four at a time, becoming a customer-facing implementation consultant and pre-sales resource across complex ERP delivery work.",
            outcome="Use this when asked about learning quickly, ambiguity, or becoming useful before every answer is known.",
            evidence_terms=("concurrent", "client engagements"),
            signals=("learning", "rapid", "implementation", "requirements", "customer", "erp"),
        ),
        StoryCard(
            title="$1M+ account stabilization",
            story_types=("Persuasion", "Challenge and Failure", "Customer Disagreement"),
            hook="At Aptean, several accounts inside a $6M+ book were sliding toward churn, with roughly $1M in annual revenue at risk.",
            takeaways=("Created one accountable path through the issue", "Listened for the real business pain behind the escalation", "Kept product, development, and customer stakeholders focused on resolution"),
            evidence="At Aptean, consolidated case ownership, led structured working sessions, and coordinated product and development teams around complex failures.",
            level3_trait="Show what was noticed in the room: the customer needed ownership and a credible recovery path more than another status update.",
            result="Protected $1M+ in at-risk annual revenue and converted shaky relationships back into retained accounts.",
            outcome="Use this for customer trust, escalation recovery, and influencing without authority.",
            evidence_terms=("at-risk annual revenue", "book of business"),
            signals=("risk", "escalation", "retention", "revenue", "integration", "customer success"),
        ),
        StoryCard(
            title="200+ dashboards and decision visibility",
            story_types=("Analysis and Decision", "Individual Achievement", "Ambiguous Problem"),
            hook="200+ KPI dashboards and reporting tools had to turn performance, workflow friction, and trend signals into clearer operating decisions.",
            takeaways=("Clarified the decision the report needed to support", "Translated operational questions into usable metrics", "Made the output practical for leaders and operators"),
            evidence="Built 200+ dashboards, KPI reports, and analytics tools using SQL, Crystal Reports, and Power BI.",
            level3_trait="Show how the question behind the data was clarified before building the report.",
            result="Improved visibility into operational performance, customer experience metrics, and process gaps.",
            outcome="Use this for data-driven decision-making, analytical structure, and business-minded reporting.",
            evidence_terms=("dashboards", "Power BI"),
            signals=("analytics", "dashboard", "kpi", "reporting", "data", "visibility"),
        ),
        StoryCard(
            title="60+ workshops and QBRs",
            story_types=("Managing and Leading", "Persuasion", "Teamwork"),
            hook="At Aptean, 60+ executive workshops and QBRs had to keep delivery stakeholders aligned when each group cared about different outcomes.",
            takeaways=("Read each stakeholder group differently", "Made tradeoffs visible", "Kept the conversation tied to business objectives"),
            evidence="Facilitated 60+ executive workshops and quarterly business reviews focused on roadmap alignment, adoption needs, and business priorities.",
            level3_trait="Show what was noticed: executives needed confidence in outcomes, operators needed workflow clarity, and delivery teams needed decision rights.",
            result="Maintained executive confidence throughout multi-phase delivery programs.",
            outcome="Use this for leadership, executive communication, and working with people from different backgrounds.",
            evidence_terms=("executive business reviews",),
            signals=("executive", "stakeholder", "qbr", "alignment", "roadmap", "leadership"),
        ),
        StoryCard(
            title="East West ERP ownership",
            story_types=("Managing and Leading", "Ambiguous Problem", "Teamwork"),
            hook="At East West, a five-site ERP environment supporting 150+ users had to keep adoption, data, and operational trust intact.",
            takeaways=("Put structure around ambiguous needs", "Balanced operations, finance, and engineering priorities", "Protected adoption through training and validation"),
            evidence="Owned ERP strategy, administration, and continuous improvement across five sites and more than 150 users.",
            level3_trait="Show how each group was heard differently before requirements and recommendations were finalized.",
            result="Kept core operations and finance workflows running across a global footprint while improving the ERP system through training, testing, and release readiness.",
            outcome="Use this as the main story for role scope, stakeholder complexity, and practical ownership.",
            evidence_terms=("five sites", "enterprise systems"),
            signals=("implementation", "go-live", "delivery", "testing", "global", "stakeholder"),
        ),
        StoryCard(
            title="East West Salesforce visibility",
            story_types=("Analysis and Decision", "Teamwork", "Process Improvement"),
            hook="At East West, migration teams needed clearer request and project visibility without letting follow-up disappear into spreadsheet tracking.",
            takeaways=("Kept the operating view inside the system", "Connected CRM visibility to ERP and reporting work", "Made owner and next step easier to see across teams"),
            evidence="Used Salesforce alongside ERP data and SQL-backed reporting to track requests, surface owner and next step, and give business teams clearer visibility into customer and project activity during migration and post-go-live support.",
            level3_trait="Show what was noticed: when teams updated side trackers instead of the system, the real blocker was not effort but visibility and ownership.",
            result="Improved cross-functional coordination and reduced manual status chasing during migration and post-go-live support.",
            outcome="Use this for Salesforce adoption, digital mindset, and explaining why system-based workflow visibility is stronger than spreadsheet-driven coordination.",
            evidence_terms=("East West", "Salesforce"),
            signals=("salesforce", "crm", "visibility", "reporting", "workflow", "adoption", "digital", "operations"),
        ),
        StoryCard(
            title="Salesforce backlog and release coordination",
            story_types=("Analysis and Decision", "Managing and Leading", "Teamwork"),
            hook="Customer-facing CRM and digital-workflow changes had to stay useful for customers and support teams instead of becoming another spreadsheet-driven status exercise.",
            takeaways=("Translated noisy requests into backlog-ready work", "Used testing and release discipline to protect adoption", "Kept the workflow visible in system rather than in side trackers"),
            evidence="Turned business needs into backlog-ready requirements, coordinated UAT, and validated releases across Salesforce customer and marketing workflows.",
            level3_trait="Show what was noticed: when ownership lived in email threads or spreadsheets, follow-up got blurry, so the work had to move into clearer CRM workflows, test scenarios, and next-step tracking.",
            result="Improved post-go-live follow-through, clearer issue ownership, and more reliable coordination across customer-facing teams.",
            outcome="Use this for Salesforce product ownership, backlog management, UAT, release coordination, and explaining why structured CRM workflows beat spreadsheet tracking.",
            evidence_terms=("salesforce", "marketing cloud"),
            signals=("salesforce", "crm", "digital", "backlog", "uat", "release", "product", "adoption", "workflow", "customer experience"),
        ),
        StoryCard(
            title="Zero-to-one SMS support channel",
            story_types=("Individual Achievement", "Analysis and Decision", "Rapid Learning"),
            hook="At The Home Depot, customers had no way to reach support over text, and the pilot team had to stand up an SMS support channel from zero.",
            takeaways=("Designed the workflow before scaling", "Configured repeatable messaging steps", "Documented the setup so the channel could be repeated"),
            evidence=f"Configured LivePerson LiveEngage chat and text workflows, automated greetings and closings, AI-assisted chatbot logic, and early channel-usage monitoring for the {COMPANY_HOME_DEPOT} SMS pilot.",
            level3_trait="Show what was noticed: the new channel needed an operating workflow first, including how text conversations opened, routed, closed, and got measured.",
            result="Launched a working SMS support channel and documented the setup so the workflow could be repeated consistently.",
            outcome="Use this for zero-to-one workflow design, practical automation, messaging workflows, conversational AI, or channel adoption.",
            evidence_terms=("liveengage", "text messaging"),
            signals=("automation", "ai", "chatbot", "messaging", "workflow", "nlp"),
        ),
        StoryCard(
            title="Aptean lifecycle delivery",
            story_types=("Individual Achievement", "Managing and Leading", "Ambiguous Problem"),
            hook="At Aptean, 80+ manufacturing clients needed ambiguous business needs translated into practical ERP scope, delivery, and adoption.",
            takeaways=("Started with discovery before solutioning", "Converted requirements into scope and milestones", "Stayed with clients through go-live and hypercare"),
            evidence="Led discovery, requirements definition, configuration, data migration, integration, testing, go-live, and post-go-live support.",
            level3_trait="Show how vague asks were translated into SOWs, functional requirements, test plans, and delivery checkpoints.",
            result="Helped international clients move through full lifecycle ERP implementation with clearer scope and lower delivery risk.",
            outcome="Use this for implementation, consulting delivery, and structuring ambiguous work.",
            evidence_terms=("requirements", "implementation", "adoption"),
            signals=("discovery", "requirements", "solution", "design", "implementation", "consulting"),
        ),
        StoryCard(
            title="Operations versus finance alignment",
            story_types=("Persuasion", "Teamwork", "Opposing Views"),
            hook="At East West, the central issue was getting several internal teams and the vendor onto one decision path for the business tradeoff.",
            takeaways=("Listened for the constraint behind each position", "Made tradeoffs explicit", "Recommended the option that protected the business outcome"),
            evidence="Led cross-functional discovery, surfaced the tradeoffs, and negotiated priorities with vendors and internal stakeholders.",
            level3_trait="Show what was noticed: one group was optimizing speed, another was protecting control, and the answer had to make the tradeoff visible.",
            result="Balanced cost, timeline, and operational impact across competing stakeholder interests.",
            outcome="Use this for opposing views, difficult stakeholders, and influence without authority.",
            evidence_terms=("finance", "engineering"),
            signals=("opposing", "disagree", "stakeholder", "finance", "operations", "persuasion"),
        ),
        StoryCard(
            title="Failure lesson and stronger validation",
            story_types=("Challenge and Failure", "Analysis and Decision", "Rapid Learning"),
            hook="During East West release-readiness work, unclear requirements and weak validation could turn a solvable system issue into a larger adoption problem.",
            takeaways=("Own the miss without over-explaining", "Show the control that changed afterward", "Connect the lesson to better delivery risk management"),
            evidence="Led go-live readiness, sandbox testing, user acceptance validation, issue triage, and release readiness across ERP work.",
            level3_trait="Show the changed behavior: clearer requirements, stronger validation checkpoints, more explicit rollback planning, and earlier stakeholder signoff.",
            result="Reduced production disruption, downstream defects, and implementation risk across concurrent program tracks.",
            outcome="Use this for failure questions. Keep it honest, calm, and focused on what changed.",
            evidence_terms=("validation",),
            signals=("failure", "mistake", "learn", "testing", "validation", "risk"),
        ),
        StoryCard(
            title="Customer loss and proactive success lesson",
            story_types=("Challenge and Failure", "Customer Disagreement", "Persuasion"),
            hook="At Aptean, an inherited customer relationship had to be recovered after a broken implementation, even though resolving every technical issue did not save the account.",
            takeaways=(
                "Owned the relationship directly rather than managing it through escalation",
                "Negotiated feature acceleration to rebuild trust faster than a standard roadmap allowed",
                "Learned that waiting for a customer to raise concerns means the decision is already made",
            ),
            evidence="Took ownership of an at-risk account at a manufacturing ERP company where an incorrectly configured integration had eroded trust; met with the customer president weekly and worked across product and development to accelerate key roadmap items from a six-month timeline into a two-month beta release.",
            level3_trait="Show what was noticed: the customer needed a clear owner and a credible path forward, not another status update. Then show what changed: reaching out before a customer has a reason to complain, not after, because by the time someone raises their hand the decision is often already made.",
            result="Resolved every technical issue the customer had raised. The account still churned when the customer chose a cheaper competitor. The loss clarified the proactive customer success model applied in every engagement afterward.",
            outcome="Use this for failure questions, customer churn questions, or any question about proactive account management and what was learned from a loss. It is the strongest story for roles where customer health ownership is an explicit expectation.",
            evidence_terms=("at-risk annual revenue",),
            signals=("failure", "churn", "loss", "customer", "proactive", "retention", "account", "escalation", "discovery", "executive", "consulting", "transformation", "enablement"),
        ),
        StoryCard(
            title="13-month modernization complexity",
            story_types=("Ambiguous Problem", "Managing and Leading", "Persuasion"),
            hook="At Aptean, a four-to-seven-month modernization engagement became 13 months when discovery uncovered infrastructure too outdated for modern software.",
            takeaways=(
                "Surfaced a constraint the customer had not anticipated and could not work around",
                "Aligned CEO and upper management on real costs before any software work could begin",
                "Kept the engagement alive through a 13-month delivery when the scope was set for four to seven months",
            ),
            evidence="Led a full ERP modernization engagement where requirements gathering revealed tens of thousands of dollars in required hardware upgrades before implementation could begin. I delivered a satisfied customer and billable customization work through an engagement that ran nearly three times the standard timeline.",
            level3_trait="Show what was noticed: the customer asked for software, but the real constraint was infrastructure. Show what was done: named the problem directly to leadership instead of softening it, managed expectations through a significantly longer delivery, and kept the customer confident enough to stay.",
            result="Delivered a satisfied customer after a 13-month engagement scoped at four to seven months. The extended timeline opened billable customization work that would not have existed in a standard delivery.",
            outcome="Use this for most complex implementation, stakeholder alignment under pressure, managing scope surprises, or expectations management with executive audiences who did not anticipate the real cost or timeline of the work they asked for.",
            evidence_terms=("implementation", "go-live"),
            signals=("complex", "implementation", "timeline", "stakeholder", "executive", "scope", "modernization", "discovery", "consulting", "transformation"),
        ),
        StoryCard(
            title="UAT defect catch before go-live",
            story_types=("Challenge and Failure", "Persuasion", "Analysis and Decision"),
            hook="During Aptean UAT, a defect would have broken a live client workflow if it reached production.",
            takeaways=(
                "Named the go-live risk directly instead of softening it",
                "Coordinated root-cause work quickly across development and product partners",
                "Protected the client outcome even when that meant slowing the timeline",
            ),
            evidence="Identified a critical defect during user acceptance testing, led triage with development, validated the fix, and withheld go-live approval until the workflow was safe.",
            level3_trait="Show what was noticed: the real risk was not a bug count but the production impact on a live client process, so the conversation stayed anchored on business harm, validation, and release readiness instead of schedule pressure.",
            result="Prevented a production issue that would have disrupted live client operations after go-live.",
            outcome="Use this for delivery risk management, quality validation, cross-functional coordination, or any question about making a difficult go-live call.",
            evidence_terms=("user acceptance", "go-live"),
            signals=("uat", "testing", "risk", "delivery", "client management", "validation", "defect", "go-live"),
        ),
        StoryCard(
            title="CEO hardware scoping conversation",
            story_types=("Persuasion", "Customer Disagreement", "Managing and Leading"),
            hook="At Aptean, an executive sponsor needed to see outdated infrastructure as a business risk before ERP work could move forward.",
            takeaways=(
                "Diagnosed the real blocker before talking solutions",
                "Framed hardware upgrades as implementation risk rather than IT preference",
                "Kept leadership, vendors, and technical teams aligned on readiness",
            ),
            evidence="Scoped server and hardware requirements with leadership, vendors, and IT teams to confirm compatibility, capacity, security, and upgrade readiness before ERP deployment.",
            level3_trait="Show what was noticed: leadership thought the project was a software decision, but the real constraint was infrastructure readiness, so the discussion had to shift from features to business exposure if the environment failed under live load.",
            result="Secured infrastructure-readiness alignment early enough to prevent post-deployment performance failures.",
            outcome="Use this for executive persuasion, technical scoping, stakeholder alignment, or surfacing hidden delivery risk before go-live.",
            evidence_terms=("hardware", "infrastructure"),
            signals=("persuasion", "stakeholder", "executive", "hardware", "implementation", "risk", "scope", "infrastructure"),
        ),
        StoryCard(
            title="New warehouse and Amazon Robotics systems launch",
            story_types=("Individual Achievement", "Managing and Leading", "Ambiguous Problem"),
            hook="At East West Manufacturing, a new warehouse operation and Amazon Robotics program had to be production-ready by go-live across concurrent systems workstreams.",
            takeaways=(
                "Treated product families, GL accounts, BOMs, and training as parallel workstreams",
                "Sequenced the work so systems and users were ready at cutover",
                "Delivered production readiness without needing formal authority over every contributor",
            ),
            evidence="At East West, launched a production-ready system setup for a new warehouse operation and Amazon Robotics program, scoping product families, GL accounts, BOMs, and cross-site training from initial requirements through go-live.",
            level3_trait="Show what was noticed: this was not one task but several concurrent workstreams that all had to converge by go-live.",
            result="Delivered a production-ready go-live with the systems and the people ready at the same time.",
            outcome="Use this for high-stakes cross-functional delivery, most complex project, manufacturing execution, and parallel workstream ownership.",
            evidence_terms=("Amazon Robotics", "warehouse"),
            signals=("manufacturing", "implementation", "compliance", "delivery", "executive", "stakeholder", "go-live", "complex"),
        ),
        StoryCard(
            title="Cross-site rollout to the Mexico teams",
            story_types=("Cross-Cultural", "Teamwork", "Managing and Leading"),
            hook="During the East West ERP rollout, two Mexico sites needed to be genuinely ready for go-live, not merely installed.",
            takeaways=("Recognized that one-size training would leave adoption gaps", "Went on-site in El Paso and Juarez", "Adapted onboarding and compliance steps to the local teams"),
            evidence="Supported the Mexico sites in person during the East West rollout, adapting onboarding, training, compliance, and financial steps to how the local teams worked.",
            level3_trait="Show what was noticed: language, process, and on-the-ground differences meant remote-only support would leave gaps.",
            result="The Mexico sites went live ready, not just installed, and the cross-site rollout held together.",
            outcome="Use this for cross-cultural collaboration, adoption, multi-site work, and stakeholder empathy.",
            evidence_terms=("training", "adoption"),
            signals=("cross-cultural", "cross-site", "Mexico", "training", "adoption", "go-live", "stakeholder"),
        ),
        StoryCard(
            title="Parallel workstream prioritization",
            story_types=("Prioritization", "Managing and Leading", "Ambiguous Problem"),
            hook="At East West Manufacturing, a hard-date warehouse and Amazon Robotics launch had four urgent workstreams that could not all be treated as equal.",
            takeaways=("Locked the data foundation first", "Ran independent GL setup in parallel", "Held training for the final configuration and protected the critical path"),
            evidence="Sequenced product families, BOMs, GL setup, and site training around the critical path, saying no to changes that put the go-live date at risk.",
            level3_trait="Show what was noticed: if the data foundation slipped, training and go-live would collapse on top of it.",
            result="Systems and people converged at go-live on schedule.",
            outcome="Use this for prioritization, deadline pressure, parallel work, and saying no to date-risking scope.",
            evidence_terms=("go-live", "training"),
            signals=("prioritization", "critical path", "parallel", "go-live", "training", "deadline", "scope"),
        ),
        StoryCard(
            title="Redirecting a churning account without arguing",
            story_types=("Customer Disagreement", "Persuasion", "Opposing Views"),
            hook="At Aptean, an at-risk account blamed the product and was ready to leave, while the evidence pointed to adoption gaps and stalled custom work.",
            takeaways=("Diagnosed the root cause with the customer", "Reframed disagreement as a shared fix", "Created a weekly ownership cadence"),
            evidence="Walked the customer through where usage had dropped and which integration had stalled, then took ownership and worked the actual gaps with them.",
            level3_trait="Show what was noticed: being right about the root cause would not help if the customer did not feel heard or see a credible path forward.",
            result="The account moved from churning to retained.",
            outcome="Use this for difficult customers, conflict, influence, root-cause thinking, and customer recovery.",
            evidence_terms=("adoption",),
            signals=("customer", "disagreement", "adoption", "integration", "retention", "persuasion", "conflict"),
        ),
        StoryCard(
            title="Data-migration setback and validation checkpoint",
            story_types=("Challenge and Failure", "Analysis and Decision", "Rapid Learning"),
            hook="During the East West data migration, a portion of the data did not map cleanly and was caught later than it should have been.",
            takeaways=("Owned the miss immediately", "Paused the affected cutover step and rebuilt mapping validation", "Added a checkpoint so the gap could not recur"),
            evidence="Paused the affected migration step, rebuilt the mapping and validation, re-ran it before production, and added a validation checkpoint.",
            level3_trait="Show what was noticed: the source data was not as clean as assumed, so the process had to change rather than rely on a later inspection.",
            result="The data migrated cleanly and the new checkpoint reduced recurrence risk.",
            outcome="Use this for failure, ownership, resilience, data migration, and learning from a miss.",
            evidence_terms=("migration", "validation"),
            signals=("failure", "migration", "validation", "data", "ownership", "learning", "risk"),
        ),
        StoryCard(
            title="Acting on hard communication feedback",
            story_types=("Receiving Feedback", "Rapid Learning", "Individual Achievement"),
            hook="During a client engagement, a manager told me my updates ran too long and buried the point.",
            takeaways=("Accepted the feedback as accurate", "Led with the outcome and offered detail on request", "Practiced the change in meetings and client calls"),
            evidence="Rebuilt my communication around outcome-first updates and practiced the change deliberately until it became automatic.",
            level3_trait="Show the behavior change: the answer became the headline first, with the process available only when the audience needed it.",
            result="Updates became sharper, meetings shorter, and stakeholders came to me first for a clear read.",
            outcome="Use this for feedback, weaknesses, coachability, self-awareness, and communication growth.",
            evidence_terms=("adoption",),
            signals=("feedback", "communication", "coachability", "learning", "concise", "stakeholder"),
        ),
        StoryCard(
            title="East West end-to-end ERP implementation",
            story_types=("Managing and Leading", "Ambiguous Problem", "Teamwork"),
            hook="I led the East West ERP implementation and data migration across five sites and more than 150 users.",
            takeaways=("Aligned operations, finance, and engineering", "Owned onboarding, compliance, financial, and training sessions", "Led ETL and migration to a clean go-live"),
            evidence="Led the end-to-end ERP implementation and migration, supported the Mexico offices in person, and owned the ETL and data migration through go-live.",
            level3_trait="Show what was noticed: the work was an alignment problem across sites, functions, and countries, not a software install.",
            result="The sites went live with systems and people ready together, and the migration landed clean.",
            outcome="Use this as the implementation lead story for end-to-end ownership, ERP delivery, onboarding, and customer-side execution.",
            evidence_terms=("five sites", "enterprise systems"),
            signals=("implementation", "ERP", "migration", "go-live", "five sites", "training", "global", "ownership"),
            sensitive_note="My role wrapped when the migration finished and the team consolidated.",
        ),
        StoryCard(
            title="Both-sides implementation breadth",
            story_types=("Individual Achievement", "Rapid Learning", "Ambiguous Problem"),
            hook="I have delivered the same kind of software from both sides of the table: as a vendor across more than 80 client engagements and as the customer-side implementation owner.",
            takeaways=("Adapted across legacy on-premise and cloud environments", "Learned varied client workflows quickly", "Connected vendor delivery discipline to customer-side ownership"),
            evidence="At Aptean, implemented and supported more than 80 clients across varied configurations, then led the East West implementation from the customer side.",
            level3_trait="Show the differentiator: vendor breadth helps me anticipate where implementations break, while customer-side ownership keeps the work grounded in adoption and operating reality.",
            result="I bring implementation judgment from both sides of the table.",
            outcome="Use this as the broad opening hook for implementation, solution consulting, and customer-facing delivery roles.",
            evidence_terms=("client engagements", "migration"),
            signals=("both sides", "client engagements", "implementation", "migration", "ERP", "cloud", "discovery"),
        ),
    ]
    stable_keys = {
        "EFT/ACH payment integration replacement": "payment_integration",
        "High-volume inventory automation": "inventory_automation",
        "Aptean rapid product learning": "rapid_learning",
        "$1M+ account stabilization": "account_stabilization",
        "200+ dashboards and decision visibility": "dashboards",
        "60+ workshops and QBRs": "executive_workshops",
        "East West ERP ownership": "erp_ownership",
        "East West Salesforce visibility": "crm_visibility",
        "Salesforce backlog and release coordination": "backlog_release",
        "Zero-to-one SMS support channel": "sms_channel",
        "Aptean lifecycle delivery": "lifecycle_delivery",
        "Operations versus finance alignment": "ops_finance",
        "Failure lesson and stronger validation": "failure_validation",
        "Customer loss and proactive success lesson": "customer_loss",
        "13-month modernization complexity": "modernization_scope",
        "UAT defect catch before go-live": "uat_defect",
        "CEO hardware scoping conversation": "ceo_hardware",
        "New warehouse and Amazon Robotics systems launch": "amazon_robotics",
        "Cross-site rollout to the Mexico teams": "cross_site_adoption",
        "Parallel workstream prioritization": "parallel_workstreams",
        "Redirecting a churning account without arguing": "churn_redirect",
        "Data-migration setback and validation checkpoint": "migration_setback",
        "Acting on hard communication feedback": "communication_feedback",
        "East West end-to-end ERP implementation": "east_west_end_to_end",
        "Both-sides implementation breadth": "both_sides_breadth",
    }
    return [replace(card, boost_key=card.boost_key or stable_keys.get(card.title, "")) for card in cards]
def story_by_boost_key(stories: Sequence[StoryCard], boost_key: str) -> StoryCard | None:
    return next((card for card in stories if card.boost_key == boost_key), None)
def supported_story_bank(resume_text: str = "", *, eligibility_text: str = "") -> list[StoryCard]:
    gate_text = eligibility_text or resume_text or question_prep.approved_source_resume_text()
    return [card for card in expanded_story_bank() if contains_all(gate_text, card.evidence_terms, safe=True)]
def story_for_type(
    stories: list[StoryCard],
    story_type: str,
    profile: resume_analysis.JobProblemProfile | None = None,
) -> StoryCard | None:
    if story_type == "Challenge and Failure":
        preferred_keys = ("customer_loss", "failure_validation")
        if profile and profile.primary_lane in {"implementation_delivery", "change_enablement", "process_improvement"}:
            preferred_keys = ("migration_setback", "failure_validation", "customer_loss")
        elif profile and profile.primary_lane == "customer_success":
            preferred_keys = ("customer_loss", "churn_redirect", "failure_validation")
        preferred = next((story_by_boost_key(stories, key) for key in preferred_keys), None)
        if preferred:
            return preferred
    return next((card for card in stories if story_type in card.story_types), None)
def story_theme_key(card: StoryCard) -> str:
    keyed_themes = {
        "payment_integration": "payment_integration",
        "inventory_automation": "inventory",
        "rapid_learning": "learning",
        "account_stabilization": "account",
        "dashboards": "dashboards",
        "executive_workshops": "workshops",
        "erp_ownership": "erp_ownership",
        "crm_visibility": "crm_visibility",
        "backlog_release": "backlog_release",
        "sms_channel": "messaging_automation",
        "lifecycle_delivery": "lifecycle_delivery",
        "ops_finance": "ops_finance",
        "failure_validation": "failure",
        "customer_loss": "customer_loss",
        "modernization_scope": "modernization_scope",
        "uat_defect": "failure",
        "ceo_hardware": "ceo_hardware",
        "amazon_robotics": "amazon_robotics",
        "cross_site_adoption": "cross_site_adoption",
        "parallel_workstreams": "parallel_workstreams",
        "churn_redirect": "churn_redirect",
        "migration_setback": "migration_setback",
        "communication_feedback": "communication_feedback",
        "east_west_end_to_end": "erp_ownership",
        "both_sides_breadth": "both_sides_breadth",
    }
    if card.boost_key in keyed_themes:
        return keyed_themes[card.boost_key]
    lowered = card.title.lower()
    if "inventory" in lowered:
        return "inventory"
    if "eft" in lowered or "payment" in lowered:
        return "payment_integration"
    if "account" in lowered or "$1m" in lowered:
        return "account"
    if "dashboard" in lowered or "decision visibility" in lowered:
        return "dashboards"
    if "rapid" in lowered or "product learning" in lowered:
        return "learning"
    if "operations versus finance" in lowered or "finance alignment" in lowered:
        return "ops_finance"
    if "failure" in lowered or "validation" in lowered:
        return "failure"
    if "workshop" in lowered or "qbr" in lowered:
        return "workshops"
    if "customer loss" in lowered or "proactive success" in lowered:
        return "customer_loss"
    if "13-month" in lowered or "modernization complexity" in lowered:
        return "modernization_scope"
    if "amazon robotics" in lowered or "warehouse certification" in lowered:
        return "amazon_robotics"
    if "erp ownership" in lowered:
        return "erp_ownership"
    if "salesforce visibility" in lowered:
        return "crm_visibility"
    if "backlog" in lowered or "release coordination" in lowered:
        return "backlog_release"
    if "liveperson" in lowered or "messaging workflows" in lowered or "sms" in lowered:
        return "messaging_automation"
    if "lifecycle delivery" in lowered:
        return "lifecycle_delivery"
    return "default"
def story_specific_bridge(card: StoryCard, profile: resume_analysis.JobProblemProfile) -> str:
    key = story_theme_key(card)
    bridges = {
        "inventory": "Bridge: this is the process-improvement proof: map the actual workflow, find the structural gap, validate the fix with users, pilot it, and measure whether the work actually changed.",
        "payment_integration": "Bridge: this is the cross-functional delivery proof: name the operational risk, create one accountable path across finance, IT, vendor partners plus banking stakeholders, then validate that the workflow is reliable before handoff.",
        "account": "Bridge: this is the trust-recovery proof: when an experience is breaking down, the answer is accountable ownership and a credible path forward, not a better status cadence.",
        "dashboards": "Bridge: this is the decision-quality proof: define the business decision before touching the data, validate the source, and segment the view so the next action is obvious.",
        "learning": "Bridge: this is the ramp proof: learn through the live workflow and the people doing it, not through documentation alone.",
        "ops_finance": "Bridge: this is the stakeholder-tradeoff proof: surface what each group is protecting before designing a process that has to satisfy all of them.",
        "failure": "Bridge: this is the quality-control proof: build SME validation, acceptance criteria, and checkpoints into the process before go-live, not after the risk reaches users.",
        "workshops": "Bridge: this is the translation proof: turn one process goal into the decision, workflow, or risk language each audience needs to act.",
        "erp_ownership": "Bridge: this is the systems-ownership proof: keep a mission-critical platform stable for every stakeholder group while still pushing through training, testing, and release improvements instead of just maintaining the status quo.",
        "crm_visibility": "Bridge: this is the visibility proof: when work lives in side trackers instead of the system of record, the fix is moving ownership and next steps back into the platform everyone already uses.",
        "backlog_release": "Bridge: this is the release-discipline proof: turn noisy, ambiguous requests into backlog-ready work with real UAT and validation so adoption survives past go-live.",
        "messaging_automation": "Bridge: this is the channel-adoption proof: learn the new workflow through live customer interactions first, then standardize the steps so the whole team can repeat it.",
        "lifecycle_delivery": "Bridge: this is the discovery-to-delivery proof: turn an ambiguous ask into defined scope, milestones, and checkpoints, then stay through go-live so adoption actually holds.",
        "customer_loss": "Bridge: this is the proactive account ownership proof: success in a high-touch customer role means identifying risk before the customer names it, because by the time they raise their hand the decision may already be made.",
        "modernization_scope": "Bridge: this is the scoping realism proof: the most dangerous assumption in a complex implementation is that the customer's environment matches what they believe it to be; surface constraints early, name the real cost directly, and hold expectations across a longer-than-expected delivery.",
        "amazon_robotics": "Bridge: this is the compliance-constrained delivery proof: when a customer or partner has non-negotiable certification requirements, there is no room to learn by doing — every configuration decision upstream has to account for what it unlocks or blocks downstream.",
        "ceo_hardware": "Bridge: this is the executive-scoping proof: surface the real infrastructure constraint early, translate it into business exposure, and align leadership before the delivery date makes the risk expensive.",
        "cross_site_adoption": "Bridge: this is the adoption proof: localize the change to the people and operating context that have to live with it, then confirm readiness in practice rather than only in documentation.",
        "parallel_workstreams": "Bridge: this is the prioritization proof: protect the critical path, parallelize only independent work, and defer changes that would make the hard date less credible.",
        "churn_redirect": "Bridge: this is the disagreement proof: use evidence to reframe the problem as a shared fix instead of trying to win the argument.",
        "migration_setback": "Bridge: this is the learning-from-failure proof: own the miss, stop it before production, and change the checkpoint so the same assumption cannot recur.",
        "communication_feedback": "Bridge: this is the coachability proof: turn uncomfortable feedback into a visible behavior change and practice it until the improvement is reliable.",
        "both_sides_breadth": "Bridge: this is the adaptability proof: vendor-side breadth plus customer-side ownership makes it easier to anticipate delivery risk and keep adoption grounded in operating reality.",
    }
    return bridges.get(
        key,
        f"Bridge: connect this specific outcome to {candidate_problem_phrase(profile)} by naming the workflow, decision, stakeholder, risk, or customer problem it proves.",
    )
def should_use_cart(company_name: str, role_title: str, job_description: str) -> bool:
    return bool(
        resume_analysis.is_consulting_job_description(job_description)
        or re.search(r"\b(?:vp|director|head of|senior director)\b", role_title, re.I)
        or resume_analysis.jd_mentions(
            job_description,
            "executive stakeholders",
            "board",
            "C-suite",
            "leadership alignment",
        )
    )
def uses_star_answer_framework(company_name: str, job_description: str) -> bool:
    return resume_analysis.jd_mentions(job_description, "star method", "situation task action result")
def spoken_caar_answer(card: StoryCard, profile: resume_analysis.JobProblemProfile) -> str:
    parts = [
        concrete_story_opening(card),
    ]
    if card.level3_trait:
        parts.append(spoken_level3_trait_sentence(card.level3_trait))
    if card.evidence:
        parts.append(story_evidence_sentence(card.evidence))
    if card.result:
        parts.append(story_result_sentence(card.result))
    bridge = story_specific_bridge(card, profile).replace("Bridge: ", "")
    if bridge and spoken_word_count(interview_join(*parts, bridge)) <= STANDARD_SPOKEN_WORD_RANGE[1]:
        parts.append(bridge[:1].upper() + bridge[1:])
    return interview_join(*parts)
def spoken_cart_answer(card: StoryCard, profile: resume_analysis.JobProblemProfile) -> str:
    parts = [
        concrete_story_opening(card),
        cart_takeaway_sentence(card),
    ]
    if card.evidence:
        parts.append(story_evidence_sentence(card.evidence))
    if card.level3_trait:
        parts.append(spoken_level3_trait_sentence(card.level3_trait))
    if card.result:
        parts.append(story_result_sentence(card.result))
    bridge = story_specific_bridge(card, profile).replace("Bridge: ", "")
    if bridge and spoken_word_count(interview_join(*parts, bridge)) <= STANDARD_SPOKEN_WORD_RANGE[1]:
        parts.append(bridge[:1].upper() + bridge[1:])
    return interview_join(*parts)
def cart_takeaway_sentence(card: StoryCard) -> str:
    steps = [lower_clause(item) for item in card.takeaways if item]
    if not steps:
        return "I kept the business risk visible while moving the work forward"
    if len(steps) == 1:
        return f"My approach was to {steps[0]} while keeping the business risk visible"
    if len(steps) == 2:
        return f"First, I {steps[0]}. Then I {steps[1]} while keeping the business risk visible"
    return (
        f"First, I {steps[0]}. Then I {steps[1]}. Finally, I {steps[2]} while keeping the business risk visible"
    )
def spoken_pyramid_answer(card: StoryCard, profile: resume_analysis.JobProblemProfile) -> str:
    parts = [
        "Yes, I have handled that kind of situation by structuring the problem first and then using evidence and stakeholder alignment to move toward a practical outcome",
        concrete_story_opening(card),
    ]
    if card.level3_trait:
        parts.append(spoken_level3_trait_sentence(card.level3_trait))
    if card.evidence:
        parts.append(story_evidence_sentence(card.evidence))
    if card.result:
        parts.append(story_result_sentence(card.result))
    bridge = story_specific_bridge(card, profile).replace("Bridge: ", "")
    if bridge and spoken_word_count(interview_join(*parts, bridge)) <= STANDARD_SPOKEN_WORD_RANGE[1]:
        parts.append(bridge[:1].upper() + bridge[1:])
    return interview_join(*parts)
def spoken_story_answer(
    card: StoryCard,
    profile: resume_analysis.JobProblemProfile,
    company_name: str = "",
    role_title: str = "",
    job_description: str = "",
) -> str:
    if uses_star_answer_framework(company_name, job_description):
        answer = spoken_pyramid_answer(card, profile)
    elif should_use_cart(company_name, role_title, job_description):
        answer = spoken_cart_answer(card, profile)
    else:
        answer = spoken_caar_answer(card, profile)
    answer = prose_engine.spoken_register(answer).text
    assert_full_spoken_answer(f"{card.title} story answer", answer, min_words=40)
    return answer
def likely_question_story(item: InterviewQuestion, stories: list[StoryCard], used_titles: set[str] | None = None) -> StoryCard:
    used_titles = used_titles or set()
    prompt = f"{item.question} {item.angle}".lower()
    mapped_title = closest_anchor_story_title(item.question, item.angle)
    lifecycle_terms = ("implementation", "go-live", "configuration", "readiness", "lifecycle", "rollout")
    enhancement_terms = ("upgrade", "customization", "service pack", "already live", "enhancement")
    hints: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
        (("data", "metric", "report", "excel", "sql", "validate"), ("Analysis and Decision", "KPI", "dashboard", "reporting")),
        (("risk", "stabilize", "difficult", "escalation", "customer"), ("Challenge and Failure", "Persuasion", "account stabilization", "recovery")),
        (("train", "training", "adoption", "enablement"), ("Teamwork", "workshop", "QBR", "adoption")),
        (("discovery", "demo", "solution", "buyer"), ("Persuasion", "pre-sales", "discovery", "solution")),
        (("implementation", "go-live", "configuration", "readiness"), ("Individual Achievement", "implementation", "go-live", "Aptean")),
        (("technical", "project", "integration", "api", "migration"), ("Rapid Learning", "ERP", "migration", "technical")),
        (("stakeholder", "competing", "priority", "influence"), ("Persuasion", "Teamwork", "alignment")),
        (("gap", "learn", "new", "comfort"), ("Rapid Learning", "Challenge and Failure", "learning")),
    )
    scored: list[tuple[int, StoryCard]] = []
    for story in stories[:12]:
        score = signal_score(prompt, story.signals)
        story_text = " ".join((story.title, story.hook, " ".join(story.story_types), " ".join(story.signals))).lower()
        if mapped_title and story.title == mapped_title:
            score += 100
        for question_terms, story_terms in hints:
            if any(term in prompt for term in question_terms):
                if any(term.lower() in story_text for term in story_terms):
                    score += 8
        if any(term in prompt for term in lifecycle_terms):
            if "aptean" in story_text:
                score += 10
            if "east west" in story_text:
                score -= 4
        if any(term in prompt for term in enhancement_terms):
            if "east west" in story_text:
                score += 10
        if story.title in used_titles:
            # Large enough to lose to any unused story regardless of keyword
            # bonuses above, so a story only repeats within the same question
            # list when every other story has truly been used already. A
            # small penalty here let the same story answer two different
            # questions verbatim in the same interview, which is exactly the
            # "sounds rehearsed" failure mode this tool exists to avoid.
            score -= 1000
        scored.append((score, story))
    return max(scored, key=lambda item_score: item_score[0])[1]
def closest_anchor_story_title(prompt: str, angle: str = "") -> str:
    text = f"{prompt} {angle}".lower()
    mapping = (
        (("walk me through", "implementation you owned", "full lifecycle"), "Aptean lifecycle delivery"),
        (("scope creep", "changing requirements", "sow", "frd"), "Aptean lifecycle delivery"),
        (("data migration", "go-live risk", "integration risk", "payment", "validation"), "EFT/ACH payment integration replacement"),
        (("went wrong", "failure", "lost the account", "mistake"), "Customer loss and proactive success lesson"),
        (("ambiguity", "ambiguous", "methodology", "run a project"), "Aptean lifecycle delivery"),
        (("largest project", "most complex project", "no formal authority"), "EFT/ACH payment integration replacement"),
        (("warehouse", "amazon robotics"), "New warehouse and Amazon Robotics systems launch"),
        (("manual work", "process improvement", "inventory"), "High-volume inventory automation"),
        (("sms", "liveengage", "new workflow", "zero"), "Zero-to-one SMS support channel"),
        (("at-risk", "churn", "recovery", "retention"), "$1M+ account stabilization"),
    )
    for terms, title in mapping:
        if any(term in text for term in terms):
            return title
    return ""
