#!/usr/bin/env python3
"""End-to-end function-chain integration test for the resume system."""

from __future__ import annotations

import _bootstrap

_bootstrap.ensure_script_path()

import contextlib
import io
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from zipfile import ZipFile
from xml.etree import ElementTree as ET

import build_detailed_interview_guide
import build_claude_review_packet
import build_cover_letter
import build_federal_cover_letter
import build_federal_detailed_interview_guide
import build_federal_interview_cheat_sheet
import build_federal_resume
import build_interview_cheat_sheet
import build_resume
import federal_supporting_docs
import prose_engine
import resume_analysis
import resume_content


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{WORD_NS}}}"

SAMPLE_JOB_DESCRIPTION = """
Company: Acme HealthTech
Role: Implementation Consultant

Acme HealthTech is hiring an Implementation Consultant to lead customer onboarding,
requirements gathering, workflow configuration, data migration validation, UAT,
training, go-live readiness, stakeholder communication, and post-launch adoption.
The role works with healthcare operations leaders, product teams, and customer
success partners to reduce implementation risk and improve reporting quality.
"""

FEDERAL_SAMPLE_JOB_DESCRIPTION = """
Agency: Department of Veterans Affairs
Role: IT Program Manager

This federal role leads enterprise implementation, data migration, acquisition support,
program governance, executive stakeholder briefings, reporting, change management,
and cross-functional delivery across a multi-site environment.
"""


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def docx_visible_text(path: Path) -> str:
    with ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    return "\n".join(
        "".join(node.text or "" for node in paragraph.findall(f".//{W}t"))
        for paragraph in root.findall(f".//{W}p")
    )


def assert_federal_wrapper_delegation(
    *,
    wrapper_module: object,
    helper_owner: object,
    helper_name: str,
    context: federal_supporting_docs.FederalSupportingDocContext,
    expected_suffix: str,
    cover_mode: str | None = None,
) -> None:
    captured: dict[str, object] = {}
    original_resolve = wrapper_module.federal_supporting_docs.resolve_federal_context
    original_helper = getattr(helper_owner, helper_name)
    original_parse_args = getattr(wrapper_module, "parse_args", None)
    try:
        wrapper_module.federal_supporting_docs.resolve_federal_context = lambda: context
        if original_parse_args is not None and cover_mode is not None:
            wrapper_module.parse_args = lambda: SimpleNamespace(mode=cover_mode)

        def fake_helper(**kwargs):
            captured.update(kwargs)
            if helper_name == "build_cover_letter_for_inputs":
                return SimpleNamespace(
                    company_name=kwargs["company_name"],
                    role_title=kwargs["role_title"],
                    resume_docx=kwargs["resume_docx"],
                    output_docx=kwargs["output_docx"],
                    bullets_used=4,
                    audit_status="PASS",
                    specificity_warnings=[],
                    mode=kwargs["mode"],
                )
            return SimpleNamespace(
                company_name=kwargs["company_name"],
                role_title=kwargs["role_title"],
                resume_docx=kwargs["resume_docx"],
                output_docx=kwargs["output_docx"],
            )

        setattr(helper_owner, helper_name, fake_helper)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            wrapper_module.main()
    finally:
        wrapper_module.federal_supporting_docs.resolve_federal_context = original_resolve
        setattr(helper_owner, helper_name, original_helper)
        if original_parse_args is not None and cover_mode is not None:
            wrapper_module.parse_args = original_parse_args

    assert_true(captured["job_description"] == context.job_description, "Federal wrapper should pass the validated federal job description into the shared helper")
    assert_true(captured["resume_docx"] == context.resume_docx, "Federal wrapper should pass the resolved federal resume into the shared helper")
    assert_true(captured["company_name"] == context.company_name, "Federal wrapper should preserve the detected federal agency name")
    assert_true(captured["role_title"] == context.role_title, "Federal wrapper should preserve the detected federal role title")
    assert_true(
        captured["output_docx"].name == f"Christian Estrada - {context.output_target_name} Federal {expected_suffix}.docx",
        f"Federal wrapper should use the expected supporting-doc name; got {captured['output_docx']}",
    )
    assert_true("[" not in captured["output_docx"].name, f"Federal wrapper should not emit placeholder output names; got {captured['output_docx'].name}")


