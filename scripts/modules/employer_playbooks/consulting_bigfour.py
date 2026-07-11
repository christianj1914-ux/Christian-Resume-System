"""Big Four and strategy consulting interview and cover-letter playbook."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from build_interview_cheat_sheet import StoryCard
    from modules.employer_playbooks.state_farm import PrepInsights


CONSULTING_SIGNALS = (
    "kpmg",
    "deloitte",
    "pwc",
    "ernst young",
    "ey",
    "bain",
    "mckinsey",
    "bcg",
    "accenture",
    "booz allen",
    "oliver wyman",
    "management consulting",
    "strategy consulting",
    "advisory firm",
)


def text_has_consulting_signal(text: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", " ", text.lower())
    for signal in CONSULTING_SIGNALS:
        normalized_signal = re.sub(r"[^a-z0-9]+", " ", signal.lower()).strip()
        if re.search(rf"(?<![a-z0-9]){re.escape(normalized_signal)}(?![a-z0-9])", normalized):
            return True
    return False


def is_bigfour_consulting_active(
    company_name: str,
    role_title: str,
    job_description: str,
    company_research: str = "",
    interview_notes: str = "",
) -> bool:
    combined = f"{company_name}\n{role_title}\n{job_description}\n{company_research}\n{interview_notes}"
    return text_has_consulting_signal(combined)


def bigfour_cover_opening(company_name: str, role_title: str) -> str:
    firm_name = company_name.strip() or "the firm"
    return (
        f"{firm_name}'s reputation for delivering results rather than recommendations matters because my career has been built around the same principle. "
        "Across ten years of enterprise software implementation, customer-facing delivery, and executive-facing operations work, I have learned that the most valuable "
        "thing a consultant can do is not hand over a deck and leave. It is to stay in the room until the outcome is real. "
        f"That is the operating pattern I would bring to the {role_title} role."
    )


def bigfour_prep_insights() -> "PrepInsights":
    from modules.employer_playbooks.state_farm import PrepInsights

    return PrepInsights(
        situation_read=(
            "This is a consulting interview as much as a role interview. The team will likely evaluate whether Christian can bring client-service judgment: structure an ambiguous problem, communicate the recommendation clearly, and stay practical about what implementation will require.",
            "The strongest narrative is not 'I want to move into consulting.' It is 'I have already done the implementation side of consulting work: discovery, stakeholder alignment, solution design, executive workshops, adoption, and measurable outcomes across a broad client portfolio.'",
            "Consulting firms will likely listen for whether Christian can separate analysis from action. The recommendation only matters if he can translate it into owners, risks, decisions, adoption steps, and metrics.",
        ),
        interviewer_read=(
            "Expect concise, structured answers. Lead with the answer, then give the case evidence, then state the business implication.",
            "Assume the interviewer is checking whether Christian can sound credible in front of a client: calm, specific, measured, and not inflated.",
        ),
        likely_scorecard=(
            "Can structure ambiguous client problems into a clean issue tree, decision path, or implementation plan.",
            "Can communicate complex systems and operational tradeoffs in plain business language.",
            "Can show client-service judgment: credibility, follow-through, expectation management, and practical recommendations.",
            "Can connect analysis to implementation instead of stopping at a presentation or abstract strategy.",
            "Can use measurable outcomes, international client exposure, executive workshops, and delivery ownership as proof.",
        ),
        pushbacks=(
            (
                "You do not have formal consulting credentials from a major firm.",
                "That is accurate, and I would not pretend otherwise. What I do bring is the operating pattern consulting teams need after the recommendation: I have worked across 80+ clients, translated ambiguous requirements into implementation plans, facilitated executive workshops, and stayed accountable until the change was adopted. My consulting learning curve is about firm method and cadence, not client-facing delivery fundamentals.",
            ),
            (
                "You may not have classic case interview experience.",
                "That is fair. My preparation would be to use a structured case method: clarify the objective, segment the problem, state assumptions, identify the highest-value analysis, and convert the finding into a practical recommendation. The work I have done gives me real examples of doing that in live delivery settings rather than only in practice cases.",
            ),
            (
                "Your background may look more implementation-heavy than strategy-heavy.",
                "That is the point of differentiation I would lead with carefully. I am strongest where strategy has to become an operating plan: stakeholder alignment, workflow design, data validation, training, adoption, and measurable outcomes. I would not sell myself as a pure strategy theorist; I would sell the ability to make recommendations executable.",
            ),
            (
                "Can you handle a client-facing environment with senior stakeholders?",
                "Yes. The proof is 60+ executive workshops and QBRs, 80+ client engagements, SOW and requirements work, and account recovery conversations where trust had to be rebuilt. My style is to be direct, practical, and prepared enough that stakeholders can make a decision.",
            ),
        ),
        selling_angles=(
            "Lead with the 80+ client portfolio and international delivery geography: this proves repeated client exposure, not a one-off project.",
            "Use 60+ executive workshops and QBRs as the consulting communication proof: Christian can structure the conversation for decision-makers.",
            "Use implementation ownership as the differentiator: he understands where recommendations break after the deck, and that makes his analysis more practical.",
            "Use the $1M+ account-risk stabilization story to show client-service judgment under pressure.",
            "Use five-site ERP ownership and 150+ user adoption to show he can translate strategy into operating change across multiple stakeholder groups.",
        ),
        anticipated_questions=(
            (
                "Why consulting, and why this firm?",
                "The honest answer is that the best parts of my work have always looked like practical consulting: understand the client problem, structure the path, align stakeholders, and stay with the work until the outcome is real. What attracts me to this firm is the chance to do that at greater scale and with a sharper problem-solving discipline.",
            ),
            (
                "Tell me about a time you solved an ambiguous client problem.",
                "Use the implementation or account recovery story. Lead with the ambiguity, then explain how Christian clarified the business outcome, identified the stakeholder conflict or process gap, built a practical path, and measured the result.",
            ),
            (
                "How would you turn analysis into an implementation plan?",
                "Start with the recommendation, then define the owner, decision needed, adoption risk, data requirement, timeline, and measure of success. The important move is to name what must become true operationally before the recommendation has value.",
            ),
        ),
        smart_questions=(
            "Where does this practice most often need people who can bridge recommendation and implementation?",
            "What separates someone who is analytically strong from someone clients actually trust in this role?",
            "How does the team decide when a recommendation is ready to move from analysis into execution planning?",
            "What types of client problems would this person likely touch in the first six months?",
        ),
        brevity_rules=(
            "Use a consulting answer shape: answer first, three-part structure, proof, implication.",
            "Do not over-narrate implementation details unless asked. Translate them into client problem, action, and result.",
            "End stories with what the client, stakeholder, or operating team could do differently because of the work.",
        ),
    )


def bigfour_story_key(title: str) -> str:
    lowered = title.lower()
    if "inventory" in lowered:
        return "inventory"
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
    return "default"


def bigfour_story_bridge(card: "StoryCard") -> str:
    key = bigfour_story_key(card.title)
    return {
        "inventory": "For a consulting client, this story shows the pattern I would use before recommending change: map the actual workflow, prove the root cause, design the practical control, and measure whether the new process works.",
        "account": "In consulting terms, this is client-service judgment under pressure: understand what broke trust, create one accountable recovery path, align the right stakeholders, and make progress visible enough for the client to believe again.",
        "dashboards": "The consulting bridge is decision quality. I do not treat reporting as the deliverable; I start with the decision the client has to make, validate the data, and turn the analysis into a clearer action path.",
        "learning": "This story maps to consulting ramp speed: learn the client's environment through the workflow, ask better questions quickly, and become useful before every detail is familiar.",
        "ops_finance": "This is the kind of stakeholder tradeoff consultants have to surface cleanly: each group is protecting a legitimate risk, and the work is to make the tradeoff explicit enough for leaders to decide.",
        "failure": "The consulting lesson is quality control in the recommendation process: validate assumptions earlier, bring SMEs in before the decision hardens, and build checkpoints before the cost of being wrong increases.",
        "workshops": "For consulting work, this story proves audience translation: the same recommendation has to be framed differently for executives, operators, technical teams, and customer-facing stakeholders.",
    }.get(key, f"For consulting work, this story should connect back to the client's practical problem: {card.result}")


def bigfour_calibration_question(card: "StoryCard") -> str:
    key = bigfour_story_key(card.title)
    return {
        "inventory": "Is that kind of root-cause-first process thinking useful for the client work this role supports?",
        "account": "Is rebuilding client trust through a practical recovery path a common part of this team's work?",
        "dashboards": "Does this practice value starting with the client decision before building the analysis?",
        "learning": "Is that kind of rapid client-environment ramp important for new consultants on this team?",
        "ops_finance": "How often does this role need to help clients make tradeoffs between groups with competing definitions of success?",
        "failure": "Is early assumption validation one of the habits this team emphasizes in client work?",
        "workshops": "How often would this role need to translate the same recommendation for different client audiences?",
    }.get(key, "Is that the right consulting frame for how this story maps to the role?")
