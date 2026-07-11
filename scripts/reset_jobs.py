#!/usr/bin/env python3
"""Archive and clear job-search context files safely."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import build_resume
import job_context_archive


PROJECT_ROOT = Path(__file__).resolve().parents[1]
JOBS_DIR = PROJECT_ROOT / "jobs"
JOB_FILES = (
    "job_description.txt",
    "application_questions.txt",
    "company_research.txt",
    "interview_notes.txt",
    "debrief_history.txt",
)
DEBRIEF_DELIMITER = "POST-INTERVIEW DEBRIEF CAPTURED"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Archive and clear job-search context files.")
    parser.add_argument("--archive-only", action="store_true", help="Archive non-empty jobs files without clearing anything.")
    parser.add_argument("--clear", action="store_true", help="Archive, then clear the active job description and application questions.")
    parser.add_argument("--full-clear", action="store_true", help="Archive, then clear all job context files.")
    parser.add_argument("--list-archives", action="store_true", help="List prior jobs archives newest first.")
    args = parser.parse_args()
    selected = sum(bool(value) for value in (args.archive_only, args.clear, args.full_clear, args.list_archives))
    if selected > 1:
        parser.error("choose only one mode")
    return args


def file_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig")


def archive_current_jobs() -> Path:
    snapshot = job_context_archive.archive_active_context(
        workflow_type="commercial",
        source_command="reset-jobs",
        archive_reason="reset_jobs_archive",
    )
    copied = 1 + int(snapshot.questions_present)
    for name in JOB_FILES:
        if name in {"job_description.txt", "application_questions.txt"}:
            continue
        source = JOBS_DIR / name
        if source.exists() and source.read_text(encoding="utf-8-sig").strip():
            shutil.copy2(source, snapshot.path / name)
            copied += 1
    print(f"Archived {copied} non-empty job file(s) to: {snapshot.path}")
    return snapshot.path


def debrief_entry_count(path: Path) -> int:
    text = file_text(path)
    return text.count(DEBRIEF_DELIMITER)


def print_file_state(path: Path, cleared: bool = False) -> None:
    if cleared:
        print(f"Cleared: {path.name}")
        return
    if path.name == "debrief_history.txt":
        print(f"Preserved: {path.name} ({debrief_entry_count(path)} entries)")
        return
    if path.exists() and path.read_text(encoding="utf-8-sig").strip():
        print(f"Preserved: {path.name} (non-empty)")
    else:
        print(f"Preserved: {path.name} (empty or missing)")


def clear_files(names: tuple[str, ...]) -> None:
    JOBS_DIR.mkdir(exist_ok=True)
    for name in names:
        path = JOBS_DIR / name
        path.write_text("", encoding="utf-8")
        print_file_state(path, cleared=True)
    for name in JOB_FILES:
        if name not in names:
            print_file_state(JOBS_DIR / name)


def list_archives() -> None:
    rows = job_context_archive.read_index()
    if not rows:
        print("No job archives found.")
        return
    for row in rows:
        archive = job_context_archive.snapshot_dir(row.get("snapshot_id", ""))
        job_text = job_context_archive.job_description_text_for_row(row)
        company = build_resume.extract_company_name(job_text) or row.get("company", "") or "Unknown company"
        role = row.get("role", "") or "Unknown role"
        print(f"{row.get('snapshot_id', '')} | {company} | {role} | {archive}")


def current_state() -> None:
    print("Current jobs directory state:")
    for name in JOB_FILES:
        print_file_state(JOBS_DIR / name)


def interactive_mode() -> str:
    current_state()
    print()
    print("Choose mode: archive-only, clear, full-clear, list-archives, or cancel")
    choice = input("> ").strip().lower()
    aliases = {
        "archive": "archive-only",
        "archive-only": "archive-only",
        "clear": "clear",
        "full": "full-clear",
        "full-clear": "full-clear",
        "list": "list-archives",
        "list-archives": "list-archives",
        "cancel": "cancel",
        "": "cancel",
    }
    return aliases.get(choice, "cancel")


def run_mode(mode: str) -> int:
    if mode == "list-archives":
        list_archives()
        return 0
    if mode == "cancel":
        print("No changes made.")
        return 0

    archive_current_jobs()
    if mode == "archive-only":
        for name in JOB_FILES:
            print_file_state(JOBS_DIR / name)
        return 0
    if mode == "clear":
        clear_files(("job_description.txt", "application_questions.txt"))
        return 0
    if mode == "full-clear":
        clear_files(JOB_FILES)
        return 0
    print(f"Unknown mode: {mode}")
    return 1


def main() -> int:
    args = parse_args()
    if args.list_archives:
        return run_mode("list-archives")
    if args.archive_only:
        return run_mode("archive-only")
    if args.clear:
        return run_mode("clear")
    if args.full_clear:
        return run_mode("full-clear")
    return run_mode(interactive_mode())


if __name__ == "__main__":
    raise SystemExit(main())