def run_federal_supporting_doc_checks() -> None:
    validated = federal_supporting_docs.read_validated_federal_job_description(FEDERAL_SAMPLE_JOB_DESCRIPTION)
    agency = build_federal_resume.extract_federal_agency_name(validated)
    role = build_federal_resume.extract_federal_role_title(validated)
    output_name = build_federal_resume.extract_federal_output_name(validated)
    assert_true(agency == "Department of Veterans Affairs", f"Expected a federal agency name; got {agency!r}")
    assert_true(role == "IT Program Manager", f"Expected a federal role title; got {role!r}")
    assert_true(
        output_name == "Department of Veterans Affairs - IT Program Manager",
        f"Federal output name should combine the agency and role; got {output_name!r}",
    )

    original_output_dir = federal_supporting_docs.OUTPUT_DIR
    try:
        with TemporaryDirectory(prefix="federal_integration_") as temp_name:
            output_dir = Path(temp_name)
            federal_supporting_docs.OUTPUT_DIR = output_dir

            older_resume = output_dir / f"Christian Estrada - {output_name} Federal Resume.docx"
            newer_resume = output_dir / f"Christian Estrada - {output_name} Final Federal Resume.docx"
            older_resume.write_text("older", encoding="utf-8")
            newer_resume.write_text("newer", encoding="utf-8")
            now = output_dir.stat().st_mtime or 1
            os.utime(older_resume, (now - 120, now - 120))
            os.utime(newer_resume, (now - 10, now - 10))

            selected_resume = federal_supporting_docs.find_federal_resume_output(validated)
            assert_true(
                selected_resume == newer_resume,
                f"Federal supporting-doc lookup should resolve the newest matching federal resume; got {selected_resume}",
            )

            context = federal_supporting_docs.resolve_federal_context(FEDERAL_SAMPLE_JOB_DESCRIPTION)
            assert_true(context.company_name == agency, f"Resolved federal context should preserve the agency name; got {context.company_name!r}")
            assert_true(context.role_title == role, f"Resolved federal context should preserve the role title; got {context.role_title!r}")
            assert_true(context.resume_docx == newer_resume, f"Resolved federal context should carry the latest federal resume; got {context.resume_docx}")

            assert_federal_wrapper_delegation(
                wrapper_module=build_federal_cover_letter,
                helper_owner=build_federal_cover_letter.build_cover_letter,
                helper_name="build_cover_letter_for_inputs",
                context=context,
                expected_suffix="Cover Letter",
                cover_mode="standard",
            )
            assert_federal_wrapper_delegation(
                wrapper_module=build_federal_interview_cheat_sheet,
                helper_owner=build_federal_interview_cheat_sheet.cheat,
                helper_name="build_interview_cheat_sheet_for_inputs",
                context=context,
                expected_suffix="Interview Cheat Sheet",
            )
            assert_federal_wrapper_delegation(
                wrapper_module=build_federal_detailed_interview_guide,
                helper_owner=build_federal_detailed_interview_guide.detailed_guide,
                helper_name="build_detailed_interview_guide_for_inputs",
                context=context,
                expected_suffix="Detailed Interview Guide",
            )
    finally:
        federal_supporting_docs.OUTPUT_DIR = original_output_dir


