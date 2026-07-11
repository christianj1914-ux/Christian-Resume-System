#!/usr/bin/env python3
"""Task runner for the Christian Resume System.

# This is the canonical way to invoke all resume system scripts. The individual
# bat files are kept only for Windows double-click convenience.
"""

from __future__ import annotations

import subprocess
import sys
import time
import zipfile
import contextlib
import io
import csv
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
import re
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))
import render_checks  # type: ignore[import-not-found]
import business_context  # type: ignore[import-not-found]


PROJECT_ROOT = Path(__file__).resolve().parent
JOB_DESCRIPTION = PROJECT_ROOT / "jobs" / "job_description.txt"
APPLICATIONS_CSV = PROJECT_ROOT / "scratch" / "applications.csv"
DEBRIEF_HISTORY = PROJECT_ROOT / "jobs" / "debrief_history.txt"
DEBRIEF_DELIMITER = "POST-INTERVIEW DEBRIEF CAPTURED"


@dataclass(frozen=True)
class Task:
    description: str
    args: tuple[str, ...]
    needs_job_description: bool = True
    maturity: str = "Stable"
    production_safe: bool = True


TASKS: dict[str, Task] = {
    "validate": Task("Run the smoke test and print a pass/fail summary.", ("scripts/smoke_test.py",), False),
    "integration-test": Task("Run the end-to-end function-chain integration test.", ("scripts/integration_test.py",), False),
    "morning": Task("Show a one-screen job-search briefing.", (), False),
    "ci": Task("Show how to run or trigger the GitHub Actions smoke-test workflow.", (), False),
    "jd-check": Task("Check job description quality without building anything.", (), True),
    "business-context-check": Task("Show detected business context and research gaps.", (), True),
    "align": Task("Show the pre-build alignment score without writing files.", (), True),
    "ats-check": Task("Validate the latest generated resume as plain ATS text.", (), True),
    "preview-summary": Task("Preview the generated Professional Summary without writing files.", ("scripts/preview_summary.py",), True),
    "writing-eval": Task("Grade resume or cover-letter prose against the writing-style evaluator.", ("scripts/writing_eval.py",), False),
    "writing-extract": Task("Extract resume summaries and cover-letter sections from DOCX examples into text snippets.", ("scripts/extract_writing_examples.py",), False),
    "check": Task(
        "Pre-flight analysis: shows lane detection, keyword gaps, evidence coverage, and fit risks without building anything.",
        (),
    ),
    "dry-run": Task("Validate the current job description and planned workflow without writing files.", ("scripts/run_resume_workflow.py", "--dry-run"), False),
    "resume": Task("Build the tailored resume and cover letter workflow.", ("scripts/run_resume_workflow.py",)),
    "federal-dry-run": Task("Validate the federal job description and federal resume workflow without writing files.", ("scripts/run_federal_resume_workflow.py", "--dry-run"), False),
    "federal-resume": Task(
        "Build the tailored federal resume workflow. Optional flags: --with-cover, --with-interview, --with-guide, --with-supporting-docs.",
        ("scripts/run_federal_resume_workflow.py",),
        False,
    ),
    "federal-cover": Task(
        "Build the matching federal cover letter directly from the latest federal resume.",
        ("scripts/build_federal_cover_letter.py",),
        False,
        "Experimental",
        False,
    ),
    "federal-interview": Task(
        "Build the matching federal interview cheat sheet directly from the latest federal resume.",
        ("scripts/build_federal_interview_cheat_sheet.py",),
        False,
        "Experimental",
        False,
    ),
    "federal-guide": Task(
        "Build the matching federal detailed interview guide directly from the latest federal resume.",
        ("scripts/build_federal_detailed_interview_guide.py",),
        False,
        "Experimental",
        False,
    ),
    "cover": Task("Build the default concise cover letter directly from the latest matching resume.", ("scripts/build_cover_letter.py",)),
    "qualifications": Task(
        "Build the standard qualifications statement or application-question companion document.",
        ("scripts/build_standard_qualifications_statement.py",),
    ),
    "cover-short": Task(
        "Legacy alias: build the default concise cover letter directly from the latest matching resume.",
        ("scripts/build_cover_letter.py", "--mode", "standard"),
    ),
    "cover-long": Task(
        "Legacy alias: build the default one-page cover letter directly from the latest matching resume.",
        ("scripts/build_cover_letter.py", "--mode", "standard"),
    ),
    "cover-check": Task("Preview the default concise cover letter structure and opening pattern selection without generating a file.", (), True),
    "checklist": Task("Build a one-page job-specific application checklist.", ("scripts/build_application_checklist.py",), True),
    "thank-you": Task("Build a post-interview thank-you note.", ("scripts/build_thank_you.py",), True),
    "followup": Task(
        "Build a no-response application follow-up email guide.",
        ("scripts/build_followup_email.py",),
        True,
        "Experimental",
        False,
    ),
    "interview-followup": Task(
        "Build a post-interview follow-up email document from the latest debrief.",
        ("scripts/build_interview_followup.py",),
        True,
        "Experimental",
        False,
    ),
    "post-round": Task(
        "Build post-round follow-up and next-round prep from the latest debrief.",
        ("scripts/build_post_round.py",),
        True,
        "Experimental",
        False,
    ),
    "linkedin": Task("Build a LinkedIn profile update guide.", ("scripts/build_linkedin_update.py",), True),
    "linkedin-calendar": Task(
        "Build a 30-day LinkedIn content calendar.",
        ("scripts/build_linkedin_calendar.py",),
        True,
        "Experimental",
        False,
    ),
    "outreach": Task(
        "Build networking outreach templates.",
        ("scripts/build_networking_outreach.py",),
        True,
        "Experimental",
        False,
    ),
    "plan": Task(
        "Build a role-specific first 90 days plan.",
        ("scripts/build_first_90_days.py",),
        True,
        "Experimental",
        False,
    ),
    "track": Task("Add the active job to the application tracker.", ("scripts/track_applications.py", "add"), True),
    "track-list": Task("List tracked applications.", ("scripts/track_applications.py", "list"), False),
    "track-report": Task("Print an application tracker summary.", ("scripts/track_applications.py", "report"), False),
    "track-refresh": Task("Refresh tracker lane and fit metadata from current or archived job descriptions.", ("scripts/track_applications.py", "refresh"), False),
    "application-status": Task("Show active application package readiness.", ("scripts/application_status.py",), True),
    "analytics": Task("Build the job-search analytics report.", ("scripts/build_search_analytics.py",), False),
    "assess": Task(
        "Build a Four Career Value Driver Assessment.",
        ("scripts/build_career_value_assessment.py",),
        False,
        "Template-only",
        False,
    ),
    "trajectory": Task(
        "Build an Up-or-Out Trajectory Analysis.",
        ("scripts/build_trajectory_analysis.py",),
        False,
        "Template-only",
        False,
    ),
    "story-audit": Task(
        "Audit and improve a candidate-provided interview story.",
        ("scripts/build_story_audit.py",),
        False,
        "Template-only",
        False,
    ),
    "salary-guide": Task(
        "Build a salary negotiation preparation guide.",
        ("scripts/build_salary_guide.py",),
        True,
        "Experimental",
        False,
    ),
    "internal-interview": Task(
        "Build an internal interview guide.",
        ("scripts/build_internal_interview.py",),
        True,
        "Experimental",
        False,
    ),
    "monthly-review": Task(
        "Build the monthly job-search review report.",
        ("scripts/build_monthly_review.py",),
        False,
        "Experimental",
        False,
    ),
    "skills-gap": Task(
        "Build the future-proofing skills gap analysis.",
        ("scripts/build_skills_gap.py",),
        False,
        "Experimental",
        False,
    ),
    "skills-db": Task("Build or refresh the structured skills database from the source resumes.", ("scripts/build_skills_database.py",), False),
    "skills-db-refresh": Task("Force-refresh the structured skills database from the source resumes.", ("scripts/build_skills_database.py", "--refresh"), False),
    "weekly-plan": Task(
        "Build the weekly job-search plan.",
        ("scripts/build_weekly_tracker.py",),
        False,
        "Experimental",
        False,
    ),
    "jd-archive": Task("Archive the active job description.", ("scripts/build_jd_library.py", "archive"), True),
    "jd-patterns": Task("Show job-description library patterns.", ("scripts/build_jd_library.py", "patterns"), False),
    "interview": Task("Build the standard interview cheat sheet directly.", ("scripts/build_interview_cheat_sheet.py",)),
    "guide": Task("Build the detailed interview guide directly.", ("scripts/build_detailed_interview_guide.py",)),
    "interview-review": Task(
        "Build the latest interview review and positioning-diagnosis document from structured debriefs.",
        ("scripts/build_interview_review.py",),
        False,
        "Experimental",
        False,
    ),
    "debrief": Task("Capture a new post-interview debrief.", ("scripts/post_interview_debrief.py", "--capture")),
    "prepare-company-notes": Task(
        "Create or open the canonical company interview dossier scaffold.",
        ("scripts/post_interview_debrief.py", "--prepare-company-notes"),
        False,
    ),
    "list-debriefs": Task("List captured debrief entries.", ("scripts/post_interview_debrief.py", "--list"), False),
    "debrief-patterns": Task("Analyze captured debriefs for repeated questions, story signals, interviewer language, and delivery habits.", ("scripts/build_debrief_analysis.py",), False),
    "debrief-repair": Task(
        "Back up and repair legacy debrief and company-research artifacts into structured round records.",
        ("scripts/post_interview_debrief.py", "--repair-legacy"),
        False,
    ),
    "reset-jobs": Task("Archive job context and optionally clear active job files.", ("scripts/reset_jobs.py",), False),
    "list-archives": Task("List archived job context snapshots.", ("scripts/reset_jobs.py", "--list-archives"), False),
    "clean-renders": Task("Delete render check folders older than 24 hours.", ("scripts/cleanup_render_checks.py", "--delete", "--hours", "24"), False),
    "cleanup": Task("Prompt to delete stale render folders and output files older than retention limits.", ("scripts/cleanup_output.py",), False),
    "advice": Task("Build the Career Operating Manual.", ("scripts/build_general_advice.py",), False),
    "claude-packet": Task("Rebuild the ready-to-upload Claude review packet from live files.", ("scripts/build_claude_review_packet.py",), False),
    "claude-prompt": Task("Print the Claude review or plan prompt for a packet mode.", ("scripts/build_claude_prompt.py",), False),
    "claude-refresh": Task("Refresh the common Claude Review upload bundle in one step.", ("scripts/refresh_claude_review_bundle.py",), False),
}

