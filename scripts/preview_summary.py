#!/usr/bin/env python3
"""Preview the generated Professional Summary without writing files."""

from __future__ import annotations

import re
import time
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import build_resume
from utils import fail, read_text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
JOB_DESCRIPTION = PROJECT_ROOT / "jobs" / "job_description.txt"


def docx_visible_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        xml_bytes = archive.read("word/document.xml")
    root = ET.fromstring(xml_bytes)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", namespace):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", namespace))
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def main() -> None:
    started = time.monotonic()
    if not JOB_DESCRIPTION.is_file():
        fail(f"job description not found: {JOB_DESCRIPTION}")
    job_description = read_text(JOB_DESCRIPTION)
    if not job_description:
        fail("jobs/job_description.txt is empty; add one complete job description before previewing the summary")

    selected_resume = build_resume.choose_resume(job_description)
    resume_text = docx_visible_text(selected_resume)
    summary = build_resume.build_problem_first_summary(job_description, resume_text)
    words = re.findall(r"\b[\w+.#'-]+\b", summary)
    erp_mentions = len(re.findall(r"\berp\b", summary, flags=re.I))
    profile = build_resume.job_problem_profile(job_description, resume_text)
    story_lens = build_resume.primary_story_lens(job_description)
    employer_context = build_resume.primary_employer_context(job_description)

    print()
    print("Generated Professional Summary")
    print("-" * 38)
    print(summary)
    print()
    print("Summary Diagnostics")
    print(f"  Word count: {len(words)}")
    print(
        f"  Length rule: "
        f"{'PASS' if build_resume.PROFESSIONAL_SUMMARY_MIN_WORDS <= len(words) <= build_resume.PROFESSIONAL_SUMMARY_MAX_WORDS else 'FAIL'} "
        f"({build_resume.PROFESSIONAL_SUMMARY_MIN_WORDS} to {build_resume.PROFESSIONAL_SUMMARY_MAX_WORDS} words)"
    )
    print(f"  ERP mentions: {erp_mentions}")
    print(f"  Detected lane: {profile.primary_lane}")
    print(f"  Story lens: {story_lens.get('key') if story_lens else 'None'}")
    print(f"  Employer context: {employer_context.get('key') if employer_context else 'None'}")
    print(f"  Source resume: {selected_resume.name}")
    print(f"  Elapsed: {time.monotonic() - started:.2f}s")


if __name__ == "__main__":
    main()
