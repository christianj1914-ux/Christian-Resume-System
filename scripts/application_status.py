#!/usr/bin/env python3
"""Show readiness status for the active application package."""

from __future__ import annotations

from pathlib import Path

import resume_analysis
import track_applications


PROJECT_ROOT = Path(__file__).resolve().parents[1]
JOBS_DIR = PROJECT_ROOT / "jobs"
OUTPUT_DIR = PROJECT_ROOT / "output"
JOB_DESCRIPTION = JOBS_DIR / "job_description.txt"


def read_job() -> str:
    return JOB_DESCRIPTION.read_text(encoding="utf-8-sig").strip() if JOB_DESCRIPTION.exists() else ""


def has_output(patterns: str | list[str]) -> str:
    if isinstance(patterns, str):
        patterns = [patterns]
    matches: list[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        for candidate in OUTPUT_DIR.glob(pattern):
            if candidate not in seen:
                matches.append(candidate)
                seen.add(candidate)
    matches.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return matches[0].name if matches else ""


def latest_output_name(job_description: str, suffix_pattern: str) -> str:
    matches = resume_analysis.matching_output_files(OUTPUT_DIR, job_description, suffix_pattern)
    if suffix_pattern != "Resume.docx":
        resume_matches = resume_analysis.matching_output_files(OUTPUT_DIR, job_description, "Resume.docx")
        if resume_matches:
            current_resume = resume_matches[0]
            current_state = resume_analysis.output_audit_state(current_resume)
            resume_mtime = current_resume.stat().st_mtime
            matches = [
                candidate
                for candidate in matches
                if candidate.stat().st_mtime >= resume_mtime
                and resume_analysis.output_audit_state(candidate) == current_state
            ]
    return matches[0].name if matches else ""


def tracker_status(company: str, role_title: str) -> str:
    rows = track_applications.read_rows()
    index = track_applications.matching_row_index(rows, company, role_title)
    if index is None:
        return ""
    row = rows[index]
    status = row.get("current_status", "")
    round_text = row.get("last_round", "")
    outcome = row.get("outcome", "")
    details = status
    if round_text:
        details += f", round {round_text}"
    if outcome:
        details += f", outcome {outcome}"
    return details or "tracked"


def print_status(label: str, detail: str) -> None:
    state = "OK" if detail else "MISSING"
    suffix = f" - {detail}" if detail else ""
    print(f"{state}: {label}{suffix}")


def main() -> int:
    job_description = read_job()
    if not job_description:
        print("No active job description found.")
        return 1
    company = resume_analysis.extract_output_name(job_description)
    target_name = resume_analysis.extract_output_target_name(job_description)
    role_title = resume_analysis.extract_job_title(job_description) or "Target Role"
    print(f"Application Status: {company} - {role_title}")
    print()
    print_status("Resume", latest_output_name(job_description, "Resume.docx"))
    print_status("Cover letter", latest_output_name(job_description, "Cover Letter.docx"))
    print_status("Qualifications statement", latest_output_name(job_description, "Qualifications Statement.docx"))
    print_status("Application checklist", latest_output_name(job_description, "Application Checklist.docx"))
    print_status("Tracker row", tracker_status(company, role_title))
    print_status("Interview cheat sheet", latest_output_name(job_description, "Interview Cheat Sheet.docx"))
    print_status("Detailed interview guide", latest_output_name(job_description, "Detailed Interview Guide.docx"))
    print_status("Thank-you note", latest_output_name(job_description, "Thank-You Note.docx"))
    print_status("Follow-up email", latest_output_name(job_description, "Follow-Up Email.docx"))
    print_status("Post-round prep", latest_output_name(job_description, "Post-Round*.docx"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