COMMERCIAL_AUTO_ARCHIVE_COMMANDS = {
    "resume",
    "cover",
    "cover-short",
    "cover-long",
    "qualifications",
    "checklist",
    "thank-you",
    "followup",
    "interview-followup",
    "post-round",
    "linkedin",
    "linkedin-calendar",
    "outreach",
    "plan",
    "track",
    "interview",
    "guide",
    "salary-guide",
    "internal-interview",
}


def print_help() -> None:
    print("Usage: python tasks.py COMMAND")
    if render_checks.RENDER_AVAILABLE:
        print("Render: available")
    else:
        print("Render: unavailable (page count estimated from XML)")
    print()
    print("Commands:")
    for name, task in TASKS.items():
        safe_label = "safe" if task.production_safe else "review"
        print(f"  {name:<14} [{task.maturity:<12} | {safe_label:<6}] {task.description}")
    print("  help           Show this command list.")
    print("  commands       Print registered commands and script targets.")


def print_command_inventory() -> int:
    for name in sorted(TASKS):
        task = TASKS[name]
        target = " ".join(task.args) if task.args else "(internal)"
        safe_label = "production-safe" if task.production_safe else "human-review"
        print(f"{name}: {task.maturity} | {safe_label} | {target}")
    print("help: (internal)")
    print("commands: (internal)")
    return 0


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def debrief_entries() -> list[str]:
    if not DEBRIEF_HISTORY.exists():
        return []
    text = DEBRIEF_HISTORY.read_text(encoding="utf-8-sig")
    return [f"{DEBRIEF_DELIMITER}{entry}".strip() for entry in text.split(DEBRIEF_DELIMITER) if entry.strip()]


