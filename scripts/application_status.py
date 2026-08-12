#!/usr/bin/env python3
"""Report submission readiness for the active commercial application package."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import job_context_archive
import resume_analysis
import track_applications
from config.paths import JOB_DESCRIPTION, OUTPUT_DIR


ArtifactState = resume_analysis.ArtifactState

ARTIFACT_PATTERNS = {
    "resume": "Resume.docx",
    "cover": "Cover Letter.docx",
    "qualifications": "Qualifications Statement.docx",
    "checklist": "Application Checklist.docx",
    "interview": "Interview Cheat Sheet.docx",
    "guide": "Detailed Interview Guide.docx",
    "thank-you": "Thank-You Note.docx",
    "follow-up": "Follow-Up Email.docx",
    "post-round": "Post-Round*.docx",
}
ARTIFACT_LABELS = {
    "resume": "Resume",
    "cover": "Cover letter",
    "qualifications": "Qualifications statement",
    "checklist": "Application checklist",
    "interview": "Interview cheat sheet",
    "guide": "Detailed interview guide",
    "thank-you": "Thank-you note",
    "follow-up": "Follow-up email",
    "post-round": "Post-round documents",
    "tracker": "Tracker row",
}
DEFAULT_REQUIRED = ("resume", "cover", "qualifications")
ALL_REQUIREMENTS = (*ARTIFACT_PATTERNS, "tracker")


@dataclass(frozen=True)
class ArtifactRecord:
    artifact_type: str
    path: Path | None
    state: ArtifactState | None
    status: str
    detail: str


@dataclass(frozen=True)
class ApplicationReadinessReport:
    company: str
    role_title: str
    snapshot_id: str
    selected_resume: Path | None
    artifacts: tuple[ArtifactRecord, ...]
    required_artifact_types: tuple[str, ...]
    optional_artifact_types: tuple[str, ...]
    tracker_status: ArtifactRecord
    overall_state: str
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Show active application package readiness.")
    parser.add_argument(
        "--require",
        dest="required",
        help="Comma-separated required set, for example resume or resume,cover,qualifications,tracker.",
    )
    return parser.parse_args(argv)


def parse_required_set(value: str | None) -> tuple[str, ...]:
    if value is None:
        return DEFAULT_REQUIRED
    values = tuple(item.strip().lower() for item in value.split(",") if item.strip())
    if not values:
        raise ValueError("--require needs at least one artifact type")
    duplicates = sorted({item for item in values if values.count(item) > 1})
    unknown = sorted(set(values) - set(ALL_REQUIREMENTS))
    if duplicates:
        raise ValueError(f"Duplicate --require value(s): {', '.join(duplicates)}")
    if unknown:
        raise ValueError(f"Unknown --require value(s): {', '.join(unknown)}")
    return values


def read_job() -> str:
    return JOB_DESCRIPTION.read_text(encoding="utf-8-sig").strip() if JOB_DESCRIPTION.exists() else ""


def latest_artifact(job_description: str, artifact_type: str) -> Path | None:
    matches = resume_analysis.matching_output_files(
        OUTPUT_DIR,
        job_description,
        ARTIFACT_PATTERNS[artifact_type],
        include_drafts=True,
    )
    return matches[0] if matches else None


def state_status(state: ArtifactState) -> str:
    if state is ArtifactState.PASS:
        return "READY"
    if state in {ArtifactState.BRIDGE, ArtifactState.DRAFT}:
        return "REVIEW"
    return "BLOCKED"


def artifact_record(
    artifact_type: str,
    path: Path | None,
    *,
    required: bool,
    selected_resume: Path | None,
) -> ArtifactRecord:
    if path is None:
        status = "MISSING" if required else "NOT BUILT"
        return ArtifactRecord(artifact_type, None, None, status, "")

    state = resume_analysis.output_artifact_state(path)
    if artifact_type != "resume" and selected_resume is not None:
        resume_state = resume_analysis.output_artifact_state(selected_resume)
        stale_reasons: list[str] = []
        if path.stat().st_mtime < selected_resume.stat().st_mtime:
            stale_reasons.append("predates selected resume")
        if state is not resume_state:
            stale_reasons.append(f"state {state.value} disagrees with resume {resume_state.value}")
        if stale_reasons:
            return ArtifactRecord(artifact_type, path, state, "STALE", "; ".join(stale_reasons))
    return ArtifactRecord(artifact_type, path, state, state_status(state), path.name)


def normalized_path(path_value: str) -> Path | None:
    if not path_value.strip():
        return None
    path = Path(path_value)
    if not path.is_absolute():
        path = (OUTPUT_DIR.parent / path).resolve()
    return path.resolve()


def tracker_record(
    company: str,
    role_title: str,
    snapshot_id: str,
    selected_resume: Path | None,
    *,
    required: bool,
) -> ArtifactRecord:
    rows = track_applications.read_rows()
    index = track_applications.matching_row_index(rows, company, role_title)
    if index is None:
        return ArtifactRecord("tracker", None, None, "MISSING" if required else "NOT BUILT", "")
    row = rows[index]
    stale_reasons: list[str] = []
    if row.get("snapshot_id", "").strip() != snapshot_id:
        stale_reasons.append("snapshot ID differs from active snapshot")
    recorded_path = normalized_path(row.get("output_file", ""))
    if selected_resume is None or recorded_path != selected_resume.resolve():
        stale_reasons.append("output path differs from selected resume")
    resume_state = resume_analysis.output_artifact_state(selected_resume)
    tracker_state = (row.get("audit_flag", "").strip() or "PASS").upper()
    if tracker_state != resume_state.value:
        stale_reasons.append(f"audit flag {tracker_state} disagrees with resume {resume_state.value}")
    detail = ", ".join(
        value
        for value in (
            row.get("current_status", "").strip(),
            f"round {row.get('last_round', '').strip()}" if row.get("last_round", "").strip() else "",
            f"outcome {row.get('outcome', '').strip()}" if row.get("outcome", "").strip() else "",
        )
        if value
    )
    if stale_reasons:
        return ArtifactRecord("tracker", recorded_path, None, "STALE", "; ".join(stale_reasons))
    return ArtifactRecord("tracker", recorded_path, resume_state, "READY", detail or "tracked")


def build_report(job_description: str, required: tuple[str, ...]) -> ApplicationReadinessReport:
    company = resume_analysis.extract_semantic_organization(job_description)[0]
    role_title = resume_analysis.extract_job_title(job_description) or "Target Role"
    snapshot_id = job_context_archive.current_snapshot_id() or job_context_archive.find_snapshot_id_for_active_context()
    selected_resume = latest_artifact(job_description, "resume")
    records = tuple(
        artifact_record(
            artifact_type,
            latest_artifact(job_description, artifact_type),
            required=artifact_type in required,
            selected_resume=selected_resume,
        )
        for artifact_type in ARTIFACT_PATTERNS
    )
    tracker = tracker_record(
        company,
        role_title,
        snapshot_id,
        selected_resume,
        required="tracker" in required,
    )
    by_type = {record.artifact_type: record for record in (*records, tracker)}
    non_ready = [by_type[artifact_type] for artifact_type in required if by_type[artifact_type].status != "READY"]
    blockers = tuple(
        f"{ARTIFACT_LABELS[record.artifact_type]}: {record.status}"
        for record in non_ready
        if record.status in {"BLOCKED", "MISSING", "STALE"}
    )
    warnings = tuple(
        f"{ARTIFACT_LABELS[record.artifact_type]}: {record.status}"
        for record in non_ready
        if record.status == "REVIEW"
    )
    overall = "READY" if not non_ready else ("BLOCKED" if blockers else "REVIEW")
    optional = tuple(item for item in ALL_REQUIREMENTS if item not in required)
    return ApplicationReadinessReport(
        company=company,
        role_title=role_title,
        snapshot_id=snapshot_id,
        selected_resume=selected_resume,
        artifacts=records,
        required_artifact_types=required,
        optional_artifact_types=optional,
        tracker_status=tracker,
        overall_state=overall,
        blockers=blockers,
        warnings=warnings,
    )


def print_record(record: ArtifactRecord) -> None:
    suffix = f" - {record.detail}" if record.detail else ""
    print(f"{record.status}: {ARTIFACT_LABELS[record.artifact_type]}{suffix}")


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        required = parse_required_set(args.required)
    except ValueError as error:
        print(f"Invalid readiness request: {error}")
        return 1
    job_description = read_job()
    if not job_description:
        print(f"No active job description found at {JOB_DESCRIPTION}.")
        return 1
    try:
        report = build_report(job_description, required)
    except (OSError, ValueError) as error:
        print(f"Could not determine application readiness: {error}")
        return 1

    print(f"Application Status: {report.company} - {report.role_title}")
    print(f"Target snapshot: {report.snapshot_id or 'not archived'}")
    print()
    for record in report.artifacts:
        print_record(record)
    print_record(report.tracker_status)
    print()
    print(f"Overall: {report.overall_state}")
    return 0 if report.overall_state == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
