#!/usr/bin/env python3
"""Analyze structured or legacy post-interview debriefs for recurring patterns."""

from __future__ import annotations

import _bootstrap

_bootstrap.ensure_script_path()

import argparse
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Mapping, Sequence

import interview_context
from utils import read_text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
JOB_DESCRIPTION = PROJECT_ROOT / "jobs" / "job_description.txt"
DEBRIEF_HISTORY = PROJECT_ROOT / "jobs" / "debrief_history.txt"
DEBRIEF_DELIMITER = "POST-INTERVIEW DEBRIEF CAPTURED"

STORY_THEME_RULES: dict[str, tuple[str, ...]] = {
    "Inventory adjustment system": ("inventory adjustment", "inventory workflow", "manual work", "discrepanc"),
    "Aptean rapid product learning": ("learn quickly", "learning quickly", "ramp quickly", "comfortable with", "new product"),
    "$1M+ account stabilization": ("account risk", "at-risk account", "customer trust", "escalation", "renewal risk", "revenue risk"),
    "200+ dashboards and decision visibility": ("dashboard", "dashboards", "reporting", "excel", "kpi", "data trust"),
    "60+ workshops and QBRs": ("training others", "training", "workshops", "qbr", "executive conversation", "presenting"),
    "East West ERP ownership": ("erp ownership", "erp", "five sites", "technical projects", "systems administration"),
    "LivePerson messaging workflows": ("liveperson", "chat", "messaging", "sms", "conversational ai", "nlp"),
    "Aptean lifecycle delivery": ("implementation lifecycle", "data migration", "go-live", "hypercare", "technical project"),
    "Operations versus finance alignment": ("stakeholder disagreement", "opposing views", "operations and finance", "tradeoff"),
    "Failure lesson and stronger validation": ("failure", "mistake", "validation", "testing", "what went wrong"),
}


@dataclass(frozen=True)
class DebriefPatternSummary:
    company_name: str
    entry_count: int
    most_common_question: str
    recurring_question_count: int
    top_story_title: str
    top_story_count: int
    repeated_role_language: tuple[str, ...]
    top_coaching_signals: tuple[str, ...] = ()


def field_value(entry: str, label: str) -> str:
    match = re.search(rf"(?im)^\s*{re.escape(label)}:\s*(.*?)\s*$", entry)
    return match.group(1).strip() if match else ""


def section_value(entry: str, section_label: str) -> str:
    match = re.search(rf"(?ims)^{re.escape(section_label)}:\s*(.*?)(?=\n[A-Z][A-Za-z -]+:\s|\Z)", entry)
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else ""


def _record_to_entry(record: Mapping[str, object]) -> str:
    return interview_context.record_to_debrief_entry(record)


def entry_sort_date(entry: str) -> datetime:
    first_line = entry.splitlines()[0] if entry.splitlines() else ""
    match = re.search(r"(\d{4}-\d{2}-\d{2})(?:\s+(\d{2}:\d{2}:\d{2}))?", first_line)
    if match:
        raw = f"{match.group(1)} {match.group(2) or '00:00:00'}"
        try:
            return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    interview_date = field_value(entry, "Interview date")
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(interview_date, fmt)
        except ValueError:
            continue
    return datetime.min


def all_debrief_entries(debrief_path: Path = DEBRIEF_HISTORY) -> list[str]:
    if debrief_path == DEBRIEF_HISTORY:
        structured_entries = interview_context.debrief_entries_for_company(PROJECT_ROOT / "jobs")
        if structured_entries:
            return structured_entries
    if not debrief_path.exists():
        return []
    text = read_text(debrief_path)
    entries = [
        f"{DEBRIEF_DELIMITER}{entry}".strip()
        for entry in text.split(DEBRIEF_DELIMITER)
        if entry.strip()
    ]
    return sorted(entries, key=entry_sort_date, reverse=True)


def find_debrief_entries_for_company(company_name: str, debrief_path: Path = DEBRIEF_HISTORY) -> list[str]:
    if debrief_path == DEBRIEF_HISTORY and company_name:
        structured_entries = interview_context.debrief_entries_for_company(PROJECT_ROOT / "jobs", company_name)
        if structured_entries:
            return structured_entries
    if not company_name:
        return all_debrief_entries(debrief_path)
    needle = company_name.lower()
    return [
        entry
        for entry in all_debrief_entries(debrief_path)
        if needle in field_value(entry, "Company name").lower()
    ]