def debrief_field(entry: str, label: str) -> str:
    match = re.search(rf"(?im)^\s*{re.escape(label)}:\s*(.*?)\s*$", entry)
    return match.group(1).strip() if match else ""


def pending_debrief_followups() -> list[str]:
    followups = []
    seen = set()
    for entry in debrief_entries():
        if debrief_field(entry, "Outcome").lower() != "pending":
            continue
        company = debrief_field(entry, "Company name") or "Unknown company"
        role = debrief_field(entry, "Role title") or "Unknown role"
        round_number = debrief_field(entry, "Round number") or "?"
        feedback = entry.lower()
        interview_date_raw = debrief_field(entry, "Interview date")
        window = "follow-up window unknown"
        try:
            interview_date = datetime.strptime(interview_date_raw, "%m/%d/%Y").date()
            if "1 to 2 weeks" in feedback or "1-2 weeks" in feedback or "one to 2 weeks" in feedback:
                start = interview_date + timedelta(days=7)
                end = interview_date + timedelta(days=14)
                window = f"follow-up window {start.isoformat()} to {end.isoformat()}"
            else:
                window = f"follow-up check after {(interview_date + timedelta(days=7)).isoformat()}"
        except ValueError:
            pass
        line = f"{company} Round {round_number} - outcome pending, {window}."
        key = (company.lower(), round_number, window)
        if key not in seen:
            followups.append(line)
            seen.add(key)
    return followups


