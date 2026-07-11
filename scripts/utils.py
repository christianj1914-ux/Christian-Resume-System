"""Shared helpers for resume automation scripts."""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

PROJECT_ROOT = Path(__file__).resolve().parents[1]


W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

ET.register_namespace("w", "http://schemas.openxmlformats.org/wordprocessingml/2006/main")
ET.register_namespace("", "http://schemas.openxmlformats.org/package/2006/relationships")


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def join_answer_sentences(*parts: str) -> str:
    """Clean a series of sentence fragments and join them into one answer string.

    Shared by build_cover_letter.py and build_interview_cheat_sheet.py. Lives here
    (rather than in either module) because build_interview_cheat_sheet.py imports
    build_cover_letter.py, so defining this helper in either of those two files
    and importing it from the other would create a circular import.
    """
    sentences: list[str] = []
    for part in parts:
        cleaned = re.sub(r"\s+", " ", part).strip()
        if not cleaned:
            continue
        if cleaned[-1] not in ".!?":
            cleaned += "."
        sentences.append(cleaned)
    return " ".join(sentences)


def debug_enabled(flag: str = "DEBUG_RESUME_SYSTEM") -> bool:
    return os.environ.get("DEBUG_RESUME_SYSTEM") == "1" or os.environ.get(flag) == "1"


def debug_print(message: str, *, file: object = sys.stdout, flag: str = "DEBUG_RESUME_SYSTEM") -> None:
    if debug_enabled(flag):
        print(message, file=file)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig").strip()
    except UnicodeDecodeError:
        print(f"WARNING: {path.name} encoding fallback (UTF-8 decode failed, trying UTF-16)", file=sys.stderr)
        return path.read_text(encoding="utf-16").strip()


def optional_text(path: Path) -> str:
    if not path.exists():
        return ""
    return read_text(path)


MISSING_RENDER_VALUES = {
    "",
    "none",
    "none supplied",
    "none supplied.",
    "n/a",
    "na",
    "null",
    "unknown",
    "not supplied",
    "not provided",
}

TOPIC_LABEL_REWRITES = {
    "goal": "{body}",
    "tasks": "{body}",
    "implementation scale": "{body}",
    "biggest challenge": "{body}",
    "tier 1 ramp (first 3-4 months)": "the first few months of ramp through {body}",
    "tier 1 ramp": "the first few months of ramp through {body}",
    "after ramp": "the transition after ramp into {body}",
}

TOPIC_LABEL_PREFERENCES = {
    "goal": 4,
    "biggest challenge": 4,
    "tasks": 3,
    "implementation scale": 2,
    "tier 1 ramp (first 3-4 months)": 2,
    "tier 1 ramp": 2,
    "after ramp": 1,
}

TOPIC_SKIP_PATTERNS = (
    r"^post-?interview debrief captured\b",
    r"^(interview date|company name|role title|round number|outcome)\s*:",
    r"^(review notes|raw notes|stories that generated follow-up questions|unexpected questions|specific interviewer language about the role|specific language the interviewer used about the role|feedback received|insider company intelligence learned)\s*:?",
    r"^\d+\.\s+",
    r"^three rounds\s*:?",
    r"^(prescreen|hiring manager interview|on-site|onsite)\b",
    r"^jonathan's feedback on fit\s*:?",
    r"\b(feel good about the resume|experience aligns well|communication and relevant experience as positives)\b",
    r"^scoped interview notes\s*:",
    r"^bulk interview notes captured\b",
    r"^interview notes file\s*:",
    r"^paste raw interview notes below this line\b",
    r"^title is\b",
    r"^clients range\b",
    r"^each module functions\b",
    r"^poultry production has\b",
    r"^technical complexity\b",
    r"^noted depth of experience\b",
    r"^highlighted communication\b",
    r"^await hiring team feedback\b",
)

TOPIC_PREFERENCE_PATTERNS = (
    r"\b(challenge|ramp|implementation|support function|uat|data validation|documentation|client culture|go-live|customer|delivery|ownership|workflow|scope)\b",
)

LEAKAGE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("standalone None value", r"(?<![A-Za-z])None(?: supplied)?\.?(?![A-Za-z])"),
    ("unresolved curly-brace placeholder", r"\{[^{}]+\}"),
    ("python-style quoted list fragment", r"\[[^\]]*'[^']+'[^\]]*\]"),
    (
        "raw interview-note marker",
        r"(?i)\b(?:appendix:\s*raw supplied notes|company research supplied by christian|interview or recruiter notes supplied by christian|interview round\s*:|post-interview note\s*\[)\b",
    ),
)

