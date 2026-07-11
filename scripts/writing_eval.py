#!/usr/bin/env python3
"""Lightweight writing-style evaluator for resume and cover-letter prose."""

from __future__ import annotations

import argparse
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


ARTIFACT_CHOICES = (
    "generic",
    "resume_summary",
    "cover_letter_opening",
    "cover_letter_proof",
    "cover_letter_bridge",
    "cover_letter_close",
    "cover_letter_full",
    "thank_you_body",
    "followup_email_body",
    "interview_followup_body",
    "post_round_email_body",
    "interview_pitch",
    "interview_story_answer",
    "checklist_narrative",
)

DOCX_SECTION_CHOICES = (
    "resume_summary",
    "cover_letter_opening",
    "cover_letter_proof",
    "cover_letter_bridge",
    "cover_letter_close",
    "cover_letter_full",
)
WORD_NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
RESUME_SUMMARY_MIN_WORDS = 70
RESUME_SUMMARY_MAX_WORDS = 110
SENDABLE_COVER_ARTIFACTS = {
    "cover_letter_opening",
    "cover_letter_proof",
    "cover_letter_bridge",
    "cover_letter_close",
    "cover_letter_full",
}
SENDABLE_EMAIL_ARTIFACTS = {
    "thank_you_body",
    "followup_email_body",
    "interview_followup_body",
    "post_round_email_body",
}
PREP_ARTIFACTS = {
    "interview_pitch",
    "interview_story_answer",
    "checklist_narrative",
}
LIST_DENSITY_ARTIFACTS = SENDABLE_COVER_ARTIFACTS | SENDABLE_EMAIL_ARTIFACTS | PREP_ARTIFACTS
FALLBACK_CLAUSE_ARTIFACTS = SENDABLE_COVER_ARTIFACTS | SENDABLE_EMAIL_ARTIFACTS
CONTAINS_THAT_WARNING_ARTIFACTS = PREP_ARTIFACTS | {"resume_summary"}


@dataclass(frozen=True)
class Issue:
    code: str
    severity: str
    message: str
    snippet: str = ""


@dataclass(frozen=True)
class EvaluationSample:
    sample_id: str
    artifact: str
    text: str
    source_path: str | None = None
    expected_outcome: str | None = None
    must_flag: tuple[str, ...] = ()
    must_not_flag: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvaluationResult:
    sample: EvaluationSample
    issues: tuple[Issue, ...]
    score: int
    passed: bool