def run_morning() -> int:
    print("Morning Briefing")
    print()
    print("Active Target")
    if JOB_DESCRIPTION.exists() and JOB_DESCRIPTION.read_text(encoding="utf-8-sig").strip():
        build_resume = load_build_resume()
        job_description = JOB_DESCRIPTION.read_text(encoding="utf-8-sig").strip()
        company = build_resume.extract_company_name(job_description) or build_resume.extract_output_name(job_description)
        role = build_resume.extract_job_title(job_description) or "Unknown role"
        print(f"  {company} - {role}")
    else:
        print("  No active job description. Run tasks.py jd-check after pasting a new posting.")

    rows = read_csv_rows(APPLICATIONS_CSV)
    print()
    print("Pipeline Status")
    buckets = {
        "Applied": sum(1 for row in rows if row.get("current_status") == "applied"),
        "Phone Screen": sum(1 for row in rows if row.get("current_status") == "phone_screen"),
        "Interview": sum(1 for row in rows if row.get("current_status") == "interview"),
        "Final Round": sum(1 for row in rows if row.get("current_status") == "final_round"),
        "Pending Outcome": sum(1 for row in rows if row.get("current_status") in {"phone_screen", "interview", "final_round"} and not row.get("outcome")),
    }
    print("  " + " | ".join(f"{label}: {count}" for label, count in buckets.items()))

    print()
    print("Recent Intelligence")
    if DEBRIEF_HISTORY.exists():
        recent_count = len(debrief_entries())
        print(f"  Debrief entries captured: {recent_count}")
        for pending in pending_debrief_followups()[:3]:
            print(f"  {pending}")
    else:
        print("  No debrief history found.")

    print()
    print("Next Recommended Action")
    silent_followups = []
    today = date.today()
    for row in rows:
        if row.get("current_status") == "applied" and row.get("applied_date"):
            try:
                applied = datetime.strptime(row["applied_date"], "%Y-%m-%d").date()
            except ValueError:
                continue
            if today - applied >= timedelta(days=14):
                silent_followups.append(row.get("company", "Unknown company"))
    pending_rounds = pending_debrief_followups()
    if pending_rounds:
        print(f"  {pending_rounds[0]}")
        print("  Run python tasks.py post-round if you have not sent a follow-up or prepped next-round answers.")
    elif silent_followups:
        print(f"  Follow up with: {', '.join(silent_followups[:3])}.")
    elif any(row.get("current_status") in {"phone_screen", "interview", "final_round"} for row in rows):
        print("  Prepare interview materials for the most advanced active opportunity.")
    elif rows:
        print("  Add new applications or update statuses for the current pipeline.")
    else:
        print("  Add the active job to the tracker with python tasks.py track.")
    return 0


def validate_job_description() -> bool:
    if not JOB_DESCRIPTION.exists():
        print("jobs/job_description.txt is missing. Add one complete job description before running this command.")
        return False
    if not JOB_DESCRIPTION.read_text(encoding="utf-8-sig").strip():
        print("jobs/job_description.txt is empty. Add one complete job description before running this command.")
        return False
    return True


def load_build_resume() -> object:
    script_dir = PROJECT_ROOT / "scripts"
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    import build_resume  # type: ignore[import-not-found]

    return build_resume


def load_build_cover_letter() -> object:
    script_dir = PROJECT_ROOT / "scripts"
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    import build_cover_letter  # type: ignore[import-not-found]

    return build_cover_letter


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


def term_occurrences(text: str, term: str) -> int:
    normalized = term.strip()
    if not normalized:
        return 0
    flags = re.I
    if " " in normalized:
        return len(re.findall(re.escape(normalized), text, flags))
    return len(re.findall(rf"\b{re.escape(normalized)}\b", text, flags))


