#!/usr/bin/env python3
"""Maintain a CSV tracker for job applications and outcomes."""

from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path
import re

import job_context_archive
import resume_analysis
from utils import companies_refer_to_same


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRATCH_DIR = PROJECT_ROOT / "scratch"
TRACKER = SCRATCH_DIR / "applications.csv"
JOB_DESCRIPTION = PROJECT_ROOT / "jobs" / "job_description.txt"
OUTPUT_DIR = PROJECT_ROOT / "output"
JD_LIBRARY_DIR = SCRATCH_DIR / "jd_library"
JD_LIBRARY_INDEX = JD_LIBRARY_DIR / "index.csv"

COLUMNS = (
    "date_added",
    "company",
    "role_title",
    "lane_label",
    "fit_status",
    "audit_flag",
    "source_resume",
    "output_file",
    "snapshot_id",
    "applied_date",
    "current_status",
    "last_round",
    "outcome",
    "notes",
)
VALID_STATUSES = {"draft", "applied", "phone_screen", "interview", "final_round", "offer", "rejected", "withdrawn"}
STATUS_PRECEDENCE = {
    "draft": 0,
    "applied": 1,
    "phone_screen": 2,
    "interview": 3,
    "final_round": 4,
    "offer": 5,
    "rejected": 6,
    "withdrawn": 6,
}
KNOWN_LANE_LABELS = {
    *(str(lane["label"]) for lane in resume_analysis.TARGETING_LANES),
    str(resume_analysis.CORPORATE_STRATEGY_PROFILE["label"]),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Track job applications.")
    subparsers = parser.add_subparsers(dest="command")
    add = subparsers.add_parser("add", help="Add the active job as an application row.")
    add.add_argument("--applied-date", default="", help="Date applied, YYYY-MM-DD.")
    add.add_argument("--status", default="draft", choices=sorted(VALID_STATUSES), help="Current application status.")
    add.add_argument("--notes", default="", help="Optional notes.")

    update = subparsers.add_parser("update", help="Update the most recent row matching a company.")
    update.add_argument("company")
    update.add_argument("--status", choices=sorted(VALID_STATUSES))
    update.add_argument("--applied-date")
    update.add_argument("--last-round")
    update.add_argument("--outcome")
    update.add_argument("--notes")

    refresh = subparsers.add_parser("refresh", help="Refresh lane and fit metadata from current or archived job descriptions.")
    refresh.add_argument("--force", action="store_true", help="Recalculate lane and fit even when a row already has values.")

    subparsers.add_parser("list", help="List application rows.")
    subparsers.add_parser("report", help="Print a status summary.")
    args = parser.parse_args()
    if not args.command:
        args.command = "list"
    return args


def read_rows() -> list[dict[str, str]]:
    if not TRACKER.exists():
        return []
    with TRACKER.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return [canonicalize_row(row) for row in rows]


def write_rows(rows: list[dict[str, str]]) -> None:
    SCRATCH_DIR.mkdir(exist_ok=True)
    with TRACKER.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(canonicalize_row(row))


def read_job_description() -> str:
    return JOB_DESCRIPTION.read_text(encoding="utf-8-sig").strip() if JOB_DESCRIPTION.exists() else ""


def latest_resume(job_description: str) -> Path | None:
    candidates = resume_analysis.matching_output_files(OUTPUT_DIR, job_description, "Resume.docx")
    return candidates[0] if candidates else None


def derive_audit_flag(output_file: str | Path | None) -> str:
    state = resume_analysis.output_audit_state(output_file)
    return "" if state == "PASS" else state


def canonicalize_row(row: dict[str, str]) -> dict[str, str]:
    normalized = {column: row.get(column, "") for column in COLUMNS}
    lane_label = (normalized.get("lane_label") or "").strip()
    fit_status = (normalized.get("fit_status") or "").strip()
    if not lane_label and fit_status in KNOWN_LANE_LABELS:
        lane_label = fit_status
        fit_status = ""
    normalized["lane_label"] = lane_label
    normalized["fit_status"] = fit_status
    if not (normalized.get("audit_flag") or "").strip():
        normalized["audit_flag"] = derive_audit_flag(normalized.get("output_file", ""))
    return normalized


def normalize_role_key(value: str) -> str:
    lowered = re.sub(r"\s+", " ", (value or "").strip().lower())
    lowered = re.sub(r"^(?:job title|role title|role)\s*[:\-]?\s*", "", lowered)
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s+", " ", lowered).strip()


def roles_refer_to_same(left: str, right: str) -> bool:
    left_key = normalize_role_key(left)
    right_key = normalize_role_key(right)
    if not left_key or not right_key:
        return False
    return left_key == right_key or left_key in right_key or right_key in left_key


def read_jd_library_rows() -> list[dict[str, str]]:
    return job_context_archive.read_index()


def row_job_description_text(row: dict[str, str]) -> str:
    current_job_description = read_job_description()
    if current_job_description:
        current_company = resume_analysis.extract_output_name(current_job_description)
        current_role = resume_analysis.extract_job_title(current_job_description) or ""
        if companies_refer_to_same(row.get("company", ""), current_company) and roles_refer_to_same(row.get("role_title", ""), current_role):
            return current_job_description

    snapshot_id = row.get("snapshot_id", "").strip()
    if snapshot_id:
        archived = job_context_archive.snapshot_job_description_text(snapshot_id)
        if archived:
            return archived

    for item in read_jd_library_rows():
        if not companies_refer_to_same(row.get("company", ""), item.get("company", "")):
            continue
        if not roles_refer_to_same(row.get("role_title", ""), item.get("role", "")):
            continue
        archived = job_context_archive.job_description_text_for_row(item)
        if archived:
            return archived
    return ""


def refresh_row_metadata(row: dict[str, str], *, force: bool = False) -> tuple[dict[str, str], bool]:
    normalized = canonicalize_row(row)
    needs_lane = force or not normalized.get("lane_label", "").strip()
    needs_fit = force or not normalized.get("fit_status", "").strip()
    if not (needs_lane or needs_fit):
        return normalized, False

    output_value = normalized.get("output_file", "").strip()
    if not output_value:
        return normalized, False
    output_path = Path(output_value)
    if not output_path.exists():
        company = normalized.get("company", "unknown company")
        role = normalized.get("role_title", "unknown role")
        print(f"SKIPPED refresh: output file not found for {company} - {role}.")
        return normalized, False

    job_description = row_job_description_text(normalized)
    if not job_description:
        company = normalized.get("company", "unknown company")
        role = normalized.get("role_title", "unknown role")
        print(
            f"SKIPPED refresh: no current or archived JD found for {company} - {role}. "
            "Recent commercial runs auto-archive job context, but this row has no matching snapshot. "
            "Archive the active JD with 'python tasks.py jd-archive' before the next posting replaces it."
        )
        return normalized, False

    try:
        import build_resume
    except Exception:
        return normalized, False

    resume_text = build_resume.docx_visible_text_from_path(output_path)
    changed = False
    if needs_lane:
        profile = resume_analysis.job_problem_profile(job_description, resume_text)
        lane_label = str(profile.lane_label).strip()
        if lane_label and lane_label != normalized.get("lane_label", ""):
            normalized["lane_label"] = lane_label
            changed = True
    if needs_fit:
        fit_status = active_job_fit_status(job_description, output_path)
        if fit_status and fit_status != normalized.get("fit_status", ""):
            normalized["fit_status"] = fit_status
            changed = True
    return normalized, changed


def refresh_metadata(force: bool = False) -> tuple[int, int]:
    rows = read_rows()
    updated = 0
    unchanged = 0
    refreshed_rows: list[dict[str, str]] = []
    for row in rows:
        refreshed, changed = refresh_row_metadata(row, force=force)
        refreshed_rows.append(refreshed)
        if changed:
            updated += 1
        else:
            unchanged += 1
    write_rows(refreshed_rows)
    return updated, unchanged


def tracker_lane_label(row: dict[str, str]) -> str:
    row = canonicalize_row(row)
    lane_label = (row.get("lane_label") or "").strip()
    if lane_label:
        return lane_label
    legacy_fit_status = (row.get("fit_status") or "").strip()
    return legacy_fit_status if legacy_fit_status in KNOWN_LANE_LABELS else ""


def tracker_fit_status(row: dict[str, str]) -> str:
    row = canonicalize_row(row)
    fit_status = (row.get("fit_status") or "").strip()
    return "" if fit_status in KNOWN_LANE_LABELS else fit_status


def tracker_audit_flag(row: dict[str, str]) -> str:
    row = canonicalize_row(row)
    return (row.get("audit_flag") or "").strip()


def active_job_fit_status(job_description: str, resume_path: Path) -> str:
    try:
        import build_resume
    except Exception:
        return ""
    resume_text = build_resume.docx_visible_text_from_path(resume_path)
    report = build_resume.alignment_score_report(job_description, resume_text)
    return str(report.get("grade", "")).strip()


def should_preserve_existing_status(existing_status: str, incoming_status: str) -> bool:
    existing = (existing_status or "").strip().lower()
    incoming = (incoming_status or "").strip().lower()
    if not existing or not incoming:
        return False
    if existing not in STATUS_PRECEDENCE or incoming not in STATUS_PRECEDENCE:
        return False
    if existing in {"rejected", "withdrawn"} and incoming != existing:
        return True
    return STATUS_PRECEDENCE[incoming] < STATUS_PRECEDENCE[existing]


def matching_row_index(rows: list[dict[str, str]], company: str, role_title: str = "") -> int | None:
    company_lower = company.lower().strip()
    role_lower = role_title.lower().strip()
    for index in range(len(rows) - 1, -1, -1):
        row = rows[index]
        row_company = row.get("company", "")
        if company_lower and not (
            company_lower in row_company.lower() or companies_refer_to_same(company, row_company)
        ):
            continue
        if role_lower and role_lower != row.get("role_title", "").lower().strip():
            continue
        return index
    return None


def row_for_active_job(status: str = "draft", notes: str = "") -> dict[str, str]:
    job_description = read_job_description()
    if not job_description:
        raise ValueError("No active job description found.")
    company = resume_analysis.extract_output_name(job_description)
    role_title = resume_analysis.extract_job_title(job_description) or ""
    selected_resume = resume_analysis.choose_resume(job_description)
    output_file = latest_resume(job_description)
    analysis_resume = output_file or selected_resume
    try:
        import build_resume

        resume_text = build_resume.docx_visible_text_from_path(analysis_resume)
    except Exception:
        resume_text = ""
    profile = resume_analysis.job_problem_profile(job_description, resume_text)
    snapshot_id = job_context_archive.current_snapshot_id() or job_context_archive.find_snapshot_id_for_active_context()
    return {
        "date_added": date.today().isoformat(),
        "company": company,
        "role_title": role_title,
        "lane_label": profile.lane_label,
        "fit_status": active_job_fit_status(job_description, analysis_resume),
        "audit_flag": derive_audit_flag(output_file),
        "source_resume": selected_resume.name,
        "output_file": str(output_file) if output_file else "",
        "snapshot_id": snapshot_id,
        "applied_date": "",
        "current_status": status,
        "last_round": "",
        "outcome": "",
        "notes": notes,
    }


def upsert_application(company: str, role_title: str, updates: dict[str, str], base_row: dict[str, str] | None = None) -> str:
    rows = read_rows()
    index = matching_row_index(rows, company, role_title)
    if index is None:
        if base_row is None:
            base_row = {
                column: ""
                for column in COLUMNS
            }
            base_row.update({"date_added": date.today().isoformat(), "company": company, "role_title": role_title})
        rows.append(base_row)
        index = len(rows) - 1
        action = "Added"
    else:
        action = "Updated"
    existing_status = rows[index].get("current_status", "")
    if should_preserve_existing_status(existing_status, updates.get("current_status", "")):
        updates = dict(updates)
        updates.pop("current_status", None)
    for key, value in updates.items():
        if key in COLUMNS and value is not None:
            rows[index][key] = value
    write_rows(rows)
    return action


def add_row(args: argparse.Namespace) -> int:
    try:
        base_row = row_for_active_job(args.status, args.notes)
    except ValueError:
        print("No active job description found.")
        return 1
    updates = {
        "lane_label": base_row["lane_label"],
        "fit_status": base_row["fit_status"],
        "audit_flag": base_row["audit_flag"],
        "source_resume": base_row["source_resume"],
        "output_file": base_row["output_file"],
        "snapshot_id": base_row["snapshot_id"],
        "current_status": args.status,
        "notes": args.notes,
    }
    if args.applied_date:
        updates["applied_date"] = args.applied_date
    action = upsert_application(base_row["company"], base_row["role_title"], updates, base_row)
    print(f"{action} application row for {base_row['company']} - {base_row['role_title']}.")
    return 0


def update_row(args: argparse.Namespace) -> int:
    rows = read_rows()
    company_lower = args.company.lower()
    for row in reversed(rows):
        if company_lower in row.get("company", "").lower():
            if args.status:
                row["current_status"] = args.status
            if args.applied_date is not None:
                row["applied_date"] = args.applied_date
            if args.last_round is not None:
                row["last_round"] = args.last_round
            if args.outcome is not None:
                row["outcome"] = args.outcome
            if args.notes is not None:
                row["notes"] = args.notes
            write_rows(rows)
            print(f"Updated application row for {row.get('company', args.company)}.")
            return 0
    print(f"No application row found for {args.company}.")
    return 1


def list_rows() -> int:
    rows = read_rows()
    if not rows:
        print("No application rows found.")
        return 0
    for row in rows:
        lane_label = tracker_lane_label(row) or "-"
        fit_status = tracker_fit_status(row) or "-"
        audit_flag = tracker_audit_flag(row) or "-"
        print(
            f"{row.get('date_added','')} | {row.get('company','')} | {row.get('role_title','')} | "
            f"{row.get('current_status','')} | lane: {lane_label} | fit: {fit_status} | audit: {audit_flag} | {row.get('outcome','')}"
        )
    return 0


def report_rows() -> int:
    rows = read_rows()
    counts = {status: 0 for status in sorted(VALID_STATUSES)}
    lane_counts: dict[str, int] = {}
    fit_counts: dict[str, int] = {}
    audit_counts: dict[str, int] = {}
    for row in rows:
        status = row.get("current_status", "draft")
        counts[status] = counts.get(status, 0) + 1
        lane_label = tracker_lane_label(row) or "Unknown"
        lane_counts[lane_label] = lane_counts.get(lane_label, 0) + 1
        fit_status = tracker_fit_status(row) or "Not classified"
        fit_counts[fit_status] = fit_counts.get(fit_status, 0) + 1
        audit_flag = tracker_audit_flag(row)
        if audit_flag:
            audit_counts[audit_flag] = audit_counts.get(audit_flag, 0) + 1
    print(f"Total applications: {len(rows)}")
    for status, count in counts.items():
        if count:
            print(f"{status}: {count}")
    print("Lane breakdown:")
    for lane_label, count in sorted(lane_counts.items()):
        print(f"{lane_label}: {count}")
    print("Fit breakdown:")
    for fit_status, count in sorted(fit_counts.items()):
        print(f"{fit_status}: {count}")
    if audit_counts:
        print("Audit breakdown:")
        for audit_flag, count in sorted(audit_counts.items()):
            print(f"{audit_flag}: {count}")
    return 0


def refresh_rows_command(args: argparse.Namespace) -> int:
    updated, unchanged = refresh_metadata(force=args.force)
    print(f"Tracker metadata refresh complete: updated {updated} row(s), left {unchanged} unchanged.")
    if updated == 0:
        print("No additional lane or fit values could be refreshed from the current or archived job descriptions.")
    return 0


def main() -> int:
    args = parse_args()
    if args.command == "add":
        return add_row(args)
    if args.command == "update":
        return update_row(args)
    if args.command == "refresh":
        return refresh_rows_command(args)
    if args.command == "report":
        return report_rows()
    return list_rows()


if __name__ == "__main__":
    raise SystemExit(main())