LEAKAGE_NOTE_LABEL_PATTERN = (
    r"(?:goal|tasks?|implementation scale|biggest challenge|role language|performance summary|"
    r"coaching signals|specific interviewer language(?: about the role)?|feedback received|"
    r"insider company intelligence learned|stories that generated follow-up questions|"
    r"unexpected questions|interview round|post-interview note(?:\s*\[[^\]]+\])?|"
    r"company research supplied by christian|interview or recruiter notes supplied by christian|"
    r"company name|role title|round number|outcome)"
)

LEAKAGE_DASH_RUN_RE = re.compile(
    rf"(?:^|.*?\S\s)-\s*{LEAKAGE_NOTE_LABEL_PATTERN}\s*:\s*[^.\n]+"
    rf"(?:\s+-\s*{LEAKAGE_NOTE_LABEL_PATTERN}\s*:\s*[^.\n]+)+",
    re.I,
)


def normalize_generated_value(value: str | None) -> str:
    cleaned = re.sub(r"\s+", " ", (value or "")).strip(" ;,.-")
    return "" if cleaned.lower() in MISSING_RENDER_VALUES else cleaned


def _candidate_topic_fragments(value: str) -> list[str]:
    cleaned = normalize_generated_value(value)
    if not cleaned:
        return []

    fragments: list[str] = []
    for raw_line in re.split(r"[\r\n]+", cleaned):
        line = re.sub(r"^[\-•*]+\s*", "", raw_line).strip()
        if not line:
            continue
        parts = [
            re.sub(r"\s+", " ", part).strip(" -;,.")
            for part in re.split(r"\s*(?:;|•|\s-\s)\s*", line)
            if re.sub(r"\s+", " ", part).strip(" -;,.")
        ]
        for part in parts or [line]:
            if any(re.search(pattern, part, re.I) for pattern in TOPIC_SKIP_PATTERNS):
                continue
            fragments.append(part)
    return [fragment for fragment in fragments if normalize_generated_value(fragment)]


def _rewrite_labeled_topic(fragment: str) -> str:
    match = re.match(r"^(?P<label>[A-Za-z0-9 ()/-]+):\s*(?P<body>.+)$", fragment)
    if not match:
        return fragment
    label = re.sub(r"\s+", " ", match.group("label")).strip().lower()
    body = normalize_generated_value(match.group("body"))
    if not body:
        return ""
    if label == "goal" and re.match(
        r"^(?:absorb|build|learn|own|support|improve|reduce|increase|keep|create|drive|translate|turn|move|protect|stabilize)\b",
        body,
        re.I,
    ):
        return f"the goal to {body}"
    template = TOPIC_LABEL_REWRITES.get(label)
    if template:
        return template.format(body=body)
    return f"the {label} around {body}"


def extract_single_discussion_topic(value: str | None) -> str:
    fragments = _candidate_topic_fragments(value or "")
    if not fragments:
        return ""

    def score(fragment: str) -> tuple[int, int, int]:
        label_bonus = 0
        match = re.match(r"^(?P<label>[A-Za-z0-9 ()/-]+):\s*(?P<body>.+)$", fragment)
        if match:
            label = re.sub(r"\s+", " ", match.group("label")).strip().lower()
            label_bonus = TOPIC_LABEL_PREFERENCES.get(label, 1)
        rewritten = _rewrite_labeled_topic(fragment) or fragment
        lowered = rewritten.lower()
        preferred = sum(1 for pattern in TOPIC_PREFERENCE_PATTERNS if re.search(pattern, lowered, re.I))
        list_penalty = -1 if lowered.count(",") >= 2 else 0
        length_score = -abs(len(lowered.split()) - 9)
        return (label_bonus, preferred, list_penalty, length_score)

    best = max(fragments, key=score)
    rewritten = _rewrite_labeled_topic(best) or best
    rewritten = normalize_generated_value(rewritten)
    return rewritten.rstrip(".")


def discussion_topic_sentence(value: str | None, *, intro: str) -> str:
    topic = extract_single_discussion_topic(value)
    if not topic:
        return ""
    topic = topic[0].lower() + topic[1:] if len(topic) > 1 and topic[0].isupper() else topic
    return f"{intro} {topic}."


def assert_company_name_in_source(company_name: str, source_text: str, *, label: str) -> None:
    """Defense-in-depth staleness guard: confirms the active job description text actually
    mentions the company we're building documents for. Catches cases where jobs/job_description.txt
    was stale, empty, or swapped for a different company after company_name/role_title were already
    resolved from a prior snapshot, which previously caused cross-company content contamination in
    generated interview materials."""
    if not company_name or not source_text:
        return
    if company_name.strip().lower() not in source_text.lower():
        fail(
            f"{label}: company name '{company_name}' was not found anywhere in the active job "
            "description text. jobs/job_description.txt is likely stale or was swapped for a "
            "different company after this build started. Refusing to continue."
        )


