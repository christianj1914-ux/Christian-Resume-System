#!/usr/bin/env python3
"""Build a federal detailed interview guide from the latest matching federal resume."""

from __future__ import annotations

import _bootstrap

_bootstrap.ensure_script_path()

import argparse
import sys

import build_federal_resume
import build_detailed_interview_guide as detailed_guide
import federal_supporting_docs


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Christian Estrada's federal detailed interview guide.")
    parser.add_argument("--target-grade", type=build_federal_resume.federal_grade_argument, default="", metavar="GS-XX")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args([] if argv is None else argv)
    context = (
        federal_supporting_docs.resolve_federal_context(target_grade=args.target_grade)
        if args.target_grade
        else federal_supporting_docs.resolve_federal_context()
    )
    output_docx = (
        federal_supporting_docs.supporting_output_path(
            context.output_target_name,
            "Detailed Interview Guide",
            is_draft=context.is_draft,
        )
        if getattr(context, "is_draft", False)
        else federal_supporting_docs.supporting_output_path(context.output_target_name, "Detailed Interview Guide")
    )
    result = detailed_guide.build_detailed_interview_guide_for_inputs(
        job_description=context.job_description,
        resume_docx=context.resume_docx,
        output_docx=output_docx,
        company_name=context.company_name,
        role_title=context.role_title,
    )
    print(f"Company: {result.company_name}")
    print(f"Role: {result.role_title}")
    print(f"Resume source: {result.resume_docx}")
    print(f"Output DOCX: {result.output_docx}")


if __name__ == "__main__":
    main(sys.argv[1:])
