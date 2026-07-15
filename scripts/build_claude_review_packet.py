#!/usr/bin/env python3
"""Generate a live Claude review packet from the current codebase."""

from __future__ import annotations

import _bootstrap

_bootstrap.ensure_script_path()

import argparse
import ast
import csv
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import claude_review_bundle
import workspace_health


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLAUDE_REVIEW_DIR = PROJECT_ROOT / "Claude Review"
PACKET_PATH = CLAUDE_REVIEW_DIR / "TEMP_FOR_REVIEW.md"
TASKS_PATH = PROJECT_ROOT / "tasks.py"
JOB_DESCRIPTION = PROJECT_ROOT / "jobs" / "job_description.txt"
TRACKER = PROJECT_ROOT / "scratch" / "applications.csv"
JD_LIBRARY_INDEX = PROJECT_ROOT / "scratch" / "jd_library" / "index.csv"
REVIEW_TEMPLATE = PROJECT_ROOT / ".context" / "CLAUDE_REVIEW_TEMPLATE.md"
PLAN_TEMPLATE = PROJECT_ROOT / ".context" / "CLAUDE_TASK_TEMPLATE.md"
PROGRESS_CHECK_TEMPLATE = PROJECT_ROOT / ".context" / "CLAUDE_PROGRESS_CHECK_TEMPLATE.md"
COMMAND_OUTPUT_CACHE: dict[str, str] = {}

CONTEXT_FILES = (
    "CLAUDE.md",
    ".context/RESUME_SYSTEM_BRIEF.md",
    ".context/ARCHITECTURE_MAP.md",
    ".context/RULES_FOR_CLAUDE.md",
    ".context/CODE_REVIEW_PACKET_GUIDE.md",
    ".context/SCRIPT_INDEX.md",
    ".context/COMMON_CHANGE_AREAS.md",
)


@dataclass(frozen=True)
class FunctionExcerpt:
    rel_path: str
    function_name: str
    title: str
    head_lines: int | None = None
    tail_lines: int | None = None


@dataclass(frozen=True)
class PacketMode:
    name: str
    title: str
    review_goal: str
    desired_behavior: tuple[str, ...]
    questions: tuple[str, ...]
    excerpts: tuple[FunctionExcerpt, ...]


def fx(
    rel_path: str,
    function_name: str,
    title: str,
    *,
    head_lines: int | None = None,
    tail_lines: int | None = None,
) -> FunctionExcerpt:
    return FunctionExcerpt(rel_path, function_name, title, head_lines, tail_lines)


BROAD_EXCERPTS = (
    fx("scripts/build_resume.py", "alignment_score_report", "Resume pre-build alignment scoring"),
    fx("scripts/build_resume.py", "final_fit_audit", "Resume final fit audit and FAIL/POOR logic", head_lines=80),
    fx("scripts/build_resume.py", "build_resume", "Resume builder orchestration", head_lines=28, tail_lines=18),
    fx("scripts/build_cover_letter.py", "find_resume_output", "Cover letter dependency on matching generated resume"),
    fx("scripts/build_cover_letter.py", "build_cover_letter", "Cover letter output naming and resume dependency"),
    fx("scripts/build_application_checklist.py", "analysis_resume_path", "Checklist analysis resume selection"),
    fx("scripts/build_application_checklist.py", "analysis_basis_label", "Checklist analysis basis labeling"),
    fx("scripts/build_application_checklist.py", "fit_snapshot_status", "Checklist tailored-output vs source-fallback fit logic"),
    fx("scripts/build_application_checklist.py", "build_application_checklist", "Checklist builder orchestration", head_lines=48),
    fx("scripts/track_applications.py", "row_job_description_text", "Tracker current/archived JD resolution"),
    fx("scripts/track_applications.py", "refresh_row_metadata", "Tracker lane and fit backfill logic"),
    fx("scripts/track_applications.py", "row_for_active_job", "Tracker active-job row creation"),
    fx("scripts/track_applications.py", "upsert_application", "Tracker row update behavior"),
    fx("scripts/track_applications.py", "add_row", "Tracker add command refresh behavior"),
    fx("scripts/build_search_analytics.py", "build_report", "Tracker-based search analytics output"),
    fx("scripts/run_resume_workflow.py", "run_dry_run", "Workflow dry-run readiness logic", head_lines=90),
    fx("scripts/run_resume_workflow.py", "main", "Workflow resume, cover, and tracker sequencing"),
    fx("scripts/post_interview_debrief.py", "update_tracker_from_debrief", "Debrief-to-tracker synchronization"),
)