def assert_no_template_leakage(text: str) -> None:
    raw_text = text or ""
    if not raw_text.strip():
        return
    if any(LEAKAGE_DASH_RUN_RE.search(line.strip()) for line in raw_text.splitlines() if line.strip()):
        fail("Template leakage detected (dash-prefixed raw note fragments) in generated text:\n" + re.sub(r"\s+", " ", raw_text).strip())
    normalized = re.sub(r"\s+", " ", raw_text).strip()
    for label, pattern in LEAKAGE_PATTERNS:
        if re.search(pattern, normalized):
            fail(f"Template leakage detected ({label}) in generated text:\n{normalized}")


def prose_quality_report(text: str, artifact: str) -> dict[str, Any]:
    normalized = re.sub(r"\s+", " ", (text or "")).strip()
    if not normalized:
        return {"score": 100, "passed": True, "failures": [], "warnings": []}

    import writing_eval

    result = writing_eval.evaluate_text(artifact, normalized, sample_id="generated")
    failures: list[str] = []
    warnings: list[str] = []
    for issue in result.issues:
        message = issue.message
        if issue.snippet:
            message = f"{message} [{issue.snippet}]"
        if issue.severity == "fail":
            failures.append(message)
        else:
            warnings.append(message)
    return {
        "score": result.score,
        "passed": result.passed,
        "failures": failures,
        "warnings": warnings,
    }


PROSE_HARD_FAIL_ARTIFACTS = {
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
}

PROSE_WARN_ONLY_ARTIFACTS = {
    "interview_pitch",
    "interview_story_answer",
    "checklist_narrative",
    "generic",
}


def enforce_prose_quality(
    text: str,
    artifact: str,
    *,
    label: str = "Generated text",
    mode: str = "auto",
    check_template_leakage: bool = True,
) -> dict[str, Any]:
    normalized = re.sub(r"\s+", " ", (text or "")).strip()
    if check_template_leakage:
        assert_no_template_leakage(normalized)
    report = prose_quality_report(normalized, artifact)
    failures = [str(item) for item in report.get("failures", ())]
    warnings = [str(item) for item in report.get("warnings", ())]

    normalized_mode = (mode or "auto").strip().lower()
    if normalized_mode == "auto":
        normalized_mode = "fail" if artifact in PROSE_HARD_FAIL_ARTIFACTS else "warn"
    if normalized_mode not in {"fail", "warn"}:
        raise ValueError(f"Unsupported prose enforcement mode: {mode!r}")

    if failures and normalized_mode == "fail":
        fail(f"{label} failed prose-quality checks: " + "; ".join(failures))
    for failure in failures:
        print(f"{label} PROSE WARNING: {failure}")
    for warning in warnings:
        print(f"{label} PROSE WARNING: {warning}")
    return report


def validate_job_description(job_description_path: Path) -> None:
    """Validate that job description file exists with helpful error message.

    Call this at the start of any script that requires an active job description.
    Fails with clear guidance if file is missing.
    """
    if not job_description_path.exists():
        fail(
            f"Active job description not found at {job_description_path}\n"
            "Please set up a job description by running:\n"
            "  python tasks.py check (to verify job description location)\n"
            "  or copy a job posting into jobs/job_description.txt"
        )


def normalize_company_key(name: str) -> str:
    """Normalize company names for tracker and debrief matching."""
    cleaned = re.sub(r"\s+", " ", (name or "").strip().lower())
    cleaned = re.sub(r"\b(inc\.?|llc|ltd\.?|corp\.?|corporation)\b\.?", "", cleaned).strip(" .,-")
    return cleaned


def companies_refer_to_same(left: str, right: str) -> bool:
    """Return True when two company labels likely refer to the same employer."""
    left_key = normalize_company_key(left)
    right_key = normalize_company_key(right)
    if not left_key or not right_key:
        return False
    if left_key == right_key:
        return True
    return left_key in right_key or right_key in left_key


def agent_debug_log(
    location: str,
    message: str,
    data: dict[str, object],
    *,
    hypothesis_id: str,
    run_id: str = "pre-fix",
) -> None:
    # region agent log
    payload = {
        "sessionId": "9b3920",
        "location": location,
        "message": message,
        "data": data,
        "hypothesisId": hypothesis_id,
        "runId": run_id,
        "timestamp": int(time.time() * 1000),
    }
    log_path = PROJECT_ROOT / "debug-9b3920.log"
    try:
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except OSError:
        pass
    # endregion


