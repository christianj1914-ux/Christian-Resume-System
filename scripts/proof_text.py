"""Shared proof-sentence cleanup and ranking helpers."""

from __future__ import annotations

import re
from typing import Iterable


ACTION_VERB_PATTERN = re.compile(
    r"\b(?:built|created|converted|delivered|drove|enabled|facilitated|helped|improved|launched|led|managed|"
    r"owned|protected|recovered|reduced|stabilized|supported|translated|turned)\b",
    re.I,
)
METRIC_PATTERN = re.compile(r"\b(?:\d+%|\d+\+|\$\d[\d.,]*[MK]?|one million|five sites|150\+ users)\b", re.I)
LIST_CONNECTOR_PATTERN = re.compile(r"\b(?:and|or|with|across|through|including)\b", re.I)
DENSE_PROOF_REWRITES: tuple[tuple[str, str], ...] = (
    (
        r"\bsupported enterprise data migration by extracting, validating, transforming, and loading system and "
        r"database records through ETL tools, SQL checks, and migration readiness planning\b",
        "supported enterprise data migration through ETL validation, SQL checks, and migration-readiness planning",
    ),
    (
        r"\bprotected migration stability by leading implementation readiness, scope alignment, sandbox testing, "
        r"UAT validation, and targeted training across concurrent program tracks\b",
        "protected migration stability through readiness planning, sandbox testing, UAT validation, and targeted training",
    ),
    (
        r"\bstabilized high-risk accounts across a \$6M\+ book of business, including more than one million dollars "
        r"in at-risk annual revenue, by diagnosing root causes, consolidating ownership, and driving resolution\b",
        "stabilized high-risk accounts across a $6M+ book of business, including $1M+ in at-risk annual revenue, by consolidating ownership and driving resolution",
    ),
    (
        r"\bconverted complex implementation and data-migration requirements into statements of work and functional "
        r"requirements across 80\+ international manufacturing client engagements before build work began\b",
        "converted complex implementation and data-migration requirements into SOWs and functional requirements across 80+ client engagements",
    ),
    (
        r"\bowned a mission-critical enterprise system across five sites and 150\+ users while supporting data migration, validation, training, and adoption\b",
        "owned a mission-critical enterprise system for five sites and 150+ users through migration readiness and user adoption",
    ),
    (
        r"\bat east west manufacturing,? i owned enterprise system operations across five sites and 150\+ users through migration planning, testing, and go-live readiness\b",
        "At East West Manufacturing, I owned enterprise system operations for five sites and 150+ users and kept migration readiness on track through testing and go-live planning",
    ),
    (
        r"\bmanaged a portfolio of more than 80 international manufacturing clients across discovery, requirements definition, implementation, adoption, and handoff-ready support\b",
        "managed 80+ international manufacturing client engagements across discovery, implementation, and adoption",
    ),
    (
        r"\bturned ambiguous operations, finance, and engineering needs into scoped system recommendations, vendor tradeoffs, cost and timeline options, and risk-aware implementation plans for directors and VPs before build work began\b",
        "turned ambiguous operations, finance, and engineering needs into scoped recommendations and implementation plans for directors and VPs",
    ),
    (
        r"\blaunched a production-ready system setup for a new warehouse operation and Amazon Robotics program, driving the work from requirements through cross-site training and go-live\b",
        "launched a production-ready warehouse and Amazon Robotics system from requirements through go-live",
    ),
)
GENERIC_PROOF_PATTERNS: tuple[str, ...] = (
    r"\bTogether, that background shows\b",
    r"\bWhere the role reaches beyond\b",
    r"\bThe work needs\b",
    r"\bThe role moves\b",
    r"\bThe experience behind that\b",
)


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w+.#'-]+\b", text))


def split_sentences(text: str) -> list[str]:
    normalized = normalize_spaces(text)
    if not normalized:
        return []
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", normalized) if part.strip()]


def _trim_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    trimmed = " ".join(words[:max_words]).rstrip(",;:-")
    if "," in trimmed:
        trimmed = trimmed.rsplit(",", 1)[0].rstrip(",;:-")
    return trimmed


