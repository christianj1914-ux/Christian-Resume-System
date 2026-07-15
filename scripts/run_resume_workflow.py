#!/usr/bin/env python3
"""Run the resume workflow with basic recovery instead of a bare batch failure."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from config.paths import (
    APPLICATION_QUESTIONS,
    JOB_DESCRIPTION,
    PYTHON_EXECUTABLE,
    SCRIPTS_DIR,
    SCRATCH_RENDER_LOGS,
    SOURCE_DIR,
)
import job_context_archive
from utils import read_text, remove_linkedin_hyperlinks, validate_job_description
import workspace_health

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = SCRATCH_RENDER_LOGS
PYTHON = PYTHON_EXECUTABLE
SOURCE_DOCX_NAMES = (
    "Estrada_Resume_Implementation.docx",
    "Estrada_Resume_PreSales_CSM.docx",
    "Christian_Estrada_KPMG_Final_Tightened_EdFix.docx",
)
DRY_RUN_INVALID_TITLES = {
    "about the role",
    "basic qualifications",
    "essential duties",
    "essential responsibilities",
    "job description",
    "preferred qualifications",
    "qualifications",
    "responsibilities",
    "the role",
    "what you will do",
    "what you'll do",
}


@dataclass(frozen=True)
class StepResult:
    name: str
    returncode: int
    stdout: str
    stderr: str
    log_path: Path
    specificity_warnings: list[str]
    cover_warnings: list[str]
    preflight_warnings: list[str]
    trace_path: Path | None = None

    @property
    def output(self) -> str:
        return "\n".join(part for part in (self.stdout, self.stderr) if part)

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def write_log(step_name: str, stdout: str, stderr: str) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", step_name).strip("_").lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = LOG_DIR / f"{timestamp}_{safe_name}.log"
    snapshot_id = os.environ.get("JOB_CONTEXT_SNAPSHOT_ID", "").strip()
    snapshot_line = f"JOB CONTEXT SNAPSHOT: {snapshot_id}\n" if snapshot_id else ""
    path.write_text(
        f"STEP: {step_name}\n{snapshot_line}\nSTDOUT\n{stdout}\n\nSTDERR\n{stderr}\n",
        encoding="utf-8",
    )
    return path


def run_step(step_name: str, script_name: str) -> StepResult:
    print(f"\n{step_name}...")
    result = subprocess.run(
        [str(PYTHON), str(SCRIPTS_DIR / script_name)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    log_path = write_log(step_name, result.stdout, result.stderr)
    if result.stdout.strip():
        print(result.stdout.strip())
    output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    trace_match = re.search(r"COVER LETTER TRACE:\s*(.+)", output)
    trace_path = Path(trace_match.group(1).strip()) if trace_match else None
    specificity_warnings: list[str] = []
    cover_warnings: list[str] = []
    preflight_warnings: list[str] = []
    if result.returncode != 0:
        print_failure_summary(step_name, result.stdout, result.stderr, log_path)
    else:
        try:
            specificity_warnings, cover_warnings, preflight_warnings = repair_generated_docx_outputs(output)
        except Exception as error:  # noqa: BLE001
            failure_stderr = (result.stderr.rstrip() + "\n" if result.stderr.strip() else "") + f"ERROR: {error}\n"
            log_path = write_log(step_name, result.stdout, failure_stderr)
            print_failure_summary(step_name, result.stdout, failure_stderr, log_path)
            return StepResult(
                name=step_name,
                returncode=1,
                stdout=result.stdout,
                stderr=failure_stderr,
                log_path=log_path,
                trace_path=trace_path,
                specificity_warnings=[],
                cover_warnings=[],
                preflight_warnings=[],
            )
    return StepResult(
        name=step_name,
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        log_path=log_path,
        trace_path=trace_path,
        specificity_warnings=specificity_warnings,
        cover_warnings=cover_warnings,
        preflight_warnings=preflight_warnings,
    )


def generated_docx_paths(stdout: str) -> list[Path]:
    paths: list[Path] = []
    for match in re.finditer(r"Output DOCX:\s*(.+?\.docx)", stdout):
        candidate = Path(match.group(1).strip())
        if candidate.exists():
            paths.append(candidate)
    return paths


def repack_docx(temp_root: Path, docx_path: Path) -> None:
    replacement = docx_path.with_suffix(".repairing.docx")
    with zipfile.ZipFile(replacement, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in temp_root.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(temp_root).as_posix())
    with zipfile.ZipFile(replacement) as archive:
        bad_file = archive.testzip()
        if bad_file:
            replacement.unlink(missing_ok=True)
            raise RuntimeError(f"DOCX package validation failed at {bad_file}")
    replacement.replace(docx_path)


def repair_docx_open_issues(docx_path: Path) -> int:
    with zipfile.ZipFile(docx_path) as archive:
        bad_file = archive.testzip()
        if bad_file:
            raise RuntimeError(f"DOCX package validation failed at {bad_file}")
    with tempfile.TemporaryDirectory(prefix="resume_docx_repair_") as temp_name:
        temp_root = Path(temp_name)
        with zipfile.ZipFile(docx_path) as archive:
            archive.extractall(temp_root)
        changes = remove_linkedin_hyperlinks(temp_root)
        if changes:
            repack_docx(temp_root, docx_path)
        return changes


def warning_lines_from_output(output: str, prefix: str) -> list[str]:
    warnings: list[str] = []
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            warnings.append(stripped.removeprefix(prefix).strip())
    return warnings


def specificity_warnings_from_output(output: str) -> list[str]:
    return warning_lines_from_output(output, "SPECIFICITY WARNING:")


def cover_warnings_from_output(output: str) -> list[str]:
    return warning_lines_from_output(output, "COVER LETTER WARNING:")


def preflight_warnings_from_output(output: str) -> list[str]:
    return warning_lines_from_output(output, "COVER LETTER PREFLIGHT:")


def repair_generated_docx_outputs(output: str) -> tuple[list[str], list[str], list[str]]:
    specificity_warnings = specificity_warnings_from_output(output)
    cover_warnings = cover_warnings_from_output(output)
    preflight_warnings = preflight_warnings_from_output(output)
    docx_errors: list[str] = []
    for docx_path in generated_docx_paths(output):
        try:
            changes = repair_docx_open_issues(docx_path)
        except Exception as error:  # noqa: BLE001
            docx_errors.append(f"{docx_path.name}: {type(error).__name__}: {error}")
            continue
        if changes:
            print(f"Post-build DOCX repair: removed LinkedIn hyperlink relationship from {docx_path.name}.")
    if docx_errors:
        raise RuntimeError("Post-build DOCX validation failed: " + "; ".join(docx_errors))
    return specificity_warnings, cover_warnings, preflight_warnings


def run_tracker_auto_add() -> None:
    tracker = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "track_applications.py"), "add", "--status", "draft", "--notes", "Auto-tracked by resume workflow."],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if tracker.returncode == 0:
        print(tracker.stdout.strip())
    else:
        detail = (tracker.stderr or tracker.stdout).strip()
        if detail:
            print(f"Application tracker was not updated automatically. Underlying error: {detail}")
        else:
            print("Application tracker was not updated automatically. Run python tasks.py track if needed.")


def underlying_error_line(stdout: str, stderr: str) -> str:
    output = "\n".join(part for part in (stdout, stderr) if part)
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    for line in lines:
        if line.startswith("ERROR:"):
            return "SystemExit: " + line.removeprefix("ERROR:").strip()
    for line in reversed(lines):
        if re.search(r"\b[A-Za-z_]+(?:Error|Exception):\s+", line):
            return line
    if lines:
        return lines[-1]
    return ""


def print_failure_summary(step_name: str, stdout: str, stderr: str, log_path: Path) -> None:
    output = "\n".join(part for part in (stdout, stderr) if part)
    useful_lines = [
        line.strip()
        for line in output.splitlines()
        if line.strip() and (
            line.startswith("ERROR:")
            or "TRACE:" in line
            or "Traceback" in line
            or "PermissionError" in line
            or "FileNotFoundError" in line
            or "render" in line.lower()
        )
    ]
    if not useful_lines:
        useful_lines = [line.strip() for line in output.splitlines() if line.strip()][-8:]
    print(f"{step_name} did not finish.")
    root_cause = underlying_error_line(stdout, stderr)
    if root_cause:
        print(f"  Underlying error: {root_cause}")
    for line in useful_lines[-8:]:
        print(f"  {line}")
    print(f"Full log: {log_path}")


def failure_kind(result: StepResult) -> str:
    output = result.output.lower()
    if "resume gap blocker" in output:
        return "resume_gap_blocker"
    if "jobs/job_description.txt is empty" in output or "job description is empty" in output:
        return "empty_job_description"
    if "could not determine company name or job title" in output:
        return "missing_output_name"
    if "not found:" in output:
        return "missing_required_file"
    if "matching resume output not found" in output:
        return "missing_resume_output"
    if "permissionerror" in output or "being used by another process" in output or "access is denied" in output:
        return "file_locked"
    if "render_docx" in output or "artifact-tool" in output or "timed out" in output:
        return "render_or_timeout"
    if "traceback" in output:
        return "unexpected_traceback"
    return "validation_failure"


def resume_gap_blocker_message_from_output(output: str) -> str:
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("Resume bridge gaps:"):
            return stripped.removeprefix("Resume bridge gaps:").strip()
        if stripped.startswith("Resume gap blockers:"):
            return stripped.removeprefix("Resume gap blockers:").strip()
    return ""


def explain_unresolved(result: StepResult) -> None:
    kind = failure_kind(result)
    print("\nI could not safely repair this one automatically.")
    if result.trace_path:
        print(f"Cover-letter trace: {result.trace_path}")
    if kind == "empty_job_description":
        print("Next action: paste one complete job posting into jobs\\job_description.txt, then run again.")
    elif kind == "missing_output_name":
        print("Next action: add a clear Company: or Job Title: line at the top of jobs\\job_description.txt.")
    elif kind == "missing_required_file":
        print("Next action: restore the missing source file named in the message above.")
    elif kind == "file_locked":
        print("Next action: close the matching Word document in the output or render_check folder, then run again.")
    elif kind == "resume_gap_blocker":
        print("Next action: fix the resume blockers listed above first. The system stopped before building downstream documents that would overstate the fit.")
    elif kind == "validation_failure":
        print("Next action: review the validation message above. The system stopped to avoid creating a partial or unsafe file.")
    else:
        print("Next action: review the log above. The system stopped before creating a partial or unsafe file.")


def run_with_recovery(step_name: str, script_name: str, *, can_rebuild_resume: bool = False) -> StepResult:
    first = run_step(step_name, script_name)
    if first.ok:
        return first

    kind = failure_kind(first)
    if can_rebuild_resume and kind == "missing_resume_output":
        print("\nRecovery: the matching resume was missing, so I am rebuilding the resume and retrying this step.")
        rebuilt = run_with_recovery("Building resume", "build_resume.py")
        if not rebuilt.ok:
            return rebuilt
        retry = run_step(f"{step_name} retry", script_name)
        if retry.ok:
            print("Recovery succeeded.")
        return retry

    if kind in {"render_or_timeout", "unexpected_traceback"}:
        print("\nRecovery: retrying once in case this was a temporary render or file-system issue.")
        retry = run_step(f"{step_name} retry", script_name)
        if retry.ok:
            print("Recovery succeeded.")
        return retry

    return first


def dry_run_failure(failures: list[str], message: str) -> None:
    failures.append(message)
    print(f"FAIL: {message}")


def top_keyword_scores(build_resume: object, job_description: str) -> list[tuple[str, int]]:
    ranked: dict[str, int] = {}
    for keyword in build_resume.audit_keywords(job_description):
        display_keyword = re.sub(r"\s+", " ", keyword).strip(" .")
        if not display_keyword:
            continue
        score = build_resume.keyword_hits(job_description, {keyword})
        if score <= 0:
            continue
        ranked[display_keyword] = max(ranked.get(display_keyword, 0), score)
    scored = list(ranked.items())
    scored.sort(
        key=lambda item: (
            *build_resume.audit_keyword_sort_key(job_description, item[0]),
            item[1],
        ),
        reverse=True,
    )
    return scored[:10]


def matching_resume_outputs(build_resume: object, job_description: str) -> list[Path]:
    return build_resume.matching_output_files(build_resume.OUTPUT_DIR, job_description, "Resume.docx")


def dry_run_valid_role_title(role_title: str | None) -> bool:
    if not role_title:
        return False
    normalized = re.sub(r"\s+", " ", role_title).strip().lower().rstrip(":")
    return normalized not in DRY_RUN_INVALID_TITLES


def run_dry_run() -> int:
    question_prep = load_question_prep_module()
    failures: list[str] = []
    print("\nDry-run validation: no files will be written.")

    if not JOB_DESCRIPTION.exists():
        dry_run_failure(failures, "jobs/job_description.txt does not exist.")
        job_description = ""
    else:
        job_description = read_text(JOB_DESCRIPTION)
        if not job_description:
            dry_run_failure(failures, "jobs/job_description.txt is empty.")
        else:
            print("OK: jobs/job_description.txt exists and is non-empty.")

    missing_sources = [
        name
        for name in SOURCE_DOCX_NAMES
        if not (SOURCE_DIR / name).is_file()
    ]
    if missing_sources:
        for name in missing_sources:
            dry_run_failure(failures, f"source/{name} is missing.")
    else:
        print("OK: all three source DOCX files exist.")

    try:
        import build_resume
    except Exception as error:  # noqa: BLE001
        dry_run_failure(failures, f"could not import build_resume: {error}")
        return 1

    if not job_description:
        print("\nDry-run stopped after file checks because the job description is not readable.")
        return 1

    prompt_state = question_prep.load_application_prompt_state()
    if prompt_state.uses_default_questions and not prompt_state.explicit_prompts:
        print("NOTE: jobs/application_questions.txt is empty; using default role-interest question.")
    elif prompt_state.uses_default_questions:
        print("NOTE: jobs/application_questions.txt contains only the default role-interest question.")
    else:
        print("OK: jobs/application_questions.txt contains active application questions.")

    try:
        validated_job_description = build_resume.validate_inputs()
        company_name = build_resume.extract_company_name(validated_job_description)
        role_title = build_resume.extract_job_title(validated_job_description)
        output_name = build_resume.extract_output_name(validated_job_description)
        if not company_name:
            dry_run_failure(failures, "could not determine a valid company name from jobs/job_description.txt.")
        if not dry_run_valid_role_title(role_title):
            dry_run_failure(failures, "could not determine a valid job title from jobs/job_description.txt.")
        if company_name and dry_run_valid_role_title(role_title):
            print(f"OK: detected company and title: {company_name} - {role_title}.")
    except SystemExit as error:
        dry_run_failure(failures, f"validate_inputs() failed: {error}")
        validated_job_description = job_description
        output_name = build_resume.extract_company_name(job_description) or build_resume.extract_job_title(job_description) or "Unknown"
    except Exception as error:  # noqa: BLE001
        dry_run_failure(failures, f"validate_inputs() failed: {error}")
        validated_job_description = job_description
        output_name = build_resume.extract_company_name(job_description) or build_resume.extract_job_title(job_description) or "Unknown"

    selected_resume = build_resume.choose_resume(validated_job_description)
    presales_matches = sorted(
        signal
        for signal in build_resume.PRESALES_SIGNALS
        if signal in validated_job_description.lower()
    )
    if selected_resume == build_resume.PRESALES_CSM_RESUME:
        reason = f"selected because at least two Pre-Sales/CSM signals matched: {', '.join(presales_matches[:8])}."
    else:
        reason = (
            "selected because fewer than two Pre-Sales/CSM signals matched"
            + (f" ({', '.join(presales_matches)})." if presales_matches else ".")
        )
    print(f"Source resume that would be used: {selected_resume.name} - {reason}")

    selected_resume_text = build_resume.docx_visible_text_from_path(selected_resume)
    profile = build_resume.job_problem_profile(validated_job_description, selected_resume_text)
    print("\nDetected job profile:")
    print(f"  Lane: {profile.primary_lane} ({profile.lane_label})")
    print(f"  Core problem: {profile.core_problem}")
    print(f"  Direct matches: {', '.join(profile.direct_matches) if profile.direct_matches else 'No direct matches detected'}")
    print(f"  Adjacent matches: {', '.join(profile.adjacent_matches) if profile.adjacent_matches else 'No adjacent matches detected'}")
    print(f"  Unsupported requirements: {', '.join(profile.unsupported_requirements) if profile.unsupported_requirements else 'No unsupported requirements detected'}")

    top_keywords = top_keyword_scores(build_resume, validated_job_description)
    print("\nTop keyword signals:")
    if top_keywords:
        for keyword, hits in top_keywords:
            print(f"  {keyword} ({hits})")
    else:
        dry_run_failure(failures, "audit_keywords() did not find any usable keywords.")

    existing_resumes = matching_resume_outputs(build_resume, validated_job_description)
    print("\nDependent document readiness:")
    if existing_resumes:
        print(f"  Matching resume exists: {existing_resumes[0].name}")
        readiness = build_resume.resume_readiness_for_output(
            validated_job_description,
            existing_resumes[0],
            source_resume_text=selected_resume_text,
            audit_status="PASS",
        )
        if readiness.hard_blockers:
            print("  Cover letter can still build, but it should bridge these resume gaps honestly:")
            for gap in readiness.hard_blockers[:3]:
                print(f"    - {build_resume.resume_gap_summary_line(gap)}")
        else:
            print("  Cover letter build would have the resume it needs.")
        print("  Interview guide builds would have the resume they need.")
    else:
        print(f"  No matching resume found for: {build_resume.extract_output_target_name(validated_job_description)}")
        print("  Cover letter build would require a resume build first.")
        print("  Interview guide builds would require a resume build first.")

    if failures:
        print("\nDry-run FAILED.")
        return 1

    print("\nDry-run PASSED.")
    return 0


def load_question_prep_module() -> object:
    import question_prep

    return question_prep


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the tailored resume workflow with recovery.")
    parser.add_argument("--resume-only", action="store_true", help="Build only the tailored resume and skip dependent documents.")
    parser.add_argument("--include-cheat-sheet", action="store_true", help="Also build the standard interview cheat sheet.")
    parser.add_argument("--include-detailed-guide", action="store_true", help="Also build the deep interview guide.")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs and print the planned workflow without writing files.")
    parser.add_argument("--skip-cover-letter", action="store_true", help="Skip the cover letter step (for temp/recruiter roles where no cover letter is needed).")
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    if args.resume_only and (args.include_cheat_sheet or args.include_detailed_guide):
        raise SystemExit("--resume-only cannot be combined with interview-output options.")
    workspace_health.ensure_workspace_health_or_exit("The standard commercial workflow")
    if args.dry_run:
        raise SystemExit(run_dry_run())
    question_prep = load_question_prep_module()
    validate_job_description(JOB_DESCRIPTION)
    pairing_issue = job_context_archive.application_question_pairing_issue(
        read_text(JOB_DESCRIPTION),
        read_text(APPLICATION_QUESTIONS),
    )
    if pairing_issue:
        raise SystemExit(
            "Application-question/JD swap check stopped the workflow. "
            + pairing_issue
            + " Replace or clear jobs/application_questions.txt for the active target, then run again."
        )
    question_prep.require_active_application_prompts(
        workflow_name="The standard commercial workflow",
    )

    required_steps = [
        ("Building resume", "build_resume.py", False),
    ]
    resume_only = getattr(args, "resume_only", False)
    skip_cover_letter = resume_only or getattr(args, "skip_cover_letter", False)
    if not skip_cover_letter:
        required_steps.append(("Building cover letter", "build_cover_letter.py", True))
    if not resume_only:
        required_steps.append(("Building qualifications statement", "build_standard_qualifications_statement.py", True))
    optional_steps: list[tuple[str, str, bool]] = []
    if args.include_cheat_sheet:
        optional_steps.append(("Building interview cheat sheet", "build_interview_cheat_sheet.py", True))
    if args.include_detailed_guide:
        optional_steps.append(("Building deep interview guide", "build_detailed_interview_guide.py", True))

    cover_specificity_warnings: list[str] = []
    cover_warnings: list[str] = []
    cover_preflight_warnings: list[str] = []
    resume_gap_blockers = ""
    draft_artifact_created = False
    for step_name, script_name, can_rebuild_resume in required_steps:
        result = run_with_recovery(step_name, script_name, can_rebuild_resume=can_rebuild_resume)
        if not result.ok:
            explain_unresolved(result)
            raise SystemExit(result.returncode)
        if script_name == "build_resume.py":
            resume_gap_blockers = resume_gap_blocker_message_from_output(result.output)
        if script_name == "build_cover_letter.py":
            cover_specificity_warnings.extend(result.specificity_warnings)
            cover_warnings.extend(result.cover_warnings)
            cover_preflight_warnings.extend(result.preflight_warnings)
        if re.search(r"(?:Final audit:\s*DRAFT|Output DOCX:.*\bDRAFT\b)", result.output, re.I):
            draft_artifact_created = True
            print("Workflow stopped: a DRAFT artifact was created and is excluded from downstream builders and tracker updates.")
            break
    if draft_artifact_created:
        raise SystemExit(2)
    run_tracker_auto_add()
    if resume_only:
        print("\nDone. Resume-only build complete. Check the output folder and render_check folder.")
        if resume_gap_blockers:
            print("\nResume bridge guidance for this role:")
            print(f"  {resume_gap_blockers}")
        return
    for step_name, script_name, can_rebuild_resume in optional_steps:
        result = run_with_recovery(step_name, script_name, can_rebuild_resume=can_rebuild_resume)
        if not result.ok:
            explain_unresolved(result)
            raise SystemExit(result.returncode)

    print("\nDone. Check the output folder and render_check folder.")
    if cover_specificity_warnings:
        print("\nCover letter specificity warnings to resolve before submission:")
        for warning in cover_specificity_warnings:
            print(f"  SPECIFICITY WARNING: {warning}")
    if cover_warnings:
        print("\nCover letter warnings to review before submission:")
        for warning in cover_warnings:
            print(f"  COVER LETTER WARNING: {warning}")
    if cover_preflight_warnings:
        print("\nCover letter preflight warnings to review before submission:")
        for warning in cover_preflight_warnings:
            print(f"  COVER LETTER PREFLIGHT: {warning}")
    if not args.include_detailed_guide:
        print("For a long sample-answer interview guide, choose the deep interview guide option in run_resume.bat when needed.")
    if resume_gap_blockers:
        print("\nResume bridge guidance for this role:")
        print(f"  {resume_gap_blockers}")


if __name__ == "__main__":
    main()