def coverage_status(term: str, resume_text: str) -> str:
    if term_occurrences(resume_text, term):
        return "COVERED"
    parts = [
        part
        for part in re.findall(r"[A-Za-z][A-Za-z+.#-]{2,}", term.lower())
        if part not in {"and", "for", "the", "with", "from"}
    ]
    if len(parts) > 1 and any(term_occurrences(resume_text, part) for part in parts):
        return "PARTIAL"
    return "MISSING"


def print_list(label: str, values: tuple[str, ...] | list[str]) -> None:
    print(f"{label}:")
    if not values:
        print("  - None")
        return
    for value in values:
        print(f"  - {value}")


def truncate(text: str, limit: int) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(0, limit - 3)].rstrip() + "..."


def matching_resume_outputs(build_resume: object, job_description: str) -> list[Path]:
    resume_matches: list[Path] = []
    seen: set[Path] = set()
    for output_name in build_resume.output_name_candidates(job_description):
        for candidate in (PROJECT_ROOT / "output").glob(f"Christian Estrada - {output_name}*Resume.docx"):
            if candidate not in seen:
                resume_matches.append(candidate)
                seen.add(candidate)
    resume_matches.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return resume_matches


def run_check() -> int:
    started = time.monotonic()
    if not validate_job_description():
        return 1

    build_resume = load_build_resume()
    job_description = JOB_DESCRIPTION.read_text(encoding="utf-8-sig").strip()
    job_description = build_resume.validate_inputs(job_description)
    selected_resume = build_resume.choose_resume(job_description)
    resume_matches = matching_resume_outputs(build_resume, job_description)
    resume_docx = resume_matches[0] if resume_matches else selected_resume
    resume_text = docx_visible_text(resume_docx)

    presales_matches = sorted(signal for signal in build_resume.PRESALES_SIGNALS if signal in job_description.lower())
    if selected_resume == build_resume.PRESALES_CSM_RESUME:
        explanation = f"selected because {len(presales_matches)} pre-sales/customer-success signal(s) were found"
    else:
        explanation = f"selected because fewer than two pre-sales/customer-success signals were found ({len(presales_matches)})"

    print("Resume Selection")
    print(f"  Source: {selected_resume.name}")
    print(f"  Why: {explanation}.")
    if resume_docx != selected_resume:
        print(f"  Audit artifact: {resume_docx.name} (latest generated output)")
    else:
        print("  Audit artifact: source resume content database (no generated resume found)")
    if presales_matches:
        print(f"  Matching signals: {', '.join(presales_matches[:8])}")

    profile = build_resume.job_problem_profile(job_description, resume_text)
    print("\nDetected Role Lane")
    print(f"  Lane key: {profile.primary_lane}")
    print(f"  Lane label: {profile.lane_label}")
    print(f"  Core problem: {profile.core_problem}")
    print(f"  Audience: {profile.audience}")
    print(f"  Outcomes: {', '.join(profile.outcomes) if profile.outcomes else 'None'}")

    keywords = build_resume.audit_keywords(job_description)
    ranked_keywords = sorted(
        (
            (keyword, term_occurrences(job_description, keyword), coverage_status(keyword, resume_text))
            for keyword in keywords
        ),
        key=lambda item: (item[1], item[2] == "COVERED", len(item[0].split()), len(item[0]), item[0]),
        reverse=True,
    )[:15]
    print("\nTop Keyword Coverage")
    print(f"{'Keyword':<42} {'JD hits':>7}  Status")
    print(f"{'-' * 42} {'-' * 7}  {'-' * 8}")
    for keyword, count, status in ranked_keywords:
        display = keyword[:39] + "..." if len(keyword) > 42 else keyword
        print(f"{display:<42} {count:>7}  {status}")

    placement_report = build_resume.keyword_placement_audit(job_description, resume_text)
    placement_gaps = placement_report.get("gaps", [])
    print("\nTop Placement Gaps")
    if isinstance(placement_gaps, list) and placement_gaps:
        for gap in placement_gaps[:5]:
            if not isinstance(gap, dict):
                continue
            keyword = str(gap.get("keyword", "")).strip()
            issue = str(gap.get("issue", "")).strip()
            if keyword and issue:
                print(f"  - {keyword}: {issue}")
    else:
        print("  - None")

    print()
    print_list("Direct matches", profile.direct_matches)
    print_list("Adjacent matches", profile.adjacent_matches)
    print_list("Unsupported requirements", profile.unsupported_requirements)

    poor_fit = build_resume.poor_fit_requirements(job_description, resume_text)
    if poor_fit:
        print("\nWARNING: Poor-Fit Requirement Signals")
        for item in poor_fit:
            print(f"  - {item}")

    lens = build_resume.primary_story_lens(job_description)
    if lens:
        print("\nPrimary Story Lens")
        print(f"  Identity: {lens.get('identity', '')}")
        print(f"  Business problem: {lens.get('business_problem', '')}")
        print(f"  Candidate story: {lens.get('candidate_story', '')}")

    print(f"\nElapsed: {time.monotonic() - started:.2f}s")
    return 0


