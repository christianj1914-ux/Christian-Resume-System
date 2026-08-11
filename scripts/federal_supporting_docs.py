#!/usr/bin/env python3
"""Shared helpers for federal supporting-document generation."""

from __future__ import annotations

import _bootstrap

_bootstrap.ensure_script_path()

from dataclasses import dataclass
from pathlib import Path

import build_federal_resume
import question_prep
import requirement_engine
from config.paths import OUTPUT_DIR
from utils import fail


@dataclass(frozen=True)
class FederalSupportingDocContext:
    company_name: str
    role_title: str
    output_target_name: str
    job_description: str
    resume_docx: Path
    target_grade: str = ""
    is_draft: bool = False


def read_validated_federal_job_description(job_description_text: str | None = None) -> str:
    return build_federal_resume.validate_inputs(job_description_text)


def matching_federal_resume_outputs(output_target_name: str, *, is_draft: bool = False) -> list[Path]:
    if not OUTPUT_DIR.exists():
        return []
    candidates = OUTPUT_DIR.glob(f"Christian Estrada - {output_target_name}*Federal Resume.docx")
    return sorted(
        (
            path
            for path in candidates
            if ((" DRAFT" in path.stem.upper()) if is_draft else (" DRAFT" not in path.stem.upper()))
        ),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )


def find_federal_resume_output(
    job_description: str,
    *,
    target_grade: str = "",
    is_draft: bool | None = None,
) -> Path:
    target_context = requirement_engine.build_target_context(
        job_description,
        workflow="federal",
        target_grade=target_grade,
    )
    output_target_name = target_context.output_label
    if is_draft is None:
        is_draft = not target_context.verified
    matches = matching_federal_resume_outputs(output_target_name, is_draft=is_draft)
    if matches:
        return matches[0]
    fail(
        "matching federal resume output not found for "
        f"{output_target_name}; run scripts/build_federal_resume.py first"
    )


def supporting_output_path(output_target_name: str, document_label: str, *, is_draft: bool = False) -> Path:
    marker = " DRAFT" if is_draft else ""
    return OUTPUT_DIR / f"Christian Estrada - {output_target_name}{marker} Federal {document_label}.docx"


def resolve_federal_context(
    job_description_text: str | None = None,
    *,
    target_grade: str = "",
) -> FederalSupportingDocContext:
    job_description = read_validated_federal_job_description(job_description_text)
    target_context = requirement_engine.build_target_context(
        job_description,
        workflow="federal",
        target_grade=target_grade,
    )
    company_name = target_context.agency or target_context.company
    role_title = target_context.official_title
    if not role_title:
        fail(
            "could not determine a federal role title from jobs/federal_job_description.txt; "
            "add a Role: or Position: line near the top"
        )
    output_target_name = target_context.output_label
    question_issues = question_prep.application_question_context_issues(
        job_description,
        question_prep.load_application_prompt_state(),
        workflow="federal",
    )
    is_draft = bool(question_issues) or not target_context.verified
    resume_docx = find_federal_resume_output(
        job_description,
        target_grade=target_grade,
        is_draft=is_draft,
    )
    return FederalSupportingDocContext(
        company_name=company_name,
        role_title=role_title,
        output_target_name=output_target_name,
        job_description=job_description,
        resume_docx=resume_docx,
        target_grade=target_context.target_grade,
        is_draft=is_draft,
    )
