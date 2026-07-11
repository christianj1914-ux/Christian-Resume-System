#!/usr/bin/env python3
"""Shared helpers for federal supporting-document generation."""

from __future__ import annotations

import _bootstrap

_bootstrap.ensure_script_path()

from dataclasses import dataclass
from pathlib import Path

import build_federal_resume
from config.paths import OUTPUT_DIR
from utils import fail


@dataclass(frozen=True)
class FederalSupportingDocContext:
    company_name: str
    role_title: str
    output_target_name: str
    job_description: str
    resume_docx: Path


def read_validated_federal_job_description(job_description_text: str | None = None) -> str:
    return build_federal_resume.validate_inputs(job_description_text)


def matching_federal_resume_outputs(output_target_name: str) -> list[Path]:
    if not OUTPUT_DIR.exists():
        return []
    return sorted(
        OUTPUT_DIR.glob(f"Christian Estrada - {output_target_name}*Federal Resume.docx"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )


def find_federal_resume_output(job_description: str) -> Path:
    output_target_name = build_federal_resume.extract_federal_output_name(job_description)
    matches = matching_federal_resume_outputs(output_target_name)
    if matches:
        return matches[0]
    fail(
        "matching federal resume output not found for "
        f"{output_target_name}; run scripts/build_federal_resume.py first"
    )


def supporting_output_path(output_target_name: str, document_label: str) -> Path:
    return OUTPUT_DIR / f"Christian Estrada - {output_target_name} Federal {document_label}.docx"


def resolve_federal_context(job_description_text: str | None = None) -> FederalSupportingDocContext:
    job_description = read_validated_federal_job_description(job_description_text)
    company_name = (
        build_federal_resume.extract_federal_agency_name(job_description)
        or build_federal_resume.extract_federal_output_name(job_description)
    )
    role_title = build_federal_resume.extract_federal_role_title(job_description)
    if not role_title:
        fail(
            "could not determine a federal role title from jobs/federal_job_description.txt; "
            "add a Role: or Position: line near the top"
        )
    output_target_name = build_federal_resume.extract_federal_output_name(job_description)
    resume_docx = find_federal_resume_output(job_description)
    return FederalSupportingDocContext(
        company_name=company_name,
        role_title=role_title,
        output_target_name=output_target_name,
        job_description=job_description,
        resume_docx=resume_docx,
    )