GLOBAL_REGEX_RULES = (
    (
        "template_label",
        "fail",
        r"\b(Target context:|Strong fit for roles|Experience spans|Background includes|Background spans)\b",
        "Uses labeled or narrated template phrasing instead of direct prose.",
    ),
    (
        "system_fit_closer",
        "fail",
        r"\b(This background fits(?: teams that need)?|This background is strongest|The same pattern fits)\b",
        "Uses a system-like fit closer instead of ending with concrete role relevance or outcomes.",
    ),
    (
        "proof_opener_includes",
        "fail",
        r"(^|[.!?]\s+)(Work includes|Recent work has included|Prior work includes)\b",
        "Opens proof with an 'includes' construction that reads like generated narration.",
    ),
    (
        "experience_behind_that",
        "fail",
        r"\bThe experience behind that\b",
        "Uses the canned bridge phrase 'The experience behind that'.",
    ),
    (
        "time_clause_during_periods",
        "fail",
        r"\bduring periods when\b",
        "Uses an appended 'during periods when...' clause instead of direct context.",
    ),
    (
        "time_clause_at_a_point_where",
        "fail",
        r"\bat a point where\b",
        "Uses 'at a point where' narration instead of direct context.",
    ),
    (
        "team_appears_narration",
        "fail",
        r"\bThe team appears to be\b",
        "Narrates the team's situation instead of speaking directly about the work.",
    ),
    (
        "what_so_formula_close",
        "fail",
        r"\bWhat I bring to\b.*\bSo what that means\b",
        "Uses the 'What I bring / So what that means' close formula.",
    ),
    (
        "generic_conversation_close",
        "fail",
        r"\bI would welcome a conversation about where (?:that|you most need|that visibility|that perspective)\b",
        "Uses a generic conversation close instead of naming the concrete problem to discuss.",
    ),
    (
        "along_the_way_transition",
        "fail",
        r"\bAlong the way\b",
        "Uses 'Along the way' as a weak transition.",
    ),
    (
        "consistent_pattern_same",
        "fail",
        r"\bthe consistent pattern was the same\b",
        "Uses the redundant phrase 'the consistent pattern was the same'.",
    ),
    (
        "practical_execution_depth",
        "fail",
        r"\bpractical execution depth\b",
        "Uses vague narrative filler instead of a concrete value claim.",
    ),
    (
        "i_want_to_do_more_of",
        "fail",
        r"\bI want to do more of\b",
        "Uses the explicit aspiration phrase 'I want to do more of' instead of direct evidence.",
    ),
    (
        "reputation_first_opening",
        "fail",
        r"\breputation\b.*\bmatters because\b",
        "Leads with company reputation instead of the role's concrete problem.",
    ),
    (
        "direct_alignment_bridge",
        "fail",
        r"\b(?:which is exactly the kind of|speaks directly to|aligns directly with|aligns directly to)\b",
        "Uses self-explaining bridge language instead of direct proof.",
    ),
    (
        "content_free_aphorism",
        "fail",
        r"\b(?:work like this only sticks when|the work only matters when it changes a decision)\b",
        "Uses a content-free aphorism instead of a concrete claim.",
    ),
    (
        "weak_hypothetical_close",
        "fail",
        r"\b(?:would be valuable|would be beneficial)\b",
        "Uses a weak hypothetical close instead of a direct ask.",
    ),
    (
        "abstract_role_moves",
        "fail",
        r"\brole moves\b",
        "Uses the abstract 'The role moves...' pattern instead of direct fit language.",
    ),
    (
        "abstract_work_needs",
        "fail",
        r"\bThe work needs\b",
        "Uses the abstract 'The work needs...' pattern instead of concrete proof.",
    ),
    (
        "together_background_shows",
        "fail",
        r"\bTogether, that background shows\b",
        "Uses the canned 'Together, that background shows...' line.",
    ),
    (
        "where_role_reaches_beyond",
        "fail",
        r"\bWhere the role reaches beyond\b",
        "Uses the canned 'Where the role reaches beyond...' bridge.",
    ),
    (
        "role_summary_opening",
        "fail",
        r"(^|[.!?]\s+)At [A-Z][A-Za-z0-9&' .-]+,\s+[^.]{0,120}\brole supporting\b",
        "Opens with role-summary narration instead of a direct company-and-role statement.",
    ),
)

SENTENCE_START_RULES = (
    (
        "sentence_starts_with_that",
        "fail",
        "That",
        "Starts a sentence with 'That', which usually sounds generic in this system.",
    ),
    (
        "sentence_starts_with_this_background",
        "fail",
        "This background",
        "Starts a sentence with 'This background', which sounds like system narration.",
    ),
    (
        "sentence_starts_with_the_same_pattern",
        "fail",
        "The same pattern",
        "Starts a sentence with 'The same pattern', which sounds like a templated close.",
    ),
    (
        "sentence_starts_with_work_includes",
        "fail",
        "Work includes",
        "Starts a sentence with 'Work includes', which sounds like proof scaffolding.",
    ),
    (
        "sentence_starts_with_recent_work_has_included",
        "fail",
        "Recent work has included",
        "Starts a sentence with 'Recent work has included', which sounds like system narration.",
    ),
    (
        "sentence_starts_with_prior_work_includes",
        "fail",
        "Prior work includes",
        "Starts a sentence with 'Prior work includes', which sounds like summary scaffolding.",
    ),
    (
        "sentence_starts_with_the_team_appears",
        "fail",
        "The team appears",
        "Starts a sentence with 'The team appears', which narrates the setup instead of making a direct point.",
    ),
    (
        "sentence_starts_with_the_experience_behind_that",
        "fail",
        "The experience behind that",
        "Starts a sentence with 'The experience behind that', which sounds assembled instead of direct.",
    ),
    (
        "sentence_starts_with_what_i_bring_to",
        "fail",
        "What I bring to",
        "Starts a sentence with 'What I bring to', which often signals a templated close.",
    ),
)


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w+.#'-]+\b", text))


def normalize_artifact(value: str) -> str:
    cleaned = (value or "generic").strip().lower()
    if cleaned not in ARTIFACT_CHOICES:
        raise ValueError(f"Unsupported artifact {value!r}. Expected one of: {', '.join(ARTIFACT_CHOICES)}")
    return cleaned


def normalize_docx_section(value: str) -> str:
    cleaned = (value or "").strip().lower()
    if cleaned not in DOCX_SECTION_CHOICES:
        raise ValueError(f"Unsupported DOCX extract {value!r}. Expected one of: {', '.join(DOCX_SECTION_CHOICES)}")
    return cleaned


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def split_sentences(text: str) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []
    parts = re.split(r"(?<=[.!?])\s+", normalized)
    return [part.strip() for part in parts if part.strip()]


