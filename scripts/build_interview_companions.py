#!/usr/bin/env python3
"""Build optional interview-prep companion outputs from shared guide helpers."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import _bootstrap

_bootstrap.ensure_script_path()

import build_cover_letter
import build_detailed_interview_guide as detailed_guide
import build_interview_cheat_sheet as cheat
import build_resume
import interview_context
from utils import fail, read_text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
JOB_DESCRIPTION = PROJECT_ROOT / "jobs" / "job_description.txt"
OUTPUT_DIR = PROJECT_ROOT / "output"

RECRUITER_SCREEN = "recruiter_screen"
FIRST_90_DAYS = "first_90_days"
DEBRIEF_ADDENDUM = "debrief_addendum"
MODES = (RECRUITER_SCREEN, FIRST_90_DAYS, DEBRIEF_ADDENDUM)
MODE_LABELS = {
    RECRUITER_SCREEN: "Recruiter screen prep",
    FIRST_90_DAYS: "90-day one-pager",
    DEBRIEF_ADDENDUM: "Debrief prep addendum",
}


@dataclass(frozen=True)
class CompanionContext:
    job_description: str
    company_name: str
    output_target_name: str
    role_title: str
    resume_docx: Path
    resume_text: str
    profile: build_resume.JobProblemProfile
    supplied_context: str
    interview_notes: str
    round_records: tuple[dict[str, object], ...]
    stories: tuple[cheat.StoryCard, ...]


@dataclass(frozen=True)
class CompanionBuildResult:
    mode: str
    output_docx: Path
    company_name: str
    role_title: str


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build optional interview-prep companion outputs.")
    parser.add_argument("--mode", choices=MODES, required=True, help="Companion output to build or check.")
    parser.add_argument("--check", action="store_true", help="Exit 0 when the requested companion is currently available.")
    parser.add_argument("--output", type=Path, default=None, help="Optional explicit output path.")
    return parser.parse_args(argv)


def load_active_context() -> CompanionContext:
    build_resume.require_file(PROJECT_ROOT / "AGENTS.md", "AGENTS.md")
    build_resume.require_file(JOB_DESCRIPTION, "job description")
    job_description = read_text(JOB_DESCRIPTION).strip()
    if not job_description:
        fail("job description is empty")
    company_name = build_resume.extract_output_name(job_description)
    output_target_name = build_resume.extract_output_target_name(job_description)
    role_title = build_cover_letter.extract_role_title(job_description) or "Role"
    resume_docx = build_cover_letter.find_resume_output(job_description)
    resume_text = "\n".join(cheat.paragraph_texts(resume_docx))
    profile = cheat.adjusted_profile_for_role(
        build_resume.job_problem_profile(job_description, resume_text),
        role_title,
        job_description,
    )
    context_bundle = interview_context.load_company_context(
        PROJECT_ROOT / "jobs",
        company_name,
        role_title,
        company_research_path=detailed_guide.COMPANY_RESEARCH,
        global_interview_notes_path=detailed_guide.INTERVIEW_NOTES,
        mode="compact",
    )
    stories = tuple(cheat.supported_story_bank(resume_text))
    return CompanionContext(
        job_description=job_description,
        company_name=company_name,
        output_target_name=output_target_name,
        role_title=role_title,
        resume_docx=resume_docx,
        resume_text=resume_text,
        profile=profile,
        supplied_context=context_bundle.supplied_context,
        interview_notes=context_bundle.interview_notes,
        round_records=context_bundle.round_records,
        stories=stories,
    )


def _default_output_path(context: CompanionContext, mode: str) -> Path:
    names = {
        RECRUITER_SCREEN: f"Christian Estrada - {context.output_target_name} Recruiter Screen Prep.docx",
        FIRST_90_DAYS: f"Christian Estrada - {context.output_target_name} 90 Day Plan One-Pager.docx",
        DEBRIEF_ADDENDUM: f"Christian Estrada - {context.output_target_name} Debrief Prep Addendum.docx",
    }
    return OUTPUT_DIR / names[mode]


def mode_available(mode: str, context: CompanionContext | None = None) -> bool:
    active = context or load_active_context()
    if mode == DEBRIEF_ADDENDUM:
        return (
            detailed_guide.build_debrief_addendum_document(
                active.company_name,
                active.role_title,
                active.round_records,
            )
            is not None
        )
    return True


def build_companion(
    mode: str,
    *,
    output_path: Path | None = None,
    context: CompanionContext | None = None,
) -> CompanionBuildResult:
    active = context or load_active_context()
    if mode == RECRUITER_SCREEN:
        document = detailed_guide.build_recruiter_screen_companion_document(
            active.profile,
            active.company_name,
            active.role_title,
            active.job_description,
            active.resume_text,
            active.supplied_context,
            active.interview_notes,
            active.stories,
        )
    elif mode == FIRST_90_DAYS:
        document = detailed_guide.build_first_90_day_one_pager_document(
            active.profile,
            active.company_name,
            active.role_title,
            active.job_description,
        )
    elif mode == DEBRIEF_ADDENDUM:
        document = detailed_guide.build_debrief_addendum_document(
            active.company_name,
            active.role_title,
            active.round_records,
        )
        if document is None:
            fail("no structured debrief signals are available for the active company and role")
    else:
        fail(f"unsupported companion mode: {mode}")

    target = output_path or _default_output_path(active, mode)
    target.parent.mkdir(exist_ok=True)
    document.save(str(target))
    print(f"{MODE_LABELS[mode]} created: {target}")
    return CompanionBuildResult(
        mode=mode,
        output_docx=target,
        company_name=active.company_name,
        role_title=active.role_title,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.check:
        return 0 if mode_available(args.mode) else 1
    build_companion(args.mode, output_path=args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