def _repair_mojibake_once(text: str) -> str:
    for encoding in ("cp1252", "latin1"):
        try:
            return text.encode(encoding).decode("utf-8")
        except UnicodeError:
            continue
    return text


def clean_source_text(text: str) -> str:
    cleaned = text
    for _ in range(2):
        repaired = _repair_mojibake_once(cleaned)
        if repaired == cleaned:
            break
        cleaned = repaired

    replacements = {
        chr(8211): "-",
        chr(8212): " - ",
        chr(8216): "'",
        chr(8217): "'",
        chr(8220): '"',
        chr(8221): '"',
        chr(8594): "->",
    }
    for original, replacement in replacements.items():
        cleaned = cleaned.replace(original, replacement)

    cleaned = re.sub(r"[\U0001F300-\U0001FAFF]", "", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


GREAT_EIGHT_OUTCOMES = (
    "increased revenue",
    "decreased costs or saved money",
    "improved efficiency",
    "improved quality",
    "reduced risk",
    "improved compliance or governance",
    "improved customer satisfaction",
    "improved employee satisfaction or engagement",
)


def has_great_eight_signal(text: str) -> bool:
    """Detect Great Eight business outcomes in resume bullets and story results.

    The Great Eight model checks whether a statement connects to revenue, cost,
    efficiency, quality, risk, compliance, customer experience, or team
    performance. Resume bullet audits and interview story audits share this
    helper so the quality bar stays consistent across scripts.
    """
    signal_groups = (
        ("revenue", "arr", "renewal", "expansion", "growth", "sales", "account growth"),
        ("cost", "saved", "savings", "expense", "spend", "budget", "margin"),
        ("efficiency", "efficient", "cycle time", "manual work", "automated", "automation", "faster", "accelerated", "streamlined", "reduced time"),
        ("quality", "accuracy", "defect", "error", "validation", "readiness", "service quality"),
        ("risk", "stabilized", "mitigated", "protected", "issue", "escalation", "controls", "go-live", "cutover"),
        ("compliance", "governance", "audit", "control", "policy", "traceability", "signoff"),
        ("customer satisfaction", "customer experience", "client satisfaction", "adoption", "retention", "churn", "trust", "customer-facing"),
        ("employee satisfaction", "engagement", "enablement", "training", "user adoption", "stakeholder adoption", "team performance"),
    )
    lowered = text.lower()
    if any(outcome in lowered for outcome in GREAT_EIGHT_OUTCOMES):
        return True
    return any(any(signal in lowered for signal in signals) for signals in signal_groups)


def _element_text(element: ET.Element) -> str:
    return "".join(text for text in element.itertext())


def _linkedin_profile_text(value: str) -> bool:
    normalized = (value or "").lower()
    return "linkedin.com/in/cjne" in normalized or "linkedin.com/in/cjne/" in normalized


def remove_linkedin_hyperlinks(temp_root: Path) -> int:
    """Flatten LinkedIn links in DOCX XML and remove their relationship entries.

    This cleans both layers Word uses for external hyperlinks: the visible
    ``w:hyperlink`` elements in ``word/document.xml`` and the matching hyperlink
    relationships in ``word/_rels/document.xml.rels``.
    """
    document_xml = temp_root / "word" / "document.xml"
    if not document_xml.exists():
        return 0

    changed = 0
    tree = ET.parse(document_xml)
    root = tree.getroot()
    for paragraph in root.iter(f"{W_NS}p"):
        children = list(paragraph)
        rebuilt: list[ET.Element] = []
        paragraph_changed = False
        for child in children:
            if child.tag == f"{W_NS}hyperlink" and _linkedin_profile_text(_element_text(child)):
                rebuilt.extend(list(child))
                paragraph_changed = True
                changed += 1
            else:
                rebuilt.append(child)
        if paragraph_changed:
            paragraph[:] = rebuilt
    if changed:
        tree.write(document_xml, encoding="utf-8", xml_declaration=True)

    rels_path = temp_root / "word" / "_rels" / "document.xml.rels"
    if rels_path.exists():
        rels_changed = False
        rels_tree = ET.parse(rels_path)
        rels_root = rels_tree.getroot()
        for rel in list(rels_root):
            rel_type = rel.attrib.get("Type", "")
            target = rel.attrib.get("Target", "")
            if rel_type.endswith("/hyperlink") and _linkedin_profile_text(target):
                rels_root.remove(rel)
                changed += 1
                rels_changed = True
        if rels_changed:
            rels_tree.write(rels_path, encoding="utf-8", xml_declaration=True)

    return changed