def list_density_issue(sentence: str) -> Issue | None:
    normalized = normalize_text(sentence)
    if word_count(normalized) < 18:
        return None
    comma_count = normalized.count(",")
    if comma_count < 3:
        return None
    connector_count = len(re.findall(r"\b(?:and|or|with|across|through|including)\b", normalized, re.I))
    if connector_count < 3:
        return None
    return Issue(
        code="list_density_overload",
        severity="fail",
        message="Sentence reads like a stacked list instead of one controlled idea.",
        snippet=normalized,
    )


def unsafe_fallback_clause_issue(text: str) -> Issue | None:
    pattern = r"\b(?:across|in|with)\s+(?:building|delivering|translating|turning|protecting|keeping|aligning)\b"
    match = re.search(pattern, text, re.I)
    if not match:
        return None
    return Issue(
        code="unsafe_fallback_clause",
        severity="fail",
        message="Contains a fallback-built connector clause that reads like stitched job-description text.",
        snippet=normalize_text(match.group(0)),
    )


def read_docx_paragraphs(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", WORD_NAMESPACE):
        texts = [node.text or "" for node in paragraph.findall(".//w:t", WORD_NAMESPACE)]
        line = "".join(texts).strip()
        if line:
            paragraphs.append(line)
    return paragraphs


def resume_summary_from_paragraphs(paragraphs: list[str]) -> str:
    for index, paragraph in enumerate(paragraphs):
        if paragraph.strip().upper() == "PROFESSIONAL SUMMARY":
            for candidate in paragraphs[index + 1 :]:
                if candidate.strip():
                    return candidate.strip()
    raise ValueError("DOCX summary extraction failed: could not locate the Professional Summary paragraph")


def cover_letter_body_from_paragraphs(paragraphs: list[str]) -> list[str]:
    start = next((index for index, line in enumerate(paragraphs) if line.lower().startswith("dear ")), -1)
    if start < 0:
        raise ValueError("DOCX cover-letter extraction failed: could not locate a salutation line")

    body: list[str] = []
    for line in paragraphs[start + 1 :]:
        lowered = line.lower()
        if lowered.startswith("thank you"):
            break
        if line == "Christian Estrada":
            break
        body.append(line.strip())

    if not body:
        raise ValueError("DOCX cover-letter extraction failed: no body paragraphs found after the salutation")
    return body


def extract_docx_text(path: Path, section: str) -> str:
    normalized_section = normalize_docx_section(section)
    paragraphs = read_docx_paragraphs(path)
    if normalized_section == "resume_summary":
        return resume_summary_from_paragraphs(paragraphs)

    body = cover_letter_body_from_paragraphs(paragraphs)
    section_map = {
        "cover_letter_opening": 0,
        "cover_letter_proof": 1,
        "cover_letter_bridge": 2,
        "cover_letter_close": -1,
    }
    if normalized_section == "cover_letter_full":
        return "\n".join(body)
    index = section_map[normalized_section]
    try:
        return body[index].strip()
    except IndexError as error:
        raise ValueError(
            f"DOCX cover-letter extraction failed: {path.name} does not contain enough body paragraphs for {normalized_section}"
        ) from error


def load_text_from_path(path: Path, artifact: str, extract: str | None = None) -> str:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        target_section = normalize_docx_section(extract or artifact)
        return extract_docx_text(path, target_section)
    return path.read_text(encoding="utf-8-sig")


def issue_from_match(code: str, severity: str, message: str, text: str, pattern: str) -> Issue | None:
    match = re.search(pattern, text, re.I)
    if not match:
        return None
    snippet = normalize_text(match.group(0))
    return Issue(code=code, severity=severity, message=message, snippet=snippet)


def evaluate_text(artifact: str, text: str, sample_id: str = "inline") -> EvaluationResult:
    normalized_artifact = normalize_artifact(artifact)
    normalized_text = normalize_text(text)
    issues: list[Issue] = []

    for code, severity, pattern, message in GLOBAL_REGEX_RULES:
        issue = issue_from_match(code, severity, message, normalized_text, pattern)
        if issue:
            issues.append(issue)

    sentences = split_sentences(normalized_text)
    for sentence in sentences:
        stripped = sentence.lstrip("\"'([{")
        for code, severity, prefix, message in SENTENCE_START_RULES:
            if stripped.startswith(prefix):
                issues.append(Issue(code=code, severity=severity, message=message, snippet=stripped))
        if normalized_artifact in LIST_DENSITY_ARTIFACTS:
            list_issue = list_density_issue(stripped)
            if list_issue:
                issues.append(list_issue)

    if normalized_artifact in CONTAINS_THAT_WARNING_ARTIFACTS:
        repeated_that_sentence = next(
            (
                sentence
                for sentence in sentences
                if len(re.findall(r"\b[Tt]hat\b", sentence)) >= 2
            ),
            "",
        )
        if repeated_that_sentence:
            issues.append(
                Issue(
                    code="contains_that",
                    severity="warn",
                    message="Repeats the word 'that' in a way that can make the sentence sound padded.",
                    snippet=normalize_text(repeated_that_sentence),
                )
            )

    if normalized_artifact == "resume_summary":
        if len(sentences) != 3:
            issues.append(
                Issue(
                    code="summary_sentence_count",
                    severity="fail",
                    message="Resume summary should use exactly three recruiter-friendly sentences.",
                    snippet=str(len(sentences)),
                )
            )
        words = word_count(normalized_text)
        if words < RESUME_SUMMARY_MIN_WORDS or words > RESUME_SUMMARY_MAX_WORDS:
            issues.append(
                Issue(
                    code="summary_word_count",
                    severity="fail",
                    message=(
                        f"Resume summary should stay between "
                        f"{RESUME_SUMMARY_MIN_WORDS} and {RESUME_SUMMARY_MAX_WORDS} words."
                    ),
                    snippet=str(words),
                )
            )
        if normalized_text.count(";") > 1:
            issues.append(
                Issue(
                    code="summary_semicolon_heavy",
                    severity="warn",
                    message="Resume summary sounds semicolon-heavy; keep to at most one semicolon.",
                    snippet=str(normalized_text.count(";")),
                )
            )

    if normalized_artifact in {
        "cover_letter_opening",
        "cover_letter_proof",
        "cover_letter_bridge",
        "cover_letter_close",
        "cover_letter_full",
    }:
        if normalized_text.count(";") > 2:
            issues.append(
                Issue(
                    code="cover_letter_semicolon_heavy",
                    severity="warn",
                    message="Cover-letter prose sounds over-scaffolded; reduce semicolon-heavy sentence chaining.",
                    snippet=str(normalized_text.count(";")),
                )
            )

    if normalized_artifact in SENDABLE_EMAIL_ARTIFACTS and normalized_text.count(";") > 1:
        issues.append(
            Issue(
                code="email_semicolon_heavy",
                severity="fail",
                message="Outbound email copy reads over-scaffolded; reduce semicolon-heavy sentence chaining.",
                snippet=str(normalized_text.count(";")),
            )
        )

    if normalized_artifact in FALLBACK_CLAUSE_ARTIFACTS:
        fallback_issue = unsafe_fallback_clause_issue(normalized_text)
        if fallback_issue:
            issues.append(fallback_issue)

    fail_count = sum(1 for issue in issues if issue.severity == "fail")
    warn_count = sum(1 for issue in issues if issue.severity == "warn")
    score = max(0, 100 - (fail_count * 25) - (warn_count * 8))
    sample = EvaluationSample(sample_id=sample_id, artifact=normalized_artifact, text=normalized_text)
    return EvaluationResult(sample=sample, issues=tuple(issues), score=score, passed=fail_count == 0)


def load_dataset(path: Path) -> list[EvaluationSample]:
    samples: list[EvaluationSample] = []
    with path.open(encoding="utf-8-sig") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"{path} line {line_number}: invalid JSON: {error}") from error

            sample_id = str(payload.get("id") or f"{path.stem}:{line_number}")
            artifact = normalize_artifact(str(payload.get("artifact") or "generic"))
            extract = payload.get("extract")
            extract_value = str(extract).strip().lower() if extract is not None else None
            source_path: str | None = None
            text = payload.get("text") or payload.get("candidate_text") or payload.get("output")
            file_value = payload.get("file")
            if file_value is not None:
                file_path = Path(str(file_value))
                if not file_path.is_absolute():
                    file_path = path.parent / file_path
                if not file_path.exists():
                    raise ValueError(f"{path} line {line_number}: file does not exist: {file_path}")
                text = load_text_from_path(file_path, artifact, extract_value)
                source_path = str(file_path)
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"{path} line {line_number}: each record needs a non-empty text field or file field")

            expected_outcome = payload.get("expected_outcome")
            if expected_outcome is not None:
                expected_outcome = str(expected_outcome).strip().lower()
                if expected_outcome not in {"pass", "fail"}:
                    raise ValueError(
                        f"{path} line {line_number}: expected_outcome must be 'pass' or 'fail' when provided"
                    )

            must_flag = tuple(str(code) for code in payload.get("must_flag", ()))
            must_not_flag = tuple(str(code) for code in payload.get("must_not_flag", ()))
            samples.append(
                EvaluationSample(
                    sample_id=sample_id,
                    artifact=artifact,
                    text=text,
                    source_path=source_path,
                    expected_outcome=expected_outcome,
                    must_flag=must_flag,
                    must_not_flag=must_not_flag,
                )
            )
    if not samples:
        raise ValueError(f"{path} did not contain any JSONL records")
    return samples