PACKET_MODES = {
    "broad": PacketMode(
        name="broad",
        title="Broad Claude Review Packet",
        review_goal=(
            "Review the current live resume system for likely bugs, hidden regressions, stale assumptions, "
            "and high-value improvements across the main workflow."
        ),
        desired_behavior=(
            "Resume, checklist, cover letter, workflow, tracker, and debrief paths should agree on fit logic and output naming.",
            "Tracker rows should use the newest matching tailored resume when one exists and should never mix `lane_label` with `fit_status`.",
            "Source-resume fallback should stay advisory for pre-build alignment and should not masquerade as a final-output fit audit.",
            "Historical backfill should stay conservative and only refresh rows when the current or archived job description truly matches.",
            "Compact Claude handoff files should stay synchronized with the live code and command surface.",
            "Validation coverage should catch hidden regressions before Christian depends on them.",
        ),
        questions=(
            "Identify the most likely bugs, regressions, or stale assumptions in these live excerpts.",
            "Prioritize findings by severity, especially anything that could produce misleading fit, stale tracker state, wrong output naming, or unsupported-claim drift.",
            "Point out missing tests or weak validation coverage that should be added to `scripts/smoke_test.py` or `scripts/integration_test.py`.",
            "Suggest the smallest next file or snippet to inspect only if this packet is insufficient for a confident finding.",
            "Give exact Codex-ready instructions or small replacement snippets rather than broad rewrites.",
        ),
        excerpts=BROAD_EXCERPTS,
    ),
    "tracker": PacketMode(
        name="tracker",
        title="Tracker Claude Review Packet",
        review_goal=(
            "Review the tracker, debrief sync, search analytics, and workflow auto-tracking path for stale fit state, "
            "wrong status transitions, and historical-refresh risk."
        ),
        desired_behavior=(
            "Tracker rows should preserve separate `lane_label`, `fit_status`, and audit signals.",
            "Workflow auto-tracking should happen as soon as required artifacts exist, not after optional artifacts succeed.",
            "Debrief outcome handling should be explicit and should never silently convert unknown values into in-process tracker states.",
            "Search analytics should surface meaningful tracker state rather than flattening review-required outputs into clean fit labels.",
        ),
        questions=(
            "Identify the highest-risk bugs or stale assumptions in the tracker, debrief, analytics, and workflow sync path.",
            "Call out any status mapping, fit-state, audit-flag, or historical-refresh behavior that could mislead Christian about application readiness or pipeline health.",
            "Point out exact smoke-test or integration-test additions that would catch these regressions next time.",
            "If one more snippet is required, name only the smallest additional tracker or workflow function to inspect.",
        ),
        excerpts=(
            fx("scripts/track_applications.py", "row_job_description_text", "Tracker current/archived JD resolution"),
            fx("scripts/track_applications.py", "refresh_row_metadata", "Tracker lane and fit backfill logic"),
            fx("scripts/track_applications.py", "row_for_active_job", "Tracker active-job row creation"),
            fx("scripts/track_applications.py", "upsert_application", "Tracker row update behavior"),
            fx("scripts/track_applications.py", "add_row", "Tracker add command refresh behavior"),
            fx("scripts/build_search_analytics.py", "build_report", "Tracker-based search analytics output"),
            fx("scripts/run_resume_workflow.py", "main", "Workflow resume, cover, and tracker sequencing"),
            fx("scripts/post_interview_debrief.py", "update_tracker_from_debrief", "Debrief-to-tracker synchronization"),
        ),
    ),
    "checklist": PacketMode(
        name="checklist",
        title="Checklist Claude Review Packet",
        review_goal=(
            "Review application checklist logic for analysis-resume selection, fit snapshot behavior, keyword coverage, "
            "and debrief carry-through."
        ),
        desired_behavior=(
            "The checklist should prefer the newest matching tailored resume output when one exists.",
            "Source-resume fallback should stay pre-build and advisory instead of pretending to be final fit review.",
            "Checklist keyword and debrief sections should reflect only the active company and active resume basis.",
        ),
        questions=(
            "Review whether the checklist is reading the right resume basis and presenting an honest fit snapshot.",
            "Call out stale-output risk, wrong-company debrief carry-through, and any keyword or evidence logic that can mislead the user.",
            "Name exact validation or smoke-test coverage to add for checklist basis selection and fit snapshot logic.",
        ),
        excerpts=(
            fx("scripts/build_application_checklist.py", "analysis_resume_path", "Checklist analysis resume selection"),
            fx("scripts/build_application_checklist.py", "analysis_basis_label", "Checklist analysis basis labeling"),
            fx("scripts/build_application_checklist.py", "fit_snapshot_status", "Checklist tailored-output vs source-fallback fit logic"),
            fx("scripts/build_application_checklist.py", "build_application_checklist", "Checklist builder orchestration", head_lines=48),
            fx("scripts/build_resume.py", "alignment_score_report", "Resume pre-build alignment scoring"),
            fx("scripts/build_resume.py", "final_fit_audit", "Resume final fit audit and FAIL/POOR logic", head_lines=80),
        ),
    ),
    "resume": PacketMode(
        name="resume",
        title="Resume Claude Review Packet",
        review_goal=(
            "Review the resume generation path for source selection, summary shaping, fit audit, and output naming risk."
        ),
        desired_behavior=(
            "Resume generation should preserve source-truth boundaries, fit audits, and two-page targeting logic.",
            "Professional summary logic should stay recruiter-friendly, proof-based, and free of prompt-like phrasing.",
            "FAIL or POOR output naming should stay aligned with the real fit audit outcome.",
        ),
        questions=(
            "Identify the highest-risk resume logic issues in source selection, summary generation, fit audit, or output naming.",
            "Call out unsupported-claim drift, stale guardrails, or summary logic that can weaken recruiter skim quality.",
            "Point out the most useful smoke-test or integration-test additions for these resume paths.",
        ),
        excerpts=(
            fx("scripts/resume_analysis.py", "choose_resume", "Resume source selection"),
            fx("scripts/resume_analysis.py", "job_problem_profile", "Resume role-lane and evidence mapping", head_lines=100),
            fx("scripts/resume_content.py", "build_problem_first_summary", "Professional summary construction", head_lines=80),
            fx("scripts/resume_content.py", "rewrite_professional_summary_for_role", "Summary rewrite application", head_lines=60),
            fx("scripts/build_resume.py", "final_fit_audit", "Resume final fit audit and FAIL/POOR logic", head_lines=80),
            fx("scripts/build_resume.py", "build_resume", "Resume builder orchestration", head_lines=28, tail_lines=18),
        ),
    ),
    "cover": PacketMode(
        name="cover",
        title="Cover Letter Claude Review Packet",
        review_goal=(
            "Review the cover letter path for resume dependency, opening selection, supported proof, and output naming alignment."
        ),
        desired_behavior=(
            "Cover letters should depend on the matching generated resume and should not outrun supported evidence.",
            "Opening and proof paragraphs should stay concrete, natural, and aligned with the generated resume's fit status.",
            "Cover-letter output naming should stay consistent with the active company and role target.",
        ),
        questions=(
            "Identify the most likely bugs or stale assumptions in the cover letter resume-dependency and evidence path.",
            "Call out unsupported proof, generic opening logic, or naming mismatches that can confuse the workflow.",
            "Suggest the smallest test additions needed for cover-letter dependency or evidence-selection logic.",
        ),
        excerpts=(
            fx("scripts/build_cover_letter.py", "find_resume_output", "Cover letter dependency on matching generated resume"),
            fx("scripts/build_cover_letter.py", "selected_evidence_items_ordered", "Cover letter proof ordering", head_lines=80),
            fx("scripts/build_cover_letter.py", "opening_method_paragraph", "Cover letter opening method paragraph", head_lines=80),
            fx("scripts/build_cover_letter.py", "proof_paragraph", "Cover letter proof paragraph", head_lines=80),
            fx("scripts/build_cover_letter.py", "build_cover_letter", "Cover letter output naming and resume dependency"),
        ),
    ),
    "interview": PacketMode(
        name="interview",
        title="Interview Claude Review Packet",
        review_goal=(
            "Review interview output logic for the shared elevator-speech system, human-motivation layer, "
            "supported story selection, role alignment, and prep readiness."
        ),
        desired_behavior=(
            "Interview outputs should not make stronger claims than the resume can support.",
            "The cheat sheet and detailed guide should reuse one pitch system so 30-second, 60-second, 90-second, and extended TMAY answers do not drift from each other.",
            "Interview prep should favor rehearsed spoken answers, anchor facts, and adaptation drills over brittle framework fragments.",
            "Human-motivation and longer-answer sections should feel personal and useful without inventing unsupported motives, values, or culture fit.",
            "Story-bank, long-form sample answers, and questions-to-ask logic should stay tied to the active role, lane, and company context.",
            "Interview prep sections should remain concise, useful, and free of unsupported company assumptions or stale cover-letter-to-interview drift.",
        ),
        questions=(
            "Identify the highest-risk interview-prep issues in shared pitch reuse, human-layer logic, story support, role alignment, or company-context use.",
            "Call out unsupported claims, stale cover-letter-to-interview drift, wrong story-to-human mapping, bloated sections, or stale role-lane assumptions that can weaken prep quality.",
            "Point out exact smoke-test or integration-test additions that should protect pitch variants, extended TMAY logic, and long-answer human-connection behavior.",
            "Suggest the smallest follow-up snippets needed only if these excerpts are not enough for a confident finding.",
        ),
        excerpts=(
            fx("scripts/build_interview_cheat_sheet.py", "adjusted_profile_for_role", "Interview profile adjustment"),
            fx("scripts/build_interview_cheat_sheet.py", "interview_pitch_parts", "Interview reuse of cover-letter positioning signals"),
            fx("scripts/build_interview_cheat_sheet.py", "human_motivation_sentence", "Interview human-motivation sentence"),
            fx("scripts/build_interview_cheat_sheet.py", "pitch_variants", "Shared 30/60/90-second pitch builder", head_lines=80),
            fx("scripts/build_interview_cheat_sheet.py", "rehearsal_foundation_lines", "Shared rehearsal and adaptation coaching"),
            fx("scripts/build_interview_cheat_sheet.py", "story_adaptation_drill_lines", "Story adaptation drill helper"),
            fx("scripts/build_interview_cheat_sheet.py", "story_human_connection_line", "Story-to-human-layer mapping"),
            fx("scripts/build_interview_cheat_sheet.py", "hero_stories", "Interview hero story selection", head_lines=80),
            fx("scripts/build_interview_cheat_sheet.py", "behavioral_answer_scripts", "Interview behavioral answer scripts", head_lines=90),
            fx("scripts/build_interview_cheat_sheet.py", "questions_to_ask", "Interview questions-to-ask logic", head_lines=80),
            fx("scripts/build_detailed_interview_guide.py", "build_extended_tmay_sections", "Extended Tell Me About Yourself structure"),
            fx("scripts/build_detailed_interview_guide.py", "story_sample_answer", "Detailed guide sample-answer assembly", head_lines=100),
            fx("scripts/build_detailed_interview_guide.py", "story_quality_audit", "Detailed guide story quality audit", head_lines=80),
            fx("scripts/build_thank_you.py", "thank_you_body", "Thank-you topic extraction and fallback handling", head_lines=90),
            fx("scripts/build_interview_followup.py", "interview_followup_body", "Interview follow-up topic extraction and fallback handling", head_lines=90),
            fx("scripts/build_post_round.py", "post_round_followup_email", "Post-round follow-up sentence assembly", head_lines=80),
            fx("scripts/utils.py", "extract_single_discussion_topic", "Shared debrief-topic extraction helper", head_lines=90),
            fx("scripts/utils.py", "assert_no_template_leakage", "Shared template-leakage validator", head_lines=60),
        ),
    ),
    "workflow": PacketMode(
        name="workflow",
        title="Workflow Claude Review Packet",
        review_goal=(
            "Review workflow dry-run, recovery, step ordering, and output repair logic for failure-path gaps and sequencing bugs."
        ),
        desired_behavior=(
            "Dry-run output should accurately represent what the full workflow would do.",
            "Required and optional steps should be sequenced so partial success still preserves critical workflow side effects such as tracking.",
            "DOCX repair and retry logic should stay explicit and should not hide failures behind vague output.",
        ),
        questions=(
            "Identify the highest-risk failure paths or sequencing issues in the workflow runner.",
            "Call out unclear recovery behavior, tracker timing mistakes, or output-repair blind spots that can leave the system in a misleading state.",
            "Suggest the smallest smoke-test or integration-test additions needed to lock these workflow paths down.",
        ),
        excerpts=(
            fx("scripts/run_resume_workflow.py", "run_step", "Workflow step runner"),
            fx("scripts/run_resume_workflow.py", "failure_kind", "Workflow failure classification"),
            fx("scripts/run_resume_workflow.py", "run_with_recovery", "Workflow retry and resume logic", head_lines=80),
            fx("scripts/run_resume_workflow.py", "run_dry_run", "Workflow dry-run readiness logic", head_lines=90),
            fx("scripts/run_resume_workflow.py", "main", "Workflow resume, cover, and tracker sequencing"),
        ),
    ),
    "federal": PacketMode(
        name="federal",
        title="Federal Claude Review Packet",
        review_goal=(
            "Review the federal resume workflow for posting validation, requirement audit quality, "
            "qualifications-statement alignment, wrapper portability, and workflow diagnostics."
        ),
        desired_behavior=(
            "Federal runs should keep the federal contract separate from commercial fit-state naming and tracker semantics.",
            "The federal resume should stay at exactly two pages with 10pt minimum body text, while the federal qualifications statement remains a separate Word document.",
            "Federal supporting documents should reuse shared cover and interview engines where safe, without importing commercial-only assumptions or output naming.",
            "Federal workflow diagnostics should make requirement visibility gaps, layout choices, and supporting-doc wrapper behavior easy to audit.",
        ),
        questions=(
            "Identify the highest-risk bugs or stale assumptions in the federal resume, qualifications-statement, supporting-doc wrapper, or federal workflow path.",
            "Call out places where commercial logic leaks into the federal contract or where federal-specific guardrails are too weak.",
            "Point out exact smoke-test or integration-test additions that should protect federal planning, qualifications output, and supporting-doc portability.",
            "If one more snippet is required, name only the smallest additional federal function to inspect.",
        ),
        excerpts=(
            fx("scripts/build_federal_resume.py", "validate_inputs", "Federal posting validation"),
            fx("scripts/build_federal_resume.py", "federal_requirement_audit", "Federal requirement audit and coverage classification", head_lines=100),
            fx("scripts/build_federal_resume.py", "build_gs14_summary", "Federal summary construction"),
            fx("scripts/build_federal_resume.py", "resume_plan", "Federal resume and qualifications planning", head_lines=100),
            fx("scripts/build_federal_resume.py", "federal_plain_text_validation", "Federal ATS plain-text validation"),
            fx("scripts/build_federal_resume.py", "build_federal_resume", "Federal resume build orchestration", head_lines=50),
            fx("scripts/federal_supporting_docs.py", "resolve_federal_context", "Federal supporting-doc context resolution"),
            fx("scripts/run_federal_resume_workflow.py", "run_dry_run", "Federal workflow dry-run readiness", head_lines=100),
            fx("scripts/run_federal_resume_workflow.py", "print_failure_summary", "Federal workflow failure messaging"),
            fx("scripts/run_federal_resume_workflow.py", "main", "Federal workflow orchestration", head_lines=60),
        ),
    ),
    "claude-review": PacketMode(
        name="claude-review",
        title="Claude Review System Packet",
        review_goal=(
            "Review the Claude Review bundle, packet generator, prompt generator, and progress-check contract so "
            "Claude reports live implementation state clearly, separates interview features from commit packaging, "
            "and stops recommending mismatched states or stale assumptions."
        ),
        desired_behavior=(
            "The Claude-side progress checker should report both an Interview Feature Track for phases 1 to 4 and a Commit Train Track for commits 1 to 7.",
            "Claude packets and prompts should distinguish current live behavior from proposed additions and should not let non-existent states masquerade as current behavior.",
            "The progress checker should keep companion outputs opt-in, treat Commit 6 archive normalization as the highest-risk gate, and avoid making support/docs commits look like interview regressions.",
            "The common bundle should stay synchronized with current packet modes, audit-state contracts, cover-length contracts, and federal-vs-commercial distinctions.",
            "Packet refresh should reuse validation and tracker command capture across multiple modes instead of rerunning the same expensive checks unnecessarily.",
        ),
        questions=(
            "Identify the highest-risk drift points in the Claude review bundle, packet generator, prompt generator, progress-check contract, and refresh workflow.",
            "Call out missing dual-track monitoring guidance, stale mode coverage, or packet/prompt mismatches that can make Claude misreport interview-feature progress or commit-train progress.",
            "Check whether the progress-check prompt enforces the required report sections, top-level health language, commit-specific gates, and repo-hygiene checks.",
            "Point out exact smoke-test additions needed to keep the review tooling synchronized with the live codebase.",
            "If one more snippet is required, name only the smallest additional review-tooling function to inspect.",
        ),
        excerpts=(
            fx("scripts/build_claude_review_packet.py", "packet_self_audit", "Packet self-audit checks"),
            fx("scripts/build_claude_review_packet.py", "build_packet", "Claude packet assembly", head_lines=100),
            fx("scripts/build_claude_prompt.py", "build_prompt", "Claude prompt assembly"),
            fx("scripts/claude_review_bundle.py", "build_review_claude_md", "Review bundle CLAUDE.md augmentation"),
            fx("scripts/claude_review_bundle.py", "build_review_rules_for_claude", "Review bundle rules augmentation"),
            fx("scripts/claude_review_bundle.py", "refresh_support_files", "Review bundle support-file refresh"),
            fx("scripts/refresh_claude_review_bundle.py", "refresh_bundle", "Review bundle end-to-end refresh workflow"),
        ),
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a ready-to-upload Claude review packet.")
    parser.add_argument(
        "--skip-checks",
        action="store_true",
        help="Skip validate/integration-test/track-report command capture.",
    )
    parser.add_argument(
        "--mode",
        choices=tuple(PACKET_MODES),
        default="broad",
        help="Packet mode to generate.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write the generated packet. Defaults to the mode-specific file in `Claude Review`.",
    )
    return parser.parse_args()


def default_packet_filename(mode_name: str) -> str:
    if mode_name == "broad":
        return "TEMP_FOR_REVIEW.md"
    return f"TEMP_FOR_REVIEW_{mode_name.upper().replace('-', '_')}.md"


def default_packet_output_path(mode_name: str) -> Path:
    return CLAUDE_REVIEW_DIR / default_packet_filename(mode_name)


def packet_manifest_path(packet_path: Path) -> Path:
    return packet_path.with_name(f"{packet_path.stem}.manifest.json")


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return path


def write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def packet_source_hashes(mode: PacketMode) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for ref in CONTEXT_FILES:
        path = PROJECT_ROOT / ref
        if path.exists():
            hashes[ref] = workspace_health.sha256_path(path)
    template_paths = [REVIEW_TEMPLATE, PLAN_TEMPLATE, TASKS_PATH]
    if mode.name == "claude-review":
        template_paths.append(PROGRESS_CHECK_TEMPLATE)
    for template_path in template_paths:
        if template_path.exists():
            hashes[workspace_health.rel_path(template_path)] = workspace_health.sha256_path(template_path)
    for excerpt in mode.excerpts:
        path = PROJECT_ROOT / excerpt.rel_path
        if path.exists():
            hashes[excerpt.rel_path] = workspace_health.sha256_path(path)
    return hashes


def build_packet_manifest(mode: PacketMode, packet_path: Path, *, skip_checks: bool) -> dict[str, object]:
    bundle_manifest = claude_review_bundle.bundle_manifest_path()
    bundle_hash = workspace_health.sha256_path(bundle_manifest) if bundle_manifest.exists() else None
    source_hash_map = packet_source_hashes(mode)
    return {
        "artifact_kind": "claude-review-packet",
        "generated_at": workspace_health.utc_timestamp(),
        "packet_mode": mode.name,
        "packet_path": str(packet_path.resolve()),
        "packet_sha256": workspace_health.sha256_path(packet_path),
        "bundle_manifest_path": str(bundle_manifest.resolve()),
        "bundle_manifest_sha256": bundle_hash,
        "template_hashes": {
            workspace_health.rel_path(REVIEW_TEMPLATE): source_hash_map.get(workspace_health.rel_path(REVIEW_TEMPLATE)),
            workspace_health.rel_path(PLAN_TEMPLATE): source_hash_map.get(workspace_health.rel_path(PLAN_TEMPLATE)),
        },
        "excerpt_hashes": {
            excerpt.rel_path: source_hash_map.get(excerpt.rel_path)
            for excerpt in mode.excerpts
        },
        "source_hashes": source_hash_map,
        "check_status": {
            "skip_checks": skip_checks,
            "commands_captured": [] if skip_checks else ["validate", "integration-test", "track-report"],
        },
    }


def write_packet_artifacts(mode_name: str, *, skip_checks: bool, output_path: Path | None = None) -> list[Path]:
    mode = PACKET_MODES[mode_name]
    packet_text = build_packet(mode_name, skip_checks=skip_checks)
    packet_output_path = output_path or default_packet_output_path(mode_name)
    packet_path = write_text(packet_output_path, packet_text)
    manifest_path = write_json(
        packet_manifest_path(packet_path),
        build_packet_manifest(mode, packet_path, skip_checks=skip_checks),
    )
    return [packet_path, manifest_path]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def append_warning_once(warnings: list[str], message: str) -> None:
    if message not in warnings:
        warnings.append(message)


def extract_function_source(path: Path, function_name: str) -> str:
    source = read_text(path)
    module = ast.parse(source)
    lines = source.splitlines()
    for node in module.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return "\n".join(lines[node.lineno - 1 : node.end_lineno])
    raise ValueError(f"Function {function_name} not found in {path}")


def trim_source(source: str, head_lines: int | None, tail_lines: int | None) -> str:
    lines = source.splitlines()
    if head_lines is None and tail_lines is None:
        return source
    if head_lines is not None and tail_lines is not None and len(lines) > head_lines + tail_lines:
        return "\n".join(lines[:head_lines] + ["    ..."] + lines[-tail_lines:])
    if head_lines is not None and len(lines) > head_lines:
        return "\n".join(lines[:head_lines] + ["    ..."])
    if tail_lines is not None and len(lines) > tail_lines:
        return "\n".join(["    ..."] + lines[-tail_lines:])
    return source


def packet_excerpt_resolution_warnings(mode: PacketMode) -> tuple[str, ...]:
    warnings: list[str] = []
    for spec in mode.excerpts:
        path = PROJECT_ROOT / spec.rel_path
        if not path.exists():
            append_warning_once(warnings, f"Missing excerpt file: `{spec.rel_path}`")
            continue
        try:
            extract_function_source(path, spec.function_name)
        except Exception as error:  # noqa: BLE001
            append_warning_once(
                warnings,
                f"Missing excerpt function: `{spec.rel_path}` -> `{spec.function_name}()` ({error})",
            )
    return tuple(warnings)


def excerpt_block(spec: FunctionExcerpt, warnings: list[str]) -> str:
    path = PROJECT_ROOT / spec.rel_path
    if not path.exists():
        append_warning_once(warnings, f"Missing excerpt file: `{spec.rel_path}`")
        return "\n".join(
            (
                f"### {spec.title}",
                f"File: `{spec.rel_path}`",
                "```text",
                f"Missing file: {spec.rel_path}",
                "```",
            )
        )
    try:
        source = extract_function_source(path, spec.function_name)
    except Exception as error:  # noqa: BLE001
        append_warning_once(warnings, f"Missing excerpt function: `{spec.rel_path}` -> `{spec.function_name}()` ({error})")
        return "\n".join(
            (
                f"### {spec.title}",
                f"File: `{spec.rel_path}`",
                "```text",
                f"Missing function excerpt: {spec.function_name}()",
                "```",
            )
        )
    trimmed = trim_source(source, spec.head_lines, spec.tail_lines)
    return "\n".join(
        (
            f"### {spec.title}",
            f"File: `{spec.rel_path}`",
            "```python",
            trimmed,
            "```",
        )
    )


def run_command(command_name: str) -> str:
    if command_name in COMMAND_OUTPUT_CACHE:
        return COMMAND_OUTPUT_CACHE[command_name]
    result = subprocess.run(
        [sys.executable, str(TASKS_PATH), command_name],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    output_parts = [part.strip() for part in (result.stdout, result.stderr) if part and part.strip()]
    output = "\n".join(output_parts)
    if result.returncode != 0:
        output = f"[exit {result.returncode}]\n{output}" if output else f"[exit {result.returncode}]"
    if not output:
        output = "(no output captured)"
    COMMAND_OUTPUT_CACHE[command_name] = output
    return output


def clear_command_output_cache() -> None:
    COMMAND_OUTPUT_CACHE.clear()


def compact_lines(text: str, limit: int = 18) -> str:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if len(lines) <= limit:
        return "\n".join(lines)
    head = max(1, limit // 2)
    tail = max(1, limit - head)
    return "\n".join(lines[:head] + ["..."] + lines[-tail:])


def active_job_excerpt(max_lines: int = 16) -> str:
    if not JOB_DESCRIPTION.exists():
        return "jobs/job_description.txt is missing."
    lines = [line.rstrip() for line in read_text(JOB_DESCRIPTION).splitlines() if line.strip()]
    if not lines:
        return "jobs/job_description.txt is empty."
    if len(lines) <= max_lines:
        return "\n".join(lines)
    return "\n".join(lines[:max_lines] + ["..."])


def tracker_tail(max_rows: int = 4) -> str:
    if not TRACKER.exists():
        return "scratch/applications.csv is missing."
    with TRACKER.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return "scratch/applications.csv has no rows."
    selected = rows[-max_rows:]
    lines = [
        "date_added | company | role_title | lane_label | fit_status | audit_flag | current_status | output_file"
    ]
    for row in selected:
        lines.append(
            " | ".join(
                (
                    row.get("date_added", ""),
                    row.get("company", ""),
                    row.get("role_title", ""),
                    row.get("lane_label", ""),
                    row.get("fit_status", ""),
                    row.get("audit_flag", ""),
                    row.get("current_status", ""),
                    Path(row.get("output_file", "")).name if row.get("output_file", "") else "",
                )
            )
        )
    return "\n".join(lines)


def jd_library_summary() -> str:
    if not JD_LIBRARY_INDEX.exists():
        return "scratch/jd_library/index.csv is missing."
    with JD_LIBRARY_INDEX.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        return "scratch/jd_library/index.csv has no archived rows."
    lines = [f"Archived JD rows: {len(rows)}"]
    for row in rows[-3:]:
        lines.append(
            " | ".join(
                (
                    row.get("date", ""),
                    row.get("company", ""),
                    row.get("role", ""),
                    row.get("lane", ""),
                    row.get("filename", ""),
                )
            )
        )
    return "\n".join(lines)


def command_section(skip_checks: bool) -> str:
    if skip_checks:
        return "Skipped by `--skip-checks`."
    sections = []
    for label, command_name in (
        ("Latest validation", "validate"),
        ("Latest integration test", "integration-test"),
        ("Latest tracker summary", "track-report"),
    ):
        sections.append(f"### {label}")
        sections.append("```text")
        sections.append(compact_lines(run_command(command_name)))
        sections.append("```")
    return "\n".join(sections)


def current_system_contract() -> str:
    try:
        import build_cover_letter
        import build_federal_resume
        import resume_analysis
    except Exception as error:  # noqa: BLE001
        return f"Live contract snapshot unavailable because imports failed: {error}"

    audit_states = ", ".join(resume_analysis.AUDIT_STATUS_ORDER)
    standard_min, standard_max = build_cover_letter.cover_letter_word_range(build_cover_letter.STANDARD_COVER_MODE)
    long_min, long_max = build_cover_letter.cover_letter_word_range(build_cover_letter.LONG_COVER_MODE)
    packet_modes = ", ".join(PACKET_MODES)
    default_refresh_modes = ", ".join(claude_review_bundle.DEFAULT_PACKET_MODES)
    lines = (
        f"- Commercial filename audit states live today: `{audit_states}`.",
        "- `DRAFT` is a live commercial output-state suffix when filename parsing detects draft output. It is documented separately from `resume_analysis.AUDIT_STATUS_ORDER`, not a replacement for it.",
        "- `REVIEW` is not a live audit state today. Treat it as a proposal unless and until the codebase explicitly adds and propagates it.",
        "- Tracker fields are separate today: `lane_label`, `fit_status`, and `audit_flag` are not interchangeable.",
        f"- Commercial cover-letter modes live today: `standard` = `{standard_min}-{standard_max}` words, `long` = `{long_min}-{long_max}` words.",
        f"- Federal resume contract live today: exactly `{build_federal_resume.TARGET_PAGE_COUNT}` pages at `{build_federal_resume.MIN_BODY_FONT_SIZE:.0f}pt` minimum body text, plus a separate federal qualifications statement.",
        "- Federal outputs do not use commercial filename audit states or tracker fit-state semantics today.",
        "- Federal cover, interview cheat sheet, and detailed guide are wrappers over shared commercial builders with federal context resolution.",
        f"- Current packet modes: `{packet_modes}`.",
        f"- Current default `claude-refresh` packet modes: `{default_refresh_modes}`.",
    )
    return "\n".join(lines)


def packet_self_audit(mode: PacketMode, warnings: list[str]) -> None:
    for ref in CONTEXT_FILES:
        if not (PROJECT_ROOT / ref).exists():
            append_warning_once(warnings, f"Missing context file: `{ref}`")
    if not mode.excerpts:
        append_warning_once(warnings, f"Packet mode `{mode.name}` has no excerpt map.")
    for warning in packet_excerpt_resolution_warnings(mode):
        append_warning_once(warnings, warning)
    if not TASKS_PATH.exists():
        append_warning_once(warnings, "Missing task runner: `tasks.py`")
        return
    task_source = read_text(TASKS_PATH)
    for command in ("claude-packet", "claude-prompt", "claude-refresh", "validate", "integration-test", "track-report"):
        if command not in task_source:
            append_warning_once(warnings, f"tasks.py does not visibly register `{command}`.")
    template_paths = [REVIEW_TEMPLATE, PLAN_TEMPLATE]
    if mode.name == "claude-review":
        template_paths.append(PROGRESS_CHECK_TEMPLATE)
    for template_path in template_paths:
        if not template_path.exists():
            append_warning_once(warnings, f"Missing Claude prompt template: `{template_path.relative_to(PROJECT_ROOT)}`")
            continue
        template_text = read_text(template_path)
        if "Distinguish current live behavior from proposed improvements" not in template_text and "Distinguish live behavior from proposals" not in template_text:
            append_warning_once(warnings, f"Claude prompt template is missing live-vs-proposal guidance: `{template_path.name}`")
    if mode.name not in {"broad", "tracker", "checklist", "resume", "cover", "interview", "workflow", "federal", "claude-review"}:
        append_warning_once(warnings, f"Unexpected packet mode encountered: `{mode.name}`")


def warning_section(warnings: list[str]) -> str:
    if not warnings:
        return ""
    lines = ["## Packet Self-Audit"]
    lines.extend(f"- {warning}" for warning in warnings)
    return "\n".join(lines)


def prompt_commands(mode_name: str) -> tuple[str, str, str]:
    packet = f"python tasks.py claude-packet --mode {mode_name}"
    review = f"python tasks.py claude-prompt review --packet-mode {mode_name}"
    plan = f"python tasks.py claude-prompt plan --packet-mode {mode_name}"
    return packet, review, plan


def build_packet(mode_name: str, *, skip_checks: bool) -> str:
    mode = PACKET_MODES[mode_name]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    warnings: list[str] = []
    packet_self_audit(mode, warnings)
    code_sections = "\n\n".join(excerpt_block(spec, warnings) for spec in mode.excerpts)
    context_list = "\n".join(f"- {item}" for item in CONTEXT_FILES)
    desired_behavior = "\n".join(f"- {item}" for item in mode.desired_behavior)
    questions = "\n".join(f"{index}. {question}" for index, question in enumerate(mode.questions, start=1))
    packet_command, review_command, plan_command = prompt_commands(mode_name)
    warning_block = warning_section(warnings)
    warning_text = f"{warning_block}\n\n" if warning_block else ""
    return f"""# {mode.title}

This file is generated from the live codebase. It is a review packet, not source truth.

## Packet Metadata

- Packet mode: `{mode.name}`
- Packet generated: `{timestamp}`
- Packet refresh command: `{packet_command}`
- Recommended review prompt: `{review_command}`
- Recommended plan prompt: `{plan_command}`

{warning_text}## Review Goal

{mode.review_goal}

Do not rewrite whole files. Prioritize concrete findings, edge cases, and exact Codex instructions.

## Suggested Upload Set

Upload this file plus the compact context files below:

{context_list}

If Claude says a specific file still needs direct inspection, add only that file next rather than the whole repo.

## Context Files Read

{context_list}

## Current Behavior

- Latest compact docs and changelog should reflect the current packet and prompt workflow.
- Latest known local validation before this packet:

{command_section(skip_checks)}

## Current System Contract

{current_system_contract()}

### Active Job Excerpt
```text
{active_job_excerpt()}
```

### Current Tracker Tail
```text
{tracker_tail()}
```

### Archived JD Summary
```text
{jd_library_summary()}
```

## Desired Behavior

{desired_behavior}

## Relevant Code

{code_sections}

## Questions For Claude

{questions}
"""


def main() -> int:
    args = parse_args()
    claude_review_bundle.refresh_support_files()
    written = write_packet_artifacts(args.mode, skip_checks=args.skip_checks, output_path=args.output)
    print(f"Claude review packet created: {written[0]}")
    print(f"Claude review packet manifest: {written[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
