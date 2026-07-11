"""Shared job-search guidance used across advice, interview, and networking outputs."""

from __future__ import annotations

import re

import resume_analysis


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        clean = re.sub(r"\s+", " ", item).strip()
        key = clean.lower()
        if clean and key not in seen:
            ordered.append(clean)
            seen.add(key)
    return ordered


def search_strategy_lines() -> list[str]:
    return [
        "Work from a one-page career vision before applying: target role, alternative titles, preferred company profile, the business problem Christian solves, and the proof that supports it.",
        "Keep a shortlist of 5-7 priority companies, but load only one active posting into jobs/job_description.txt at a time so targeting and evidence do not get mixed.",
        "Think like a job shopper, not a volume-only applicant: clear target, intentional outreach, and direct proof beat vague interest and mass applying.",
        "Aim for 5-10 intentional applications per week once the base materials are strong. More volume is useful only if the target is already clear.",
        "Do the soul-search before the job search. If the target is muddy, the resume, LinkedIn profile, and interview answers will sound muddy too.",
    ]


def job_search_diagnosis_lines() -> list[str]:
    return [
        "Diagnose the search before reacting to it. A slow search can come from a hard market, a narrow target list, weak top-third proof, shaky recruiter screens, or broad interview answers.",
        "When the target and message are strong but the market is tight, the fix is usually more runway, more adjacent titles, or a broader company mix, not panic rewriting.",
        "When conversations start but stall, inspect the message first: title targeting, summary clarity, answer structure, and knockout-term alignment are more controllable than the market.",
        "Use Christian's own pipeline patterns to diagnose the search. Do not force generic internet ratios or application benchmarks onto every market cycle.",
    ]


def jd_wish_list_reality_lines() -> list[str]:
    return [
        "Many job descriptions are broad wish lists or moving targets. Apply when the core problem, lane, and proof fit are substantively aligned even if a few secondary items are adjacent.",
        "Separate real knockout terms from preference language. The recruiter screen often reveals which listed requirements are truly fixed.",
        "Do not over-explain every missing line item. A broad-fit application is still credible when the main problem, stakeholder pattern, and operating environment match Christian's proof.",
    ]


def resume_strategy_lines() -> list[str]:
    return [
        "The resume is a marketing document, not an autobiography. Its job is to earn the interview by showing similar problems solved with credible proof.",
        "ATS reality: most missed opportunities come from weak proof, poor positioning, or knockout answers, not from a secret score that can be hacked.",
        "Use one strong base resume and tailor the top third, proof points, and keywords to the active role. Do not spend hours rewriting every line for every posting.",
        "Never use white-font text, keyword stuffing, or copied job-ad claims. If Christian cannot defend the wording in conversation, it does not belong on the page.",
        "Avoid both 'I just' minimization and autobiography syndrome. Paid, unpaid, short-term, and volunteer work can count when the contribution is real and accurately framed.",
        "Front-load proof of business relevance: what changed, for whom, at what scope, and why it mattered.",
    ]


def recruiter_screen_lines(job_description: str = "") -> list[str]:
    lines = [
        "Treat the recruiter screen as a terms-and-clarity test. The usual risks are not mysterious: mismatch on job terms, weak communication, or a true must-have gap.",
        "Prepare honest one-line answers on work authorization, preferred location, remote or hybrid expectations, travel tolerance, compensation range, and start-date flexibility.",
        "If a question sounds like a knockout filter, answer it directly and truthfully. Do not game work authorization, relocation, travel, or tool-depth questions.",
        "Keep recruiter-screen answers short: answer, reason, and one proof point. Do not turn the first call into a full career narrative.",
        "If the recruiter asks for compensation first, ask for the approved range and keep the conversation focused on fit and scope rather than personal need.",
    ]
    if resume_analysis.jd_mentions(job_description, "travel", "% travel"):
        lines.append("This posting mentions travel. Be ready with a direct answer on percentage tolerance before the recruiter has to ask twice.")
    if resume_analysis.jd_mentions(job_description, "remote", "hybrid", "onsite", "on-site"):
        lines.append("This posting names a work-location policy. Confirm Christian's location fit early instead of letting it become a late-stage surprise.")
    if resume_analysis.jd_mentions(job_description, "clearance", "authorized to work", "sponsorship", "visa"):
        lines.append("This posting signals screening around authorization or compliance. Keep the answer precise and avoid hopeful language.")
    return _dedupe(lines)


def recruiter_call_research_calibration_lines() -> list[str]:
    return [
        "First recruiter call: light research is enough. Know the company, the role, the business model, and one concrete reason the work fits.",
        "Hiring-manager and later-round conversations require deeper research: team priorities, customer problem, workflow friction, success measures, and likely handoffs.",
        "Do not spend hours on deep research before basics like compensation range, location fit, travel, and must-have terms are confirmed.",
    ]


