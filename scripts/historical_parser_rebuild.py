#!/usr/bin/env python3
"""Rebuild and compare the known commercial parser blast radius in isolation."""

from __future__ import annotations

import argparse
import contextlib
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator

import build_resume
import requirement_engine
import resume_analysis
from config.paths import PYTHON_EXECUTABLE


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = PROJECT_ROOT / "scratch" / "jd_library"
OUTPUT = PROJECT_ROOT / "output"
AUDIT_ROOT = PROJECT_ROOT / "scratch" / "parser_rebuild_audit"


@dataclass(frozen=True)
class RebuildCase:
    key: str
    snapshot_id: str
    baseline_resume: str
    baseline_notes: str
    control: bool = False


CASES = (
    RebuildCase(
        "epicor",
        "20260810_183525_Epicor_Associate_Consulting_Services_Project_Manager_Building_Supply_dbfa7a02",
        "Christian Estrada - Epicor - Associate Consulting Services Project Manager Building Supply BRIDGE Resume.docx",
        "Christian Estrada - Epicor - Associate Consulting Services Project Manager Building Supply BRIDGE Resume Notes.txt",
    ),
    RebuildCase(
        "paylocity_client",
        "20260806_152257_Paylocity_Client_Project_Manager_Ops_931aca9f",
        "Christian Estrada - Paylocity - Client Project Manager Ops FAIL Resume.docx",
        "Christian Estrada - Paylocity - Client Project Manager Ops FAIL Resume Notes.txt",
    ),
    RebuildCase(
        "paylocity_senior_it",
        "20260806_133647_Paylocity_Senior_IT_Project_Manager_Enterprise_Applications_43e8e167",
        "Christian Estrada - Paylocity - Senior IT Project Manager Enterprise Applications FAIL Resume.docx",
        "Christian Estrada - Paylocity - Senior IT Project Manager Enterprise Applications FAIL Resume Notes.txt",
    ),
    RebuildCase(
        "aptean_bridge",
        "20260729_190957_Aptean_ERP_Consultant_0463523a",
        "Christian Estrada - Aptean - ERP Consultant BRIDGE Resume.docx",
        "Christian Estrada - Aptean - ERP Consultant BRIDGE Resume Notes.txt",
    ),
    RebuildCase(
        "aptean_fail",
        "20260730_003531_Aptean_ERP_Consultant_38dc2514",
        "Christian Estrada - Aptean - ERP Consultant FAIL Resume.docx",
        "Christian Estrada - Aptean - ERP Consultant FAIL Resume Notes.txt",
    ),
    RebuildCase(
        "paylocity_release_control",
        "20260806_150155_Paylocity_Project_Manager_Release_Operations_Ops_ad8a5583",
        "Christian Estrada - Paylocity - Project Manager Release Operations Ops FAIL Resume.docx",
        "Christian Estrada - Paylocity - Project Manager Release Operations Ops FAIL Resume Notes.txt",
        True,
    ),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def active_hashes() -> dict[str, str]:
    paths = (
        PROJECT_ROOT / "jobs" / "job_description.txt",
        PROJECT_ROOT / "jobs" / "application_questions.txt",
        PROJECT_ROOT / "jobs" / "company_research.txt",
        PROJECT_ROOT / "jobs" / "interview_notes.txt",
    )
    return {str(path): sha256(path) if path.exists() else "<missing>" for path in paths}


def _clear_analysis_caches() -> None:
    for function in (
        resume_analysis.commercial_analysis_context,
        resume_analysis.classify_keyword_candidate,
        resume_analysis._audit_keywords_cached,
        resume_analysis._high_value_audit_keywords_cached,
        resume_analysis._ats_scan_terms_cached,
    ):
        function.cache_clear()


@contextlib.contextmanager
def legacy_parser_behavior() -> Iterator[None]:
    original = requirement_engine.parse_commercial_posting

    def legacy(job_description: str) -> requirement_engine.CommercialParseResult:
        requirements = requirement_engine.parse_commercial_requirements_legacy(job_description)
        sections = requirement_engine._legacy_commercial_requirement_sections(job_description)
        verified = bool(requirements)
        return requirement_engine.CommercialParseResult(
            sections=sections if verified else (),
            requirements=requirements,
            parse_mode="structured" if verified else "whole_posting_fallback",
            diagnostics=(),
            verified=verified,
        )

    _clear_analysis_caches()
    requirement_engine.parse_commercial_posting = legacy
    try:
        yield
    finally:
        requirement_engine.parse_commercial_posting = original
        _clear_analysis_caches()


def note_value(text: str, label: str) -> str:
    match = re.search(rf"(?im)^{re.escape(label)}:\s*(.+?)\s*$", text)
    return match.group(1).strip() if match else ""


def note_alignment_score(text: str) -> str:
    match = re.search(r"Final tailored alignment score is\s+(\d+/\d+)", text, re.I)
    return match.group(1) if match else ""


def _diff_lines(old: tuple[str, ...], new: tuple[str, ...]) -> list[str]:
    return list(difflib.unified_diff(old, new, fromfile="baseline", tofile="rebuilt", lineterm=""))


def _analysis(job_description: str, resume_path: Path) -> dict[str, object]:
    resume_text = build_resume.docx_visible_text_from_path(resume_path)
    snapshot = build_resume.resume_variable_snapshot_from_docx(resume_path)
    alignment = build_resume.alignment_score_report(job_description, resume_text)
    ats_coverage = build_resume.ats_coverage(job_description, resume_text)
    return {
        "core_keywords": sorted(resume_analysis.high_value_audit_keywords(job_description)),
        "breadth_keywords": resume_analysis.ats_scan_terms(job_description, limit=200),
        "alignment_score": alignment["total_score"],
        "alignment_max": alignment["score_scale_max"],
        "alignment_grade": alignment["grade"],
        "requirement_coverage": alignment["requirement_coverage"],
        "ats_coverage": ats_coverage,
        "lane": resume_analysis.job_problem_profile(job_description, resume_text).lane_label,
        "source_resume": resume_analysis.choose_resume(job_description).name,
        "summary": snapshot.summary,
        "competency_labels": list(snapshot.competency_labels),
        "competency_items": list(snapshot.competency_items),
        "role_summaries": list(snapshot.role_summaries),
        "bullets": list(snapshot.bullets),
        "unsupported_claims": build_resume.unsupported_platform_action_claims(resume_text),
    }


def compare_case(
    case: RebuildCase,
    job_description: str,
    baseline_resume: Path,
    baseline_notes: Path,
    rebuilt_resume: Path,
    rebuilt_notes: Path,
) -> dict[str, object]:
    old_parse_count = len(requirement_engine.parse_commercial_requirements_legacy(job_description))
    new_parse = requirement_engine.parse_commercial_posting(job_description)
    with legacy_parser_behavior():
        old_analysis = _analysis(job_description, baseline_resume)
    new_analysis = _analysis(job_description, rebuilt_resume)
    old_notes_text = baseline_notes.read_text(encoding="utf-8", errors="replace")
    new_notes_text = rebuilt_notes.read_text(encoding="utf-8", errors="replace")

    changes = {
        "summary_changed": old_analysis["summary"] != new_analysis["summary"],
        "competencies_added": sorted(set(new_analysis["competency_items"]) - set(old_analysis["competency_items"])),
        "competencies_removed": sorted(set(old_analysis["competency_items"]) - set(new_analysis["competency_items"])),
        "role_summary_diff": _diff_lines(tuple(old_analysis["role_summaries"]), tuple(new_analysis["role_summaries"])),
        "bullet_diff": _diff_lines(tuple(old_analysis["bullets"]), tuple(new_analysis["bullets"])),
    }
    old_status = note_value(old_notes_text, "Fit status")
    new_status = note_value(new_notes_text, "Fit status")
    grade_changed = (
        old_analysis["alignment_grade"] != new_analysis["alignment_grade"]
        or old_status != new_status
    )
    targeting_changed = (
        old_analysis["core_keywords"] != new_analysis["core_keywords"]
        or old_analysis["breadth_keywords"] != new_analysis["breadth_keywords"]
        or any(bool(value) for value in changes.values())
    )
    classification = (
        "fit grade/status changed"
        if grade_changed
        else "targeting changed with stable grade"
        if targeting_changed
        else "no material change"
    )
    historical_impact = (
        "Potential historical application impact: alignment grade or sendability status moved; preserve both artifacts and review this as application information, not an automatic correction."
        if grade_changed
        else ""
    )
    return {
        "case": case.key,
        "control": case.control,
        "snapshot_id": case.snapshot_id,
        "classification": classification,
        "potential_historical_application_impact": historical_impact,
        "old_parse_mode": "structured" if old_parse_count else "whole_posting_fallback",
        "old_requirement_count": old_parse_count,
        "new_parse_mode": new_parse.parse_mode,
        "new_requirement_count": len(new_parse.requirements),
        "new_parse_verified": new_parse.verified,
        "old_notes_reported_alignment_score": note_alignment_score(old_notes_text),
        "new_notes_reported_alignment_score": note_alignment_score(new_notes_text),
        "old_fit_status": old_status,
        "new_fit_status": new_status,
        "old": old_analysis,
        "new": new_analysis,
        "text_changes": changes,
        "baseline_resume": str(baseline_resume),
        "rebuilt_resume": str(rebuilt_resume),
    }


def _write_markdown(path: Path, payload: dict[str, object]) -> None:
    lines = [
        "# Commercial Parser Historical Rebuild Audit",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        "| Case | Control | Old parse | New parse | Old score/grade/status | New score/grade/status | Classification |",
        "|---|---:|---|---|---|---|---|",
    ]
    for row in payload["cases"]:
        old_score = row["old_notes_reported_alignment_score"] or f"{row['old']['alignment_score']}/{row['old']['alignment_max']}"
        new_score = row["new_notes_reported_alignment_score"] or f"{row['new']['alignment_score']}/{row['new']['alignment_max']}"
        lines.append(
            f"| {row['case']} | {'yes' if row['control'] else 'no'} | "
            f"{row['old_parse_mode']} ({row['old_requirement_count']}) | "
            f"{row['new_parse_mode']} ({row['new_requirement_count']}) | "
            f"{old_score} / {row['old']['alignment_grade']} / {row['old_fit_status']} | "
            f"{new_score} / {row['new']['alignment_grade']} / {row['new_fit_status']} | "
            f"{row['classification']} |"
        )
    impact_rows = [row for row in payload["cases"] if row["potential_historical_application_impact"]]
    if impact_rows:
        lines.extend(["", "## Potential Historical Application Impact", ""])
        for row in impact_rows:
            lines.append(f"- **{row['case']}**: {row['potential_historical_application_impact']}")
    lines.extend(["", "Both baseline and rebuilt artifacts are preserved under this audit directory."])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def refresh_existing(run_root: Path) -> int:
    active_before = active_hashes()
    comparisons: list[dict[str, object]] = []
    for case in CASES:
        case_root = run_root / case.key
        baseline_resumes = sorted((case_root / "baseline").glob("* Resume.docx"))
        baseline_notes = sorted((case_root / "baseline").glob("* Resume Notes.txt"))
        rebuilt_resumes = sorted((case_root / "rebuilt").glob("* Resume.docx"))
        rebuilt_notes = sorted((case_root / "rebuilt").glob("* Resume Notes.txt"))
        if not all(len(paths) == 1 for paths in (baseline_resumes, baseline_notes, rebuilt_resumes, rebuilt_notes)):
            raise RuntimeError(f"Existing audit case is incomplete: {case_root}")
        job_path = ARCHIVE / case.snapshot_id / "job_description.txt"
        comparisons.append(
            compare_case(
                case,
                job_path.read_text(encoding="utf-8-sig"),
                baseline_resumes[0],
                baseline_notes[0],
                rebuilt_resumes[0],
                rebuilt_notes[0],
            )
        )
    if active_before != active_hashes():
        raise RuntimeError("Historical parser comparison changed one or more active job/context files")
    payload: dict[str, object] = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "run_root": str(run_root),
        "active_files_unchanged": True,
        "cases": comparisons,
        "failures": [],
    }
    (run_root / "comparison.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_markdown(run_root / "comparison.md", payload)
    print(f"Historical rebuild report refreshed: {run_root / 'comparison.md'}", flush=True)
    return 0


def run(timeout_seconds: int = 600) -> int:
    active_before = active_hashes()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_root = AUDIT_ROOT / stamp
    run_root.mkdir(parents=True, exist_ok=False)
    comparisons: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []

    for index, case in enumerate(CASES, 1):
        print(f"[{index}/{len(CASES)}] {case.key}", flush=True)
        snapshot_dir = ARCHIVE / case.snapshot_id
        job_path = snapshot_dir / "job_description.txt"
        baseline_resume_source = OUTPUT / case.baseline_resume
        baseline_notes_source = OUTPUT / case.baseline_notes
        for required in (job_path, baseline_resume_source, baseline_notes_source):
            if not required.exists():
                raise FileNotFoundError(f"Required historical audit input is missing: {required}")

        case_root = run_root / case.key
        baseline_dir = case_root / "baseline"
        rebuilt_dir = case_root / "rebuilt"
        render_dir = case_root / "renders"
        input_dir = case_root / "inputs"
        for directory in (baseline_dir, rebuilt_dir, render_dir, input_dir):
            directory.mkdir(parents=True, exist_ok=True)
        baseline_resume = baseline_dir / baseline_resume_source.name
        baseline_notes = baseline_dir / baseline_notes_source.name
        shutil.copy2(baseline_resume_source, baseline_resume)
        shutil.copy2(baseline_notes_source, baseline_notes)
        job_copy = input_dir / "job_description.txt"
        shutil.copy2(job_path, job_copy)
        empty_paths = {}
        for name in ("application_questions", "company_research", "interview_notes"):
            empty_path = input_dir / f"{name}.txt"
            empty_path.write_text("", encoding="utf-8")
            empty_paths[name] = empty_path

        environment = os.environ.copy()
        environment.update(
            {
                "RESUME_JOB_DESCRIPTION_PATH": str(job_copy.resolve()),
                "RESUME_APPLICATION_QUESTIONS_PATH": str(empty_paths["application_questions"].resolve()),
                "RESUME_COMPANY_RESEARCH_PATH": str(empty_paths["company_research"].resolve()),
                "RESUME_INTERVIEW_NOTES_PATH": str(empty_paths["interview_notes"].resolve()),
                "RESUME_OUTPUT_DIR": str(rebuilt_dir.resolve()),
                "RESUME_RENDER_DIR": str(render_dir.resolve()),
                "PYTHONUNBUFFERED": "1",
            }
        )
        started = datetime.now()
        try:
            completed = subprocess.run(
                [str(PYTHON_EXECUTABLE), str(PROJECT_ROOT / "scripts" / "build_resume.py")],
                cwd=PROJECT_ROOT,
                env=environment,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            elapsed = (datetime.now() - started).total_seconds()
            (case_root / "build.log").write_text(
                f"RETURN CODE: {completed.returncode}\nELAPSED: {elapsed:.1f}s\n\nSTDOUT\n{completed.stdout}\n\nSTDERR\n{completed.stderr}\n",
                encoding="utf-8",
            )
        except subprocess.TimeoutExpired as exc:
            failures.append({"case": case.key, "reason": "timeout", "seconds": timeout_seconds})
            (case_root / "build.log").write_text(
                f"TIMEOUT: {timeout_seconds}s\n\nSTDOUT\n{exc.stdout or ''}\n\nSTDERR\n{exc.stderr or ''}\n",
                encoding="utf-8",
            )
            continue
        if completed.returncode != 0:
            failures.append({"case": case.key, "reason": "nonzero", "returncode": completed.returncode})
            continue
        rebuilt_resumes = sorted(rebuilt_dir.glob("* Resume.docx"))
        rebuilt_notes = sorted(rebuilt_dir.glob("* Resume Notes.txt"))
        if len(rebuilt_resumes) != 1 or len(rebuilt_notes) != 1:
            failures.append(
                {
                    "case": case.key,
                    "reason": "artifact_count",
                    "resumes": [path.name for path in rebuilt_resumes],
                    "notes": [path.name for path in rebuilt_notes],
                }
            )
            continue
        comparisons.append(
            compare_case(
                case,
                job_copy.read_text(encoding="utf-8-sig"),
                baseline_resume,
                baseline_notes,
                rebuilt_resumes[0],
                rebuilt_notes[0],
            )
        )

    active_after = active_hashes()
    if active_before != active_after:
        raise RuntimeError("Historical parser rebuild changed one or more active job/context files")
    payload: dict[str, object] = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "run_root": str(run_root),
        "active_files_unchanged": True,
        "cases": comparisons,
        "failures": failures,
    }
    (run_root / "comparison.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_markdown(run_root / "comparison.md", payload)
    print(f"Historical rebuild report: {run_root / 'comparison.md'}", flush=True)
    return 1 if failures else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=int, default=600, help="Per-resume build ceiling in seconds.")
    parser.add_argument("--existing-run", type=Path, help="Refresh comparison data for an existing completed audit without rebuilding.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.existing_run:
            return refresh_existing(args.existing_run.resolve())
        return run(timeout_seconds=args.timeout)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