def build_file_samples(paths: list[Path], artifact: str) -> list[EvaluationSample]:
    normalized_artifact = normalize_artifact(artifact)
    samples: list[EvaluationSample] = []
    for path in paths:
        text = load_text_from_path(path, normalized_artifact)
        samples.append(
            EvaluationSample(
                sample_id=path.stem,
                artifact=normalized_artifact,
                text=text,
                source_path=str(path),
            )
        )
    return samples


def expectation_mismatches(sample: EvaluationSample, result: EvaluationResult) -> list[str]:
    mismatches: list[str] = []
    actual = "pass" if result.passed else "fail"
    issue_codes = {issue.code for issue in result.issues}
    if sample.expected_outcome and sample.expected_outcome != actual:
        mismatches.append(f"expected {sample.expected_outcome} but evaluator returned {actual}")
    for code in sample.must_flag:
        if code not in issue_codes:
            mismatches.append(f"expected rule {code!r} to be flagged")
    for code in sample.must_not_flag:
        if code in issue_codes:
            mismatches.append(f"expected rule {code!r} to stay clear")
    return mismatches


def print_result(result: EvaluationResult, mismatches: list[str]) -> None:
    status = "PASS" if result.passed else "FAIL"
    print(
        f"{status}: {result.sample.sample_id} [{result.sample.artifact}] "
        f"score={result.score} issues={len(result.issues)}"
    )
    if result.sample.source_path:
        print(f"  source: {result.sample.source_path}")
    for issue in result.issues:
        snippet = f" | snippet: {issue.snippet}" if issue.snippet else ""
        print(f"  - {issue.severity}/{issue.code}: {issue.message}{snippet}")
    for mismatch in mismatches:
        print(f"  - eval-mismatch: {mismatch}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate resume and cover-letter prose for system-narration and templated-writing patterns."
    )
    parser.add_argument("--dataset", type=Path, help="JSONL dataset with text samples and optional expected outcomes.")
    parser.add_argument(
        "--text-file",
        action="append",
        type=Path,
        default=[],
        help="Plain-text or DOCX file to grade. Repeat the flag to grade multiple files.",
    )
    parser.add_argument("--text", help="Inline text to grade.")
    parser.add_argument(
        "--artifact",
        default="generic",
        choices=ARTIFACT_CHOICES,
        help="Artifact type to grade for --text or --text-file inputs.",
    )
    parser.add_argument(
        "--allow-failures",
        action="store_true",
        help="Return exit code 0 even when raw grading finds failing samples.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_modes = sum(bool(value) for value in (args.dataset, args.text_file, args.text))
    if input_modes != 1:
        print("Provide exactly one input mode: --dataset, --text-file, or --text.")
        return 1

    if args.dataset:
        samples = load_dataset(args.dataset)
    elif args.text_file:
        samples = build_file_samples(args.text_file, args.artifact)
    else:
        samples = [EvaluationSample(sample_id="inline", artifact=args.artifact, text=args.text)]

    results: list[EvaluationResult] = []
    issue_counter: Counter[str] = Counter()
    mismatch_count = 0

    for sample in samples:
        result = evaluate_text(sample.artifact, sample.text, sample.sample_id)
        result = EvaluationResult(sample=sample, issues=result.issues, score=result.score, passed=result.passed)
        mismatches = expectation_mismatches(sample, result)
        mismatch_count += len(mismatches)
        print_result(result, mismatches)
        results.append(result)
        issue_counter.update(issue.code for issue in result.issues)

    passed = sum(1 for result in results if result.passed)
    failed = len(results) - passed
    print()
    print(f"Samples: {len(results)} | Passed: {passed} | Failed: {failed}")
    if issue_counter:
        print("Top issues:")
        for code, count in issue_counter.most_common(8):
            print(f"  {code}: {count}")

    if any(sample.expected_outcome is not None or sample.must_flag or sample.must_not_flag for sample in samples):
        if mismatch_count:
            print(f"Dataset expectation mismatches: {mismatch_count}")
            return 1
        print("Dataset expectations matched.")
        return 0

    if failed and not args.allow_failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
