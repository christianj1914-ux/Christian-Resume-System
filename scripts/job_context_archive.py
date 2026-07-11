#!/usr/bin/env python3
"""Canonical archive helpers for active commercial job context."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from config.paths import APPLICATION_QUESTIONS, JOBS_DIR, JOB_DESCRIPTION, SCRATCH_JD_LIBRARY
import resume_analysis


SNAPSHOT_ID_ENV = "JOB_CONTEXT_SNAPSHOT_ID"
SNAPSHOT_PATH_ENV = "JOB_CONTEXT_SNAPSHOT_PATH"
SOURCE_COMMAND_ENV = "JOB_CONTEXT_SOURCE_COMMAND"
WORKFLOW_TYPE_ENV = "JOB_CONTEXT_WORKFLOW_TYPE"
INDEX_PATH = SCRATCH_JD_LIBRARY / "index.csv"
METADATA_FILENAME = "metadata.json"
JOB_DESCRIPTION_FILENAME = "job_description.txt"
APPLICATION_QUESTIONS_FILENAME = "application_questions.txt"
LEGACY_NAMED_JOB_GLOB = "job_description - *.txt"
TRACE_BACKFILL_DAYS = 7
INDEX_COLUMNS = (
    "snapshot_id",
    "created_at",
    "company",
    "role",
    "workflow_type",
    "source_command",
    "archive_reason",
    "lane",
    "questions_present",
    "question_count",
    "relative_path",
    "job_description_sha256",
    "application_questions_sha256",
)

_SYNC_COMPLETE = False


@dataclass(frozen=True)
class ArchivedJobContext:
    snapshot_id: str
    created_at: str
    company: str
    role: str
    workflow_type: str
    source_command: str
    archive_reason: str
    lane: str
    questions_present: bool
    question_count: int
    path: Path
    job_description_sha256: str
    application_questions_sha256: str


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def safe_name(value: str, *, max_length: int = 64) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-")
    return cleaned[:max_length] or "Unknown"


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig").strip()


def parse_question_blocks(text: str) -> tuple[str, ...]:
    prompts: list[str] = []
    current: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if current:
                prompts.append(normalize_spaces(" ".join(current)))
                current = []
            continue
        if re.fullmatch(r"(application )?(supplemental )?(qualifications )?questions?", line, re.I):
            continue
        current.append(line)
    if current:
        prompts.append(normalize_spaces(" ".join(current)))
    return tuple(dict.fromkeys(prompt for prompt in prompts if prompt))


def sha256_text(text: str) -> str:
    if not text.strip():
        return ""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def current_snapshot_id() -> str:
    return os.environ.get(SNAPSHOT_ID_ENV, "").strip()


def snapshot_dir(snapshot_id: str) -> Path:
    return SCRATCH_JD_LIBRARY / snapshot_id


def job_description_path_for_snapshot(snapshot_id: str) -> Path:
    return snapshot_dir(snapshot_id) / JOB_DESCRIPTION_FILENAME


def application_questions_path_for_snapshot(snapshot_id: str) -> Path:
    return snapshot_dir(snapshot_id) / APPLICATION_QUESTIONS_FILENAME


def metadata_path_for_snapshot(snapshot_id: str) -> Path:
    return snapshot_dir(snapshot_id) / METADATA_FILENAME


def _read_index_raw() -> list[dict[str, str]]:
    if not INDEX_PATH.exists():
        return []
    with INDEX_PATH.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_index(rows: list[dict[str, str]]) -> None:
    SCRATCH_JD_LIBRARY.mkdir(parents=True, exist_ok=True)
    ordered = sorted(
        ({column: str(row.get(column, "")) for column in INDEX_COLUMNS} for row in rows),
        key=lambda item: item.get("created_at", ""),
        reverse=True,
    )
    with INDEX_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=INDEX_COLUMNS)
        writer.writeheader()
        writer.writerows(ordered)


def _new_style_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {column: str(row.get(column, "")) for column in INDEX_COLUMNS}
        for row in rows
        if row.get("snapshot_id", "").strip()
    ]


def _safe_company_name(job_description_text: str) -> str:
    for extractor in (
        resume_analysis.extract_company_name,
        resume_analysis.extract_output_name,
    ):
        try:
            value = extractor(job_description_text)
        except SystemExit:
            value = ""
        if value:
            return normalize_spaces(str(value))
    return "Unknown Company"


def _safe_role_title(job_description_text: str) -> str:
    try:
        value = resume_analysis.extract_job_title(job_description_text)
    except SystemExit:
        value = ""
    if value:
        return normalize_spaces(str(value))
    return "Unknown Role"


def _safe_lane(job_description_text: str) -> str:
    try:
        return str(resume_analysis.job_problem_profile(job_description_text, "").primary_lane).strip()
    except Exception:
        return ""


def _default_snapshot_id(company: str, role: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = f"{safe_name(company)}_{safe_name(role)}"
    return f"{timestamp}_{slug}_{uuid.uuid4().hex[:8]}"


def _row_from_metadata(metadata: dict[str, object]) -> dict[str, str]:
    return {
        "snapshot_id": str(metadata.get("snapshot_id", "")),
        "created_at": str(metadata.get("created_at", "")),
        "company": str(metadata.get("company", "")),
        "role": str(metadata.get("role", "")),
        "workflow_type": str(metadata.get("workflow_type", "")),
        "source_command": str(metadata.get("source_command", "")),
        "archive_reason": str(metadata.get("archive_reason", "")),
        "lane": str(metadata.get("lane", "")),
        "questions_present": "true" if bool(metadata.get("questions_present")) else "false",
        "question_count": str(int(metadata.get("question_count", 0) or 0)),
        "relative_path": str(metadata.get("relative_path", "")),
        "job_description_sha256": str(metadata.get("job_description_sha256", "")),
        "application_questions_sha256": str(metadata.get("application_questions_sha256", "")),
    }


def _snapshot_from_metadata(metadata: dict[str, object], path: Path) -> ArchivedJobContext:
    return ArchivedJobContext(
        snapshot_id=str(metadata.get("snapshot_id", "")),
        created_at=str(metadata.get("created_at", "")),
        company=str(metadata.get("company", "")),
        role=str(metadata.get("role", "")),
        workflow_type=str(metadata.get("workflow_type", "")),
        source_command=str(metadata.get("source_command", "")),
        archive_reason=str(metadata.get("archive_reason", "")),
        lane=str(metadata.get("lane", "")),
        questions_present=bool(metadata.get("questions_present")),
        question_count=int(metadata.get("question_count", 0) or 0),
        path=path,
        job_description_sha256=str(metadata.get("job_description_sha256", "")),
        application_questions_sha256=str(metadata.get("application_questions_sha256", "")),
    )


def _existing_snapshot_by_hash(
    rows: list[dict[str, str]],
    *,
    job_description_sha256: str,
    application_questions_sha256: str,
) -> ArchivedJobContext | None:
    for row in rows:
        if row.get("job_description_sha256", "") != job_description_sha256:
            continue
        if row.get("application_questions_sha256", "") != application_questions_sha256:
            continue
        metadata = metadata_for_snapshot(row.get("snapshot_id", ""))
        if metadata:
            return _snapshot_from_metadata(metadata, snapshot_dir(row["snapshot_id"]))
    return None


def application_question_pairing_issue(
    job_description_text: str,
    application_questions_text: str,
) -> str:
    """Flag a question set previously paired with a different active JD."""

    job_description_text = job_description_text.strip()
    application_questions_text = application_questions_text.strip()
    if not job_description_text or not parse_question_blocks(application_questions_text):
        return ""
    job_hash = sha256_text(job_description_text)
    question_hash = sha256_text(application_questions_text)
    active_prompts = parse_question_blocks(application_questions_text)
    for row in reversed(_read_index_raw()):
        same_question_set = row.get("application_questions_sha256", "") == question_hash
        if not same_question_set:
            archived_questions = application_questions_path_for_snapshot(row.get("snapshot_id", ""))
            if archived_questions.exists():
                same_question_set = parse_question_blocks(
                    archived_questions.read_text(encoding="utf-8-sig")
                ) == active_prompts
        if not same_question_set:
            continue
        if row.get("job_description_sha256", "") in {"", job_hash}:
            continue
        company = row.get("company", "an earlier target") or "an earlier target"
        role = row.get("role", "").strip()
        target = f"{company} - {role}" if role else company
        return (
            f"The active application-question set was previously archived with {target}, "
            "but the active job description has a different content hash."
        )
    return ""


def _create_snapshot_metadata(
    *,
    job_description_text: str,
    application_questions_text: str,
    workflow_type: str,
    source_command: str,
    archive_reason: str,
    snapshot_id: str,
) -> dict[str, object]:
    prompts = parse_question_blocks(application_questions_text)
    company = _safe_company_name(job_description_text)
    role = _safe_role_title(job_description_text)
    created_at = datetime.now().isoformat(timespec="seconds")
    return {
        "snapshot_id": snapshot_id,
        "created_at": created_at,
        "company": company,
        "role": role,
        "workflow_type": workflow_type,
        "source_command": source_command,
        "archive_reason": archive_reason,
        "lane": _safe_lane(job_description_text),
        "questions_present": bool(prompts),
        "question_count": len(prompts),
        "relative_path": snapshot_id,
        "job_description_sha256": sha256_text(job_description_text),
        "application_questions_sha256": sha256_text(application_questions_text),
    }


def archive_texts(
    *,
    job_description_text: str,
    application_questions_text: str = "",
    workflow_type: str = "commercial",
    source_command: str = "",
    archive_reason: str = "manual_archive",
    snapshot_id: str = "",
    dedupe_by_content: bool = False,
    sync_legacy: bool = True,
) -> ArchivedJobContext:
    job_description_text = job_description_text.strip()
    if not job_description_text:
        raise ValueError("Active job description is empty; nothing to archive.")
    if sync_legacy:
        sync_legacy_archives()
    snapshot_id = snapshot_id.strip() or _default_snapshot_id(
        _safe_company_name(job_description_text),
        _safe_role_title(job_description_text),
    )
    metadata = _create_snapshot_metadata(
        job_description_text=job_description_text,
        application_questions_text=application_questions_text.strip(),
        workflow_type=workflow_type,
        source_command=source_command,
        archive_reason=archive_reason,
        snapshot_id=snapshot_id,
    )
    rows = _read_index_raw()
    if dedupe_by_content:
        existing = _existing_snapshot_by_hash(
            rows,
            job_description_sha256=str(metadata["job_description_sha256"]),
            application_questions_sha256=str(metadata["application_questions_sha256"]),
        )
        if existing:
            return existing
    path = snapshot_dir(snapshot_id)
    path.mkdir(parents=True, exist_ok=False)
    job_description_path_for_snapshot(snapshot_id).write_text(job_description_text + "\n", encoding="utf-8")
    if application_questions_text.strip():
        application_questions_path_for_snapshot(snapshot_id).write_text(
            application_questions_text.strip() + "\n",
            encoding="utf-8",
        )
    metadata_path_for_snapshot(snapshot_id).write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    rows.append(_row_from_metadata(metadata))
    _write_index(rows)
    return _snapshot_from_metadata(metadata, path)


def archive_active_context(
    *,
    workflow_type: str = "commercial",
    source_command: str = "",
    archive_reason: str = "command_auto_archive",
    snapshot_id: str = "",
) -> ArchivedJobContext:
    return archive_texts(
        job_description_text=read_text(JOB_DESCRIPTION),
        application_questions_text=read_text(APPLICATION_QUESTIONS),
        workflow_type=workflow_type,
        source_command=source_command,
        archive_reason=archive_reason,
        snapshot_id=snapshot_id,
        sync_legacy=True,
    )


def metadata_for_snapshot(snapshot_id: str) -> dict[str, object]:
    snapshot_id = snapshot_id.strip()
    if not snapshot_id:
        return {}
    path = metadata_path_for_snapshot(snapshot_id)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def current_snapshot_metadata() -> dict[str, object]:
    return metadata_for_snapshot(current_snapshot_id())


def snapshot_job_description_text(snapshot_id: str) -> str:
    path = job_description_path_for_snapshot(snapshot_id)
    return read_text(path)


def path_from_row(row: dict[str, str]) -> Path | None:
    relative_path = row.get("relative_path", "").strip()
    if relative_path:
        candidate = SCRATCH_JD_LIBRARY / Path(relative_path)
        if candidate.is_dir():
            return candidate
        if candidate.exists():
            return candidate.parent
    snapshot_id = row.get("snapshot_id", "").strip()
    if snapshot_id and snapshot_dir(snapshot_id).exists():
        return snapshot_dir(snapshot_id)
    filename = row.get("filename", "").strip()
    if filename:
        legacy_path = SCRATCH_JD_LIBRARY / filename
        if legacy_path.exists():
            return legacy_path.parent
    return None


def job_description_text_for_row(row: dict[str, str]) -> str:
    snapshot_id = row.get("snapshot_id", "").strip()
    if snapshot_id:
        return snapshot_job_description_text(snapshot_id)
    filename = row.get("filename", "").strip()
    if filename:
        return read_text(SCRATCH_JD_LIBRARY / filename)
    return ""


def find_snapshot_id_for_active_context() -> str:
    job_description_text = read_text(JOB_DESCRIPTION)
    if not job_description_text:
        return ""
    application_questions_text = read_text(APPLICATION_QUESTIONS)
    target_job_hash = sha256_text(job_description_text)
    target_question_hash = sha256_text(application_questions_text)
    rows = read_index()
    for row in rows:
        if row.get("job_description_sha256", "") != target_job_hash:
            continue
        if row.get("application_questions_sha256", "") != target_question_hash:
            continue
        return row.get("snapshot_id", "").strip()
    return ""


def read_index() -> list[dict[str, str]]:
    sync_legacy_archives()
    return sorted(_read_index_raw(), key=lambda row: row.get("created_at", ""), reverse=True)


def _import_legacy_named_job_files() -> None:
    for path in sorted(JOBS_DIR.glob(LEGACY_NAMED_JOB_GLOB)):
        text = read_text(path)
        if not text:
            continue
        archive_texts(
            job_description_text=text,
            application_questions_text="",
            workflow_type="commercial",
            source_command="legacy_import",
            archive_reason="legacy_named_job_file",
            dedupe_by_content=True,
            sync_legacy=False,
        )


def _import_legacy_jd_library_rows(legacy_rows: list[dict[str, str]]) -> None:
    for row in legacy_rows:
        filename = row.get("filename", "").strip()
        if not filename:
            continue
        legacy_path = SCRATCH_JD_LIBRARY / filename
        text = read_text(legacy_path)
        if not text:
            continue
        archive_texts(
            job_description_text=text,
            application_questions_text="",
            workflow_type="commercial",
            source_command="legacy_import",
            archive_reason="legacy_jd_library",
            dedupe_by_content=True,
            sync_legacy=False,
        )


def _backfill_from_cover_traces() -> None:
    trace_dir = SCRATCH_JD_LIBRARY.parent / "cover_letter_traces"
    if not trace_dir.exists():
        return
    cutoff = datetime.now() - timedelta(days=TRACE_BACKFILL_DAYS)
    for path in sorted(trace_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        modified = datetime.fromtimestamp(path.stat().st_mtime)
        if modified < cutoff:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        job_description_text = str(payload.get("plan", {}).get("job_description", "")).strip()
        if not job_description_text:
            continue
        archive_texts(
            job_description_text=job_description_text,
            application_questions_text="",
            workflow_type="commercial",
            source_command="trace_backfill",
            archive_reason="trace_backfill",
            dedupe_by_content=True,
            sync_legacy=False,
        )


def sync_legacy_archives() -> None:
    global _SYNC_COMPLETE
    if _SYNC_COMPLETE:
        return
    _SYNC_COMPLETE = True
    raw_rows = _read_index_raw()
    legacy_rows = [row for row in raw_rows if row.get("filename", "").strip() and not row.get("snapshot_id", "").strip()]
    new_rows = _new_style_rows(raw_rows)
    if legacy_rows:
        _write_index(new_rows)
    elif raw_rows and raw_rows != new_rows:
        _write_index(new_rows)
    _import_legacy_jd_library_rows(legacy_rows)
    _import_legacy_named_job_files()
    _backfill_from_cover_traces()
