#!/usr/bin/env python3
"""Deep requirement-by-requirement analysis of the active job description."""

from __future__ import annotations

import re
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

import resume_analysis


PROJECT_ROOT = Path(__file__).resolve().parents[1]
JOB_DESCRIPTION = PROJECT_ROOT / "jobs" / "job_description.txt"
WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{WORD_NS}}}"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig") if path.exists() else ""


def docx_visible_text(path: Path) -> str:
    with ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    return "\n".join(
        re.sub(r"\s+", " ", "".join(node.text or "" for node in paragraph.findall(f".//{W}t"))).strip()
        for paragraph in root.findall(f".//{W}p")
    )


def requirement_sentences(job_description: str) -> list[str]:
    cleaned = resume_analysis.role_requirement_text(job_description)
    requirements: list[str] = []
    for raw_line in cleaned.splitlines():
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", raw_line).strip()
        if not line or resume_analysis.BOILERPLATE_LINE_RE.search(line):
            continue
        if len(line.split()) >= 4:
            requirements.append(line)
    if requirements:
        return list(dict.fromkeys(requirements))
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    return [sentence.strip() for sentence in sentences if len(sentence.split()) >= 6]


def key_terms(requirement: str) -> list[str]:
    trivial = {"plus", "software", "track", "verbal", "tasks", "updates", "setup", "team", "members"}
    terms = [
        term.lower()
        for term in re.findall(r"[A-Za-z][A-Za-z+.#-]{3,}(?:\s+[A-Za-z][A-Za-z+.#-]{3,})?", requirement)
        if term.lower() not in resume_analysis.STOP_WORDS
    ]
    terms = [term for term in terms if term not in trivial]
    return list(dict.fromkeys(terms))[:8]


def classify_requirement(requirement: str, resume_text: str, profile: resume_analysis.JobProblemProfile) -> tuple[str, str]:
    terms = key_terms(requirement)
    direct_hits = [term for term in terms if resume_analysis.text_mentions(resume_text, term)]
    if direct_hits:
        return "Direct", f"Resume text contains: {', '.join(direct_hits[:4])}"
    adjacent_hits = [
        area
        for area in profile.direct_matches + profile.adjacent_matches
        if any(word in requirement.lower() for word in area.lower().split())
    ]
    if adjacent_hits:
        return "Adjacent", f"Related evidence area: {adjacent_hits[0]}"
    unsupported_hits = [
        label
        for label, patterns in resume_analysis.UNSUPPORTED_REQUIREMENT_PATTERNS
        if resume_analysis.text_mentions(requirement, *patterns)
    ]
    if unsupported_hits:
        return "Unsupported", unsupported_hits[0]
    return "Transferable", "No exact resume term match; use implementation, analytics, or customer-adoption bridge language."


def story_suggestion(requirement: str, profile: resume_analysis.JobProblemProfile) -> str:
    text = requirement.lower()
    if any(term in text for term in ("data", "report", "analytics", "dashboard", "kpi")):
        return "Use the 200+ dashboards / KPI reporting story."
    if any(term in text for term in ("customer", "account", "adoption", "renewal", "risk")):
        return "Use the $1M+ at-risk account stabilization story."
    if any(term in text for term in ("migration", "uat", "testing", "go-live", "configuration")):
        return "Use the ERP migration, validation, and go-live readiness story."
    if any(term in text for term in ("training", "workshop", "stakeholder", "change")):
        return "Use the 60+ workshops / stakeholder adoption story."
    if profile.primary_lane == "process_improvement":
        return "Use the 78% manual-work reduction and 22% discrepancy reduction story."
    return "Use the implementation delivery through-line: clarify the workflow, align owners, validate the result, and drive adoption."


def main() -> None:
    job_description = read_text(JOB_DESCRIPTION).strip()
    if not job_description:
        raise SystemExit("jobs/job_description.txt is empty. Add the active job description first.")
    selected_resume = resume_analysis.choose_resume(job_description)
    resume_text = docx_visible_text(selected_resume)
    profile = resume_analysis.job_problem_profile(job_description, resume_text)

    print("Deep Job Analysis")
    print(f"Source resume: {selected_resume.name}")
    print(f"Detected lane: {profile.lane_label}")
    print()
    for index, requirement in enumerate(requirement_sentences(job_description), 1):
        classification, evidence = classify_requirement(requirement, resume_text, profile)
        print(f"{index}. {classification}: {requirement}")
        print(f"   Evidence: {evidence}")
        print(f"   Story: {story_suggestion(requirement, profile)}")


if __name__ == "__main__":
    main()
