#!/usr/bin/env python3
"""Run commercial resume workflows sequentially from independent queue files."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable

import requirement_engine
import resume_analysis
from config.paths import PYTHON_EXECUTABLE
from utils import paragraph_texts


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE_DIR = PROJECT_ROOT / "jobs" / "commercial_queue"
DEFAULT_STATE_ROOT = PROJECT_ROOT / "scratch" / "commercial_queue"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"
DEFAULT_RENDER_DIR = PROJECT_ROOT / "render_check"
SKIPPABLE_STATUSES = {"success", "fallback-warning", "review-required"}
STATUS_ORDER = ("success", "fallback-warning", "review-required", "failed", "timed-out", "skipped")
AUDIT_STATE_RE = re.compile(r"^Final audit:\s*(PASS|BRIDGE|FAIL|POOR|DRAFT)\s*$", re.MULTILINE)
STEP_DURATION_RE = re.compile(r"^Workflow step elapsed:\s*([0-9.]+)s\s*$", re.MULTILINE)


@dataclass(frozen=True)
class QueueJob:
    stem: str
    posting_path: Path
    questions_path: Path | None
    posting_text: str
    questions_text: str
    company: str
    role: str
    output_target: str
    posting_hash: str
    questions_hash: str


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalized_target(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def discover_jobs(queue_dir: Path) -> list[QueueJob]:
    jobs: list[QueueJob] = []
    for posting_path in sorted(queue_dir.glob("*.txt"), key=lambda path: path.name.lower()):
        if posting_path.name.lower().endswith(".questions.txt"):
            continue
        posting_text = posting_path.read_text(encoding="utf-8-sig").strip()
        if not posting_text:
            raise ValueError(f"Queue posting is empty: {posting_path}")
        questions_path = posting_path.with_name(f"{posting_path.stem}.questions.txt")
        questions_text = questions_path.read_text(encoding="utf-8-sig").strip() if questions_path.exists() else ""
        company = resume_analysis.extract_semantic_organization(posting_text)[0].strip()
        role = (resume_analysis.extract_job_title(posting_text) or "").strip()
        if not company or not role:
            raise ValueError(f"Queue posting must identify both company and role: {posting_path.name}")
        output_target = resume_analysis.extract_output_target_name(posting_text)
        jobs.append(
            QueueJob(
                stem=posting_path.stem,
                posting_path=posting_path.resolve(),
                questions_path=questions_path.resolve() if questions_path.exists() else None,
                posting_text=posting_text,
                questions_text=questions_text,
                company=company,
                role=role,
                output_target=output_target,
                posting_hash=text_hash(posting_text),
                questions_hash=text_hash(questions_text),
            )
        )
    return jobs


def duplicate_targets(jobs: Iterable[QueueJob]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for job in jobs:
        grouped.setdefault(normalized_target(job.output_target), []).append(job.posting_path.name)
    return {target: names for target, names in grouped.items() if len(names) > 1}


def pipeline_fingerprint(project_root: Path = PROJECT_ROOT) -> str:
    digest = hashlib.sha256()
    candidates = [project_root / "tasks.py", project_root / "run_resume.bat"]
    candidates.extend(sorted((project_root / "scripts").rglob("*.py")))
    candidates.extend(
        path
        for path in (
            project_root / "source" / "Estrada_Resume_Implementation.docx",
            project_root / "source" / "Estrada_Resume_PreSales_CSM.docx",
            project_root / "source" / "Christian_Estrada_KPMG_Final_Tightened_EdFix.docx",
        )
        if path.exists()
    )
    for path in candidates:
        if not path.is_file():
            continue
        digest.update(path.relative_to(project_root).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def completion_key(job: QueueJob, mode: str, fingerprint: str) -> str:
    return text_hash("|".join((job.posting_hash, job.questions_hash, mode, fingerprint)))


def atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def load_state(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"version": 1, "entries": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Queue state is not valid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("entries"), dict):
        raise ValueError(f"Queue state has an invalid schema: {path}")
    return payload


def artifacts_exist(entry: dict[str, object]) -> bool:
    artifacts = entry.get("artifacts", [])
    return bool(artifacts) and isinstance(artifacts, list) and all(Path(str(path)).is_file() for path in artifacts)


def should_skip(entry: dict[str, object] | None, rerun: bool) -> bool:
    return bool(
        not rerun
        and entry
        and str(entry.get("status", "")) in SKIPPABLE_STATUSES
        and artifacts_exist(entry)
    )


def directory_snapshot(directory: Path) -> dict[Path, tuple[int, int]]:
    if not directory.exists():
        return {}
    return {
        path.resolve(): (path.stat().st_mtime_ns, path.stat().st_size)
        for path in directory.iterdir()
        if path.is_file()
    }


def changed_artifacts(directory: Path, before: dict[Path, tuple[int, int]]) -> list[str]:
    if not directory.exists():
        return []
    changed = []
    for path in directory.iterdir():
        if not path.is_file():
            continue
        resolved = path.resolve()
        stat = path.stat()
        if before.get(resolved) != (stat.st_mtime_ns, stat.st_size):
            changed.append(str(resolved))
    return sorted(changed)


def active_file_hashes(project_root: Path = PROJECT_ROOT) -> dict[str, str]:
    paths = (
        project_root / "jobs" / "job_description.txt",
        project_root / "jobs" / "application_questions.txt",
        project_root / "jobs" / "company_research.txt",
        project_root / "jobs" / "interview_notes.txt",
    )
    return {str(path.resolve()): file_hash(path) if path.exists() else "<missing>" for path in paths}


def status_for_result(returncode: int, verified_parse: bool, artifacts: list[str]) -> str:
    if returncode == 124:
        return "timed-out"
    if returncode == 2:
        return "review-required"
    if returncode != 0 or not artifacts:
        return "failed"
    return "success" if verified_parse else "fallback-warning"


def artifacts_for_job(paths: list[str], job: QueueJob) -> list[str]:
    """Keep one queue result from claiming artifacts written by another job."""
    target = normalized_target(job.output_target)
    return [path for path in paths if target in normalized_target(Path(path).stem)]


def resume_audit_state_from_output(stdout: str) -> str:
    resume_output = stdout.split("Building cover letter", 1)[0]
    matches = AUDIT_STATE_RE.findall(resume_output)
    return matches[-1] if matches else "UNKNOWN"


def stage_timings_from_output(stdout: str) -> dict[str, float]:
    names = ("resume", "cover_letter", "qualifications")
    values = [float(value) for value in STEP_DURATION_RE.findall(stdout)]
    return {name: values[index] for index, name in enumerate(names) if index < len(values)}


def submission_readiness_for_result(
    *,
    status: str,
    returncode: int,
    resume_audit_state: str,
    artifacts: list[str],
) -> str:
    if status in {"failed", "timed-out"}:
        return "blocked"
    if resume_audit_state in {"FAIL", "POOR"}:
        return "blocked"
    if returncode == 2 or resume_audit_state in {"BRIDGE", "DRAFT"}:
        return "review-required"
    if any(" DRAFT" in Path(path).stem.upper() for path in artifacts):
        return "review-required"
    return "ready"


def blocker_reason_from_output(stdout: str, readiness: str) -> str:
    if readiness == "ready":
        return ""
    candidates = [
        line.strip().removeprefix("Audit note: ").strip()
        for line in stdout.splitlines()
        if line.strip().startswith("Audit note:")
        and any(token in line.lower() for token in ("bridge gaps", "fail reason", "hard blocker", "keyword placement"))
    ]
    if candidates:
        return candidates[-1]
    return "Generated packet requires human review before submission."


def cover_opening_fingerprint(artifacts: list[str], companies: Iterable[str]) -> str:
    cover = next((Path(path) for path in artifacts if "cover letter" in Path(path).stem.lower() and Path(path).suffix.lower() == ".docx"), None)
    if cover is None or not cover.exists():
        return ""
    paragraphs = [text.strip() for text in paragraph_texts(cover) if text.strip()]
    try:
        salutation_index = next(index for index, text in enumerate(paragraphs) if text.lower().startswith("dear "))
    except StopIteration:
        return ""
    if salutation_index + 1 >= len(paragraphs):
        return ""
    opening = paragraphs[salutation_index + 1].lower()
    for company in companies:
        opening = re.sub(re.escape(company.lower()), "<company>", opening)
    return re.sub(r"[^a-z0-9]+", " ", opening).strip()


def apply_queue_boilerplate_warnings(results: list[dict[str, object]]) -> None:
    companies = [str(result.get("company", "")) for result in results]
    groups: dict[str, list[dict[str, object]]] = {}
    for result in results:
        fingerprint = cover_opening_fingerprint(list(result.get("artifacts", [])), companies)
        if fingerprint:
            groups.setdefault(fingerprint, []).append(result)
    for duplicate_results in groups.values():
        if len(duplicate_results) < 2:
            continue
        names = ", ".join(str(result.get("company", "")) for result in duplicate_results)
        warning = f"Possible repeated cover-letter opening across queue entries: {names}."
        for result in duplicate_results:
            result["queue_warnings"] = [warning]
            if result.get("submission_readiness") == "ready":
                result["submission_readiness"] = "review-required"


def _job_environment(
    job: QueueJob,
    *,
    input_dir: Path,
    output_dir: Path,
    render_dir: Path,
) -> dict[str, str]:
    input_dir.mkdir(parents=True, exist_ok=True)
    empty_questions = input_dir / "application_questions.txt"
    empty_research = input_dir / "company_research.txt"
    empty_notes = input_dir / "interview_notes.txt"
    for path in (empty_questions, empty_research, empty_notes):
        if not path.exists():
            path.write_text("", encoding="utf-8")
    environment = os.environ.copy()
    environment.update(
        {
            "RESUME_JOB_DESCRIPTION_PATH": str(job.posting_path),
            "RESUME_APPLICATION_QUESTIONS_PATH": str(job.questions_path or empty_questions),
            "RESUME_COMPANY_RESEARCH_PATH": str(empty_research),
            "RESUME_INTERVIEW_NOTES_PATH": str(empty_notes),
            "RESUME_OUTPUT_DIR": str(output_dir.resolve()),
            "RESUME_RENDER_DIR": str(render_dir.resolve()),
            "PYTHONUNBUFFERED": "1",
        }
    )
    return environment


Runner = Callable[..., subprocess.CompletedProcess[str]]


def execute_queue(
    *,
    queue_dir: Path,
    state_root: Path,
    output_dir: Path,
    render_dir: Path,
    mode: str,
    rerun: bool,
    project_root: Path = PROJECT_ROOT,
    runner: Runner = subprocess.run,
    fingerprint: str | None = None,
    active_hash_provider: Callable[[Path], dict[str, str]] = active_file_hashes,
) -> tuple[int, Path, list[dict[str, object]]]:
    jobs = discover_jobs(queue_dir)
    if not jobs:
        raise ValueError(f"No queue postings found in {queue_dir}")
    duplicates = duplicate_targets(jobs)
    if duplicates:
        detail = "; ".join(f"{target}: {', '.join(names)}" for target, names in sorted(duplicates.items()))
        raise ValueError(f"Duplicate company/role output targets must be resolved before processing: {detail}")

    base_minutes = 10 if mode == "resume-only" else 30
    print(
        f"Queue contains {len(jobs)} posting(s). Base worst case: {len(jobs) * base_minutes} minutes "
        f"({base_minutes} minutes per posting for {mode}).",
        flush=True,
    )
    print(
        "There is no queue-level timeout. Each required workflow step retains its ten-minute ceiling, "
        "and an affected page-fit renderer may receive one bounded retry.",
        flush=True,
    )

    active_before = active_hash_provider(project_root)
    fingerprint = fingerprint or pipeline_fingerprint(project_root)
    state_path = state_root / "state.json"
    state = load_state(state_path)
    entries = state["entries"]
    assert isinstance(entries, dict)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    run_root = state_root / "runs" / stamp
    manifest_path = state_root / "manifests" / f"{stamp}.json"
    run_root.mkdir(parents=True, exist_ok=False)
    manifest: dict[str, object] = {
        "version": 1,
        "started_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "mode": mode,
        "rerun": rerun,
        "pipeline_fingerprint": fingerprint,
        "jobs": [],
    }
    results: list[dict[str, object]] = []
    queue_started = time.monotonic()

    for index, job in enumerate(jobs, 1):
        key = completion_key(job, mode, fingerprint)
        previous = entries.get(key)
        if isinstance(previous, dict) and should_skip(previous, rerun):
            result = {
                "stem": job.stem,
                "company": job.company,
                "role": job.role,
                "status": "skipped",
                "execution_status": "skipped",
                "submission_readiness": previous.get("submission_readiness", "review-required"),
                "resume_audit_state": previous.get("resume_audit_state", "UNKNOWN"),
                "duration_seconds": 0.0,
                "completion_key": key,
                "artifacts": previous.get("artifacts", []),
                "reason": f"unchanged prior {previous.get('status')} entry with all artifacts present",
            }
            results.append(result)
            manifest["jobs"] = results
            atomic_json(manifest_path, manifest)
            print(f"[{index}/{len(jobs)}] SKIPPED {job.company} - {job.role}", flush=True)
            continue

        print(f"[{index}/{len(jobs)}] {job.company} - {job.role}", flush=True)
        parse_result = requirement_engine.parse_commercial_posting(job.posting_text)
        before_artifacts = directory_snapshot(output_dir)
        environment = _job_environment(
            job,
            input_dir=run_root / "inputs" / job.stem,
            output_dir=output_dir,
            render_dir=render_dir,
        )
        command = [str(PYTHON_EXECUTABLE), str(project_root / "tasks.py"), "resume"]
        if mode == "resume-only":
            command.append("--resume-only")
        started = time.monotonic()
        try:
            completed = runner(
                command,
                cwd=project_root,
                env=environment,
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            completed = subprocess.CompletedProcess(command, 1, "", f"Queue child could not start: {exc}")
        duration = time.monotonic() - started
        artifacts = artifacts_for_job(changed_artifacts(output_dir, before_artifacts), job)
        status = status_for_result(completed.returncode, parse_result.verified, artifacts)
        resume_audit_state = resume_audit_state_from_output(completed.stdout or "")
        submission_readiness = submission_readiness_for_result(
            status=status,
            returncode=completed.returncode,
            resume_audit_state=resume_audit_state,
            artifacts=artifacts,
        )
        blocker_reason = blocker_reason_from_output(completed.stdout or "", submission_readiness)
        stage_timings = stage_timings_from_output(completed.stdout or "")
        log_path = run_root / f"{job.stem}.log"
        log_path.write_text(
            f"COMMAND: {' '.join(command)}\nRETURN CODE: {completed.returncode}\nSTATUS: {status}\n"
            f"DURATION: {duration:.1f}s\nPARSE MODE: {parse_result.parse_mode}\n"
            f"\nSTDOUT\n{completed.stdout or ''}\n\nSTDERR\n{completed.stderr or ''}\n",
            encoding="utf-8",
        )
        result = {
            "stem": job.stem,
            "company": job.company,
            "role": job.role,
            "status": status,
            "execution_status": "completed" if status in {"success", "fallback-warning", "review-required"} else status,
            "submission_readiness": submission_readiness,
            "resume_audit_state": resume_audit_state,
            "blocker_reason": blocker_reason,
            "stage_timings_seconds": stage_timings,
            "returncode": completed.returncode,
            "duration_seconds": round(duration, 3),
            "cumulative_seconds": round(time.monotonic() - queue_started, 3),
            "completion_key": key,
            "posting_hash": job.posting_hash,
            "questions_hash": job.questions_hash,
            "workflow_mode": mode,
            "pipeline_fingerprint": fingerprint,
            "parse_mode": parse_result.parse_mode,
            "parse_verified": parse_result.verified,
            "artifacts": artifacts,
            "log": str(log_path.resolve()),
        }
        results.append(result)
        entries[key] = result
        state["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        atomic_json(state_path, state)
        manifest["jobs"] = results
        atomic_json(manifest_path, manifest)
        display_status = submission_readiness.replace("-", " ").title()
        print(f"  Completed — {display_status}; {duration:.1f}s; log {log_path}", flush=True)

    active_after = active_hash_provider(project_root)
    if active_before != active_after:
        raise RuntimeError("Queue execution changed one or more active job/context files")
    cumulative = time.monotonic() - queue_started
    apply_queue_boilerplate_warnings(results)
    manifest.update(
        {
            "completed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "cumulative_seconds": round(cumulative, 3),
            "active_files_unchanged": True,
            "jobs": results,
        }
    )
    atomic_json(manifest_path, manifest)
    print(f"\nQueue complete in {cumulative:.1f}s", flush=True)
    for status_name in STATUS_ORDER:
        matching = [result for result in results if result["status"] == status_name]
        if matching:
            print(f"  {status_name}: {len(matching)}", flush=True)
    for readiness_name in ("ready", "review-required", "blocked"):
        matching = [result for result in results if result.get("submission_readiness") == readiness_name]
        if matching:
            print(f"  submission {readiness_name}: {len(matching)}", flush=True)
    print(f"Manifest: {manifest_path}", flush=True)
    return (1 if any(result["status"] in {"failed", "timed-out"} for result in results) else 0), manifest_path, results


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume-only", action="store_true", help="Build only the resume for every posting.")
    parser.add_argument("--rerun", action="store_true", help="Bypass completed-entry skips.")
    parser.add_argument("--queue-dir", type=Path, default=DEFAULT_QUEUE_DIR, help=argparse.SUPPRESS)
    parser.add_argument("--state-root", type=Path, default=DEFAULT_STATE_ROOT, help=argparse.SUPPRESS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help=argparse.SUPPRESS)
    parser.add_argument("--render-dir", type=Path, default=DEFAULT_RENDER_DIR, help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return execute_queue(
            queue_dir=args.queue_dir.resolve(),
            state_root=args.state_root.resolve(),
            output_dir=args.output_dir.resolve(),
            render_dir=args.render_dir.resolve(),
            mode="resume-only" if args.resume_only else "full",
            rerun=args.rerun,
        )[0]
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
