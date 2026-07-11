#!/usr/bin/env python3
"""Build a federal cover letter from the latest matching federal resume."""

from __future__ import annotations

import _bootstrap

_bootstrap.ensure_script_path()

import argparse

import build_cover_letter
import federal_supporting_docs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Christian Estrada's federal cover letter.")
    parser.add_argument(
        "--mode",
        default=build_cover_letter.DEFAULT_COVER_MODE,
        help="Use 'standard' for the default concise cover letter or 'long' for the explicit longer version.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    context = federal_supporting_docs.resolve_federal_context()
    output_docx = federal_supporting_docs.supporting_output_path(context.output_target_name, "Cover Letter")
    result = build_cover_letter.build_cover_letter_for_inputs(
        job_description=context.job_description,
        resume_docx=context.resume_docx,
        output_docx=output_docx,
        company_name=context.company_name,
        role_title=context.role_title,
        mode=args.mode,
    )
    print(f"Company: {result.company_name}")
    print(f"Role: {result.role_title}")
    print(f"Resume source: {result.resume_docx}")
    print(f"Output DOCX: {result.output_docx}")
    print(f"Proof points used: {result.bullets_used}")
    print(f"Final audit: {result.audit_status}")
    print(f"Mode: {result.mode}")
    for warning in result.specificity_warnings:
        print(f"SPECIFICITY WARNING: {warning}")


if __name__ == "__main__":
    main()