def main() -> None:
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            validated = build_resume.validate_inputs(SAMPLE_JOB_DESCRIPTION)
            assert_true("Implementation Consultant" in validated, "validate_inputs should return the sample job description")

            selected_resume = resume_analysis.choose_resume(validated)
            assert_true(selected_resume.exists(), "choose_resume should return an existing source resume")
            resume_text = docx_visible_text(selected_resume)

            profile = resume_analysis.job_problem_profile(validated, resume_text)
            assert_true(profile.primary_lane, "job_problem_profile should detect a lane")
            assert_true(profile.core_problem, "job_problem_profile should return a core problem")

            summary = resume_content.build_problem_first_summary(validated, resume_text)
            assert_true(isinstance(summary, str) and len(summary.split()) >= 50, "build_problem_first_summary should return a substantial summary")
            summary_sentences = build_resume.summary_sentences(summary)
            assert_true(
                build_resume.PROFESSIONAL_SUMMARY_MIN_WORDS <= len(summary.split()) <= build_resume.PROFESSIONAL_SUMMARY_MAX_WORDS,
                f"Commercial summary should stay within the 70-110 word contract; got {len(summary.split())} words in {summary!r}",
            )
            assert_true(
                len(summary_sentences) == 3 and bool(any(char.isdigit() for char in summary_sentences[1]) or "$" in summary_sentences[1]),
                f"Commercial summary proof sentence should retain a quantified anchor; got {summary_sentences}",
            )
            assert_true(
                prose_engine.repair_text(summary, "summary").converged,
                f"Commercial summary should still converge through prose repair; got {summary!r}",
            )

            keywords = resume_analysis.audit_keywords(validated)
            assert_true(isinstance(keywords, set) and keywords, "audit_keywords should return a non-empty set")

            poor = resume_analysis.poor_fit_requirements(validated, resume_text)
            assert_true(isinstance(poor, tuple), "poor_fit_requirements should return a tuple")

            story_lens = resume_analysis.primary_story_lens(validated)
            assert_true(story_lens is None or isinstance(story_lens, dict), "primary_story_lens should return a dict or None")

            employer_context = resume_analysis.primary_employer_context(validated)
            assert_true(employer_context is None or isinstance(employer_context, dict), "primary_employer_context should return a dict or None")

            desire_focus = build_interview_cheat_sheet.closing_desire_focus(
                profile,
                "Role: Implementation Consultant\nPriority: implementation scope, training, and go-live readiness.",
            )
            assert_true(
                "emphasis on" not in desire_focus.lower(),
                f"Interview closing helper should not emit the stale emphasis artifact; got {desire_focus!r}",
            )

            contract = build_claude_review_packet.current_system_contract()
            assert_true(
                "DRAFT" in contract and "10pt" in contract and "pages" in contract,
                f"Claude packet contract should document DRAFT and the federal two-page/10pt minimum; got {contract!r}",
            )

            cover_text = "\n".join(
                [
                    "Dear Acme HealthTech Team,",
                    "Acme HealthTech needs implementation work that reduces customer risk and improves adoption because healthcare technology teams need clear workflow discipline.",
                    "Christian has supported 80+ client engagements, built 200+ reporting tools, and owned a five-site system used by 150+ users, which fits Acme HealthTech's need for analytics, data migration validation, and reporting support.",
                    "That background supports requirements gathering, training, go-live readiness, post-launch adoption, and the kind of implementation judgment Acme HealthTech needs.",
                    "Thank you for your time and consideration,",
                    "Christian Estrada",
                ]
            )
            warnings = build_cover_letter.validate_cover_letter_specificity(cover_text, "Acme HealthTech", validated)
            assert_true(warnings == [], f"validate_cover_letter_specificity should not warn on known-good text: {warnings}")
            run_federal_supporting_doc_checks()
    except Exception:
        details = stderr_buffer.getvalue().strip() or stdout_buffer.getvalue().strip()
        if details:
            print(details, file=sys.stderr)
        raise

    print("Integration test PASSED: commercial and federal function chains resolved expected inputs and delegations.")


if __name__ == "__main__":
    main()