def run_cover_check() -> int:
    started = time.monotonic()
    if not validate_job_description():
        return 1

    build_resume = load_build_resume()
    cover = load_build_cover_letter()
    job_description = JOB_DESCRIPTION.read_text(encoding="utf-8-sig").strip()
    job_description = build_resume.validate_inputs(job_description)
    company_name = build_resume.extract_output_name(job_description)
    role_title = cover.extract_role_title(job_description) or build_resume.extract_job_title(job_description) or "Unknown Role"

    resume_matches = matching_resume_outputs(build_resume, job_description)
    if not resume_matches:
        print(
            "No matching resume exists in output/ for "
            f"{build_resume.extract_output_target_name(job_description)}. Run python tasks.py resume first."
        )
        return 1
    resume_docx = resume_matches[0]

    resume_text = docx_visible_text(resume_docx)
    normalized_mode = cover.DEFAULT_COVER_MODE
    draft = cover.compose_cover_letter_draft(
        company_name,
        role_title,
        job_description,
        resume_text,
        mode=normalized_mode,
    )
    full_letter = "\n".join(
        [
            draft.salutation,
            *draft.body_paragraphs,
            "Thank you for your time and consideration,",
            "Christian Estrada",
        ]
    )
    word_count = len(re.findall(r"\b[\w+.#'-]+\b", full_letter))
    specificity_warnings = cover.validate_cover_letter_specificity(
        full_letter,
        company_name,
        job_description,
        mode=normalized_mode,
    )
    min_words, max_words = cover.cover_letter_word_range(normalized_mode)
    preferred_min_words, preferred_max_words = cover.preferred_cover_word_range(normalized_mode)

    print("Cover Letter Slot Preview")
    print(f"  Company: {company_name}")
    print(f"  Role: {role_title}")
    print(f"  Resume: {resume_docx.name}")
    print(f"  Mode: {normalized_mode}")
    print(f"  Salutation: {draft.salutation}")
    print()
    print("Extracted Slots")
    print(f"  Mission: {truncate(draft.signals.company_mission, 100)}")
    print(f"  Role function: {truncate(draft.signals.role_core_function, 100)}")
    print(f"  Top accomplishment: {truncate(draft.signals.top_accomplishment, 100)}")
    print(f"  JD skill terms: {', '.join(draft.signals.jd_skill_terms) or 'none'}")
    print(f"  Ambiguity process: {truncate(draft.signals.ambiguity_process, 100)}")
    print(f"  Test environments: {', '.join(draft.signals.jd_test_environments) or 'none'}")
    print(f"  Partner functions: {', '.join(cover.display_partner_functions(draft.signals.partner_functions)) or 'none'}")
    print(f"  Communication metric: {truncate(draft.signals.communication_metric, 100)}")
    print(f"  Pain area: {truncate(draft.signals.jd_pain_area, 100)}")
    print()
    print("Draft Shape")
    print(f"  Body paragraphs: {draft.paragraph_shape}")
    print(f"  Proof-mapped terms: {', '.join(draft.proof_mapped_terms) or 'none'}")
    print(f"  Close-mapped terms: {', '.join(draft.close_mapped_terms) or 'none'}")
    print()
    print("Body Preview")
    for index, paragraph in enumerate(draft.body_paragraphs, 1):
        print(f"  P{index}: {truncate(paragraph, 110)}")
    print()
    print("Estimated Length")
    print(f"  Words: {word_count}")
    print(f"  Target: {'PASS' if min_words <= word_count <= max_words else 'FAIL'} ({min_words} to {max_words} words)")
    print(f"  Preferred: {'PASS' if preferred_min_words <= word_count <= preferred_max_words else 'CHECK'} ({preferred_min_words} to {preferred_max_words} words)")
    if specificity_warnings:
        print()
        print("WARNING: Specificity Issues")
        for warning in specificity_warnings:
            print(f"  - {warning}")
    print(f"\nElapsed: {time.monotonic() - started:.2f}s")
    return 0


