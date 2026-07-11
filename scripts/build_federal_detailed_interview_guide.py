#!/usr/bin/env python3
"""Build a federal detailed interview guide from the latest matching federal resume."""

from __future__ import annotations

import _bootstrap

_bootstrap.ensure_script_path()

import build_detailed_interview_guide as detailed_guide
import federal_supporting_docs


def main() -> None:
    context = federal_supporting_docs.resolve_federal_context()
    output_docx = federal_supporting_docs.supporting_output_path(context.output_target_name, "Detailed Interview Guide")
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
    main()
