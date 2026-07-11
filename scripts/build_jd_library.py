#!/usr/bin/env python3
"""Archive job descriptions and summarize cross-JD patterns."""

from __future__ import annotations

import argparse
from collections import Counter

import job_context_archive
import resume_analysis


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Archive and analyze job descriptions.")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("archive", help="Archive the active job description and active application questions.")
    subparsers.add_parser("list", help="List archived job-context snapshots.")
    search = subparsers.add_parser("search", help="Search archived job descriptions.")
    search.add_argument("term")
    subparsers.add_parser("patterns", help="Print lane and keyword patterns across the archive.")
    args = parser.parse_args()
    if not args.command:
        args.command = "list"
    return args


def archive_current() -> int:
    try:
        snapshot = job_context_archive.archive_active_context(
            workflow_type="commercial",
            source_command="jd-archive",
            archive_reason="manual_archive",
        )
    except ValueError:
        print("No active job description to archive.")
        return 1
    print(f"Archived job context snapshot: {snapshot.snapshot_id}")
    print(f"Snapshot folder: {snapshot.path}")
    if snapshot.questions_present:
        print(f"Active application questions archived: yes ({snapshot.question_count})")
    else:
        print("Active application questions archived: no")
    return 0


def list_entries() -> int:
    rows = job_context_archive.read_index()
    if not rows:
        print("No archived job descriptions found.")
        return 0
    for row in rows:
        print(
            f"{row['created_at']} | {row['company']} | {row['role']} | {row['lane']} | "
            f"{row['snapshot_id']} | questions={row['questions_present']}"
        )
    return 0


def search_entries(term: str) -> int:
    term_lower = term.lower()
    found = False
    for row in job_context_archive.read_index():
        text = job_context_archive.job_description_text_for_row(row)
        if term_lower in text.lower() or term_lower in row.get("company", "").lower() or term_lower in row.get("role", "").lower():
            print(
                f"{row['created_at']} | {row['company']} | {row['role']} | {row['snapshot_id']} | "
                f"questions={row['questions_present']}"
            )
            found = True
    if not found:
        print("No matching archived job descriptions found.")
    return 0


def pattern_summary() -> int:
    rows = job_context_archive.read_index()
    if not rows:
        print("No archived job descriptions found.")
        return 0
    lane_counts = Counter(row.get("lane", "unknown") for row in rows)
    keyword_counts: Counter[str] = Counter()
    for row in rows:
        text = job_context_archive.job_description_text_for_row(row)
        if text:
            keyword_counts.update(resume_analysis.audit_keywords(text))
    print("Lane patterns:")
    for lane, count in lane_counts.most_common():
        print(f"  {lane}: {count}")
    print("Top recurring keywords:")
    for keyword, count in keyword_counts.most_common(15):
        print(f"  {keyword}: {count}")
    return 0


def main() -> int:
    args = parse_args()
    if args.command == "archive":
        return archive_current()
    if args.command == "search":
        return search_entries(args.term)
    if args.command == "patterns":
        return pattern_summary()
    return list_entries()


if __name__ == "__main__":
    raise SystemExit(main())