def follow_up_timing_lines() -> list[str]:
    return [
        "Ask about the timeline before the interview ends so the next follow-up is anchored to something the team actually said.",
        "If they named a response window, follow up the next business day after that window ends.",
        "If they gave no timeline, a short check-in after about five business days is reasonable.",
        "If the only goal is scheduling, it is reasonable to follow up more quickly because logistics silence is different from evaluation silence.",
        "Keep follow-up emails to one or two short paragraphs. Positivity, brevity, and clarity matter more than intensity.",
        "Do not apologize for following up. Replace 'sorry to bother you' with a calm, useful update or a direct next-step question.",
        "Use current-company news only when it comes from user-supplied or otherwise verified context. Never invent a personalization angle.",
    ]


def concise_email_rules() -> list[str]:
    return [
        "State the point in the first sentence: check-in, update, or thank-you.",
        "Name one specific reason for interest or one concrete discussion point instead of repeating a full pitch.",
        "End with a clear next-step ask or a clean signal that Christian remains interested.",
        "Avoid over-formal filler, stacked compliments, and generic mission praise.",
    ]


def salary_research_lines(job_description: str = "") -> list[str]:
    lines = [
        "Research compensation from multiple sources and log the date, geography, title match, base range, and any bonus or equity component.",
        "Ask for the approved range early enough to avoid negotiating in the dark. A range-first conversation is cleaner than guessing first.",
        "Define a target, an acceptable floor, and a walkaway point before the recruiter or offer call.",
        "Negotiate late, when the company already wants Christian. Keep the tone collaborative and the reasoning tied to scope, market data, and direct proof.",
        "Separate base salary from bonus, commission, equity, PTO, remote flexibility, and development budget before comparing offers.",
    ]
    if resume_analysis.jd_mentions(job_description, "remote"):
        lines.append("Remote roles often mix national and local pay logic. Compare remote-national data separately from Atlanta or local-market ranges.")
    return _dedupe(lines)


def counteroffer_evaluation_lines() -> list[str]:
    return [
        "Evaluate a counteroffer slowly and neutrally. Start with the original reason Christian began looking, then ask whether the counteroffer actually fixes it.",
        "Compare the full package: base salary, bonus, equity, PTO, flexibility, title, reporting line, and development budget.",
        "Ask a simple truth test: if no counteroffer appeared, would staying still feel like the right decision?",
        "A counteroffer is information, not a command. Use it to clarify the better long-term fit rather than to win a short-term point.",
    ]


def remote_hybrid_screening_lines() -> list[str]:
    return [
        "Remote does not always mean work-from-anywhere. Many postings still carry state, country, tax, or time-zone limits.",
        "Confirm location, onsite rhythm, and travel expectations early so Christian does not waste energy deep in the process.",
        "If asked why remote or hybrid work matters, answer in terms of work rhythm, focus, communication, and customer value, not lifestyle alone.",
        "Use real remote-proof examples when possible: documentation quality, response discipline, workshop delivery, issue tracking, and stakeholder visibility.",
    ]


def linkedin_findability_lines() -> list[str]:
    return [
        "Headline, first three About lines, recent experience titles, and the skills section carry the most recruiter-discovery weight.",
        "Make the target lane obvious in plain English before adding tool language.",
        "Keep proof visible: scope, named platforms, customer context, and measurable outcomes should show up across the profile, not only in a skills list.",
        "Treat LinkedIn as a recruiter-facing positioning asset, not as resume-source material.",
    ]


def recruiter_facing_keywords(
    profile: resume_analysis.JobProblemProfile,
    job_description: str,
) -> list[str]:
    keywords = sorted(
        resume_analysis.audit_keywords(job_description),
        key=lambda keyword: (
            job_description.lower().count(keyword.lower()),
            len(keyword.split()),
            len(keyword),
            keyword,
        ),
        reverse=True,
    )
    combined = keywords + list(profile.safe_terms) + list(resume_analysis.visible_role_specialties(job_description))
    return _dedupe([item for item in combined if len(item) >= 3])[:15]


def safe_thought_leadership_themes(
    profile: resume_analysis.JobProblemProfile,
    job_description: str,
) -> list[str]:
    specialty = resume_analysis.role_specialty_phrase(job_description, profile.core_problem)
    by_lane = {
        "implementation_delivery": [
            "What early implementation risk signals usually show up before a launch slips.",
            "How to explain configuration, data, testing, and training in customer language instead of tool language.",
            "What makes a go-live update useful to an executive and usable to the delivery team.",
        ],
        "presales_solution": [
            "What good discovery sounds like before any demo starts.",
            "How to connect product proof to buyer risk instead of feature narration.",
            "Why implementation realism makes a solution recommendation more credible.",
        ],
        "customer_success": [
            "What account-health signals say before renewal risk becomes visible in the CRM.",
            "How customer trust is rebuilt through ownership and follow-through, not status meetings alone.",
            "What makes an executive review useful instead of generic.",
        ],
        "change_enablement": [
            "Why adoption stalls after announcements and what makes change usable in daily work.",
            "How role-based training differs from generic communications.",
            "What proof shows that a change stuck after rollout.",
        ],
        "analytics_operations": [
            "What separates a dashboard from a decision tool.",
            "How to check whether leaders trust a metric before building another report.",
            "Why workflow visibility matters as much as data volume.",
        ],
        "corporate_strategy": [
            "How to make tradeoffs visible before recommending action.",
            "Why ambiguity needs structure, owner logic, and implementation checkpoints.",
            "What makes a recommendation durable after the meeting ends.",
        ],
    }
    default = [
        f"What makes {specialty} work easier for customers, stakeholders, or operators in practice.",
        "How to turn messy workflow issues into a clearer next decision.",
        "What proof should exist before calling a change successful.",
    ]
    return by_lane.get(profile.primary_lane, default)


