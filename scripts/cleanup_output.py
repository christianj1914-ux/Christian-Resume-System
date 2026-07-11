#!/usr/bin/env python3
"""Prompt-driven cleanup for stale output files and render folders."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta
from pathlib import Path

import cleanup_render_checks


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
TRACKER_CSV = PROJECT_ROOT / "scratch" / "applications.csv"
RENDER_CHECK_PATTERN = "render_check"
RENDER_CHECK_MAX_DAYS = 7
OUTPUT_MAX_DAYS = 60
PROTECTED_STATUSES = {"interview", "phone_screen", "final_round", "offer", "rejected"}


def ask(prompt: str) -> bool:
    answer = input(prompt + " [Y/N]: ").strip().lower()
    return answer == "y"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selective", action="store_true")
    return parser.parse_args(argv)


def normalize_company(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def age_in_days(path: Path) -> int:
    return max(0, (datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)).days)


def company_name_from_output_file(path: Path) -> str:
    stem = path.stem
    prefix = "Christian Estrada - "
    remainder = stem[len(prefix):] if stem.startswith(prefix) else stem
    parts = [part.strip() for part in remainder.split(" - ") if part.strip()]
    company = parts[0] if parts else remainder
    company = company.replace(" FAIL", "").replace(" POOR", "").strip()
    company = company.removesuffix(" Long Cover Letter").removesuffix(" Cover Letter").removesuffix(" Resume").strip()
    return company


def protected_company_keys() -> set[str]:
    if not TRACKER_CSV.exists():
        return set()
    protected: set[str] = set()
    with TRACKER_CSV.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            status = (row.get("current_status") or "").strip().lower()
            if status not in PROTECTED_STATUSES:
                continue
            company = normalize_company(row.get("company", ""))
            if company:
                protected.add(company)
    return protected


def find_stale_render_folders() -> list[Path]:
    original_project_root = cleanup_render_checks.PROJECT_ROOT
    original_render_root = cleanup_render_checks.RENDER_ROOT
    try:
        cleanup_render_checks.PROJECT_ROOT = PROJECT_ROOT
        cleanup_render_checks.RENDER_ROOT = PROJECT_ROOT / "render_check"
        return cleanup_render_checks.old_render_folders(RENDER_CHECK_MAX_DAYS * 24)
    finally:
        cleanup_render_checks.PROJECT_ROOT = original_project_root
        cleanup_render_checks.RENDER_ROOT = original_render_root


def find_stale_output_files() -> list[Path]:
    if not OUTPUT_DIR.exists():
        return []
    cutoff = datetime.now() - timedelta(days=OUTPUT_MAX_DAYS)
    protected = protected_company_keys()
    matches: list[Path] = []
    for path in sorted(OUTPUT_DIR.glob("*.docx")):
        if datetime.fromtimestamp(path.stat().st_mtime) >= cutoff:
            continue
        company_key = normalize_company(company_name_from_output_file(path))
        if company_key and company_key in protected:
            continue
        matches.append(path)
    return matches


def delete_render_folder(folder: Path) -> None:
    if not cleanup_render_checks.is_safe_render_folder(folder):
        print(f"Skipped unsafe render folder target: {folder}")
        raise SystemExit(1)
    errors = cleanup_render_checks.remove_tree(folder)
    if errors:
        print("Some render folder files could not be removed:")
        for error in errors:
            print(f"  {error}")
        raise SystemExit(1)
    print(f"Deleted: {folder.name}")


def delete_output_file(path: Path) -> None:
    path.unlink()
    print(f"Deleted: {path.name}")


def run_cleanup(*, selective: bool = False) -> None:
    stale_render_folders = find_stale_render_folders()
    stale_output_files = find_stale_output_files()

    if not stale_render_folders and not stale_output_files:
        print("Nothing to clean up. All output files and render folders are within retention limits.")
        return

    if stale_render_folders:
        print(f"Found {len(stale_render_folders)} render check folder(s) older than {RENDER_CHECK_MAX_DAYS} days:")
        for folder in stale_render_folders:
            print(f"  {folder.name} ({age_in_days(folder)} days old)")
        deleted_any = False
        if selective:
            for folder in stale_render_folders:
                if ask(f"Delete {folder.name}?"):
                    delete_render_folder(folder)
                    deleted_any = True
            if not deleted_any:
                print("Skipped render check cleanup.")
        elif ask("Delete all stale render check folders?"):
            for folder in stale_render_folders:
                delete_render_folder(folder)
            deleted_any = True
        else:
            print("Skipped render check cleanup.")

    if stale_output_files:
        print(
            f"Found {len(stale_output_files)} output file(s) older than {OUTPUT_MAX_DAYS} days with no active interview process:"
        )
        for path in stale_output_files:
            print(f"  {path.name} ({age_in_days(path)} days old)")
        deleted_any = False
        if selective:
            for path in stale_output_files:
                if ask(f"Delete {path.name} ({age_in_days(path)} days old)?"):
                    delete_output_file(path)
                    deleted_any = True
            if not deleted_any:
                print("Skipped output file cleanup.")
        elif ask("Delete all stale output files?"):
            for path in stale_output_files:
                delete_output_file(path)
            deleted_any = True
        else:
            print("Skipped output file cleanup.")


if __name__ == "__main__":
    arguments = parse_args()
    run_cleanup(selective=arguments.selective)
