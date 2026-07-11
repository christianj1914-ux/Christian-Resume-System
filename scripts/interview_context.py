"""Interview dossier, structured debrief, and company-context helpers.

These helpers keep raw notes, company intelligence, and coaching signals
separate while still exposing compatibility text for older scripts.
"""

from __future__ import annotations

import json
import re
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from utils import clean_source_text, companies_refer_to_same, read_text


SCOPED_NOTES_DIR_NAME = "interview_notes_by_company"
COMPANY_NOTES_DIR_NAME = "company_notes"
STRUCTURED_DEBRIEFS_DIR_NAME = "interview_debriefs"
LEGACY_BACKUP_DIR_NAME = "interview_legacy_backups"
DEBRIEF_DELIMITER = "POST-INTERVIEW DEBRIEF CAPTURED"
REVIEW_ANALYSIS_PARSER_VERSION = "2026-06-25-compact-v1"
COMPACT_SUPPLIED_CONTEXT_MAX_WORDS = 800
NEWS_SIGNAL_TERMS = (
    "announced",
    "launched",
    "released",
    "rolled out",
    "expanded",
    "opened",
    "acquired",
    "acquisition",
    "funding",
    "award",
    "recognized",
    "named",
    "partnership",
    "partnered",
    "grew",
    "growth",
)
COACHING_SIGNAL_RULES: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    (
        "rambling",
        "Rambling / answer length",
        "Shorten answers by 30 to 40 percent and stop after the proof lands.",
        (
            r"\brambl\w*",
            r"\btoo long\b",
            r"\bwandered\b",
            r"\blong path to get to the point\b",
            r"\bover explain",
            r"\bcut your answer length by 30 ?[-–]?40%",
        ),
    ),
    (
        "delayed_answer",
        "Delayed answer / buried lead",
        "Answer in the first sentence, then give one proof example.",
        (
            r"\bdidn.?t lead with\b",
            r"\blead(?:ing)? with the direct answer\b",
            r"\banswer first\b",
            r"\bdirect answer first\b",
            r"\bget to the point\b",
            r"\bstart with the conclusion\b",
            r"\bnot answering the exact question first\b",
        ),
    ),
    (
        "wrong_example_first",
        "Wrong example first",
        "Lead with the closest full-lifecycle example, then separate enhancement work clearly.",
        (
            r"\bwrong example first\b",
            r"\busing the wrong example first\b",
            r"\bsteer you away\b",
            r"\blead with aptian\b",
            r"\buse aptian for full implementation lifecycle\b",
        ),
    ),
    (
        "filler_restarts",
        "Filler / restart language",
        "Cut filler phrases, repeated restarts, and throat-clearing setup.",
        (
            r"\bfiller\b",
            r"\brepeated restarts\b",
            r"\bthings of that nature\b",
            r"\bsort of\b",
            r"\bpretty much\b",
            r"\bin that situation\b",
        ),
    ),
    (
        "consultative_questions",
        "Questions too tactical",
        "Ask role-success, ramp, stakeholder, and client-trust questions before tactical tooling questions.",
        (
            r"\btactical, not strategic\b",
            r"\bquestions at the end were okay, not impressive\b",
            r"\bstronger questions usually center on\b",
            r"\bmixed quality\b",
            r"\basking high-impact questions\b",
        ),
    ),
    (
        "executive_presence",
        "Executive presence / polish",
        "Sound more declarative, controlled, and client-ready under pressure.",
        (
            r"\bexecutive presence\b",
            r"\bclient-facing presence\b",
            r"\bconsultative presence\b",
            r"\bnot polished\b",
            r"\bdoesn.?t present it crisply\b",
            r"\bnot sharply packaged\b",
            r"\btoo long, loose, and reactive rather than crisp and consultative\b",
        ),
    ),
)
REVIEW_SECTION_HEADINGS = {
    "where you were strongest",
    "where you were weakest",
    "where you got redirected",
    "likely positives",
    "likely concerns",
    "filler style habits",
    "best answers from this interview rewritten",
    "final honest verdict",
    "overall interview score",
    "where you underperformed",
    "biggest risks to fix",
    "round 2 cheat sheet",
    "top 5 answers to keep ready",
    "best questions to ask in round 2",
    "do not say it this way list",
    "best structure for almost every answer",
    "your strongest positioning angles",
    "your safest one sentence closer",
    "round 2 mindset",
    "brutally honest read",
    "what worked",
    "biggest risk you created",
    "best signals jonathan likely took away",
    "weak signals jonathan likely took away",
    "what round 2 will probably test",
    "what to fix before round 2",
    "most important fix before round 2",
    "best move before round 2",
    "hard coaching what to avoid",
    "best delivery formula",
    "do this instead",
}
INTERVIEW_QUESTION_STOP_HEADINGS = {
    "scorecard",
    "pattern analysis",
    "best answers from this interview rewritten",
    "hard coaching what to avoid",
    "hard coaching",
    "best delivery formula",
}
IGNORED_LIST_LINES = {
    "none supplied",
    "none supplied.",
    "raw notes:",
    "stories that generated follow-up questions:",
    "unexpected questions:",
    "specific interviewer language about the role:",
    "feedback received:",
    "insider company intelligence learned:",
    "performance summary:",
    "strongest answers:",
    "weakest answers:",
    "next-round risks:",
    "coaching signals:",
}
DEFAULT_LANGUAGE_REWRITE_AVOID = (
    "We worked on",
    "I helped with",
    "I was involved in",
    "sort of",
    "pretty much",
    "things of that nature",
)
DEFAULT_LANGUAGE_REWRITE_PREFER = (
    "I owned",
    "I led",
    "I was responsible for",
    "I coordinated",
    "I guided users through rollout",
)
DEFAULT_CONSULTATIVE_PHRASES = (
    "I aligned stakeholders",
    "I clarified requirements",
    "I reduced scope ambiguity",
    "I translated business needs into implementation steps",
    "I managed expectations",
    "I guided users through rollout",
)
OWNERSHIP_VERB_LADDER = (
    "owned",
    "led",
    "was responsible for",
    "coordinated",
    "supported",
)


@dataclass(frozen=True)
class CompanyContextBundle:
    company_research: str
    interview_notes: str
    coaching_notes: str
    supplied_context: str
    round_records: tuple[dict[str, object], ...]
    mode: str = "compact"


def slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return cleaned or "unknown"


def _clean_scalar(value: object) -> str:
    if value is None:
        return ""
    return clean_source_text(str(value)).strip()