def linkedin_comment_strategy_lines(
    profile: resume_analysis.JobProblemProfile,
    job_description: str,
) -> list[str]:
    specialty = resume_analysis.role_specialty_phrase(job_description, profile.core_problem)
    return [
        f"Comment where the post touches work Christian can credibly discuss: {specialty}, customer friction, reporting clarity, stakeholder alignment, or workflow improvement.",
        "Use a simple comment structure: observation, practical implication, and one short example or question.",
        "Prefer comments that make another operator feel understood over comments written to sound impressive.",
        "Nine out of ten interactions should support the target lane rather than scatter across unrelated topics.",
    ]


def informational_interview_lines(company_name: str = "", role_title: str = "") -> list[str]:
    company_phrase = f" at {company_name}" if company_name else ""
    role_phrase = f" about the {role_title} role" if role_title else ""
    return [
        f"Open with a short, specific ask: 20 minutes to learn{role_phrase}{company_phrase}, not a vague request to 'pick your brain'.",
        "Personalize the outreach with one visible reason the person is relevant: team, workflow, customer segment, product area, or career path.",
        "Use the conversation to learn how the team measures success, where the friction sits, and what makes someone useful quickly.",
        "Move the relationship forward with a brief thank-you and one follow-up note only when Christian has a relevant update or thoughtful next question.",
    ]


def follow_up_sequence_lines(company_name: str, role_title: str) -> list[str]:
    return [
        f"Connection request: name the {role_title} role at {company_name}, one reason the person stood out, and a light request for advice.",
        "If there is no response, send one follow-up after about five business days. Do not stack repeated nudges on cold outreach.",
        "After a conversation, send a thank-you within 24 hours that names one useful insight and one action Christian took from it.",
        "If the conversation was helpful, send a light progress update later instead of jumping straight to a referral ask.",
        "Use referral language only after there is context, fit, and enough trust for the person to say yes without feeling cornered.",
    ]


def general_advice_sections() -> dict[str, list[str]]:
    return {
        "Search Strategy": search_strategy_lines(),
        "Job Search Diagnosis": job_search_diagnosis_lines(),
        "JD Wish List Reality": jd_wish_list_reality_lines(),
        "Resume Strategy": resume_strategy_lines(),
        "Recruiter Screen": recruiter_screen_lines(),
        "Recruiter Call Research Calibration": recruiter_call_research_calibration_lines(),
        "Interview Method (CAAR)": [
            "Preferred framework: Challenge, Action, Analysis, Result.",
            "Use STAR only when the firm explicitly requires it, such as McKinsey, Bain, BCG, or Big 4 interviews.",
            "Lead top-down: answer first, then the story. Never build to the answer.",
            "Show Level 3 traits: what you noticed, what you decided, how you adjusted, and what resulted.",
            "Negative questions: answer with an omission - name something positive you wanted more of, not something you disliked.",
            "Failure questions: pivot to what you learned and specifically changed afterward.",
            "Why this job: lead with the company first, then role fit, then use the word 'because' explicitly.",
            "15-20 seconds for short answers. Let them pull for more.",
            "Eliminate fillers: 'as well,' 'you know,' and 'also.'",
        ],
        "Networking And Informational Interviews": informational_interview_lines(),
        "Follow-Up Discipline": follow_up_timing_lines() + concise_email_rules(),
        "LinkedIn": linkedin_findability_lines(),
        "Salary And Offers": salary_research_lines() + counteroffer_evaluation_lines(),
        "Remote And Hybrid Screening": remote_hybrid_screening_lines(),
        "Communication Principles": [
            "Draft first, edit second. Get the message down quickly, then tighten structure, tone, and precision.",
            "Speed of response is not competence. Appropriate response at the right time is.",
            "Paraphrase before responding: it validates the other person, improves fidelity, and buys time.",
            "Use 'Tell me more' as a universal fallback in any conversation.",
            "What / So What / Now What is the clearest structure for any short message.",
            "SCR (Situation, Complication, Resolution) for business communication. Pyramid Principle for recommendations.",
            "Sentences ending on a lower pitch sound confident. Ending on a higher pitch sounds uncertain.",
            "Concision is almost always better. Tell me the time, do not build me the clock.",
        ],
    }
