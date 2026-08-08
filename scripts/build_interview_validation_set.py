"""Build a representative set of deep interview guides and cheat sheets.

This uses archived job-description snapshots directly. It intentionally does not
copy them into jobs/job_description.txt, so the active application context remains
unchanged while the generator is tested across lanes.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PROJECT_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_cover_letter  # type: ignore  # noqa: E402
import build_detailed_interview_guide as detailed  # type: ignore  # noqa: E402
import build_interview_cheat_sheet as cheat  # type: ignore  # noqa: E402
import build_resume  # type: ignore  # noqa: E402
import interview_intelligence  # type: ignore  # noqa: E402
import interview_stage  # type: ignore  # noqa: E402
import question_prep  # type: ignore  # noqa: E402
import render_checks  # type: ignore  # noqa: E402


SOURCE_IMPLEMENTATION = PROJECT_ROOT / "source" / "Estrada_Resume_Implementation.docx"
SOURCE_PRE_SALES = PROJECT_ROOT / "source" / "Estrada_Resume_PreSales_CSM.docx"
OUTPUT_ROOT = PROJECT_ROOT / "output" / "Interview Validation Set"
REPORT = OUTPUT_ROOT / "VALIDATION_REPORT.md"


@dataclass(frozen=True)
class ValidationJob:
    label: str
    snapshot_dir: str
    lane_expectation: str
    hiring_manager_angle: str
    resume_source: Path


VALIDATION_JOBS = (
    ValidationJob(
        label="Advantive Implementation Consultant",
        snapshot_dir="20260802_185712_Advantive_Technical_Consultant_768493de",
        lane_expectation="implementation and delivery",
        hiring_manager_angle="Can this person structure technical discovery, data validation, integrations, and go-live without losing customer trust?",
        resume_source=SOURCE_IMPLEMENTATION,
    ),
    ValidationJob(
        label="Azalea Health Digital Scale Client Success Manager",
        snapshot_dir="20260729_134251_Azalea_Health_Client_Success_Manager_1b844a70",
        lane_expectation="customer success and account management",
        hiring_manager_angle="Can this person scale adoption and value realization through data, repeatable processes, and trusted-advisor judgment?",
        resume_source=SOURCE_PRE_SALES,
    ),
    ValidationJob(
        label="Adobe Solutions Consultant",
        snapshot_dir="20260720_230415_Adobe_Solutions_Consultant_244d6c7d",
        lane_expectation="solutions consulting and pre-sales",
        hiring_manager_angle="Can this person translate technical possibilities into a customer decision while partnering with sales and protecting credibility?",
        resume_source=SOURCE_PRE_SALES,
    ),
    ValidationJob(
        label="Fisher Phillips Business Process Optimization Specialist",
        snapshot_dir="20260729_165451_Fisher_Phillips_Business_Process_Optimization_Specialist_f241981a",
        lane_expectation="change enablement and process improvement",
        hiring_manager_angle="Can this person analyze how work really happens, improve the process, and make the change usable across a professional-services environment?",
        resume_source=SOURCE_IMPLEMENTATION,
    ),
)


def read_snapshot(job: ValidationJob) -> tuple[dict[str, object], str]:
    directory = PROJECT_ROOT / "scratch" / "jd_library" / job.snapshot_dir
    metadata_path = directory / "metadata.json"
    jd_path = directory / "job_description.txt"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    jd = jd_path.read_text(encoding="utf-8")
    if not jd.strip():
        raise RuntimeError(f"Archived job description is empty: {jd_path}")
    return metadata, jd


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def build_one(job: ValidationJob, *, render: bool = True) -> dict[str, object]:
    metadata, job_description = read_snapshot(job)
    company_name = str(metadata.get("company") or build_resume.extract_output_name(job_description))
    role_title = build_cover_letter.extract_role_title(job_description) or str(metadata.get("role") or "Role")
    resume_docx = job.resume_source
    output_dir = OUTPUT_ROOT / slug(company_name + " " + role_title)
    output_dir.mkdir(parents=True, exist_ok=True)
    cheat_output = output_dir / f"{company_name} - {role_title} Interview Cheat Sheet.docx"
    guide_output = output_dir / f"{company_name} - {role_title} Detailed Interview Guide.docx"

    cheat.build_document(company_name, role_title, job_description, resume_docx, cheat_output)
    detailed.build_document(
        company_name,
        role_title,
        job_description,
        resume_docx,
        guide_output,
        stage_profile=interview_stage.STAGE_PROFILES["all"],
        interviewer_context_data=interview_stage.InterviewerContext(),
    )
    if render:
        render_checks.render_docx(cheat_output)
        render_checks.render_docx(guide_output)

    resume_text = "\n".join(cheat.paragraph_texts(resume_docx))
    profile = cheat.adjusted_profile_for_role(
        build_resume.job_problem_profile(job_description, resume_text),
        role_title,
        job_description,
    )
    cards = cheat.expanded_story_bank()
    source_text = question_prep.approved_source_resume_text()
    hero = cheat.hero_stories(profile, job_description, resume_text, story_cards=cards, eligibility_text=source_text)
    scorecard = interview_intelligence.jd_competency_scorecard(job_description, resume_text)
    competency_names = []
    for item in scorecard:
        title = getattr(item, "competency", None) or getattr(item, "title", None) or getattr(item, "name", None)
        if title:
            competency_names.append(str(title))
    return {
        "label": job.label,
        "company": company_name,
        "role": role_title,
        "lane": profile.primary_lane,
        "lane_expectation": job.lane_expectation,
        "hiring_manager_angle": job.hiring_manager_angle,
        "hero_stories": [card.title for card in hero],
        "hero_types": sorted({story_type for card in hero for story_type in card.story_types}),
        "competencies": competency_names[:12],
        "cheat_sheet": str(cheat_output),
        "detailed_guide": str(guide_output),
        "source_snapshot": job.snapshot_dir,
    }


def summarize_one(job: ValidationJob) -> dict[str, object]:
    """Recompute the lane and hiring-manager coverage without rebuilding DOCX files."""
    metadata, job_description = read_snapshot(job)
    company_name = str(metadata.get("company") or build_resume.extract_output_name(job_description))
    role_title = build_cover_letter.extract_role_title(job_description) or str(metadata.get("role") or "Role")
    resume_text = "\n".join(cheat.paragraph_texts(job.resume_source))
    profile = cheat.adjusted_profile_for_role(
        build_resume.job_problem_profile(job_description, resume_text),
        role_title,
        job_description,
    )
    cards = cheat.expanded_story_bank()
    source_text = question_prep.approved_source_resume_text()
    hero = cheat.hero_stories(profile, job_description, resume_text, story_cards=cards, eligibility_text=source_text)
    scorecard = interview_intelligence.jd_competency_scorecard(job_description, resume_text)
    competency_names = [str(getattr(item, "competency", "")) for item in scorecard if getattr(item, "competency", "")]
    output_dir = OUTPUT_ROOT / slug(company_name + " " + role_title)
    cheat_output = output_dir / f"{company_name} - {role_title} Interview Cheat Sheet.docx"
    guide_output = output_dir / f"{company_name} - {role_title} Detailed Interview Guide.docx"
    return {
        "label": job.label,
        "company": company_name,
        "role": role_title,
        "lane": profile.primary_lane,
        "lane_expectation": job.lane_expectation,
        "hiring_manager_angle": job.hiring_manager_angle,
        "hero_stories": [card.title for card in hero],
        "hero_types": sorted({story_type for card in hero for story_type in card.story_types}),
        "competencies": competency_names[:12],
        "cheat_sheet": str(cheat_output),
        "detailed_guide": str(guide_output),
        "source_snapshot": job.snapshot_dir,
    }


def write_report(results: list[dict[str, object]], failures: list[str]) -> None:
    lines = [
        "# Interview Validation Set",
        "",
        "Built from archived job-description snapshots without changing the active posting.",
        "The purpose is to pressure-test whether the shared story bank and lane adaptation speak to different hiring-manager concerns.",
        "",
        "## Coverage summary",
        "",
    ]
    for result in results:
        lines.extend(
            [
                f"### {result['label']}",
                f"- Detected lane: `{result['lane']}`; expected lane: {result['lane_expectation']}.",
                f"- Hiring-manager angle: {result['hiring_manager_angle']}",
                f"- Hero stories: {', '.join(result['hero_stories'])}.",
                f"- Hero story types: {', '.join(result['hero_types'])}.",
                f"- Competency signals: {', '.join(result['competencies']) or 'scorecard labels unavailable'}.",
                f"- Cheat sheet: `{result['cheat_sheet']}`",
                f"- Detailed guide: `{result['detailed_guide']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Verification rules",
            "",
            "- The same 22-story rehearsal bank remains the source of spoken material.",
            "- Generator-only alternates remain internal and are not copied into Study materials.",
            "- Each guide is evaluated against the job's detected lane, scorecard signals, hero coverage, and hiring-manager angle.",
            "- A lane mismatch is a diagnostic result to review, not a reason to invent evidence.",
        ]
    )
    if failures:
        lines.extend(["", "## Build failures requiring review", "", *[f"- {failure}" for failure in failures]])
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-render", action="store_true", help="Build DOCX files without rendering them.")
    parser.add_argument("--report-only", action="store_true", help="Refresh the coverage report without rebuilding DOCX files.")
    args = parser.parse_args()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []
    failures: list[str] = []
    for job in VALIDATION_JOBS:
        try:
            result = summarize_one(job) if args.report_only else build_one(job, render=not args.no_render)
            results.append(result)
            print(f"Built {result['label']}")
        except BaseException as exc:  # report all jobs so one weak lane does not hide the others
            failures.append(f"{job.label}: {type(exc).__name__}: {exc}")
            print(f"FAILED {job.label}: {type(exc).__name__}: {exc}")
    write_report(results, failures)
    print(f"Validation report: {REPORT}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