def print_ci_instructions() -> int:
    print("CI Validation")
    print()
    print("Local smoke test:")
    print("  python tasks.py validate")
    print()
    print("Local GitHub Actions workflow with act, if installed:")
    print("  act push -W .github/workflows/smoke_test.yml")
    print()
    print("GitHub-hosted workflow:")
    print("  Push a commit or open/update a pull request. The workflow runs on every branch.")
    print()
    print("Pre-commit hook:")
    print("  pip install pre-commit")
    print("  pre-commit install")
    print("  pre-commit run --all-files")
    print()
    print("The CI workflow and pre-commit hook both run: python scripts/smoke_test.py")
    return 0


def run_jd_check() -> int:
    if not validate_job_description():
        return 1
    build_resume = load_build_resume()
    job_description = JOB_DESCRIPTION.read_text(encoding="utf-8-sig").strip()
    warning_count = build_resume._check_job_description_quality(job_description)
    print(f"JD quality check complete: {warning_count} warning(s).")
    return 0


def run_business_context_check() -> int:
    if not validate_job_description():
        return 1
    job_description = JOB_DESCRIPTION.read_text(encoding="utf-8-sig")
    for line in business_context.business_context_check_lines(job_description):
        print(line)
    questions = business_context.business_interview_questions(job_description, limit=5)
    print()
    print("Business-Related Interview Questions")
    for item in questions:
        print(f"- {item.question}")
        print(f"  Hidden concern: {item.hidden_concern}")
        print(f"  Ask back: {item.ask_back}")
    return 0


def run_align() -> int:
    started = time.monotonic()
    if not validate_job_description():
        return 1

    build_resume = load_build_resume()
    job_description = JOB_DESCRIPTION.read_text(encoding="utf-8-sig").strip()
    job_description = build_resume.validate_inputs(job_description)
    selected_resume = build_resume.choose_resume(job_description)
    resume_text = docx_visible_text(selected_resume)
    report = build_resume.alignment_score_report(job_description, resume_text)
    decision, actions = build_resume.alignment_gate_decision(
        int(report["total_score"]),
        report,
        job_description,
        build_resume.extract_output_name(job_description),
    )
    keywords = build_resume.audit_keywords(job_description)
    missing_keywords = sorted(
        (
            keyword
            for keyword in keywords
            if coverage_status(keyword, resume_text) == "MISSING"
        ),
        key=lambda keyword: (term_occurrences(job_description, keyword), len(keyword.split()), len(keyword), keyword),
        reverse=True,
    )[:5]

    print("Alignment Score Report")
    print(f"  Source: {selected_resume.name}")
    print(f"  Score: {report['total_score']}/{report['score_scale_max']}")
    print(f"  Grade: {report['grade']}")
    print(f"  Gate: {decision}")
    print(f"  Keyword coverage: {report['keyword_coverage']['score']}/30 ({report['keyword_coverage']['covered']}/{report['keyword_coverage']['total_keywords']})")
    print(f"  Lane fit: {report['lane_fit']['score']}/25 (direct={report['lane_fit']['direct']}, unsupported={report['lane_fit']['unsupported']})")
    print(f"  Specialty fit: {report['specialty_fit']['score']}/15")
    print(f"  Business context: {report['business_context']['score']}/25")
    print(f"  Outcome density: {report['outcome_density']['score']}/20")
    print()
    print("Top Missing Keywords")
    if missing_keywords:
        for keyword in missing_keywords:
            print(f"  - {keyword}")
    else:
        print("  - None")
    print()
    print("Recommended Actions")
    for action in actions[:5]:
        print(f"  - {action}")
    print(f"\nElapsed: {time.monotonic() - started:.2f}s")
    return 0


