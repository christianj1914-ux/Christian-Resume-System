#!/usr/bin/env python3
"""Capture structured post-interview notes and rebuild dossier outputs."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

import build_resume
import interview_context
import track_applications
from utils import agent_debug_log, companies_refer_to_same, fail, optional_text, read_text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
JOBS_DIR = PROJECT_ROOT / "jobs"
INTERVIEW_NOTES = JOBS_DIR / "interview_notes.txt"
DEBRIEF_HISTORY = JOBS_DIR / "debrief_history.txt"
COMPANY_RESEARCH = JOBS_DIR / "company_research.txt"
OUTCOMES = {"advance", "reject", "pending"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture, repair, or inspect structured post-interview debriefs.")
    parser.add_argument("--capture", action="store_true", help="Capture a new post-interview debrief.")
    parser.add_argument("--prepare-notes", action="store_true", help="Legacy alias for --prepare-company-notes.")
    parser.add_argument("--prepare-company-notes", action="store_true", help="Create/open the company dossier scaffold.")
    parser.add_argument("--repair-legacy", action="store_true", help="Back up and repair legacy debrief artifacts into structured round records.")
    parser.add_argument("--list", action="store_true", help="List captured debrief entries in reverse chronological order.")
    parser.add_argument("--company", metavar="COMPANY_NAME", help="Filter listed or searched debriefs by company name.")
    parser.add_argument("--round", metavar="ROUND_NUMBER", help="Round number for capture or dossier preparation.")
    parser.add_argument("--search", metavar="TERM", help="Search full debrief entries for a term and print matching entries.")
    parser.add_argument("--company-name", dest="company_name", help="Company name for non-interactive capture.")
    parser.add_argument("--role-title", dest="role_title", help="Role title for non-interactive capture.")
    parser.add_argument("--interview-date", dest="interview_date", help="Interview date for non-interactive capture.")
    parser.add_argument("--outcome", help="Outcome for non-interactive capture: advance, reject, or pending.")
    parser.add_argument("--raw-notes-file", help="Optional path to a raw note artifact to import into the round record.")
    parser.add_argument("--raw-notes-text", help="Optional raw notes text for non-interactive capture.")
    parser.add_argument("--import-review", help="Optional path to a DOCX or text performance review to import.")
    parser.add_argument("--story-followups", help="Optional newline-delimited story follow-up notes for non-interactive capture.")
    parser.add_argument("--unexpected-questions", help="Optional newline-delimited unexpected questions for non-interactive capture.")
    parser.add_argument("--role-language", help="Optional newline-delimited interviewer language notes for non-interactive capture.")
    parser.add_argument("--feedback-received", help="Optional newline-delimited feedback notes for non-interactive capture.")
    parser.add_argument("--company-intelligence", help="Optional newline-delimited company intelligence notes for non-interactive capture.")
    parser.add_argument("--no-prompt", action="store_true", help="Do not prompt for missing multiline sections when importing a round.")
    args = parser.parse_args()
    if not any((args.capture, args.prepare_notes, args.prepare_company_notes, args.repair_legacy, args.list, args.search)):
        args.capture = True
    if args.company and not any((args.prepare_notes, args.prepare_company_notes, args.repair_legacy, args.list, args.search, args.capture)):
        args.list = True
    return args


def safe_input(prompt: str) -> str:
    try:
        return input(prompt)
    except KeyboardInterrupt:
        print()
        fail("post-interview debrief capture canceled")
    except EOFError:
        fail("input ended before the debrief was complete")


def prompt_required(label: str, default: str = "") -> str:
    while True:
        suffix = f" [{default}]" if default else ""
        value = safe_input(f"{label}{suffix}: ").strip() or default
        if value:
            return value
        print(f"{label} is required.")


def prompt_optional(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = safe_input(f"{label}{suffix}: ").strip()
    return value or default


def prompt_outcome(default: str = "") -> str:
    while True:
        suffix = f" [{default}]" if default else ""
        outcome = safe_input(f"Outcome (advance/reject/pending){suffix}: ").strip().lower() or default.lower()
        if outcome in OUTCOMES:
            return outcome
        print("Please enter advance, reject, or pending.")


def prompt_multiline(label: str, default: str = "") -> str:
    print()
    print(label)
    print("Enter one or more lines. Leave a blank line when finished.")
    if default.strip():
        print("Press Enter twice to keep the prefilled value.")
    lines: list[str] = []
    while True:
        line = safe_input("> ")
        if not line.strip():
            break
        lines.append(line.rstrip())
    if lines:
        return "\n".join(lines).strip()
    return default.strip()


def active_job_context() -> tuple[str, str]:
    job_description = read_text(PROJECT_ROOT / "jobs" / "job_description.txt")
    company_name = build_resume.extract_output_name(job_description)
    role_title = build_resume.extract_job_title(job_description) or ""
    return company_name, role_title


def active_job_company_name(job_description: str) -> str | None:
    company_name = build_resume.extract_company_name(job_description)
    if company_name:
        return company_name
    try:
        return build_resume.extract_output_name(job_description)
    except SystemExit:
        return None


def debrief_matches_active_job(debrief_company: str, job_description: str) -> bool:
    active_company = active_job_company_name(job_description)
    if not active_company:
        return False
    return companies_refer_to_same(debrief_company, active_company)


def truncate(value: str, limit: int = 120) -> str:
    cleaned = " ".join(value.strip().split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(0, limit - 3)].rstrip() + "..."


def _read_optional_artifact(path_value: str) -> str:
    if not path_value.strip():
        return ""
    path = Path(path_value.strip().strip('"'))
    return interview_context.read_artifact_text(path)


def _read_optional_raw_notes_file(path_value: str) -> str:
    if not path_value.strip():
        return ""
    path = Path(path_value.strip().strip('"'))
    return interview_context.read_artifact_text(path)


def _noninteractive_capture(args: argparse.Namespace) -> bool:
    return bool(
        args.no_prompt
        or (
            args.company_name
            and args.interview_date
            and args.outcome
            and any(
                (
                    args.raw_notes_file,
                    args.raw_notes_text,
                    args.import_review,
                    args.story_followups,
                    args.unexpected_questions,
                    args.role_language,
                    args.feedback_received,
                    args.company_intelligence,
                )
            )
        )
    )


def collect_debrief(args: argparse.Namespace) -> dict[str, object]:
    print("Post-interview debrief capture")
    print("This tool stores one structured round record, rebuilds the company dossier, and regenerates legacy text exports.")
    print()
    default_company, default_role = active_job_context()
    noninteractive = _noninteractive_capture(args)
    company_name = args.company_name or (default_company if noninteractive else prompt_required("Company name", default_company))
    role_title = args.role_title or (default_role if noninteractive else prompt_required("Role title", default_role))
    interview_date = args.interview_date or ("" if noninteractive else prompt_required("Interview date"))
    round_number = args.round if args.round is not None else ("" if noninteractive else prompt_optional("Round number"))
    outcome = args.outcome.lower() if args.outcome else ("pending" if noninteractive else prompt_outcome())
    if args.outcome and outcome not in OUTCOMES:
        fail("Outcome must be advance, reject, or pending.")
    if noninteractive and not company_name:
        fail("Company name is required for non-interactive debrief import.")
    if noninteractive and not interview_date:
        fail("Interview date is required for non-interactive debrief import.")
    if noninteractive and outcome not in OUTCOMES:
        fail("Outcome must be advance, reject, or pending for non-interactive debrief import.")

    raw_notes = _read_optional_raw_notes_file(args.raw_notes_file or "")
    if not raw_notes and args.raw_notes_text:
        raw_notes = args.raw_notes_text.strip()
    if not raw_notes and not noninteractive:
        raw_notes = prompt_multiline("Paste raw notes from this round, including interviewer names, systems, tools, concerns, or next-step timing")

    story_followups = args.story_followups.strip() if args.story_followups else ("" if noninteractive else prompt_multiline("Which stories generated follow-up questions?"))
    unexpected_questions = args.unexpected_questions.strip() if args.unexpected_questions else ("" if noninteractive else prompt_multiline("Which questions were unexpected?"))
    role_language = args.role_language.strip() if args.role_language else ("" if noninteractive else prompt_multiline("What specific language did the interviewer use about the role?"))
    feedback_received = args.feedback_received.strip() if args.feedback_received else ("" if noninteractive else prompt_multiline("What feedback was received?"))
    company_intelligence = args.company_intelligence.strip() if args.company_intelligence else ("" if noninteractive else prompt_multiline("What insider company intelligence was learned?"))

    imported_review_path = args.import_review or ("" if noninteractive else prompt_optional("Imported performance review file path (optional)"))
    imported_review_text = _read_optional_artifact(imported_review_path)
    imported_artifacts = [str(Path(imported_review_path).resolve())] if imported_review_path.strip() else []

    return {
        "company_name": company_name,
        "role_title": role_title,
        "interview_date": interview_date,
        "round_number": round_number,
        "outcome": outcome,
        "raw_notes": raw_notes,
        "story_followups": story_followups,
        "unexpected_questions": unexpected_questions,
        "role_language": role_language,
        "feedback_received": feedback_received,
        "company_intelligence": company_intelligence,
        "imported_review_text": imported_review_text,
        "imported_artifacts": imported_artifacts,
    }


def upsert_round_record(data: dict[str, object]) -> tuple[dict[str, object], Path]:
    record_path = interview_context.structured_debrief_path(
        JOBS_DIR,
        str(data.get("company_name", "")),
        str(data.get("interview_date", "")),
        str(data.get("round_number", "")),
        str(data.get("role_title", "")),
    )
    if record_path.exists():
        existing = json.loads(record_path.read_text(encoding="utf-8"))
        merged = interview_context.merge_round_records(existing, data)
    else:
        merged = interview_context.normalize_round_record(data)
    saved_path = interview_context.save_round_record(JOBS_DIR, merged)
    return merged, saved_path


def update_tracker_from_debrief(data: dict[str, object]) -> None:
    outcome = str(data.get("outcome", "")).strip().lower()
    if outcome == "advance":
        status = "interview"
    elif outcome == "reject":
        status = "rejected"
    elif outcome == "pending":
        status = ""
    else:
        print(f"WARNING: unrecognized debrief outcome '{outcome}'. Tracker not updated.")
        return
    note_parts = []
    feedback = interview_context._split_lines(data.get("feedback_received", []))
    role_language = interview_context._split_lines(data.get("role_language", []))
    company_intelligence = interview_context._split_lines(data.get("company_intelligence", []))
    if feedback:
        note_parts.append(f"Feedback: {'; '.join(feedback[:3])}")
    if role_language:
        note_parts.append(f"Role language: {'; '.join(role_language[:3])}")
    if company_intelligence:
        note_parts.append(f"Intel: {'; '.join(company_intelligence[:3])}")
    note_body = "; ".join(note_parts) if note_parts else "No notes captured."
    updates = {
        "last_round": str(data.get("round_number", "")),
        "outcome": "" if outcome == "pending" else outcome,
        "notes": f"Latest debrief {data.get('interview_date', '')}: {truncate(note_body)}",
    }
    if status:
        updates["current_status"] = status
    base_row = None
    job_description = optional_text(PROJECT_ROOT / "jobs" / "job_description.txt")
    active_company = active_job_company_name(job_description) if job_description else None
    matches_active = debrief_matches_active_job(str(data.get("company_name", "")), job_description) if job_description else False
    agent_debug_log(
        "post_interview_debrief.py:update_tracker_from_debrief",
        "debrief tracker match evaluation",
        {
            "debrief_company": str(data.get("company_name", "")),
            "active_company": active_company or "",
            "matches_active": matches_active,
        },
        hypothesis_id="A",
    )
    # Full row metadata depends on row_for_active_job(), which only reflects the
    # currently active JD. If the debrief company does not match that active JD,
    # this pass preserves the existing archived-JD behavior and only applies the
    # lightweight tracker update below.
    if not matches_active:
        print(
            "WARNING: debrief company does not match the active job description. "
            "Tracker status and notes will update, but full row metadata will not refresh in this pass."
        )
    if matches_active:
        try:
            base_row = track_applications.row_for_active_job(
                status=status or "draft",
                notes=updates["notes"],
            )
        except ValueError as error:
            agent_debug_log(
                "post_interview_debrief.py:update_tracker_from_debrief",
                "row_for_active_job failed",
                {"error": str(error)},
                hypothesis_id="A",
            )
            base_row = None
    action = track_applications.upsert_application(str(data.get("company_name", "")), str(data.get("role_title", "")), updates, base_row)
    print(f"Application tracker {action.lower()} from debrief.")


def print_summary(record: dict[str, object], record_path: Path, dossier_path: Path) -> None:
    print()
    print("Captured debrief summary")
    print(f"Company: {record.get('company_name', '')}")
    print(f"Role: {record.get('role_title', '') or 'None supplied.'}")
    print(f"Interview date: {record.get('interview_date', '')}")
    print(f"Round: {record.get('round_number', '') or 'None supplied.'}")
    print(f"Outcome: {record.get('outcome', '')}")
    print(f"Structured round updated: {record_path}")
    print(f"Company dossier updated: {dossier_path}")
    print(f"Legacy debrief history regenerated: {DEBRIEF_HISTORY}")
    print(f"Legacy company research regenerated: {COMPANY_RESEARCH}")
    print()
    print("Reminder: rerun the standard cheat sheet or detailed guide scripts to incorporate the new intelligence and coaching signals.")


def capture_debrief(args: argparse.Namespace) -> None:
    data = collect_debrief(args)
    record, record_path = upsert_round_record(data)
    interview_context.rebuild_company_dossiers(JOBS_DIR)
    interview_context.rebuild_legacy_exports(JOBS_DIR)
    update_tracker_from_debrief(record)
    print_summary(record, record_path, interview_context.company_dossier_path(JOBS_DIR, str(record.get("company_name", ""))))


def prepare_company_notes(args: argparse.Namespace) -> None:
    default_company, default_role = active_job_context()
    company_name = args.company_name or prompt_required("Company name", default_company)
    role_title = args.role_title or prompt_optional("Role title", default_role)
    round_text = args.round if args.round is not None else prompt_optional("Round number")
    path = interview_context.prepare_company_dossier(JOBS_DIR, company_name, role_title, round_text)
    print(f"Company dossier: {path}")
    try:
        subprocess.Popen(["notepad.exe", str(path)])
    except OSError:
        print("Open the company dossier above and paste the notes into the round section.")


def repair_legacy() -> None:
    result = interview_context.repair_legacy_interview_data(JOBS_DIR)
    print("Legacy interview artifacts repaired.")
    print(f"Backup folder: {result['backup_dir']}")
    print(f"Items backed up: {len(result['backed_up_items'])}")
    print(f"Structured records written: {result['records_written']}")
    print(f"Company dossiers written: {result['dossiers_written']}")


def list_debriefs(company_name: str = "") -> list[dict[str, object]]:
    return interview_context.load_round_records(JOBS_DIR, company_name)


def print_debrief_list(entries: list[dict[str, object]]) -> None:
    if not entries:
        print("No debrief entries found.")
        return
    for entry in entries:
        review = entry.get("performance_review", {})
        if isinstance(review, dict):
            summary = str(review.get("summary", ""))
        else:
            summary = ""
        print(
            " | ".join(
                (
                    truncate(str(entry.get("interview_date", "")), 20),
                    truncate(str(entry.get("company_name", "")), 28),
                    truncate(str(entry.get("round_number", "")) or "general", 12),
                    truncate(str(entry.get("outcome", "")), 12),
                    truncate(summary or "; ".join(interview_context._split_lines(entry.get("story_followups", []))) or "No summary", 80),
                )
            )
        )


def search_debriefs(term: str, company_name: str = "") -> list[str]:
    needle = term.lower()
    matches: list[str] = []
    for record in list_debriefs(company_name):
        entry_text = interview_context.record_to_debrief_entry(record)
        if needle in entry_text.lower():
            matches.append(entry_text)
    return matches


def print_search_results(entries: list[str]) -> None:
    if not entries:
        print("No matching debrief entries found.")
        return
    for index, entry in enumerate(entries):
        if index:
            print()
            print("-" * 72)
            print()
        print(entry)


def main() -> None:
    args = parse_args()
    if args.prepare_notes or args.prepare_company_notes:
        prepare_company_notes(args)
        return
    if args.repair_legacy:
        repair_legacy()
        return
    if args.search:
        print_search_results(search_debriefs(args.search, args.company or ""))
        return
    if args.list:
        print_debrief_list(list_debriefs(args.company or ""))
        if not args.capture:
            return
    if args.capture:
        capture_debrief(args)


if __name__ == "__main__":
    main()
