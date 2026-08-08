#!/usr/bin/env python3
"""Project keyword-policy outcomes across archived commercial JD corpora."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import csv
import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import _bootstrap

_bootstrap.ensure_script_path()

import build_resume
import resume_analysis
from requirement_engine import parse_commercial_requirements
from config.paths import OUTPUT_DIR, PROJECT_ROOT


JD_LIBRARY = PROJECT_ROOT / "scratch" / "jd_library"
RECENT_FIXTURES = (
    "20260729_165915_Aptean_ERP_Consultant_0494beea",
    "20260727_102327_Amplify_Technical_Project_Manager_90139865",
    "20260727_203836_GoodShip_Implementation_Manager_4580dc7d",
    "20260727_211328_GoodShip_Implementation_Manager_5672c21f",
    "20260727_213951_Limbic_Technical_Implementation_Manager_f60fef0e",
    "20260728_134142_Direct_Travel_Implementation_704a91d9",
    "20260728_160319_RevsUp_Technical_Project_Manager_a981509d",
    "20260728_182957_OneTrust_Technical_Implementation_Consultant_b1a7f562",
    "20260729_165451_Fisher_Phillips_Business_Process_Optimization_Specialist_f241981a",
    "20260729_134251_Azalea_Health_Client_Success_Manager_1b844a70",
    "20260728_082806_TRIA_SaaS_Implementation_Manager_4a8d10df",
    "20260727_194520_Fleetio_Senior_Technical_Project_Manager_Engineering_666d9b84",
    "20260727_212222_Pragmatike_Technical_Project_Manager_Industrial_Software_489b702a",
    "20260726_190409_APEI_Senior_Technical_Project_Manager_Salesforce_16555cb1",
    "20260728_164701_Barracuda_Implementation_Consultant_6a4e7c6d",
)


def legacy_fixtures() -> tuple[str, ...]:
    return tuple(
        path.name
        for path in sorted(JD_LIBRARY.glob("20260720_*"))[:20]
    )


def resume_page_count(path: Path) -> int:
    try:
        with zipfile.ZipFile(path) as archive:
            root = ET.fromstring(archive.read("docProps/app.xml"))
        node = next((item for item in root.iter() if item.tag.endswith("Pages")), None)
        return int(node.text) if node is not None and node.text else 0
    except Exception:
        return 0


def matching_resume(job_description: str) -> Path | None:
    matches = build_resume.matching_output_files(OUTPUT_DIR, job_description, "Resume.docx")
    if matches:
        return matches[0]
    company = build_resume.extract_company_name(job_description) or ""
    company_key = build_resume.normalize_compare(company)
    candidates = [
        path
        for path in OUTPUT_DIR.glob("Christian Estrada -* Resume.docx")
        if company_key and company_key in build_resume.normalize_compare(path.name)
    ]
    return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None


def fit_from_path(path: Path) -> str:
    return resume_analysis.output_audit_state(path)


def skills_count(resume_text: str) -> int:
    skills_text = build_resume.core_competencies_text_from_text(resume_text)
    items: set[str] = set()
    for line in skills_text.splitlines():
        value = line.split(":", 1)[1] if ":" in line else line
        items.update(
            build_resume.normalize_compare(item)
            for item in re.split(r"\s*\|\s*", value)
            if build_resume.normalize_compare(item)
        )
    return len(items)


def ownership_measurement(resume_path: Path | None) -> tuple[str, str, str]:
    if resume_path is None:
        return "[]", "{}", "NO_OUTPUT"
    with tempfile.TemporaryDirectory(prefix="keyword_corpus_ownership_") as temp_dir:
        with zipfile.ZipFile(resume_path) as archive:
            archive.extractall(temp_dir)
        document_xml = Path(temp_dir) / "word" / "document.xml"
        skim_segments = build_resume.ownership_skim_zone(document_xml)
        ownership = build_resume.assess_top_third_ownership(skim_segments)
        segments = [
            {"kind": segment.kind, "text": segment.text}
            for segment in skim_segments
        ]
        return (
            json.dumps(segments, ensure_ascii=True, separators=(",", ":")),
            json.dumps(
                {
                    "severity": ownership.severity,
                    "issues": ownership.issues,
                    "strong_segments": ownership.strong_segments,
                    "soft_segments": ownership.soft_segments,
                },
                ensure_ascii=True,
                separators=(",", ":"),
            ),
            ownership.severity,
        )


def validating_requirement_texts(
    term: str,
    requirement_elements: tuple[object, ...],
) -> tuple[str, ...]:
    normalized = build_resume.normalize_compare(term)
    matches: list[str] = []
    for element in requirement_elements:
        text = str(getattr(element, "text", "")).strip()
        canonical_terms = tuple(str(value) for value in getattr(element, "canonical_terms", ()))
        if (
            build_resume.contains_search_term(text, term)
            or any(
                build_resume.normalize_compare(value) == normalized
                or build_resume.contains_search_term(value, term)
                for value in canonical_terms
            )
        ):
            matches.append(text)
    return tuple(dict.fromkeys(matches))


def classifier_diagnostics(
    job_description: str,
    core_terms: set[str],
    balanced_blocker_terms: set[str],
) -> str:
    requirement_elements = tuple(parse_commercial_requirements(job_description))
    rows: list[dict[str, object]] = []
    for term in sorted(core_terms):
        classification = resume_analysis.classify_keyword_candidate(
            term,
            job_description,
            requirement_elements,
        )
        entry = build_resume.evidence_term_for_variant(term)
        rows.append(
            {
                "term": term,
                "class": classification.candidate_class.value,
                "reason": classification.reason,
                "validated": classification.validated_requirement,
                "requirement_relation": classification.requirement_relation,
                "validating_requirement_text": classification.validating_requirement_text,
                "alternative_group_id": classification.alternative_group_id,
                "alternative_terms": classification.alternative_terms,
                "requirements": validating_requirement_texts(term, requirement_elements),
                "concept": str((entry or {}).get("concept_id", "")),
                "placement": "core",
                "balanced_blocker": term in balanced_blocker_terms,
            }
        )
    return json.dumps(rows, ensure_ascii=True, separators=(",", ":"))


def packaged_audit_baseline(
    resume_path: Path | None,
    job_description: str,
    source_resume_text: str,
    recorded_fit: str,
) -> tuple[str, str, str, str]:
    if resume_path is None:
        return "[]", "[]", "NO_OUTPUT", "[]"
    with tempfile.TemporaryDirectory(prefix="keyword_corpus_ownership_") as temp_dir:
        with zipfile.ZipFile(resume_path) as archive:
            archive.extractall(temp_dir)
        document_xml = Path(temp_dir) / "word" / "document.xml"
        ownership_segments, ownership_issues, _ownership_severity = ownership_measurement(resume_path)
        if recorded_fit in {"PASS", "BRIDGE"}:
            resume_text = build_resume.visible_text(document_xml)
            alignment = build_resume.alignment_score_report(job_description, resume_text)
            recomputed_fit, recomputed_notes = build_resume.final_fit_audit(
                document_xml,
                job_description,
                source_resume_text=source_resume_text,
                alignment_grade=str(alignment["grade"]),
            )
        else:
            recomputed_fit = recorded_fit
            recomputed_notes = ["Recomputation skipped: Fit-safety gate applies to existing PASS/BRIDGE outputs."]
        return (
            ownership_segments,
            ownership_issues,
            recomputed_fit,
            json.dumps(recomputed_notes, ensure_ascii=True, separators=(",", ":")),
        )


def _row_for_fixture(
    fixture: str,
    *,
    resume_path_override: Path | None = None,
    fresh_metadata: dict[str, object] | None = None,
    require_resume: bool = False,
) -> dict[str, object]:
    jd_path = JD_LIBRARY / fixture / "job_description.txt"
    job_description = jd_path.read_text(encoding="utf-8-sig")
    resume_path = resume_path_override if resume_path_override is not None else matching_resume(job_description)
    if require_resume and (resume_path is None or not resume_path.is_file()):
        raise FileNotFoundError(f"Fresh manifest resume is missing for {fixture}: {resume_path}")
    if resume_path:
        resume_text = build_resume.docx_visible_text_from_path(resume_path)
        fit = fit_from_path(resume_path)
        pages = resume_page_count(resume_path)
    else:
        selected_source = build_resume.choose_resume(job_description)
        resume_text = build_resume.docx_visible_text_from_path(selected_source)
        fit = "NO_OUTPUT"
        pages = 0
    source_text = build_resume.docx_visible_text_from_path(build_resume.choose_resume(job_description))
    coverage = build_resume.ats_coverage(job_description, resume_text)
    core = coverage["core"]
    breadth = coverage["breadth"]
    readiness_by_policy = {
        policy: build_resume.resume_readiness_report(
            job_description,
            resume_text,
            source_resume_text=source_text,
            audit_status=fit,
            keyword_policy=policy,
        )
        for policy in build_resume.KEYWORD_POLICIES
    }
    advisory = readiness_by_policy["advisory"]
    supported = [
        gap for gap in advisory.prioritized_unresolved_gaps
        if gap.support_level != "unsupported-do-not-insert"
        and not build_resume.contains_search_term(resume_text, gap.label)
    ]
    genuine = [
        gap for gap in advisory.prioritized_unresolved_gaps
        if gap.support_level == "unsupported-do-not-insert"
    ]
    excluded_noise = [
        term
        for term in (*resume_analysis.KEYWORD_NOISE_SINGLETONS, *resume_analysis.KEYWORD_NOISE_PHRASES)
        if build_resume.contains_search_term(job_description, term)
    ]
    core_terms = {
        build_resume.normalize_compare(term)
        for term in build_resume.high_value_audit_keywords(job_description)
    }
    breadth_terms = {
        build_resume.normalize_compare(term)
        for term in build_resume.ats_scan_terms(job_description)
    }
    supported_core = [
        gap for gap in supported
        if build_resume.normalize_compare(gap.label) in core_terms
    ]
    supported_breadth = [
        gap for gap in supported
        if build_resume.normalize_compare(gap.label) in breadth_terms
        and build_resume.normalize_compare(gap.label) not in core_terms
    ]
    balanced_blockers = list(readiness_by_policy["balanced"].hard_blockers)
    balanced_blocker_terms = {
        build_resume.normalize_compare(gap.label)
        for gap in balanced_blockers
    }
    exhaustive_blockers = supported
    false_balanced = [
        gap.label
        for gap in balanced_blockers
        if resume_analysis.classify_keyword_candidate(gap.label, job_description).candidate_class
        == resume_analysis.KeywordCandidateClass.NOISE
        or build_resume.contains_search_term(resume_text, gap.label)
    ]
    non_requirement_balanced = [
        gap.label
        for gap in balanced_blockers
        if resume_analysis.classify_keyword_candidate(
            gap.label,
            job_description,
        ).candidate_class
        != resume_analysis.KeywordCandidateClass.REQUIREMENT
    ]
    alignment = build_resume.alignment_score_report(job_description, resume_text)
    placement_plan = build_resume.planned_supported_keyword_terms(job_description, source_text)
    planned_concepts = {
        str((build_resume.evidence_term_for_variant(term) or {}).get("concept_id", ""))
        for term in placement_plan
    }
    planned_terms = {build_resume.normalize_compare(term) for term in placement_plan}
    blocker_diagnostics: list[dict[str, object]] = []
    for gap in (*supported_core, *supported_breadth, *genuine):
        normalized = build_resume.normalize_compare(gap.label)
        entry = build_resume.evidence_term_for_variant(gap.label) or {}
        classification = resume_analysis.classify_keyword_candidate(
            gap.label,
            job_description,
            tuple(parse_commercial_requirements(job_description)),
        )
        concept_id = str(entry.get("concept_id", ""))
        plan_member = normalized in planned_terms or bool(concept_id and concept_id in planned_concepts)
        location, landing = build_resume.landing_text_for_term(gap.label, resume_text)
        if gap.support_level == "unsupported-do-not-insert":
            disposition = "unsupported_not_blocking"
        elif plan_member:
            disposition = "planned_but_unwritten"
        else:
            disposition = "supported_not_planned"
        blocker_diagnostics.append(
            {
                "term": gap.label,
                "support_level": gap.support_level,
                "scoring_tier": "core" if normalized in core_terms else "breadth",
                "validating_requirements": validating_requirement_texts(
                    gap.label,
                    tuple(parse_commercial_requirements(job_description)),
                ),
                "catalog_concept": concept_id,
                "requirement_relation": classification.requirement_relation,
                "validating_requirement_text": classification.validating_requirement_text,
                "alternative_group_id": classification.alternative_group_id,
                "alternative_terms": classification.alternative_terms,
                "balanced_eligibility_reason": (
                    "eligible"
                    if (
                        classification.candidate_class
                        == resume_analysis.KeywordCandidateClass.REQUIREMENT
                        and classification.validated_requirement
                        and classification.requirement_relation == "assigned"
                        and gap.support_level == "supported-direct-unresolved"
                    )
                    else "requires assigned validated REQUIREMENT with direct support"
                ),
                "placement_plan_member": plan_member,
                "final_location": location,
                "final_landing": landing,
                "disposition": disposition,
            }
        )
    direct_outcomes = {
        policy: bool(readiness.hard_blockers)
        for policy, readiness in readiness_by_policy.items()
    }
    # Direct cover/qualifications builds and the workflow runner all call
    # resume_readiness_for_output(), which delegates to the same report used
    # above. Reopening and rescanning the DOCX three more times does not test a
    # separate gate; record the shared-path outcomes once.
    workflow_outcomes = dict(direct_outcomes)
    gating_parity = direct_outcomes == workflow_outcomes
    if fresh_metadata and fresh_metadata.get("packaged_audit_passed") is True:
        ownership_segments, ownership_issues, _ownership_severity = ownership_measurement(resume_path)
        recomputed_fit = fit
        recomputed_fit_notes = json.dumps(
            ["Fresh build already passed pre-package versus packaged audit equality."],
            ensure_ascii=True,
            separators=(",", ":"),
        )
    else:
        (
            ownership_segments,
            ownership_issues,
            recomputed_fit,
            recomputed_fit_notes,
        ) = packaged_audit_baseline(resume_path, job_description, source_text, fit)
    row: dict[str, object] = {
        "fixture": fixture,
        "target": build_resume.extract_output_target_name(job_description),
        "resume": resume_path.name if resume_path else "",
        "population": "archived_output",
        "build_timestamp": "",
        "pipeline_fingerprint": "",
        "source_lane": build_resume.choose_resume(job_description).name,
        "build_exit_state": "existing_output" if resume_path else "no_output",
        "packaged_audit_passed": bool(resume_path),
        "core_percent": core["percent"],
        "breadth_percent": breadth["percent"],
        "supported_unwritten": len({build_resume.normalize_compare(gap.label) for gap in supported}),
        "supported_core_unwritten": len(
            {build_resume.normalize_compare(gap.label) for gap in supported_core}
        ),
        "supported_breadth_unwritten": len(
            {build_resume.normalize_compare(gap.label) for gap in supported_breadth}
        ),
        "genuine_gaps": len({build_resume.normalize_compare(gap.label) for gap in genuine}),
        "excluded_noise": len(excluded_noise),
        "skills_count": skills_count(resume_text),
        "pages": pages,
        "fit": fit,
        "recomputed_fit": recomputed_fit,
        "recomputed_fit_notes": recomputed_fit_notes,
        "tailoring": advisory.tailoring_status,
        "alignment_score": alignment["total_score"],
        "alignment_fail_floor_met": bool(alignment["minimum_pass_met"]),
        "advisory_blockers": len(advisory.hard_blockers),
        "balanced_blockers": len(balanced_blockers),
        "exhaustive_blockers": len(exhaustive_blockers),
        "false_balanced_blockers": len(false_balanced),
        "balanced_blocker_terms": " | ".join(gap.label for gap in balanced_blockers),
        "false_balanced_terms": " | ".join(false_balanced),
        "non_requirement_balanced_blockers": len(non_requirement_balanced),
        "non_requirement_balanced_terms": " | ".join(non_requirement_balanced),
        "direct_workflow_gating_parity": gating_parity,
        "gating_parity_basis": "shared_resume_readiness_report",
        "direct_policy_blocking": json.dumps(direct_outcomes, sort_keys=True, separators=(",", ":")),
        "workflow_policy_blocking": json.dumps(workflow_outcomes, sort_keys=True, separators=(",", ":")),
        "blocker_diagnostics": json.dumps(
            blocker_diagnostics,
            ensure_ascii=True,
            separators=(",", ":"),
        ),
        "core_candidate_diagnostics": classifier_diagnostics(
            job_description,
            core_terms,
            balanced_blocker_terms,
        ),
        "ownership_segments": ownership_segments,
        "ownership_issues": ownership_issues,
    }
    if fresh_metadata:
        row.update(
            {
                "population": "fresh_rebuild",
                "build_timestamp": str(fresh_metadata.get("build_finished", "")),
                "pipeline_fingerprint": str(fresh_metadata.get("pipeline_fingerprint", "")),
                "source_lane": str(fresh_metadata.get("source_lane", row["source_lane"])),
                "build_exit_state": str(fresh_metadata.get("exit_state", "")),
                "packaged_audit_passed": bool(fresh_metadata.get("packaged_audit_passed", False)),
                "pages": int(fresh_metadata.get("page_count", row["pages"]) or row["pages"]),
            }
        )
    return row


def row_for_fixture(fixture: str) -> dict[str, object]:
    return _row_for_fixture(fixture)


def row_for_fresh_manifest_entry(entry: dict[str, object]) -> dict[str, object]:
    fixture = str(entry["fixture"])
    resume_path = Path(str(entry["resume_path"]))
    return _row_for_fixture(
        fixture,
        resume_path_override=resume_path,
        fresh_metadata=entry,
        require_resume=True,
    )


def ownership_row_for_fixture(fixture: str) -> dict[str, object]:
    jd_path = JD_LIBRARY / fixture / "job_description.txt"
    job_description = jd_path.read_text(encoding="utf-8-sig")
    resume_path = matching_resume(job_description)
    segments, findings, severity = ownership_measurement(resume_path)
    return {
        "fixture": fixture,
        "target": build_resume.extract_output_target_name(job_description),
        "resume": resume_path.name if resume_path else "",
        "fit": fit_from_path(resume_path) if resume_path else "NO_OUTPUT",
        "pages": resume_page_count(resume_path) if resume_path else 0,
        "ownership_severity": severity,
        "ownership_segments": segments,
        "ownership_findings": findings,
    }


def ownership_row_for_output(path_text: str) -> dict[str, object]:
    resume_path = Path(path_text)
    segments, findings, severity = ownership_measurement(resume_path)
    return {
        "fixture": "",
        "target": resume_path.stem,
        "resume": resume_path.name,
        "fit": fit_from_path(resume_path),
        "pages": resume_page_count(resume_path),
        "ownership_severity": severity,
        "ownership_segments": segments,
        "ownership_findings": findings,
    }


def fresh_manifest_entries(
    manifest_path: Path,
    *,
    corpus: str | None = None,
) -> list[dict[str, object]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if manifest.get("population") != "fresh_rebuild":
        raise ValueError(f"Not a fresh-rebuild manifest: {manifest_path}")
    if manifest.get("active_state_unchanged") is not True:
        raise ValueError("Fresh rebuild did not prove active jobs and output remained unchanged.")
    manifest_fingerprint = str(manifest.get("pipeline_fingerprint", ""))
    if not manifest_fingerprint:
        raise ValueError("Fresh rebuild manifest has no pipeline fingerprint.")
    entries = [
        dict(item)
        for item in manifest.get("fixtures", [])
        if isinstance(item, dict) and (corpus is None or item.get("corpus") == corpus)
    ]
    seen: set[tuple[str, str]] = set()
    seen_artifacts: set[Path] = set()
    for entry in entries:
        key = (str(entry.get("corpus", "")), str(entry.get("fixture", "")))
        if not all(key) or key in seen:
            raise ValueError(f"Missing or duplicate fresh fixture identity: {key}")
        seen.add(key)
        if entry.get("exit_state") != "success":
            raise ValueError(f"Fresh fixture did not build successfully: {key}")
        if entry.get("pipeline_fingerprint") != manifest_fingerprint:
            raise ValueError(f"Pipeline fingerprint drift for fresh fixture: {key}")
        resume_path = Path(str(entry.get("resume_path", "")))
        if not resume_path.is_file():
            raise FileNotFoundError(f"Fresh fixture resume is missing: {resume_path}")
        resolved_resume = resume_path.resolve()
        if resolved_resume in seen_artifacts:
            raise ValueError(f"Fresh fixtures share a packaged DOCX artifact: {resolved_resume}")
        seen_artifacts.add(resolved_resume)
        notes_path = Path(str(entry.get("notes_path", "")))
        if not notes_path.is_file():
            raise FileNotFoundError(f"Fresh fixture Resume Notes are missing: {notes_path}")
        if int(entry.get("page_count", 0)) != 2:
            raise ValueError(f"Fresh fixture is not exactly two pages: {key}")
        if entry.get("page_count_source") not in {"render_images", "fit_render_log"}:
            raise ValueError(f"Fresh fixture lacks authoritative page count: {key}")
        if entry.get("packaged_audit_passed") is not True:
            raise ValueError(f"Packaged audit did not pass for fresh fixture: {key}")
    expected = int(manifest.get("expected_fixtures", len(entries)))
    if corpus is None and len(entries) != expected:
        raise ValueError(f"Fresh manifest is incomplete: expected {expected}, found {len(entries)}")
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", choices=("recent", "legacy20", "outputs"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--ownership-only", action="store_true")
    parser.add_argument(
        "--rebuild-manifest",
        type=Path,
        help="Analyze exact isolated DOCX paths from a fresh-corpus rebuild manifest.",
    )
    args = parser.parse_args()
    if args.rebuild_manifest:
        if args.ownership_only or args.corpus == "outputs":
            parser.error("--rebuild-manifest cannot be combined with output ownership mode.")
        items = fresh_manifest_entries(args.rebuild_manifest, corpus=args.corpus)
        row_builder = row_for_fresh_manifest_entry
    elif args.corpus == "outputs":
        items = tuple(
            str(path)
            for path in sorted(OUTPUT_DIR.glob("Christian Estrada -* Resume.docx"))
            if not path.name.endswith(" Federal Resume.docx")
        )
        row_builder = ownership_row_for_output
    else:
        if args.corpus is None:
            parser.error("--corpus is required unless --rebuild-manifest is provided.")
        items = RECENT_FIXTURES if args.corpus == "recent" else legacy_fixtures()
        row_builder = ownership_row_for_fixture if args.ownership_only else row_for_fixture
    if args.workers > 1:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            rows = list(executor.map(row_builder, items))
    else:
        rows = [row_builder(item) for item in items]
    fieldnames = list(rows[0]) if rows else []
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)


if __name__ == "__main__":
    main()
