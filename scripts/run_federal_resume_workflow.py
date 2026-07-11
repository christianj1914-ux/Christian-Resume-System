#!/usr/bin/env python3
"""Run the federal resume workflow with basic recovery and dry-run support."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from config.paths import FEDERAL_ESSAY_SOURCE, FEDERAL_JOB_DESCRIPTION, FEDERAL_RESUME_SOURCE, OUTPUT_DIR, PYTHON_EXECUTABLE, SCRIPTS_DIR
import workspace_health

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON = PYTHON_EXECUTABLE
LOG_DIR = PROJECT_ROOT / "scratch" / "run_logs"


@dataclass(frozen=True)
class StepResult:
    name: str
    returncode: int
    stdout: str
    stderr: str
    log_path: Path

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
    path.write_text(
        f"STEP: {step_name}\n\nSTDOUT\n{stdout}\n\nSTDERR\n{stderr}\n",
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
    if result.returncode != 0:
        print(f"{step_name}: FAILED (log: {log_path})")
        print_failure_summary(step_name, result.stdout, result.stderr, log_path)
    else:
        print(f"{step_name}: SUCCESS (log: {log_path})")
    return StepResult(step_name, result.returncode, result.stdout, result.stderr, log_path)


def print_failure_summary(step_name: str, stdout: str, stderr: str, log_path: Path) -> None:
    output = "\n".join(part for part in (stdout, stderr) if part)
    useful_lines = [
        line.strip()
        for line in output.splitlines()
        if line.strip() and (
            line.startswith("ERROR:")
            or "TRACE:" in line
            or "Traceback" in line
            or "render" in line.lower()
            or "Federal ATS" in line
        )
    ]
    if not useful_lines:
        useful_lines = [line.strip() for line in output.splitlines() if line.strip()][-8:]
    print(f"{step_name} did not finish.")
    for line in useful_lines[-8:]:
        print(f"  {line}")
    print(f"Full log: {log_path}")


def explain_unresolved(result: StepResult) -> None:
    output = result.output.lower()
    print("\nI could not safely repair this federal build automatically.")
    if "federal_job_description.txt is empty" in output:
        print("Next action: paste one complete federal posting or questionnaire into jobs\\federal_job_description.txt, then run again.")
    elif "agency name or job title" in output:
        print("Next action: add an Agency: or Role: line near the top of jobs\\federal_job_description.txt.")
    elif "exactly two pages" in output or "10pt minimum" in output:
        print("Next action: tighten federal spacing or reprioritize bullets so the resume can stay at exactly two pages with 10pt body text.")
    else:
        print("Next action: review the log above. The system stopped before creating a partial or unsafe file.")


def matching_federal_outputs(company_name: str) -> list[Path]:
    if not OUTPUT_DIR.exists():
        return []
    return sorted(
        OUTPUT_DIR.glob(f"Christian Estrada - {company_name}*Federal Resume.docx"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )


def matching_federal_qualifications_outputs(company_name: str) -> list[Path]:
    if not OUTPUT_DIR.exists():
        return []
    return sorted(
        OUTPUT_DIR.glob(f"Christian Estrada - {company_name}*Federal Qualifications Statement.docx"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )


def top_keyword_scores(build_federal_resume: object, job_description: str) -> list[tuple[str, int]]:
    ranked: dict[str, int] = {}
    for keyword in build_federal_resume.audit_keywords(job_description):
        display = re.sub(r"\s+", " ", keyword).strip(" .")
        if not display:
            continue
        lowered = display.lower()
        if lowered in {
            "please",
            "receive",
            "detail",
            "responsibility",
            "government",
            "process",
            "specialist",
            "specialist ai",
            "receive training",
            "providing quality",
            "federal service",
        }:
            continue
        if len(display.split()) == 1 and len(display) < 5:
            continue
        score = build_federal_resume.keyword_hits(job_description, {keyword})
        if score <= 0:
            continue
        ranked[display] = max(ranked.get(display, 0), score)
    scored = list(ranked.items())
    scored.sort(
        key=lambda item: (
            *build_federal_resume.audit_keyword_sort_key(job_description, item[0]),
            item[1],
        ),
        reverse=True,
    )
    return scored[:10]


def run_dry_run() -> int:
    failures: list[str] = []
    print("\nFederal dry-run validation: no files will be written.")

    if not FEDERAL_JOB_DESCRIPTION.exists():
        failures.append("jobs/federal_job_description.txt does not exist.")
        print("FAIL: jobs/federal_job_description.txt does not exist.")
        job_description = ""
    else:
        job_description = FEDERAL_JOB_DESCRIPTION.read_text(encoding="utf-8-sig").strip()
        if not job_description:
            failures.append("jobs/federal_job_description.txt is empty.")
            print("FAIL: jobs/federal_job_description.txt is empty.")
        else:
            print("OK: jobs/federal_job_description.txt exists and is non-empty.")

    if not FEDERAL_RESUME_SOURCE.exists():
        failures.append("source/Christian_Estrada_Federal_Source.json is missing.")
        print("FAIL: source/Christian_Estrada_Federal_Source.json is missing.")
    else:
        print("OK: federal source JSON exists.")

    if not FEDERAL_ESSAY_SOURCE.exists():
        failures.append("source/Christian_Estrada_Federal_Standard_Essays.json is missing.")
        print("FAIL: source/Christian_Estrada_Federal_Standard_Essays.json is missing.")
    else:
        print("OK: federal standard essay source exists.")

    try:
        import build_federal_resume
    except Exception as error:  # noqa: BLE001
        print(f"FAIL: could not import build_federal_resume: {error}")
        return 1

    if not job_description:
        print("\nFederal dry-run stopped after file checks because the job description is not readable.")
        return 1

    try:
        validated = build_federal_resume.validate_inputs(job_description)
        agency_name = build_federal_resume.extract_federal_agency_name(validated)
        role_title = build_federal_resume.extract_federal_role_title(validated)
        output_name = build_federal_resume.extract_federal_output_name(validated)
        if not agency_name:
            failures.append("could not determine a federal agency name from jobs/federal_job_description.txt.")
            print("FAIL: could not determine a federal agency name from jobs/federal_job_description.txt.")
        if not role_title:
            failures.append("could not determine a federal role title from jobs/federal_job_description.txt.")
            print("FAIL: could not determine a federal role title from jobs/federal_job_description.txt.")
        if agency_name and role_title:
            print(f"OK: detected agency and title: {agency_name} - {role_title}.")
    except SystemExit as error:
        print(f"FAIL: validate_inputs() failed: {error}")
        return 1

    source = build_federal_resume.load_federal_source()
    profile = build_federal_resume.job_problem_profile(validated, build_federal_resume.source_visible_text(source))
    audit = build_federal_resume.federal_requirement_audit(source, validated)
    print("\nDetected federal job profile:")
    print(f"  Lane: {profile.primary_lane} ({profile.lane_label})")
    print(f"  Core problem: {profile.core_problem}")
    print(f"  Direct matches: {', '.join(profile.direct_matches) if profile.direct_matches else 'No direct matches detected'}")
    print(f"  Adjacent matches: {', '.join(profile.adjacent_matches) if profile.adjacent_matches else 'No adjacent matches detected'}")
    print(f"  Unsupported requirements: {', '.join(profile.unsupported_requirements) if profile.unsupported_requirements else 'No unsupported requirements detected'}")

    print("\nTop federal keyword signals:")
    for keyword, hits in top_keyword_scores(build_federal_resume, validated):
        print(f"  {keyword} ({hits})")

    print("\nFederal keyword targets:")
    for keyword in audit.keyword_targets:
        print(f"  {keyword}")

    temp_root = PROJECT_ROOT / "scratch" / f"federal_dry_run_{uuid.uuid4().hex}"
    temp_root.mkdir(parents=True, exist_ok=False)
    try:
        plan = build_federal_resume.resume_plan(temp_root, source, validated)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    print("\nFederal requirement audit:")
    for line in build_federal_resume.requirement_report_lines(plan.audit):
        print(f"  {line}")

    print("\nPlanned surviving bullets:")
    for line in build_federal_resume.selected_bullet_reference_lines(source, plan.bullet_groups):
        print(f"  {line}")

    print("\nFederal layout readiness:")
    print(
        f"  Resume layout: {plan.resume_layout.name} | Body font: {plan.resume_layout.font_size:.1f}pt | "
        f"Planned pages: {build_federal_resume.federal_page_count_label(plan.resume_page_count)}"
    )
    print(
        f"  Qualifications layout: {plan.qualifications_layout.name} | Body font: {plan.qualifications_layout.font_size:.1f}pt | "
        f"Planned pages: {build_federal_resume.federal_page_count_label(plan.qualifications_page_count)}"
    )
    if plan.audit.warnings:
        print("\nFederal fit warnings:")
        for warning in plan.audit.warnings:
            print(f"  {warning}")

    existing = matching_federal_outputs(output_name)
    existing_quals = matching_federal_qualifications_outputs(output_name)
    print("\nFederal output readiness:")
    if existing:
        print(f"  Matching federal resume exists: {existing[0].name}")
    else:
        print(f"  No matching federal resume found for: {output_name}")
    if existing_quals:
        print(f"  Matching federal qualifications statement exists: {existing_quals[0].name}")
    else:
        print(f"  No matching federal qualifications statement found for: {output_name}")

    if failures:
        print("\nFederal dry-run FAILED.")
        return 1

    print("\nFederal dry-run PASSED.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the federal resume workflow with recovery.")
    parser.add_argument("--dry-run", action="store_true", help="Validate federal inputs and print the planned workflow without writing files.")
    parser.add_argument("--with-cover", action="store_true", help="Also build the matching federal cover letter after the federal resume succeeds.")
    parser.add_argument("--with-interview", action="store_true", help="Also build the matching federal interview cheat sheet after the federal resume succeeds.")
    parser.add_argument("--with-guide", action="store_true", help="Also build the matching federal detailed interview guide after the federal resume succeeds.")
    parser.add_argument(
        "--with-supporting-docs",
        action="store_true",
        help="Alias for --with-cover --with-interview --with-guide.",
    )
    return parser.parse_args()


def requested_supporting_steps(args: argparse.Namespace) -> tuple[tuple[str, str], ...]:
    include_all = args.with_supporting_docs
    steps: list[tuple[str, str]] = []
    if args.with_cover or include_all:
        steps.append(("Building federal cover letter", "build_federal_cover_letter.py"))
    if args.with_interview or include_all:
        steps.append(("Building federal interview cheat sheet", "build_federal_interview_cheat_sheet.py"))
    if args.with_guide or include_all:
        steps.append(("Building federal detailed interview guide", "build_federal_detailed_interview_guide.py"))
    return tuple(steps)


def validate_federal_job_description_exists() -> None:
    if not FEDERAL_JOB_DESCRIPTION.exists():
        raise SystemExit(
            "ERROR: active federal job description not found at "
            f"{FEDERAL_JOB_DESCRIPTION}\n"
            "Paste one federal posting or questionnaire into jobs/federal_job_description.txt first."
        )


def main() -> None:
    args = parse_args()
    workspace_health.ensure_workspace_health_or_exit("The federal workflow")
    if args.dry_run:
        raise SystemExit(run_dry_run())
    validate_federal_job_description_exists()

    result = run_step("Building federal resume", "build_federal_resume.py")
    if not result.ok:
        explain_unresolved(result)
        raise SystemExit(result.returncode)

    for step_name, script_name in requested_supporting_steps(args):
        step_result = run_step(step_name, script_name)
        if not step_result.ok:
            raise SystemExit(step_result.returncode)
    print("\nDone. Check the output folder and render_check folder.")


if __name__ == "__main__":
    main()