def _unique_strings(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = re.sub(r"\s+", " ", value).strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        result.append(cleaned)
        seen.add(key)
    return result


def _split_lines(value: object) -> list[str]:
    if isinstance(value, str):
        parts: list[str] = []
        for raw_line in clean_source_text(value).splitlines():
            cleaned = re.sub(r"\s+", " ", raw_line).strip(" -")
            lowered = cleaned.lower()
            if not cleaned or lowered in IGNORED_LIST_LINES or re.match(r"^#+\s+", cleaned):
                continue
            parts.append(cleaned)
        return _unique_strings(part for part in parts if part)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        items: list[str] = []
        for item in value:
            items.extend(_split_lines(item))
        return _unique_strings(items)
    cleaned = _clean_scalar(value)
    return [cleaned] if cleaned else []


def _clean_raw_notes_text(value: object) -> str:
    cleaned = clean_source_text(str(value or "")).strip()
    if not cleaned:
        return ""
    lines = cleaned.splitlines()
    while lines and lines[0].strip().lower() in {
        "raw notes:",
        "include interviewer language, questions, objections, feedback, and next-step clues.",
    }:
        lines.pop(0)
    return "\n".join(lines).strip()


def _first_non_empty(*values: object) -> str:
    for value in values:
        cleaned = _clean_scalar(value)
        if cleaned:
            return cleaned
    return ""


def _prefer_richer_scalar(*values: object) -> str:
    candidates = [_clean_scalar(value) for value in values if _clean_scalar(value)]
    if not candidates:
        return ""
    return max(candidates, key=lambda item: (len(item), item.lower()))


def _word_count(value: str) -> int:
    return len(re.findall(r"\b\w+\b", clean_source_text(value)))


def _truncate_words(value: str, limit: int) -> str:
    cleaned = clean_source_text(value).strip()
    if not cleaned or limit <= 0:
        return ""
    words = cleaned.split()
    if len(words) <= limit:
        return cleaned
    return " ".join(words[:limit]).rstrip(" ,;:.") + "..."


def context_mentions_company(text: str, company_name: str) -> bool:
    lowered = text.lower()
    company_lower = company_name.lower().strip()
    if not company_lower:
        return False
    if company_lower == "state farm":
        return "state farm" in lowered or "statefarm" in lowered
    if company_lower in lowered:
        return True
    tokens = [token for token in re.split(r"[^a-z0-9]+", company_lower) if len(token) >= 4]
    stop = {
        "inc",
        "llc",
        "corp",
        "corporation",
        "company",
        "technologies",
        "technology",
        "systems",
        "dynamics",
        "state",
        "farm",
        "group",
        "global",
        "international",
    }
    signal_tokens = [token for token in tokens if token not in stop]
    if len(signal_tokens) >= 2:
        return all(token in lowered for token in signal_tokens)
    return bool(signal_tokens) and signal_tokens[0] in lowered


def relevant_company_context(text: str, company_name: str) -> str:
    cleaned = clean_source_text(text)
    if not cleaned:
        return ""
    blocks = [block.strip() for block in re.split(r"\n\s*\n+", cleaned) if block.strip()]
    matching_blocks = [block for block in blocks if context_mentions_company(block, company_name)]
    if matching_blocks:
        return "\n\n".join(matching_blocks).strip()
    if context_mentions_company(cleaned, company_name):
        return cleaned
    return ""


def note_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in clean_source_text(text).splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if line and not line.lower().startswith(("post-interview note", "interview notes file:")):
            lines.append(line)
    return lines


def recent_company_news_line(text: str, company_name: str) -> str:
    cleaned = relevant_company_context(text, company_name)
    if not cleaned:
        return ""
    for line in note_lines(cleaned):
        lowered = line.lower()
        if any(term in lowered for term in NEWS_SIGNAL_TERMS):
            return line
    return ""


def scoped_notes_dir(jobs_dir: Path) -> Path:
    return jobs_dir / SCOPED_NOTES_DIR_NAME


def company_notes_dir(jobs_dir: Path) -> Path:
    return jobs_dir / COMPANY_NOTES_DIR_NAME


def structured_debriefs_dir(jobs_dir: Path) -> Path:
    return jobs_dir / STRUCTURED_DEBRIEFS_DIR_NAME


def structured_company_debrief_dir(jobs_dir: Path, company_name: str) -> Path:
    return structured_debriefs_dir(jobs_dir) / slug(company_name)


def legacy_backup_dir(jobs_dir: Path) -> Path:
    return jobs_dir / LEGACY_BACKUP_DIR_NAME


def scoped_note_filename(company_name: str, role_title: str, round_number: str = "") -> str:
    company_slug = slug(company_name)
    role_slug = slug(role_title)
    round_slug = slug(f"round_{round_number}") if round_number.strip() else "general"
    return f"{company_slug}__{role_slug}__{round_slug}.txt"


def scoped_note_path(jobs_dir: Path, company_name: str, role_title: str, round_number: str = "") -> Path:
    return scoped_notes_dir(jobs_dir) / scoped_note_filename(company_name, role_title, round_number)


def company_dossier_path(jobs_dir: Path, company_name: str) -> Path:
    return company_notes_dir(jobs_dir) / f"{slug(company_name)}.md"


def review_appendix_path(jobs_dir: Path, company_name: str, interview_date: str, round_number: str = "", role_title: str = "") -> Path:
    base_name = structured_debrief_filename(interview_date, round_number, role_title).replace(".json", "__review.txt")
    return structured_company_debrief_dir(jobs_dir, company_name) / base_name


def _normalize_date_iso(value: str) -> str:
    cleaned = _clean_scalar(value)
    if not cleaned:
        return ""
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%m-%d-%y"):
        try:
            return datetime.strptime(cleaned, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def _display_date(value: str, iso_value: str = "") -> str:
    cleaned = _clean_scalar(value)
    if cleaned:
        return cleaned
    return iso_value


def structured_debrief_filename(interview_date: str, round_number: str = "", role_title: str = "") -> str:
    date_part = _normalize_date_iso(interview_date) or "unknown-date"
    round_part = slug(f"round_{round_number}") if round_number.strip() else "round_general"
    return f"{date_part}__{round_part}.json"


def structured_debrief_path(jobs_dir: Path, company_name: str, interview_date: str, round_number: str = "", role_title: str = "") -> Path:
    return structured_company_debrief_dir(jobs_dir, company_name) / structured_debrief_filename(interview_date, round_number, role_title)


def matching_scoped_note_paths(jobs_dir: Path, company_name: str, role_title: str = "") -> list[Path]:
    directory = scoped_notes_dir(jobs_dir)
    if not directory.is_dir():
        return []
    company_slug = slug(company_name)
    role_slug = slug(role_title)
    paths = sorted(directory.glob(f"{company_slug}__*.txt"))
    if role_slug and paths:
        exact_role = [path for path in paths if f"__{role_slug}__" in path.name]
        general = [path for path in paths if "__general" in path.name]
        return exact_role + [path for path in general if path not in exact_role]
    return paths


def _docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml").decode("utf-8", errors="ignore")
    text = re.sub(r"</w:p>", "\n", xml)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return clean_source_text(text)


def read_artifact_text(path: Path) -> str:
    if not path.exists():
        return ""
    if path.suffix.lower() == ".docx":
        return _docx_text(path)
    return clean_source_text(read_text(path))


def _read_review_appendix(path_value: object) -> str:
    path_text = _clean_scalar(path_value)
    if not path_text:
        return ""
    try:
        path = Path(path_text)
    except (OSError, ValueError):
        return ""
    return read_artifact_text(path) if path.exists() else ""


def _review_heading_key(value: str) -> str:
    lowered = re.sub(r"[^a-z0-9 ]+", " ", value.lower())
    return re.sub(r"\s+", " ", lowered).strip()


def _collect_review_section(lines: Sequence[str], headings: Sequence[str], limit: int = 6) -> list[str]:
    heading_keys = {_review_heading_key(item) for item in headings}
    start = -1
    for index, line in enumerate(lines):
        if _review_heading_key(line) in heading_keys:
            start = index + 1
            break
    if start < 0:
        return []
    collected: list[str] = []
    for line in lines[start:]:
        key = _review_heading_key(line)
        if key in REVIEW_SECTION_HEADINGS and collected:
            break
        if line.lower().startswith(("score", "answer:", "follow-up:", "skeptical follow-up:", "pressure-test follow-up:")):
            continue
        cleaned = re.sub(r"\s+", " ", line).strip(" -")
        if not cleaned:
            continue
        collected.append(cleaned)
        if len(collected) >= limit:
            break
    return _unique_strings(collected)


def _first_matching_review_line(lines: Sequence[str], patterns: Sequence[str]) -> str:
    for line in lines:
        lowered = line.lower()
        for pattern in patterns:
            if re.search(pattern, lowered, re.I):
                if ":" in line:
                    _, _, remainder = line.partition(":")
                    candidate = remainder.strip()
                    if candidate:
                        return candidate
                return line.strip()
    return ""


def analyze_performance_review(text: str) -> dict[str, object]:
    cleaned = clean_source_text(text)
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    strongest_answers = _collect_review_section(
        lines,
        ("Where you were strongest", "Likely positives", "Best signals Jonathan likely took away"),
    )
    weakest_answers = _collect_review_section(
        lines,
        ("Where you were weakest", "Likely concerns", "Where you underperformed"),
    )
    next_round_risks = _collect_review_section(
        lines,
        ("Biggest risks to fix", "What to fix before round 2", "Most important fix before round 2", "Best move before round 2", "Do this instead"),
        limit=8,
    )
    summary = _first_matching_review_line(
        lines,
        (
            r"^overall:",
            r"^overall performance:",
            r"^bottom line$",
            r"^final honest verdict$",
        ),
    )
    coaching_signals: list[dict[str, str]] = []
    lowered = cleaned.lower()
    for key, label, detail, patterns in COACHING_SIGNAL_RULES:
        evidence = ""
        for raw_line in lines:
            if any(re.search(pattern, raw_line, re.I) for pattern in patterns):
                evidence = raw_line
                break
        if evidence or any(re.search(pattern, lowered, re.I) for pattern in patterns):
            coaching_signals.append(
                {
                    "key": key,
                    "label": label,
                    "detail": detail,
                    "evidence": evidence,
                }
            )
    return {
        "summary": summary,
        "strongest_answers": strongest_answers,
        "weakest_answers": weakest_answers,
        "next_round_risks": next_round_risks,
        "coaching_signals": coaching_signals,
    }


def analyze_review_positioning(
    text: str,
    performance_review: Mapping[str, object] | None = None,
    *,
    company_name: str = "",
    role_title: str = "",
    role_language: Sequence[str] = (),
    company_intelligence: Sequence[str] = (),
) -> dict[str, object]:
    review = _serialize_performance_review(performance_review if isinstance(performance_review, Mapping) else {})
    cleaned = clean_source_text(text)
    lowered = cleaned.lower()
    signal_items = review.get("coaching_signals", [])
    signal_keys = {
        _clean_scalar(item.get("key"))
        for item in signal_items  # type: ignore[union-attr]
        if isinstance(item, Mapping) and _clean_scalar(item.get("key"))
    }
    strongest_answers = _split_lines(review.get("strongest_answers", []))
    weakest_answers = _split_lines(review.get("weakest_answers", []))
    next_round_risks = _split_lines(review.get("next_round_risks", []))
    interviewer_questions = list(extract_interviewer_questions(cleaned, limit=6))
    ownership_gap = bool(
        signal_keys.intersection({"wrong_example_first", "delayed_answer", "filler_restarts"})
        or re.search(r"\bownership\b|\bowned enough\b|\bclient-facing leadership\b", lowered)
    )
    consultative_gap = bool(
        signal_keys.intersection({"consultative_questions", "executive_presence"})
        or re.search(r"\bconsultative\b|\bclient-facing\b|\bexecutive presence\b|\bpolished consultant\b", lowered)
    )
    technical_credibility = bool(
        strongest_answers
        or re.search(r"\bqualified\b|\brelevant\b|\bimplementation exposure\b|\btechnical\b", lowered)
    )

    if technical_credibility and ownership_gap and consultative_gap:
        decision_headline = (
            "Relevant background came through, but the delivery did not yet sound ownership-forward, consultative, or client-ready enough for the role."
        )
    elif ownership_gap:
        decision_headline = "The background sounded relevant, but ownership and decision-making did not come through decisively enough."
    elif consultative_gap:
        decision_headline = "The experience looked relevant, but the delivery did not sound consultative or polished enough for a client-facing role."
    else:
        decision_headline = _clean_scalar(review.get("summary")) or "Relevant experience came through, but sharper positioning would improve the odds."

    translation: list[str] = []
    if technical_credibility:
        translation.append("This reads as adjacent and credible rather than a clean mismatch.")
    if ownership_gap:
        translation.append("The main gap is making personal ownership unmistakable in discovery, client leadership, implementation direction, and rollout decisions.")
    if consultative_gap:
        translation.append("The role wanted a more advisor-like, structured, and executive-ready delivery style.")
    if re.search(r"\bprioritizing candidates\b|\bfound someone stronger\b|\bclosely align\b", lowered):
        translation.append("Another candidate likely told the ownership and consultative story more cleanly.")

    reasons: list[str] = []
    if "delayed_answer" in signal_keys:
        reasons.append("Answers often buried the point instead of opening with a direct claim.")
    if "wrong_example_first" in signal_keys:
        reasons.append("Adjacent examples appeared before the closest direct implementation proof.")
    if "executive_presence" in signal_keys:
        reasons.append("Delivery sounded more reactive and operator-oriented than crisp and consultant-ready.")
    if "consultative_questions" in signal_keys:
        reasons.append("End-of-interview questions sounded more tactical than outcome-oriented.")
    if "filler_restarts" in signal_keys:
        reasons.append("Filler phrases and restarts softened authority even when the substance was solid.")
    if not reasons and weakest_answers:
        reasons.extend(weakest_answers[:4])

    good_news: list[str] = []
    if technical_credibility:
        good_news.append("The review reads as fixable presentation risk, not as a hard-background mismatch.")
    if strongest_answers:
        good_news.append("Proof already landed in stronger areas such as " + "; ".join(strongest_answers[:4]) + ".")

    hard_truth = (
        "The likely loss was less about basic relevance and more about how ownership, structure, and consultative fit came across."
        if ownership_gap or consultative_gap
        else "Sharper structure and cleaner proof would still improve the next round."
    )

    delivery_shifts = [
        "Lead with the answer in sentence one.",
        "Use one direct example before adding background.",
        "Name your role explicitly instead of leaving ownership implied.",
        "Close on business value, adoption, decision quality, or risk reduction.",
    ]
    if "wrong_example_first" in signal_keys:
        delivery_shifts.append("Lead with the closest full-lifecycle implementation example before enhancement or support stories.")
    if "consultative_questions" in signal_keys:
        delivery_shifts.append("Ask about success profile, ramp risk, stakeholder trust, and delivery outcomes before tooling details.")

    role_language_lines = _unique_strings(list(role_language))[:5]
    company_signal_lines = _unique_strings(list(company_intelligence))[:4]
    takeaway = (
        "Technically credible and relevant, but not yet packaged with strong enough ownership or consultative presence."
        if ownership_gap or consultative_gap
        else decision_headline
    )
    fit_read = (
        "Best targeting remains implementation, solution-consulting, customer-facing delivery, and adoption-heavy roles that reward structured ownership and clear stakeholder guidance."
    )
    if role_title:
        fit_read = f"For {role_title}, the best positioning is implementation ownership plus consultative stakeholder guidance without overstating authority."

    return {
        "parser_version": REVIEW_ANALYSIS_PARSER_VERSION,
        "decision_signal": {
            "headline": decision_headline,
            "translation": _unique_strings(translation)[:4],
        },
        "positioning_diagnosis": {
            "headline": decision_headline,
            "reasons": _unique_strings(reasons)[:5],
            "good_news": _unique_strings(good_news)[:3],
            "hard_truth": hard_truth,
        },
        "language_rewrites": {
            "ownership_ladder": list(OWNERSHIP_VERB_LADDER),
            "avoid": list(DEFAULT_LANGUAGE_REWRITE_AVOID),
            "prefer": list(DEFAULT_LANGUAGE_REWRITE_PREFER),
            "consultative_phrases": list(DEFAULT_CONSULTATIVE_PHRASES),
        },
        "answer_strategy": {
            "default_structure": ["Problem", "Your role", "Action", "Result"],
            "delivery_shifts": _unique_strings(delivery_shifts)[:6],
        },
        "answer_assets": {
            "best_takeaway_statement": takeaway,
            "interviewer_questions": interviewer_questions[:6],
            "role_language_lines": role_language_lines,
            "company_signal_lines": company_signal_lines,
        },
        "career_targeting": {
            "fit_read": fit_read,
            "next_steps": [
                "Rewrite core stories so sentence one states the answer and the ownership line.",
                "Make consultative behavior explicit: stakeholder alignment, requirements clarification, scope control, expectation management, and rollout guidance.",
                "Practice using the strongest truthful ownership verb the evidence supports.",
            ],
        },
    }


def extract_interviewer_questions(review_text: str, limit: int = 10) -> tuple[str, ...]:
    cleaned = clean_source_text(review_text)
    if not cleaned.strip():
        return ()

    filler_question_patterns = (
        r"\bmake sense\b",
        r"\bfollowing (?:me|that)\b",
        r"\bdoes that\b",
        r"\bam i (?:right|correct|following)\b",
        r"\bright\?\s*$",
        r"\bcorrect\?\s*$",
        r"\bif that makes sense\b",
        r"\byou know what i mean\b",
    )

    def is_substantive_interview_question(body: str) -> bool:
        lowered_body = re.sub(r"\s+", " ", body).lower().strip()
        if len(lowered_body.split()) < 4:
            return False
        return not any(re.search(pattern, lowered_body) for pattern in filler_question_patterns)

    questions: list[str] = []
    for raw_line in cleaned.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        lowered = line.lower().strip(" :")
        if lowered in INTERVIEW_QUESTION_STOP_HEADINGS:
            break
        match = re.match(r"^\d+[\).]\s*(.+)$", line)
        if not match:
            continue
        body = match.group(1).strip()
        body_lower = body.lower()
        if "your question" in body_lower or "your follow-up question" in body_lower:
            continue
        quoted = re.search(r'"([^"]+\?)"', body)
        if quoted and is_substantive_interview_question(quoted.group(1)):
            questions.append(quoted.group(1).strip())
        elif body.endswith("?") and is_substantive_interview_question(body):
            questions.append(body)
        if len(questions) >= limit:
            break
    return tuple(_unique_strings(questions[:limit]))


def interviewer_questions_from_record(record: Mapping[str, object], limit: int = 10) -> tuple[str, ...]:
    def keep_question(prompt: str) -> bool:
        normalized = re.sub(r"\s+", " ", prompt).lower().strip()
        if len(normalized.split()) < 4:
            return False
        filtered_patterns = (
            r"\bmake sense\?\s*$",
            r"\bfollowing that\b",
            r"\bfollowing me\b",
            r"\bam i following that correctly\b",
            r"\bdoes that\b",
            r"\bright\?\s*$",
            r"\bcorrect\?\s*$",
            r"\bif that makes sense\b",
            r"\byou know what i mean\b",
            r"\bquestions from our previous conversation\b",
        )
        return not any(re.search(pattern, normalized) for pattern in filtered_patterns)

    normalized = normalize_round_record(record)
    review_analysis = normalized.get("review_analysis", {})
    if isinstance(review_analysis, Mapping):
        answer_assets = review_analysis.get("answer_assets", {})
        if isinstance(answer_assets, Mapping):
            stored_questions = _split_lines(answer_assets.get("interviewer_questions", []))
            filtered = [question for question in stored_questions if keep_question(question)]
            if filtered:
                return tuple(filtered[:limit])
    imported_review_text = _clean_scalar(normalized.get("imported_review_text"))
    extracted = extract_interviewer_questions(imported_review_text, limit=limit)
    if extracted:
        return extracted
    fallback = [question for question in _split_lines(normalized.get("unexpected_questions", [])) if keep_question(question)]
    return tuple(fallback[:limit])


def _serialize_performance_review(value: Mapping[str, object] | None) -> dict[str, object]:
    review = value or {}
    signals = review.get("coaching_signals", []) if isinstance(review, Mapping) else []
    cleaned_signals: list[dict[str, str]] = []
    for item in signals if isinstance(signals, Sequence) else []:
        if not isinstance(item, Mapping):
            continue
        key = _clean_scalar(item.get("key"))
        label = _clean_scalar(item.get("label"))
        detail = _clean_scalar(item.get("detail"))
        evidence = _clean_scalar(item.get("evidence"))
        if key or label or detail or evidence:
            cleaned_signals.append(
                {
                    "key": key,
                    "label": label,
                    "detail": detail,
                    "evidence": evidence,
                }
            )
    return {
        "summary": _clean_scalar(review.get("summary")) if isinstance(review, Mapping) else "",
        "strongest_answers": _split_lines(review.get("strongest_answers", [])) if isinstance(review, Mapping) else [],
        "weakest_answers": _split_lines(review.get("weakest_answers", [])) if isinstance(review, Mapping) else [],
        "next_round_risks": _split_lines(review.get("next_round_risks", [])) if isinstance(review, Mapping) else [],
        "coaching_signals": cleaned_signals,
    }


def _serialize_review_analysis(value: Mapping[str, object] | None) -> dict[str, object]:
    analysis = value or {}
    decision_signal = analysis.get("decision_signal", {}) if isinstance(analysis, Mapping) else {}
    positioning = analysis.get("positioning_diagnosis", {}) if isinstance(analysis, Mapping) else {}
    rewrites = analysis.get("language_rewrites", {}) if isinstance(analysis, Mapping) else {}
    strategy = analysis.get("answer_strategy", {}) if isinstance(analysis, Mapping) else {}
    assets = analysis.get("answer_assets", {}) if isinstance(analysis, Mapping) else {}
    career = analysis.get("career_targeting", {}) if isinstance(analysis, Mapping) else {}
    return {
        "parser_version": _clean_scalar(analysis.get("parser_version")) if isinstance(analysis, Mapping) else REVIEW_ANALYSIS_PARSER_VERSION,
        "decision_signal": {
            "headline": _clean_scalar(decision_signal.get("headline")) if isinstance(decision_signal, Mapping) else "",
            "translation": _split_lines(decision_signal.get("translation", [])) if isinstance(decision_signal, Mapping) else [],
        },
        "positioning_diagnosis": {
            "headline": _clean_scalar(positioning.get("headline")) if isinstance(positioning, Mapping) else "",
            "reasons": _split_lines(positioning.get("reasons", [])) if isinstance(positioning, Mapping) else [],
            "good_news": _split_lines(positioning.get("good_news", [])) if isinstance(positioning, Mapping) else [],
            "hard_truth": _clean_scalar(positioning.get("hard_truth")) if isinstance(positioning, Mapping) else "",
        },
        "language_rewrites": {
            "ownership_ladder": _split_lines(rewrites.get("ownership_ladder", [])) if isinstance(rewrites, Mapping) else [],
            "avoid": _split_lines(rewrites.get("avoid", [])) if isinstance(rewrites, Mapping) else [],
            "prefer": _split_lines(rewrites.get("prefer", [])) if isinstance(rewrites, Mapping) else [],
            "consultative_phrases": _split_lines(rewrites.get("consultative_phrases", [])) if isinstance(rewrites, Mapping) else [],
        },
        "answer_strategy": {
            "default_structure": _split_lines(strategy.get("default_structure", [])) if isinstance(strategy, Mapping) else [],
            "delivery_shifts": _split_lines(strategy.get("delivery_shifts", [])) if isinstance(strategy, Mapping) else [],
        },
        "answer_assets": {
            "best_takeaway_statement": _clean_scalar(assets.get("best_takeaway_statement")) if isinstance(assets, Mapping) else "",
            "interviewer_questions": _split_lines(assets.get("interviewer_questions", [])) if isinstance(assets, Mapping) else [],
            "role_language_lines": _split_lines(assets.get("role_language_lines", [])) if isinstance(assets, Mapping) else [],
            "company_signal_lines": _split_lines(assets.get("company_signal_lines", [])) if isinstance(assets, Mapping) else [],
        },
        "career_targeting": {
            "fit_read": _clean_scalar(career.get("fit_read")) if isinstance(career, Mapping) else "",
            "next_steps": _split_lines(career.get("next_steps", [])) if isinstance(career, Mapping) else [],
        },
    }


def _merge_analysis_lists(primary: object, fallback: object, limit: int = 6) -> list[str]:
    return _unique_strings([*_split_lines(primary), *_split_lines(fallback)])[:limit]


def _merge_review_analysis(supplied: Mapping[str, object] | None, generated: Mapping[str, object] | None) -> dict[str, object]:
    left = _serialize_review_analysis(supplied if isinstance(supplied, Mapping) else {})
    right = _serialize_review_analysis(generated if isinstance(generated, Mapping) else {})
    return {
        "parser_version": _first_non_empty(left.get("parser_version"), right.get("parser_version"), REVIEW_ANALYSIS_PARSER_VERSION),
        "decision_signal": {
            "headline": _first_non_empty(
                left.get("decision_signal", {}).get("headline") if isinstance(left.get("decision_signal"), Mapping) else "",
                right.get("decision_signal", {}).get("headline") if isinstance(right.get("decision_signal"), Mapping) else "",
            ),
            "translation": _merge_analysis_lists(
                left.get("decision_signal", {}).get("translation", []) if isinstance(left.get("decision_signal"), Mapping) else [],
                right.get("decision_signal", {}).get("translation", []) if isinstance(right.get("decision_signal"), Mapping) else [],
                limit=4,
            ),
        },
        "positioning_diagnosis": {
            "headline": _first_non_empty(
                left.get("positioning_diagnosis", {}).get("headline") if isinstance(left.get("positioning_diagnosis"), Mapping) else "",
                right.get("positioning_diagnosis", {}).get("headline") if isinstance(right.get("positioning_diagnosis"), Mapping) else "",
            ),
            "reasons": _merge_analysis_lists(
                left.get("positioning_diagnosis", {}).get("reasons", []) if isinstance(left.get("positioning_diagnosis"), Mapping) else [],
                right.get("positioning_diagnosis", {}).get("reasons", []) if isinstance(right.get("positioning_diagnosis"), Mapping) else [],
                limit=6,
            ),
            "good_news": _merge_analysis_lists(
                left.get("positioning_diagnosis", {}).get("good_news", []) if isinstance(left.get("positioning_diagnosis"), Mapping) else [],
                right.get("positioning_diagnosis", {}).get("good_news", []) if isinstance(right.get("positioning_diagnosis"), Mapping) else [],
                limit=4,
            ),
            "hard_truth": _first_non_empty(
                left.get("positioning_diagnosis", {}).get("hard_truth") if isinstance(left.get("positioning_diagnosis"), Mapping) else "",
                right.get("positioning_diagnosis", {}).get("hard_truth") if isinstance(right.get("positioning_diagnosis"), Mapping) else "",
            ),
        },
        "language_rewrites": {
            "ownership_ladder": _merge_analysis_lists(
                left.get("language_rewrites", {}).get("ownership_ladder", []) if isinstance(left.get("language_rewrites"), Mapping) else [],
                right.get("language_rewrites", {}).get("ownership_ladder", []) if isinstance(right.get("language_rewrites"), Mapping) else list(OWNERSHIP_VERB_LADDER),
                limit=6,
            ),
            "avoid": _merge_analysis_lists(
                left.get("language_rewrites", {}).get("avoid", []) if isinstance(left.get("language_rewrites"), Mapping) else [],
                right.get("language_rewrites", {}).get("avoid", []) if isinstance(right.get("language_rewrites"), Mapping) else list(DEFAULT_LANGUAGE_REWRITE_AVOID),
                limit=6,
            ),
            "prefer": _merge_analysis_lists(
                left.get("language_rewrites", {}).get("prefer", []) if isinstance(left.get("language_rewrites"), Mapping) else [],
                right.get("language_rewrites", {}).get("prefer", []) if isinstance(right.get("language_rewrites"), Mapping) else list(DEFAULT_LANGUAGE_REWRITE_PREFER),
                limit=6,
            ),
            "consultative_phrases": _merge_analysis_lists(
                left.get("language_rewrites", {}).get("consultative_phrases", []) if isinstance(left.get("language_rewrites"), Mapping) else [],
                right.get("language_rewrites", {}).get("consultative_phrases", []) if isinstance(right.get("language_rewrites"), Mapping) else list(DEFAULT_CONSULTATIVE_PHRASES),
                limit=6,
            ),
        },
        "answer_strategy": {
            "default_structure": _merge_analysis_lists(
                left.get("answer_strategy", {}).get("default_structure", []) if isinstance(left.get("answer_strategy"), Mapping) else [],
                right.get("answer_strategy", {}).get("default_structure", []) if isinstance(right.get("answer_strategy"), Mapping) else ["Problem", "Your role", "Action", "Result"],
                limit=4,
            ),
            "delivery_shifts": _merge_analysis_lists(
                left.get("answer_strategy", {}).get("delivery_shifts", []) if isinstance(left.get("answer_strategy"), Mapping) else [],
                right.get("answer_strategy", {}).get("delivery_shifts", []) if isinstance(right.get("answer_strategy"), Mapping) else [],
                limit=6,
            ),
        },
        "answer_assets": {
            "best_takeaway_statement": _first_non_empty(
                left.get("answer_assets", {}).get("best_takeaway_statement") if isinstance(left.get("answer_assets"), Mapping) else "",
                right.get("answer_assets", {}).get("best_takeaway_statement") if isinstance(right.get("answer_assets"), Mapping) else "",
            ),
            "interviewer_questions": _merge_analysis_lists(
                left.get("answer_assets", {}).get("interviewer_questions", []) if isinstance(left.get("answer_assets"), Mapping) else [],
                right.get("answer_assets", {}).get("interviewer_questions", []) if isinstance(right.get("answer_assets"), Mapping) else [],
                limit=8,
            ),
            "role_language_lines": _merge_analysis_lists(
                left.get("answer_assets", {}).get("role_language_lines", []) if isinstance(left.get("answer_assets"), Mapping) else [],
                right.get("answer_assets", {}).get("role_language_lines", []) if isinstance(right.get("answer_assets"), Mapping) else [],
                limit=5,
            ),
            "company_signal_lines": _merge_analysis_lists(
                left.get("answer_assets", {}).get("company_signal_lines", []) if isinstance(left.get("answer_assets"), Mapping) else [],
                right.get("answer_assets", {}).get("company_signal_lines", []) if isinstance(right.get("answer_assets"), Mapping) else [],
                limit=4,
            ),
        },
        "career_targeting": {
            "fit_read": _first_non_empty(
                left.get("career_targeting", {}).get("fit_read") if isinstance(left.get("career_targeting"), Mapping) else "",
                right.get("career_targeting", {}).get("fit_read") if isinstance(right.get("career_targeting"), Mapping) else "",
            ),
            "next_steps": _merge_analysis_lists(
                left.get("career_targeting", {}).get("next_steps", []) if isinstance(left.get("career_targeting"), Mapping) else [],
                right.get("career_targeting", {}).get("next_steps", []) if isinstance(right.get("career_targeting"), Mapping) else [],
                limit=5,
            ),
        },
    }


def _merge_signal_lists(*signal_lists: Sequence[Mapping[str, object]]) -> list[dict[str, str]]:
    merged: list[dict[str, str]] = []
    seen: set[str] = set()
    for signal_list in signal_lists:
        for item in signal_list:
            key = _clean_scalar(item.get("key")) or slug(_clean_scalar(item.get("label")))
            if not key or key in seen:
                continue
            merged.append(
                {
                    "key": key,
                    "label": _clean_scalar(item.get("label")),
                    "detail": _clean_scalar(item.get("detail")),
                    "evidence": _clean_scalar(item.get("evidence")),
                }
            )
            seen.add(key)
    return merged


def normalize_round_record(data: Mapping[str, object]) -> dict[str, object]:
    imported_artifacts = _split_lines(data.get("imported_artifacts", []))
    interview_date = _clean_scalar(data.get("interview_date"))
    interview_date_iso = _normalize_date_iso(interview_date)
    round_number = _clean_scalar(data.get("round_number"))
    company_name = _clean_scalar(data.get("company_name"))
    role_title = _clean_scalar(data.get("role_title"))
    captured_at = _clean_scalar(data.get("captured_at")) or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    outcome = _clean_scalar(data.get("outcome")).lower()
    if outcome not in {"advance", "reject", "pending"}:
        outcome = _clean_scalar(data.get("outcome"))
    raw_notes = _clean_raw_notes_text(data.get("raw_notes"))
    story_followups = _split_lines(data.get("story_followups", []))
    if raw_notes and len(story_followups) >= 3:
        raw_notes_lower = raw_notes.lower()
        overlap_count = sum(1 for line in story_followups if line.lower() in raw_notes_lower)
        if overlap_count / max(1, len(story_followups)) >= 0.6:
            story_followups = []
    imported_review_text = _clean_scalar(data.get("imported_review_text")) or _read_review_appendix(data.get("review_appendix_path"))
    generated_review = analyze_performance_review(imported_review_text) if imported_review_text else {}
    supplied_review = _serialize_performance_review(data.get("performance_review") if isinstance(data.get("performance_review"), Mapping) else {})
    performance_review = {
        "summary": _first_non_empty(supplied_review.get("summary"), generated_review.get("summary")),
        "strongest_answers": _unique_strings(
            [
                *_split_lines(supplied_review.get("strongest_answers", [])),
                *_split_lines(generated_review.get("strongest_answers", [])),
            ]
        ),
        "weakest_answers": _unique_strings(
            [
                *_split_lines(supplied_review.get("weakest_answers", [])),
                *_split_lines(generated_review.get("weakest_answers", [])),
            ]
        ),
        "next_round_risks": _unique_strings(
            [
                *_split_lines(supplied_review.get("next_round_risks", [])),
                *_split_lines(generated_review.get("next_round_risks", [])),
            ]
        ),
        "coaching_signals": _merge_signal_lists(
            supplied_review.get("coaching_signals", []),  # type: ignore[arg-type]
            generated_review.get("coaching_signals", []),  # type: ignore[arg-type]
        ),
    }
    generated_analysis = analyze_review_positioning(
        imported_review_text,
        performance_review,
        company_name=company_name,
        role_title=role_title,
        role_language=_split_lines(data.get("role_language", [])),
        company_intelligence=_split_lines(data.get("company_intelligence", [])),
    )
    review_analysis = _merge_review_analysis(
        data.get("review_analysis") if isinstance(data.get("review_analysis"), Mapping) else {},
        generated_analysis,
    )
    legacy_text = _clean_scalar(data.get("legacy_text"))
    if raw_notes or story_followups or _split_lines(data.get("role_language", [])) or _split_lines(data.get("company_intelligence", [])):
        legacy_text = ""
    return {
        "company_name": company_name,
        "role_title": role_title,
        "interview_date": _display_date(interview_date, interview_date_iso),
        "interview_date_iso": interview_date_iso,
        "round_number": round_number,
        "outcome": outcome,
        "raw_notes": raw_notes,
        "story_followups": story_followups,
        "unexpected_questions": _split_lines(data.get("unexpected_questions", [])),
        "role_language": _split_lines(data.get("role_language", [])),
        "feedback_received": _split_lines(data.get("feedback_received", [])),
        "company_intelligence": _split_lines(data.get("company_intelligence", [])),
        "performance_review": performance_review,
        "review_analysis": review_analysis,
        "imported_review_text": imported_review_text,
        "review_appendix_path": _clean_scalar(data.get("review_appendix_path")),
        "imported_artifacts": imported_artifacts,
        "legacy_text": legacy_text,
        "parser_version": _clean_scalar(data.get("parser_version")) or REVIEW_ANALYSIS_PARSER_VERSION,
        "captured_at": captured_at,
    }


def _record_key(record: Mapping[str, object]) -> tuple[str, str, str]:
    return (
        slug(_clean_scalar(record.get("company_name"))),
        _clean_scalar(record.get("interview_date_iso")),
        slug(_clean_scalar(record.get("round_number")) or "general"),
    )


def merge_round_records(base: Mapping[str, object], incoming: Mapping[str, object]) -> dict[str, object]:
    left = normalize_round_record(base)
    right = normalize_round_record(incoming)
    merged = {
        "company_name": _first_non_empty(left.get("company_name"), right.get("company_name")),
        "role_title": _prefer_richer_scalar(right.get("role_title"), left.get("role_title")),
        "interview_date": _first_non_empty(left.get("interview_date"), right.get("interview_date")),
        "interview_date_iso": _first_non_empty(left.get("interview_date_iso"), right.get("interview_date_iso")),
        "round_number": _first_non_empty(left.get("round_number"), right.get("round_number")),
        "outcome": _first_non_empty(left.get("outcome"), right.get("outcome")),
        "raw_notes": _first_non_empty(
            left.get("raw_notes") if len(_clean_scalar(left.get("raw_notes"))) >= len(_clean_scalar(right.get("raw_notes"))) else "",
            right.get("raw_notes"),
            left.get("raw_notes"),
        ),
        "story_followups": _unique_strings([*_split_lines(left.get("story_followups", [])), *_split_lines(right.get("story_followups", []))]),
        "unexpected_questions": _unique_strings([*_split_lines(left.get("unexpected_questions", [])), *_split_lines(right.get("unexpected_questions", []))]),
        "role_language": _unique_strings([*_split_lines(left.get("role_language", [])), *_split_lines(right.get("role_language", []))]),
        "feedback_received": _unique_strings([*_split_lines(left.get("feedback_received", [])), *_split_lines(right.get("feedback_received", []))]),
        "company_intelligence": _unique_strings([*_split_lines(left.get("company_intelligence", [])), *_split_lines(right.get("company_intelligence", []))]),
        "imported_review_text": _first_non_empty(
            left.get("imported_review_text") if len(_clean_scalar(left.get("imported_review_text"))) >= len(_clean_scalar(right.get("imported_review_text"))) else "",
            right.get("imported_review_text"),
            left.get("imported_review_text"),
        ),
        "review_appendix_path": _first_non_empty(right.get("review_appendix_path"), left.get("review_appendix_path")),
        "imported_artifacts": _unique_strings([*_split_lines(left.get("imported_artifacts", [])), *_split_lines(right.get("imported_artifacts", []))]),
        "legacy_text": _first_non_empty(
            left.get("legacy_text") if len(_clean_scalar(left.get("legacy_text"))) >= len(_clean_scalar(right.get("legacy_text"))) else "",
            right.get("legacy_text"),
            left.get("legacy_text"),
        ),
        "parser_version": _first_non_empty(right.get("parser_version"), left.get("parser_version"), REVIEW_ANALYSIS_PARSER_VERSION),
        "captured_at": _first_non_empty(right.get("captured_at"), left.get("captured_at")),
    }
    left_review = _serialize_performance_review(left.get("performance_review") if isinstance(left.get("performance_review"), Mapping) else {})
    right_review = _serialize_performance_review(right.get("performance_review") if isinstance(right.get("performance_review"), Mapping) else {})
    right_has_review_source = bool(_clean_scalar(right.get("imported_review_text")))
    if right_has_review_source:
        merged["performance_review"] = {
            "summary": _first_non_empty(right_review.get("summary"), left_review.get("summary")),
            "strongest_answers": _split_lines(right_review.get("strongest_answers", [])) or _split_lines(left_review.get("strongest_answers", [])),
            "weakest_answers": _split_lines(right_review.get("weakest_answers", [])) or _split_lines(left_review.get("weakest_answers", [])),
            "next_round_risks": _split_lines(right_review.get("next_round_risks", [])) or _split_lines(left_review.get("next_round_risks", [])),
            "coaching_signals": _merge_signal_lists(
                right_review.get("coaching_signals", []),  # type: ignore[arg-type]
                left_review.get("coaching_signals", []),  # type: ignore[arg-type]
            ),
        }
    else:
        merged["performance_review"] = {
            "summary": _first_non_empty(
                left_review.get("summary") if len(_clean_scalar(left_review.get("summary"))) >= len(_clean_scalar(right_review.get("summary"))) else "",
                right_review.get("summary"),
                left_review.get("summary"),
            ),
            "strongest_answers": _unique_strings([*_split_lines(left_review.get("strongest_answers", [])), *_split_lines(right_review.get("strongest_answers", []))]),
            "weakest_answers": _unique_strings([*_split_lines(left_review.get("weakest_answers", [])), *_split_lines(right_review.get("weakest_answers", []))]),
            "next_round_risks": _unique_strings([*_split_lines(left_review.get("next_round_risks", [])), *_split_lines(right_review.get("next_round_risks", []))]),
            "coaching_signals": _merge_signal_lists(
                left_review.get("coaching_signals", []),  # type: ignore[arg-type]
                right_review.get("coaching_signals", []),  # type: ignore[arg-type]
            ),
        }
    merged["review_analysis"] = _merge_review_analysis(
        left.get("review_analysis") if isinstance(left.get("review_analysis"), Mapping) else {},
        right.get("review_analysis") if isinstance(right.get("review_analysis"), Mapping) else {},
    )
    return normalize_round_record(merged)


def save_round_record(jobs_dir: Path, record: Mapping[str, object]) -> Path:
    normalized = normalize_round_record(record)
    path = structured_debrief_path(
        jobs_dir,
        _clean_scalar(normalized.get("company_name")),
        _clean_scalar(normalized.get("interview_date")),
        _clean_scalar(normalized.get("round_number")),
        _clean_scalar(normalized.get("role_title")),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    stored = dict(normalized)
    review_text = _clean_scalar(normalized.get("imported_review_text"))
    if review_text:
        appendix = review_appendix_path(
            jobs_dir,
            _clean_scalar(normalized.get("company_name")),
            _clean_scalar(normalized.get("interview_date")),
            _clean_scalar(normalized.get("round_number")),
            _clean_scalar(normalized.get("role_title")),
        )
        appendix.parent.mkdir(parents=True, exist_ok=True)
        appendix.write_text(review_text.rstrip() + "\n", encoding="utf-8")
        stored["review_appendix_path"] = str(appendix)
    stored["imported_review_text"] = ""
    stored["legacy_text"] = ""
    stored["parser_version"] = REVIEW_ANALYSIS_PARSER_VERSION
    path.write_text(json.dumps(stored, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _record_sort_key(record: Mapping[str, object]) -> tuple[str, str]:
    return (
        _clean_scalar(record.get("interview_date_iso")) or "0000-00-00",
        _clean_scalar(record.get("captured_at")) or "0000-00-00 00:00:00",
    )


def _role_titles_match(record_role: str, requested_role: str) -> bool:
    left = _clean_scalar(record_role).lower()
    right = _clean_scalar(requested_role).lower()
    if not right:
        return True
    if left == right:
        return True
    return bool(left and right and (left in right or right in left))


def _all_structured_record_paths(jobs_dir: Path) -> list[Path]:
    directory = structured_debriefs_dir(jobs_dir)
    if not directory.is_dir():
        return []
    return sorted(directory.glob("*/*.json"))


def load_round_records(jobs_dir: Path, company_name: str = "", role_title: str = "") -> list[dict[str, object]]:
    merged_records: dict[tuple[str, str, str], dict[str, object]] = {}
    for path in _all_structured_record_paths(jobs_dir):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, Mapping):
            continue
        record = normalize_round_record(payload)
        key = _record_key(record)
        merged_records[key] = merge_round_records(merged_records[key], record) if key in merged_records else record
    records: list[dict[str, object]] = []
    for record in merged_records.values():
        if company_name and not companies_refer_to_same(_clean_scalar(record.get("company_name")), company_name):
            continue
        if role_title and not _role_titles_match(_clean_scalar(record.get("role_title")), role_title):
            continue
        records.append(record)
    return sorted(records, key=_record_sort_key, reverse=True)


def latest_round_record(jobs_dir: Path, company_name: str, role_title: str = "") -> dict[str, object] | None:
    records = load_round_records(jobs_dir, company_name, role_title)
    return records[0] if records else None


def recent_interviewer_questions(
    jobs_dir: Path,
    company_name: str = "",
    role_title: str = "",
    limit: int = 10,
) -> tuple[str, ...]:
    scoped_records = load_round_records(jobs_dir, company_name, role_title) if company_name else load_round_records(jobs_dir)
    for record in scoped_records:
        questions = interviewer_questions_from_record(record, limit=limit)
        if questions:
            return questions
    if company_name or role_title:
        for record in load_round_records(jobs_dir):
            questions = interviewer_questions_from_record(record, limit=limit)
            if questions:
                return questions
    return ()


def review_analysis_from_record(record: Mapping[str, object]) -> dict[str, object]:
    normalized = normalize_round_record(record)
    return _serialize_review_analysis(normalized.get("review_analysis") if isinstance(normalized.get("review_analysis"), Mapping) else {})


def latest_review_analysis(records: Sequence[Mapping[str, object]]) -> dict[str, object]:
    if not records:
        return _serialize_review_analysis({})
    return review_analysis_from_record(records[0])


def has_usable_coaching_signals(records: Sequence[Mapping[str, object]]) -> bool:
    for record in records:
        review = _serialize_performance_review(record.get("performance_review") if isinstance(record.get("performance_review"), Mapping) else {})
        if review.get("coaching_signals"):
            return True
    return False


def compact_round_record(record: Mapping[str, object]) -> dict[str, object]:
    normalized = normalize_round_record(record)
    compact = dict(normalized)
    compact["raw_notes"] = ""
    compact["imported_review_text"] = ""
    compact["legacy_text"] = ""
    compact["role_language"] = _split_lines(compact.get("role_language", []))[:5]
    compact["company_intelligence"] = _split_lines(compact.get("company_intelligence", []))[:4]
    compact["unexpected_questions"] = _split_lines(compact.get("unexpected_questions", []))[:6]
    return compact


def global_coaching_fallback_records(jobs_dir: Path, company_name: str = "", role_title: str = "") -> tuple[dict[str, object], ...]:
    scoped_records = tuple(load_round_records(jobs_dir, company_name, role_title))
    if has_usable_coaching_signals(scoped_records):
        return ()
    return tuple(compact_round_record(record) for record in load_round_records(jobs_dir))


def _format_section_lines(lines: Sequence[str]) -> str:
    items = _split_lines(lines)
    if not items:
        return "None supplied."
    if len(items) == 1:
        return items[0]
    return "\n".join(f"  - {item}" for item in items)


def record_to_debrief_entry(record: Mapping[str, object]) -> str:
    normalized = normalize_round_record(record)
    review = _serialize_performance_review(normalized.get("performance_review") if isinstance(normalized.get("performance_review"), Mapping) else {})
    review_analysis = _serialize_review_analysis(normalized.get("review_analysis") if isinstance(normalized.get("review_analysis"), Mapping) else {})
    sections = [
        f"{DEBRIEF_DELIMITER} {_clean_scalar(normalized.get('captured_at'))}",
        "",
        f"Interview date: {_clean_scalar(normalized.get('interview_date'))}",
        f"Company name: {_clean_scalar(normalized.get('company_name'))}",
        f"Role title: {_clean_scalar(normalized.get('role_title')) or 'None supplied.'}",
        f"Round number: {_clean_scalar(normalized.get('round_number')) or 'None supplied.'}",
        f"Outcome: {_clean_scalar(normalized.get('outcome'))}",
        "",
        "Raw notes:",
        _clean_scalar(normalized.get("raw_notes")) or "None supplied.",
        "",
        "Stories that generated follow-up questions:",
        _format_section_lines(normalized.get("story_followups", [])),
        "",
        "Unexpected questions:",
        _format_section_lines(normalized.get("unexpected_questions", [])),
        "",
        "Specific interviewer language about the role:",
        _format_section_lines(normalized.get("role_language", [])),
        "",
        "Feedback received:",
        _format_section_lines(normalized.get("feedback_received", [])),
        "",
        "Insider company intelligence learned:",
        _format_section_lines(normalized.get("company_intelligence", [])),
        "",
        "Performance summary:",
        _clean_scalar(review.get("summary")) or "None supplied.",
        "",
        "Strongest answers:",
        _format_section_lines(review.get("strongest_answers", [])),
        "",
        "Weakest answers:",
        _format_section_lines(review.get("weakest_answers", [])),
        "",
        "Next-round risks:",
        _format_section_lines(review.get("next_round_risks", [])),
        "",
        "Coaching signals:",
        _format_section_lines(
            [
                f"{_clean_scalar(item.get('label'))}: {_clean_scalar(item.get('detail'))}".strip(": ")
                for item in review.get("coaching_signals", [])  # type: ignore[union-attr]
                if isinstance(item, Mapping)
            ]
        ),
        "",
        "Decision signal:",
        _clean_scalar(review_analysis.get("decision_signal", {}).get("headline") if isinstance(review_analysis.get("decision_signal"), Mapping) else "") or "None supplied.",
        "",
        "Positioning diagnosis:",
        _format_section_lines(
            review_analysis.get("positioning_diagnosis", {}).get("reasons", [])
            if isinstance(review_analysis.get("positioning_diagnosis"), Mapping)
            else []
        ),
        "",
        "Language rewrites:",
        _format_section_lines(
            review_analysis.get("language_rewrites", {}).get("prefer", [])
            if isinstance(review_analysis.get("language_rewrites"), Mapping)
            else []
        ),
        "",
        "Answer strategy:",
        _format_section_lines(
            review_analysis.get("answer_strategy", {}).get("delivery_shifts", [])
            if isinstance(review_analysis.get("answer_strategy"), Mapping)
            else []
        ),
        "",
        "Answer assets:",
        _format_section_lines(
            review_analysis.get("answer_assets", {}).get("interviewer_questions", [])
            if isinstance(review_analysis.get("answer_assets"), Mapping)
            else []
        ),
        "",
        "Career targeting:",
        _format_section_lines(
            review_analysis.get("career_targeting", {}).get("next_steps", [])
            if isinstance(review_analysis.get("career_targeting"), Mapping)
            else []
        ),
    ]
    imported_artifacts = _split_lines(normalized.get("imported_artifacts", []))
    if imported_artifacts:
        sections.extend(
            [
                "",
                "Imported review artifacts:",
                _format_section_lines(imported_artifacts),
            ]
        )
    review_appendix = _clean_scalar(normalized.get("review_appendix_path"))
    if review_appendix:
        sections.extend(
            [
                "",
                "Imported review appendix:",
                review_appendix,
            ]
        )
    return "\n".join(sections).rstrip()


def record_to_company_research_note(record: Mapping[str, object]) -> str:
    normalized = normalize_round_record(record)
    round_text = f", round {_clean_scalar(normalized.get('round_number'))}" if _clean_scalar(normalized.get("round_number")) else ""
    lines = [
        f"POST-INTERVIEW NOTE [{_clean_scalar(normalized.get('interview_date'))}]: {_clean_scalar(normalized.get('company_name'))} - {_clean_scalar(normalized.get('role_title'))}{round_text}, outcome {_clean_scalar(normalized.get('outcome'))}.",
    ]
    intelligence_lines = _split_lines(normalized.get("company_intelligence", []))
    role_language = _split_lines(normalized.get("role_language", []))
    if intelligence_lines:
        lines.extend(f"- {line}" for line in intelligence_lines)
    if role_language:
        lines.append("- Role language:")
        lines.extend(f"  - {line}" for line in role_language[:5])
    return "\n".join(lines).rstrip()


def rebuild_legacy_exports(jobs_dir: Path) -> tuple[Path, Path]:
    records = sorted(load_round_records(jobs_dir), key=_record_sort_key)
    debrief_history = jobs_dir / "debrief_history.txt"
    company_research = jobs_dir / "company_research.txt"
    debrief_history.write_text(
        "\n\n".join(record_to_debrief_entry(record) for record in records).rstrip() + ("\n" if records else ""),
        encoding="utf-8",
    )
    company_notes = [record_to_company_research_note(record) for record in records if _split_lines(record.get("company_intelligence", [])) or _split_lines(record.get("role_language", []))]
    company_research.write_text(
        "\n\n".join(company_notes).rstrip() + ("\n" if company_notes else ""),
        encoding="utf-8",
    )
    return debrief_history, company_research


def _dossier_section(title: str, body: str) -> str:
    cleaned = body.strip()
    return f"### {title}\n{cleaned if cleaned else 'None supplied.'}"


def _record_to_dossier_markdown(record: Mapping[str, object]) -> str:
    normalized = normalize_round_record(record)
    review = _serialize_performance_review(normalized.get("performance_review") if isinstance(normalized.get("performance_review"), Mapping) else {})
    review_analysis = _serialize_review_analysis(normalized.get("review_analysis") if isinstance(normalized.get("review_analysis"), Mapping) else {})
    round_label = _clean_scalar(normalized.get("round_number")) or "general"
    header = (
        f"## {_clean_scalar(normalized.get('interview_date_iso')) or _clean_scalar(normalized.get('interview_date'))} | "
        f"Round {round_label} | {_clean_scalar(normalized.get('role_title')) or 'Unspecified role'} | "
        f"Outcome: {_clean_scalar(normalized.get('outcome')) or 'unknown'}"
    )
    sections = [
        header,
        _dossier_section("Specific Interviewer Language About The Role", "\n".join(f"- {line}" for line in _split_lines(normalized.get("role_language", [])))),
        _dossier_section("Decision Signal", _clean_scalar(review_analysis.get("decision_signal", {}).get("headline") if isinstance(review_analysis.get("decision_signal"), Mapping) else "")),
        _dossier_section(
            "Positioning Diagnosis",
            "\n".join(f"- {line}" for line in _split_lines(review_analysis.get("positioning_diagnosis", {}).get("reasons", []) if isinstance(review_analysis.get("positioning_diagnosis"), Mapping) else [])),
        ),
        _dossier_section(
            "Language Rewrites",
            "\n".join(f"- {line}" for line in _split_lines(review_analysis.get("language_rewrites", {}).get("prefer", []) if isinstance(review_analysis.get("language_rewrites"), Mapping) else [])),
        ),
        _dossier_section(
            "Answer Strategy",
            "\n".join(f"- {line}" for line in _split_lines(review_analysis.get("answer_strategy", {}).get("delivery_shifts", []) if isinstance(review_analysis.get("answer_strategy"), Mapping) else [])),
        ),
        _dossier_section(
            "Answer Assets",
            "\n".join(
                f"- {line}"
                for line in (
                    _split_lines(review_analysis.get("answer_assets", {}).get("interviewer_questions", []) if isinstance(review_analysis.get("answer_assets"), Mapping) else [])
                    + _split_lines(review_analysis.get("answer_assets", {}).get("role_language_lines", []) if isinstance(review_analysis.get("answer_assets"), Mapping) else [])
                )[:8]
            ),
        ),
        _dossier_section("Career Targeting", _clean_scalar(review_analysis.get("career_targeting", {}).get("fit_read") if isinstance(review_analysis.get("career_targeting"), Mapping) else "")),
        _dossier_section("Performance Summary", _clean_scalar(review.get("summary"))),
        _dossier_section(
            "Coaching Signals",
            "\n".join(
                f"- {_clean_scalar(item.get('label'))}: {_clean_scalar(item.get('detail'))}"
                for item in review.get("coaching_signals", [])  # type: ignore[union-attr]
                if isinstance(item, Mapping)
            ),
        ),
        _dossier_section("Next-Round Risks", "\n".join(f"- {line}" for line in _split_lines(review.get("next_round_risks", [])))),
        _dossier_section("Strongest Answers", "\n".join(f"- {line}" for line in _split_lines(review.get("strongest_answers", [])))),
        _dossier_section("Weakest Answers", "\n".join(f"- {line}" for line in _split_lines(review.get("weakest_answers", [])))),
        _dossier_section("Company Intelligence", "\n".join(f"- {line}" for line in _split_lines(normalized.get("company_intelligence", [])))),
        _dossier_section("Feedback Received", "\n".join(f"- {line}" for line in _split_lines(normalized.get("feedback_received", [])))),
        _dossier_section("Stories That Generated Follow-Up Questions", "\n".join(f"- {line}" for line in _split_lines(normalized.get("story_followups", [])))),
        _dossier_section("Unexpected Questions", "\n".join(f"- {line}" for line in _split_lines(normalized.get("unexpected_questions", [])))),
        _dossier_section("Raw Notes", _clean_scalar(normalized.get("raw_notes"))),
    ]
    imported_artifacts = _split_lines(normalized.get("imported_artifacts", []))
    if imported_artifacts:
        sections.append(_dossier_section("Imported Review Artifacts", "\n".join(f"- {line}" for line in imported_artifacts)))
    review_appendix = _clean_scalar(normalized.get("review_appendix_path"))
    if review_appendix:
        sections.append(_dossier_section("Imported Performance Review Appendix", review_appendix))
    return "\n\n".join(section for section in sections if section.strip())


def rebuild_company_dossiers(jobs_dir: Path) -> list[Path]:
    by_company: dict[str, list[dict[str, object]]] = {}
    for record in load_round_records(jobs_dir):
        company = _clean_scalar(record.get("company_name"))
        if not company:
            continue
        by_company.setdefault(company, []).append(record)
    written: list[Path] = []
    company_notes_directory = company_notes_dir(jobs_dir)
    company_notes_directory.mkdir(parents=True, exist_ok=True)
    for company, records in by_company.items():
        path = company_dossier_path(jobs_dir, company)
        ordered = sorted(records, key=_record_sort_key)
        body = [
            f"# Company Interview Dossier: {company}",
            "",
            "This dossier is the human-readable company notebook. Structured round records in jobs/interview_debriefs remain the source of truth for automation.",
            "",
            *[
                _record_to_dossier_markdown(record)
                for record in ordered
            ],
            "",
        ]
        path.write_text("\n".join(body).rstrip() + "\n", encoding="utf-8")
        written.append(path)
    return written


def prepare_company_dossier(jobs_dir: Path, company_name: str, role_title: str, round_number: str = "") -> Path:
    dossier_path = company_dossier_path(jobs_dir, company_name)
    dossier_path.parent.mkdir(parents=True, exist_ok=True)
    round_label = round_number.strip() or "general"
    scaffold = "\n".join(
        [
            f"## [Interview date] | Round {round_label} | {role_title or 'Role title'} | Outcome: pending",
            "",
            "### Specific Interviewer Language About The Role",
            "- ",
            "",
            "### Decision Signal",
            "",
            "### Positioning Diagnosis",
            "- ",
            "",
            "### Language Rewrites",
            "- ",
            "",
            "### Answer Strategy",
            "- ",
            "",
            "### Answer Assets",
            "- ",
            "",
            "### Career Targeting",
            "- ",
            "",
            "### Performance Summary",
            "",
            "### Feedback Received",
            "- ",
            "",
            "### Company Intelligence",
            "- ",
            "",
            "### Coaching Signals",
            "- ",
            "",
            "### Next-Round Risks",
            "- ",
            "",
            "### Stories That Generated Follow-Up Questions",
            "- ",
            "",
            "### Unexpected Questions",
            "- ",
            "",
            "### Raw Notes",
            "",
            "### Imported Performance Review Appendix",
            "",
        ]
    )
    existing = read_text(dossier_path) if dossier_path.exists() else ""
    if existing.strip():
        round_marker = f"round {round_label}".lower()
        role_marker = (role_title or "").strip().lower()
        if round_marker in existing.lower() and (not role_marker or role_marker in existing.lower()):
            return dossier_path
        updated = existing.rstrip() + "\n\n" + scaffold.rstrip() + "\n"
        dossier_path.write_text(updated, encoding="utf-8")
        return dossier_path
    scaffold = "\n".join(
        [
            f"# Company Interview Dossier: {company_name}",
            "",
            "Use one running document per company. Add one section per interview round or major interaction.",
            "",
            scaffold,
        ]
    )
    dossier_path.write_text(scaffold.rstrip() + "\n", encoding="utf-8")
    return dossier_path


def _structured_company_research_text(records: Sequence[Mapping[str, object]]) -> str:
    if not records:
        return ""
    notes = [record_to_company_research_note(record) for record in sorted(records, key=_record_sort_key)]
    return "\n\n".join(note for note in notes if note.strip()).strip()


def _structured_interview_notes_text(records: Sequence[Mapping[str, object]], limit: int = 3) -> str:
    blocks: list[str] = []
    for record in list(records)[:limit]:
        review = _serialize_performance_review(record.get("performance_review") if isinstance(record.get("performance_review"), Mapping) else {})
        lines = [
            f"INTERVIEW ROUND: {_clean_scalar(record.get('interview_date'))} | Role: {_clean_scalar(record.get('role_title')) or 'Unknown role'} | Round: {_clean_scalar(record.get('round_number')) or 'general'} | Outcome: {_clean_scalar(record.get('outcome')) or 'unknown'}",
        ]
        if _split_lines(record.get("story_followups", [])):
            lines.append("Stories that generated follow-up questions: " + "; ".join(_split_lines(record.get("story_followups", []))[:4]))
        if _split_lines(record.get("unexpected_questions", [])):
            lines.append("Unexpected questions: " + "; ".join(_split_lines(record.get("unexpected_questions", []))[:4]))
        if _split_lines(record.get("role_language", [])):
            lines.append("Role language: " + "; ".join(_split_lines(record.get("role_language", []))[:5]))
        if _split_lines(record.get("feedback_received", [])):
            lines.append("Feedback received: " + "; ".join(_split_lines(record.get("feedback_received", []))[:4]))
        if _clean_scalar(review.get("summary")):
            lines.append("Performance summary: " + _clean_scalar(review.get("summary")))
        if review.get("coaching_signals"):
            lines.append(
                "Coaching signals: "
                + "; ".join(
                    _clean_scalar(item.get("label")) or _clean_scalar(item.get("detail"))
                    for item in review.get("coaching_signals", [])  # type: ignore[union-attr]
                    if isinstance(item, Mapping)
                )
            )
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks).strip()


def _structured_coaching_notes_text(records: Sequence[Mapping[str, object]], limit: int = 6) -> str:
    signal_counts: dict[str, tuple[str, str, int]] = {}
    next_round_risks: list[str] = []
    latest_summary = ""
    for record in records:
        review = _serialize_performance_review(record.get("performance_review") if isinstance(record.get("performance_review"), Mapping) else {})
        if not latest_summary and _clean_scalar(review.get("summary")):
            latest_summary = _clean_scalar(review.get("summary"))
        for risk in _split_lines(review.get("next_round_risks", [])):
            if len(next_round_risks) < limit:
                next_round_risks.append(risk)
        for item in review.get("coaching_signals", []):  # type: ignore[union-attr]
            if not isinstance(item, Mapping):
                continue
            key = _clean_scalar(item.get("key")) or slug(_clean_scalar(item.get("label")))
            label = _clean_scalar(item.get("label"))
            detail = _clean_scalar(item.get("detail"))
            count = signal_counts.get(key, (label, detail, 0))[2] + 1
            signal_counts[key] = (label, detail, count)
    lines: list[str] = []
    if latest_summary:
        lines.append("Latest performance read: " + latest_summary)
    ranked = sorted(signal_counts.values(), key=lambda item: (-item[2], item[0].lower()))
    if ranked:
        lines.append("Recurring coaching themes:")
        for label, detail, count in ranked[:limit]:
            lines.append(f"- {label} ({count}): {detail}")
    if next_round_risks:
        lines.append("Next-round risks to drill:")
        for risk in _unique_strings(next_round_risks)[:limit]:
            lines.append(f"- {risk}")
    return "\n".join(lines).strip()


def _compact_company_research_text(records: Sequence[Mapping[str, object]]) -> str:
    if not records:
        return ""
    latest = normalize_round_record(records[0])
    fact_lines = _split_lines(latest.get("raw_notes", []))[:5]
    intel_lines = _split_lines(latest.get("company_intelligence", []))[:3]
    lines: list[str] = []
    if fact_lines:
        lines.append("Latest company facts: " + "; ".join(fact_lines))
    if intel_lines:
        lines.append("Latest company intelligence: " + "; ".join(intel_lines))
    return "\n".join(lines).strip()


def _compact_interview_notes_text(records: Sequence[Mapping[str, object]]) -> str:
    if not records:
        return ""
    latest = normalize_round_record(records[0])
    review_analysis = review_analysis_from_record(latest)
    answer_assets = review_analysis.get("answer_assets", {})
    role_lines = _split_lines(answer_assets.get("role_language_lines", []) if isinstance(answer_assets, Mapping) else [])[:4]
    question_lines = _split_lines(answer_assets.get("interviewer_questions", []) if isinstance(answer_assets, Mapping) else [])[:4]
    lines = [
        f"Latest round: {_clean_scalar(latest.get('interview_date'))} | Role: {_clean_scalar(latest.get('role_title')) or 'Unknown role'} | Round: {_clean_scalar(latest.get('round_number')) or 'general'} | Outcome: {_clean_scalar(latest.get('outcome')) or 'unknown'}",
    ]
    decision_headline = _clean_scalar(review_analysis.get("decision_signal", {}).get("headline") if isinstance(review_analysis.get("decision_signal"), Mapping) else "")
    if decision_headline:
        lines.append("Latest positioning read: " + decision_headline)
    if role_lines:
        lines.append("Top role language: " + "; ".join(role_lines))
    if question_lines:
        lines.append("Top interviewer questions: " + "; ".join(question_lines))
    return "\n".join(lines).strip()


def _compact_coaching_notes_text(records: Sequence[Mapping[str, object]]) -> str:
    if not records:
        return ""
    latest = normalize_round_record(records[0])
    review = _serialize_performance_review(latest.get("performance_review") if isinstance(latest.get("performance_review"), Mapping) else {})
    review_analysis = review_analysis_from_record(latest)
    signals = [
        _clean_scalar(item.get("label")) or _clean_scalar(item.get("detail"))
        for item in review.get("coaching_signals", [])  # type: ignore[union-attr]
        if isinstance(item, Mapping)
    ][:4]
    risks = _split_lines(review.get("next_round_risks", []))[:4]
    delivery_shifts = _split_lines(
        review_analysis.get("answer_strategy", {}).get("delivery_shifts", [])
        if isinstance(review_analysis.get("answer_strategy"), Mapping)
        else []
    )[:4]
    lines: list[str] = []
    if signals:
        lines.append("Top coaching signals: " + "; ".join(signals))
    if risks:
        lines.append("Top next-round risks: " + "; ".join(risks))
    if delivery_shifts:
        lines.append("Answer-strategy shifts: " + "; ".join(delivery_shifts))
    return "\n".join(lines).strip()


def company_research_context(jobs_dir: Path, company_name: str, role_title: str = "", company_research_path: Path | None = None) -> str:
    records = load_round_records(jobs_dir, company_name, role_title)
    structured = _structured_company_research_text(records)
    if structured:
        return structured
    if company_research_path and company_research_path.exists():
        return relevant_company_context(read_text(company_research_path), company_name)
    return ""


def load_company_context(
    jobs_dir: Path,
    company_name: str,
    role_title: str = "",
    *,
    company_research_path: Path | None = None,
    global_interview_notes_path: Path | None = None,
    mode: str = "compact",
) -> CompanyContextBundle:
    records = tuple(load_round_records(jobs_dir, company_name, role_title))
    if mode == "full":
        company_research = _structured_company_research_text(records)
        interview_notes = _structured_interview_notes_text(records)
        coaching_notes = _structured_coaching_notes_text(records)
        if not company_research and company_research_path and company_research_path.exists():
            company_research = relevant_company_context(read_text(company_research_path), company_name)
        global_notes = ""
        if global_interview_notes_path and global_interview_notes_path.exists():
            global_notes = relevant_company_context(read_text(global_interview_notes_path), company_name)
        parts = [part for part in (company_research, interview_notes, coaching_notes, global_notes) if part.strip()]
    else:
        company_research = _compact_company_research_text(records)
        interview_notes = _compact_interview_notes_text(records)
        coaching_notes = _compact_coaching_notes_text(records)
        if not company_research and company_research_path and company_research_path.exists():
            company_research = _truncate_words(relevant_company_context(read_text(company_research_path), company_name), 180)
        parts = [part for part in (company_research, interview_notes, coaching_notes) if part.strip()]
        supplied_word_count = sum(_word_count(part) for part in parts)
        if supplied_word_count > COMPACT_SUPPLIED_CONTEXT_MAX_WORDS:
            overflow = supplied_word_count - COMPACT_SUPPLIED_CONTEXT_MAX_WORDS
            interview_budget = max(80, _word_count(interview_notes) - overflow)
            interview_notes = _truncate_words(interview_notes, interview_budget)
            parts = [part for part in (company_research, interview_notes, coaching_notes) if part.strip()]
    return CompanyContextBundle(
        company_research=company_research,
        interview_notes=interview_notes,
        coaching_notes=coaching_notes,
        supplied_context="\n\n".join(parts),
        round_records=records,
        mode=mode,
    )


def read_scoped_interview_notes(jobs_dir: Path, company_name: str, role_title: str = "") -> str:
    records = load_round_records(jobs_dir, company_name, role_title)
    structured = _structured_interview_notes_text(records)
    if structured:
        return structured
    parts: list[str] = []
    for path in matching_scoped_note_paths(jobs_dir, company_name, role_title):
        text = relevant_company_context(read_text(path), company_name)
        if text:
            parts.append(f"INTERVIEW NOTES FILE: {path.name}\n{text}")
    return "\n\n".join(parts)


def read_global_interview_notes_if_relevant(path: Path, company_name: str) -> str:
    if not path.exists():
        return ""
    text = clean_source_text(read_text(path))
    if not text:
        return ""
    return relevant_company_context(text, company_name)


def latest_debrief_entry(jobs_dir: Path, company_name: str, role_title: str = "") -> str:
    record = latest_round_record(jobs_dir, company_name, role_title)
    if not record:
        return ""
    return record_to_debrief_entry(record)


def debrief_entries_for_company(jobs_dir: Path, company_name: str = "") -> list[str]:
    return [record_to_debrief_entry(record) for record in load_round_records(jobs_dir, company_name)]


def clean_legacy_scoped_note_text(text: str) -> str:
    cleaned = clean_source_text(text)
    matches = list(re.finditer(r"(?im)^Company:\s+", cleaned))
    if len(matches) > 1:
        cleaned = cleaned[: matches[1].start()].rstrip()
    return cleaned.strip()


def _legacy_section_value(entry: str, label: str) -> str:
    match = re.search(rf"(?ims)^{re.escape(label)}:\s*(.*?)(?=\n[A-Z][A-Za-z ]+:\s|\Z)", entry)
    return clean_source_text(match.group(1)).strip() if match else ""


def _legacy_field_value(entry: str, label: str) -> str:
    match = re.search(rf"(?im)^\s*{re.escape(label)}:\s*(.*?)\s*$", entry)
    return clean_source_text(match.group(1)).strip() if match else ""


def _extract_raw_notes_from_legacy_scoped_text(text: str) -> str:
    cleaned = clean_legacy_scoped_note_text(text)
    marker = "Paste raw interview notes below this line."
    if marker in cleaned:
        raw = cleaned.split(marker, 1)[1]
        raw_lines = [
            line
            for line in raw.splitlines()
            if line.strip()
            and not line.strip().lower().startswith("keep notes factual.")
            and not line.strip().lower().startswith("include interviewer language")
        ]
        return "\n".join(raw_lines).strip()
    raw_match = re.search(r"(?ims)^Raw notes:\s*(.*)$", cleaned)
    if raw_match:
        return clean_source_text(raw_match.group(1)).strip()
    return cleaned


def _legacy_raw_note_artifact_text(record: Mapping[str, object]) -> str:
    normalized = normalize_round_record(record)
    return "\n".join(
        [
            f"Company: {_clean_scalar(normalized.get('company_name'))}",
            f"Role: {_clean_scalar(normalized.get('role_title'))}",
            f"Round: {_clean_scalar(normalized.get('round_number')) or 'general'}",
            f"Interview date: {_clean_scalar(normalized.get('interview_date'))}",
            f"Outcome: {_clean_scalar(normalized.get('outcome'))}",
            "",
            "Raw notes:",
            _clean_scalar(normalized.get("raw_notes")) or "None supplied.",
            "",
        ]
    ).rstrip() + "\n"


def rewrite_legacy_scoped_notes(jobs_dir: Path, records: Sequence[Mapping[str, object]]) -> list[Path]:
    directory = scoped_notes_dir(jobs_dir)
    directory.mkdir(parents=True, exist_ok=True)
    for path in sorted(directory.glob("*.txt")):
        path.unlink()
    written: list[Path] = []
    for record in records:
        normalized = normalize_round_record(record)
        company_name = _clean_scalar(normalized.get("company_name"))
        role_title = _clean_scalar(normalized.get("role_title"))
        interview_date = _clean_scalar(normalized.get("interview_date"))
        if not company_name or not interview_date:
            continue
        path = scoped_note_path(
            jobs_dir,
            company_name,
            role_title or "general",
            _clean_scalar(normalized.get("round_number")),
        )
        path.write_text(_legacy_raw_note_artifact_text(normalized), encoding="utf-8")
        written.append(path)
    return written


def _parse_legacy_debrief_entries(text: str, jobs_dir: Path) -> list[dict[str, object]]:
    entries = [f"{DEBRIEF_DELIMITER}{item}".strip() for item in text.split(DEBRIEF_DELIMITER) if item.strip()]
    parsed: list[dict[str, object]] = []
    for entry in entries:
        company = _legacy_field_value(entry, "Company name")
        role = _legacy_field_value(entry, "Role title")
        interview_date = _legacy_field_value(entry, "Interview date")
        round_number = _legacy_field_value(entry, "Round number")
        raw_notes = _legacy_section_value(entry, "Raw notes") or _legacy_section_value(entry, "Bulk interview notes captured from note file")
        legacy_note_path = scoped_note_path(jobs_dir, company, role, round_number)
        if legacy_note_path.exists():
            raw_notes = _extract_raw_notes_from_legacy_scoped_text(read_text(legacy_note_path))
        parsed.append(
            normalize_round_record(
                {
                    "company_name": company,
                    "role_title": role,
                    "interview_date": interview_date,
                    "round_number": round_number,
                    "outcome": _legacy_field_value(entry, "Outcome"),
                    "raw_notes": raw_notes,
                    "story_followups": _legacy_section_value(entry, "Stories that generated follow-up questions"),
                    "unexpected_questions": _legacy_section_value(entry, "Unexpected questions"),
                    "role_language": _legacy_section_value(entry, "Specific interviewer language about the role"),
                    "feedback_received": _legacy_section_value(entry, "Feedback received"),
                    "company_intelligence": _legacy_section_value(entry, "Insider company intelligence learned"),
                    "performance_review": {
                        "summary": _legacy_section_value(entry, "Performance summary"),
                        "strongest_answers": _legacy_section_value(entry, "Strongest answers"),
                        "weakest_answers": _legacy_section_value(entry, "Weakest answers"),
                        "next_round_risks": _legacy_section_value(entry, "Next-round risks"),
                        "coaching_signals": [],
                    },
                    "legacy_text": entry,
                    "captured_at": re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", entry).group(1) if re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", entry) else "",
                }
            )
        )
    return parsed


def _parse_legacy_scoped_note_files(jobs_dir: Path) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    directory = scoped_notes_dir(jobs_dir)
    if not directory.is_dir():
        return results
    for path in sorted(directory.glob("*.txt")):
        cleaned = clean_legacy_scoped_note_text(read_text(path))
        company = _legacy_field_value(cleaned, "Company")
        role = _legacy_field_value(cleaned, "Role")
        round_number = _legacy_field_value(cleaned, "Round")
        interview_date = _legacy_field_value(cleaned, "Interview date")
        if not company or not interview_date:
            continue
        results.append(
            normalize_round_record(
                {
                    "company_name": company,
                    "role_title": role,
                    "interview_date": interview_date,
                    "round_number": round_number if round_number.lower() != "general" else "",
                    "outcome": _legacy_field_value(cleaned, "Outcome"),
                    "raw_notes": _extract_raw_notes_from_legacy_scoped_text(cleaned),
                    "story_followups": "",
                    "unexpected_questions": "",
                    "role_language": "",
                    "feedback_received": "",
                    "company_intelligence": "",
                    "legacy_text": cleaned,
                }
            )
        )
    return results


def repair_legacy_interview_data(jobs_dir: Path) -> dict[str, object]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = legacy_backup_dir(jobs_dir) / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for relative in ("debrief_history.txt", "company_research.txt", SCOPED_NOTES_DIR_NAME):
        source = jobs_dir / relative
        if not source.exists():
            continue
        destination = backup_dir / relative
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        copied.append(str(source))

    merged: dict[tuple[str, str, str], dict[str, object]] = {}
    for record in load_round_records(jobs_dir):
        merged[_record_key(record)] = normalize_round_record(record)

    debrief_history_path = jobs_dir / "debrief_history.txt"
    if debrief_history_path.exists():
        for record in _parse_legacy_debrief_entries(read_text(debrief_history_path), jobs_dir):
            key = _record_key(record)
            merged[key] = merge_round_records(merged[key], record) if key in merged else record

    for record in _parse_legacy_scoped_note_files(jobs_dir):
        key = _record_key(record)
        merged[key] = merge_round_records(merged[key], record) if key in merged else record

    for path in _all_structured_record_paths(jobs_dir):
        path.unlink()

    written_paths: list[Path] = []
    for record in merged.values():
        written_paths.append(save_round_record(jobs_dir, record))

    rewrite_legacy_scoped_notes(jobs_dir, list(merged.values()))
    dossier_paths = rebuild_company_dossiers(jobs_dir)
    rebuild_legacy_exports(jobs_dir)
    return {
        "backup_dir": backup_dir,
        "backed_up_items": copied,
        "records_written": len(written_paths),
        "dossiers_written": len(dossier_paths),
    }