def find_round_records_for_company(company_name: str = "") -> list[dict[str, object]]:
    return interview_context.load_round_records(PROJECT_ROOT / "jobs", company_name)


def normalize_text(value: str) -> str:
    lowered = value.lower()
    lowered = re.sub(r"[^a-z0-9\s$+]", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def question_chunks(text: str) -> list[str]:
    chunks = [match.strip() for match in re.findall(r"[^?]+\?", text)]
    if chunks:
        return chunks
    fallback: list[str] = []
    for raw in re.split(r"[;\n]", text):
        cleaned = re.sub(r"\s+", " ", raw).strip(" -")
        if len(cleaned.split()) >= 4:
            fallback.append(cleaned)
    return fallback


def normalize_question(value: str) -> str:
    cleaned = normalize_text(value).rstrip("?")
    cleaned = re.sub(r"\b(?:tell me about a time|tell me about|can you|could you|how do you|how did you|what is|what are|why do you|why did you)\b", "", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def story_titles_from_text(text: str) -> list[str]:
    lowered = normalize_text(text)
    matches: list[str] = []
    for title, keywords in STORY_THEME_RULES.items():
        if any(keyword in lowered for keyword in keywords):
            matches.append(title)
    return matches


def _signal_labels_from_entry(entry: str) -> list[str]:
    section = section_value(entry, "Coaching signals")
    labels: list[str] = []
    for raw in re.split(r"[;\n]", section):
        cleaned = re.sub(r"\s+", " ", raw).strip(" -")
        if not cleaned:
            continue
        label = cleaned.split(":", 1)[0].strip()
        if label:
            labels.append(label)
    return labels


def _signal_labels_from_record(record: Mapping[str, object]) -> list[str]:
    review = record.get("performance_review", {})
    if not isinstance(review, Mapping):
        return []
    labels: list[str] = []
    for item in review.get("coaching_signals", []):  # type: ignore[union-attr]
        if not isinstance(item, Mapping):
            continue
        label = str(item.get("label", "")).strip()
        if label:
            labels.append(label)
    return labels


def analyze_entries(entries: Sequence[str | Mapping[str, object]], company_name: str = "") -> DebriefPatternSummary:
    question_counts: Counter[str] = Counter()
    question_display: dict[str, str] = {}
    story_counts: Counter[str] = Counter()
    role_language_counts: Counter[str] = Counter()
    coaching_signal_counts: Counter[str] = Counter()

    for item in entries:
        if isinstance(item, Mapping):
            story_text = " ".join(
                [
                    *interview_context._split_lines(item.get("story_followups", [])),
                    *interview_context._split_lines(item.get("unexpected_questions", [])),
                ]
            )
            role_language = "\n".join(interview_context._split_lines(item.get("role_language", [])))
            coaching_labels = _signal_labels_from_record(item)
        else:
            story_text = " ".join(
                [
                    section_value(item, "Stories that generated follow-up questions"),
                    section_value(item, "Unexpected questions"),
                ]
            )
            role_language = section_value(item, "Specific interviewer language about the role")
            coaching_labels = _signal_labels_from_entry(item)

        if story_text and story_text.lower() != "none supplied.":
            for question in question_chunks(story_text):
                normalized = normalize_question(question)
                if len(normalized) < 8:
                    continue
                question_counts[normalized] += 1
                question_display.setdefault(normalized, question.strip())
            for title in story_titles_from_text(story_text):
                story_counts[title] += 1

        for raw in re.split(r"[;\n]", role_language):
            cleaned = re.sub(r"\s+", " ", raw).strip(" -")
            if len(cleaned) >= 8 and cleaned.lower() != "none supplied.":
                role_language_counts[cleaned] += 1

        for label in coaching_labels:
            cleaned = re.sub(r"\s+", " ", label).strip()
            if cleaned:
                coaching_signal_counts[cleaned] += 1

    most_common_question = ""
    recurring_question_count = 0
    if question_counts:
        question_key, question_count = question_counts.most_common(1)[0]
        if question_count > 1:
            most_common_question = question_display.get(question_key, question_key).strip()
            recurring_question_count = question_count

    top_story_title = ""
    top_story_count = 0
    if story_counts:
        candidate_title, candidate_count = story_counts.most_common(1)[0]
        if candidate_count > 1:
            top_story_title = candidate_title
            top_story_count = candidate_count

    repeated_role_language = tuple(
        phrase
        for phrase, count in role_language_counts.most_common(3)
        if count > 1
    )
    top_coaching_signals = tuple(
        f"{label} ({count})" if count > 1 else label
        for label, count in coaching_signal_counts.most_common(4)
    )

    return DebriefPatternSummary(
        company_name=company_name,
        entry_count=len(entries),
        most_common_question=most_common_question,
        recurring_question_count=recurring_question_count,
        top_story_title=top_story_title,
        top_story_count=top_story_count,
        repeated_role_language=repeated_role_language,
        top_coaching_signals=top_coaching_signals,
    )


def reorder_story_cards(stories: Sequence[object], summary: DebriefPatternSummary) -> list[object]:
    if not summary.top_story_title:
        return list(stories)
    theme_keywords = STORY_THEME_RULES.get(summary.top_story_title, ())
    target_title = normalize_text(summary.top_story_title)

    def story_score(card: object) -> int:
        title = str(getattr(card, "title", ""))
        hook = str(getattr(card, "hook", ""))
        outcome = str(getattr(card, "outcome", ""))
        signals = " ".join(str(signal) for signal in getattr(card, "signals", ()))
        haystack = normalize_text(" ".join((title, hook, outcome, signals)))
        score = 0
        if normalize_text(title) == target_title:
            score += 100
        score += sum(5 for keyword in theme_keywords if keyword in haystack)
        if summary.most_common_question:
            score += sum(2 for keyword in theme_keywords if keyword in normalize_text(summary.most_common_question))
        return score

    ranked = list(enumerate(stories))
    ranked.sort(key=lambda item: (story_score(item[1]), -item[0]), reverse=True)
    return [story for _index, story in ranked]


def summary_lines(summary: DebriefPatternSummary) -> list[str]:
    lines = [
        f"Entries analyzed: {summary.entry_count}",
    ]
    if summary.company_name:
        lines.insert(0, f"Company focus: {summary.company_name}")
    if summary.most_common_question:
        lines.append(
            f"Most common recurring question ({summary.recurring_question_count}x): {summary.most_common_question}"
        )
    else:
        lines.append("Most common recurring question: none repeated yet")
    if summary.top_story_title:
        lines.append(
            f"Top-performing story signal ({summary.top_story_count}x): {summary.top_story_title}"
        )
    else:
        lines.append("Top-performing story signal: no repeated story theme found yet")
    if summary.repeated_role_language:
        lines.append("Repeated interviewer language: " + "; ".join(summary.repeated_role_language))
    else:
        lines.append("Repeated interviewer language: none repeated yet")
    if summary.top_coaching_signals:
        lines.append("Recurring delivery habits: " + "; ".join(summary.top_coaching_signals))
    else:
        lines.append("Recurring delivery habits: none detected yet")
    return lines


def active_company_name() -> str:
    if not JOB_DESCRIPTION.exists():
        return ""
    try:
        import build_resume  # type: ignore[import-not-found]
    except Exception:
        return ""
    job_description = read_text(JOB_DESCRIPTION)
    if not job_description.strip():
        return ""
    return build_resume.extract_output_name(job_description)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze captured interview debriefs for repeated patterns.")
    parser.add_argument("--company", help="Analyze only debriefs for the named company.")
    parser.add_argument("--all", action="store_true", help="Analyze all captured debriefs instead of the active company.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    company_name = args.company or ("" if args.all else active_company_name())
    records = find_round_records_for_company(company_name) if company_name or args.all else find_round_records_for_company(company_name)
    if records:
        summary = analyze_entries(records, company_name)
        print("Debrief Pattern Analysis")
        for line in summary_lines(summary):
            print(line)
        return 0

    entries = find_debrief_entries_for_company(company_name) if company_name else all_debrief_entries()
    summary = analyze_entries(entries, company_name)
    print("Debrief Pattern Analysis")
    if not entries:
        if company_name:
            print(f"No debrief entries found for {company_name}.")
        else:
            print("No debrief entries found.")
        return 0
    for line in summary_lines(summary):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