def run_ats_check() -> int:
    started = time.monotonic()
    if not validate_job_description():
        return 1

    build_resume = load_build_resume()
    job_description = JOB_DESCRIPTION.read_text(encoding="utf-8-sig").strip()
    job_description = build_resume.validate_inputs(job_description)
    company_name = build_resume.extract_output_name(job_description)
    resume_matches = matching_resume_outputs(build_resume, job_description)
    if not resume_matches:
        print(
            "No matching resume exists in output/ for "
            f"{build_resume.extract_output_target_name(job_description)}. Run python tasks.py resume first."
        )
        return 1

    resume_docx = resume_matches[0]
    report = build_resume.ats_plain_text_validation(resume_docx)
    blockers = report.get("blockers", [])
    warnings = report.get("warnings", [])
    word_count = report.get("word_count", 0)

    print("ATS Plain-Text Check")
    print(f"  Resume: {resume_docx.name}")
    print(f"  Word count: {word_count}")
    print()
    print("Blocking Issues")
    if isinstance(blockers, list) and blockers:
        for item in blockers:
            print(f"  - {item}")
    else:
        print("  - None")
    print()
    print("Warnings")
    if isinstance(warnings, list) and warnings:
        for item in warnings:
            print(f"  - {item}")
    else:
        print("  - None")

    print(f"\nElapsed: {time.monotonic() - started:.2f}s")
    return 1 if blockers else 0


def should_auto_archive_command(command_name: str) -> bool:
    return command_name in COMMERCIAL_AUTO_ARCHIVE_COMMANDS


def archive_environment_for_command(command_name: str) -> dict[str, str]:
    env = os.environ.copy()
    if not should_auto_archive_command(command_name):
        return env
    import job_context_archive

    snapshot = job_context_archive.archive_active_context(
        workflow_type="commercial",
        source_command=command_name,
        archive_reason="command_auto_archive",
    )
    env[job_context_archive.SNAPSHOT_ID_ENV] = snapshot.snapshot_id
    env[job_context_archive.SNAPSHOT_PATH_ENV] = str(snapshot.path)
    env[job_context_archive.SOURCE_COMMAND_ENV] = command_name
    env[job_context_archive.WORKFLOW_TYPE_ENV] = "commercial"
    questions_label = f"{snapshot.question_count} active question(s)" if snapshot.questions_present else "no active application questions"
    print(f"Job context snapshot: {snapshot.snapshot_id} ({questions_label})")
    return env


def run_task(command_name: str, task: Task, extra_args: tuple[str, ...]) -> int:
    if task.needs_job_description and not validate_job_description():
        return 1
    try:
        env = archive_environment_for_command(command_name)
    except Exception as error:  # noqa: BLE001
        print(f"Could not archive the active job context before running {command_name}: {error}")
        return 1
    command = (sys.executable, *task.args, *extra_args)
    result = subprocess.run(command, cwd=PROJECT_ROOT, env=env)
    return result.returncode


def main() -> int:
    if len(sys.argv) < 2:
        print_help()
        return 0
    command = sys.argv[1].lower()
    if command == "help":
        print_help()
        return 0
    if command == "commands":
        if sys.argv[2:]:
            print("The commands command does not accept extra arguments.")
            return 1
        return print_command_inventory()
    if command == "morning":
        if sys.argv[2:]:
            print("The morning command does not accept extra arguments.")
            return 1
        return run_morning()
    if command == "business-context-check":
        if sys.argv[2:]:
            print("The business-context-check command does not accept extra arguments.")
            return 1
        return run_business_context_check()
    if command == "align":
        if sys.argv[2:]:
            print("The align command does not accept extra arguments.")
            return 1
        return run_align()
    if command == "ats-check":
        if sys.argv[2:]:
            print("The ats-check command does not accept extra arguments.")
            return 1
        return run_ats_check()
    if command == "ci":
        if sys.argv[2:]:
            print("The ci command does not accept extra arguments.")
            return 1
        return print_ci_instructions()
    if command == "check":
        if sys.argv[2:]:
            print("The check command does not accept extra arguments.")
            return 1
        return run_check()
    if command == "jd-check":
        if sys.argv[2:]:
            print("The jd-check command does not accept extra arguments.")
            return 1
        return run_jd_check()
    if command == "cover-check":
        if sys.argv[2:]:
            print("The cover-check command does not accept extra arguments.")
            return 1
        return run_cover_check()
    if command == "cover-long":
        print("Legacy note: long commercial cover letters have been retired. Running the standard one-page cover letter instead.")
    task = TASKS.get(command)
    if task is None:
        print(f"Unknown command: {command}")
        print()
        print_help()
        return 1
    return run_task(command, task, tuple(sys.argv[2:]))


if __name__ == "__main__":
    raise SystemExit(main())