def dense_list_style(text: str) -> bool:
    normalized = normalize_spaces(text)
    if word_count(normalized) < 16:
        return False
    comma_count = normalized.count(",")
    connector_count = len(LIST_CONNECTOR_PATTERN.findall(normalized))
    return comma_count >= 3 and connector_count >= 3


def prose_eval_flags_dense(text: str, artifact: str = "cover_letter_proof") -> bool:
    try:
        import writing_eval

        result = writing_eval.evaluate_text(artifact, text)
    except Exception:
        return False
    return any(issue.code == "list_density_overload" for issue in result.issues)


def rewrite_dense_proof_patterns(text: str) -> str:
    rewritten = normalize_spaces(text).rstrip(".")
    for pattern, replacement in DENSE_PROOF_REWRITES:
        rewritten = re.sub(pattern, replacement, rewritten, flags=re.I)
    rewritten = re.sub(r"\bstatements of work\b", "SOWs", rewritten, flags=re.I)
    rewritten = re.sub(r"\buser acceptance\b", "UAT", rewritten, flags=re.I)
    return rewritten


def sanitize_proof_sentence(
    text: str,
    *,
    max_words: int = 28,
    artifact: str = "cover_letter_proof",
) -> str:
    cleaned = normalize_spaces(text)
    if not cleaned:
        return ""
    cleaned = re.sub(r"^[•*\-–]\s*", "", cleaned).rstrip(".")
    cleaned = rewrite_dense_proof_patterns(cleaned)
    cleaned = re.sub(r"^That includes\b", "My experience includes", cleaned, flags=re.I)
    cleaned = re.sub(r"^That background\b", "My background", cleaned, flags=re.I)
    cleaned = re.sub(r"^That experience\b", "My experience", cleaned, flags=re.I)
    cleaned = re.sub(r"^That work\b", "This work", cleaned, flags=re.I)
    if re.match(r"^That\b", cleaned):
        return ""
    if any(re.search(pattern, cleaned, re.I) for pattern in GENERIC_PROOF_PATTERNS):
        return ""
    if word_count(cleaned) > max_words or dense_list_style(cleaned) or prose_eval_flags_dense(cleaned, artifact):
        cleaned = rewrite_dense_proof_patterns(cleaned)
        if ";" in cleaned:
            cleaned = cleaned.split(";", 1)[0].strip()
        cleaned = _trim_words(cleaned, max_words)
    cleaned = re.sub(r"\s+,", ",", cleaned)
    cleaned = re.sub(r"\s+\.", ".", cleaned)
    cleaned = cleaned.rstrip(",;:-")
    if cleaned and cleaned[-1] not in ".!?":
        cleaned += "."
    return cleaned


def proof_candidate_score(text: str, job_description: str = "") -> tuple[int, int, int, int]:
    normalized = normalize_spaces(text)
    lowered = normalized.lower()
    keyword_hits = 0
    if job_description.strip():
        for keyword in {
            match.group(0).lower()
            for match in re.finditer(r"\b(?:implementation|data migration|integration|training|testing|go-live|"
                                     r"adoption|analytics|reporting|customer|stakeholder|discovery|sql|retention|"
                                     r"workflow|support|project)\b", job_description, re.I)
        }:
            if keyword in lowered:
                keyword_hits += 1
    metric_hits = len(METRIC_PATTERN.findall(normalized))
    action_hits = len(ACTION_VERB_PATTERN.findall(normalized))
    length_penalty = abs(word_count(normalized) - 22)
    return (metric_hits, action_hits, keyword_hits, -length_penalty)


def best_proof_sentences(
    candidates: Iterable[str],
    *,
    job_description: str = "",
    max_sentences: int = 2,
    max_words: int = 28,
    artifact: str = "cover_letter_proof",
) -> list[str]:
    seen: set[str] = set()
    scored: list[tuple[tuple[int, int, int, int], str]] = []
    for candidate in candidates:
        for sentence in split_sentences(candidate):
            cleaned = sanitize_proof_sentence(sentence, max_words=max_words, artifact=artifact)
            normalized = normalize_spaces(cleaned).lower()
            if not cleaned or normalized in seen:
                continue
            seen.add(normalized)
            scored.append((proof_candidate_score(cleaned, job_description), cleaned))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [sentence for _, sentence in scored[:max_sentences]]
