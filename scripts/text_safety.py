"""Shared deterministic text-safety helpers for generated artifacts.

These helpers deliberately operate after content selection.  They prevent a
supported sentence from becoming visibly synthetic when several named terms
collapse to the same generic label, and they provide small final-output
normalizers that are safe to reuse across builders.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence


GENERIC_PLATFORM_PHRASES = (
    "enterprise platform",
    "software platform",
    "successor platform",
    "legacy platform",
    "enterprise system",
)

HEADER_STOP_WORDS = {
    "and", "of", "the", "for", "to", "in", "with", "senior", "associate",
    "lead", "principal", "manager", "consultant", "specialist", "analyst",
}


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


CONFLICTING_REGION_LIST_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    (r"\bNorth America, Asia, and Europe\b", "international client environments"),
    (r"\bNorth America and Asia\b", "a global footprint"),
    (r"\bthe Americas, Europe, and Asia\b", "international client environments"),
    (r"\bAmericas, Europe, and Asia\b", "international client environments"),
)


def neutralize_conflicting_region_lists(text: str) -> str:
    cleaned = normalize_spaces(text)
    if not cleaned:
        return cleaned
    for pattern, replacement in CONFLICTING_REGION_LIST_REPLACEMENTS:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.I)
    cleaned = re.sub(r"\bacross a global footprint\b", "across a global footprint", cleaned, flags=re.I)
    return cleaned


def with_indefinite_article(phrase: str) -> str:
    cleaned = normalize_spaces(phrase)
    if not cleaned:
        return ""
    first = re.sub(r"[^a-z]", "", cleaned.split(" ", 1)[0].lower())[:1]
    article = "an" if first in "aeiou" else "a"
    return f"{article} {cleaned}"


def fix_indefinite_articles(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        return "An " if match.group(1) == "A" else "an "

    return re.sub(r"\b([Aa])\s+(?=[aeiouAEIOU])", repl, text or "")


def sentence_splice_issues(text: str) -> tuple[str, ...]:
    issues: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", normalize_spaces(text)):
        words = sentence.split()
        if 1 <= len(words) <= 4:
            lowered = sentence.lower()
            if lowered in {"yes.", "yes", "no.", "no"}:
                continue
            if re.search(r"\b(is|are|was|were|will|can|to|and)\b", lowered):
                continue
            if re.search(r"\b(?:foundation|certification|certifications|training|credential|credentials|license|licenses)\b", lowered):
                continue
            if re.search(r"\b[A-Z]{2,}\b|\d", sentence):
                continue
            issues.append("SPLICE_FRAGMENT")
    return tuple(dict.fromkeys(issues))


def collision_safe_substitute(
    text: str,
    replacements: Sequence[tuple[str, str]],
    *,
    list_mode: bool = False,
) -> str:
    """Apply replacements while repairing collisions caused by genericization.

    Replacements remain deterministic.  When a migration's source and target
    both become the same label, the sentence is rewritten as a platform
    migration.  Spoken software lists are deduplicated after substitution.
    """

    updated = text or ""
    for pattern, replacement in replacements:
        updated = re.sub(pattern, replacement, updated, flags=re.I)

    # A -> A is never useful prose.  Prefer a truthful relationship description.
    generic = "|".join(re.escape(item) for item in GENERIC_PLATFORM_PHRASES)
    updated = re.sub(
        rf"\b(?:the\s+)?(?P<label>{generic})\s+to\s+(?:the\s+)?(?P=label)\b",
        "the platform migration",
        updated,
        flags=re.I,
    )
    updated = re.sub(
        rf"\b(?:through|during|supporting)\s+the\s+the platform migration\b",
        lambda match: match.group(0).replace("the the", "the"),
        updated,
        flags=re.I,
    )

    # Repair common missing-article constructions produced by phrase swaps.
    updated = re.sub(
        rf"\b(around|through|during|within|across)\s+(?P<label>{generic})\b",
        lambda match: f"{match.group(1)} the {match.group('label')}",
        updated,
        flags=re.I,
    )
    updated = re.sub(r"\b(a)\s+(enterprise|existing)\b", r"an \2", updated, flags=re.I)

    # A genericized sentence should name a platform category once, then use a
    # neutral reference. This also makes the duplicate-term validator
    # mechanically repairable instead of permanently non-convergent.
    repaired_sentences: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", updated):
        repaired = sentence
        for phrase in GENERIC_PLATFORM_PHRASES:
            matches = list(re.finditer(rf"\b{re.escape(phrase)}\b", repaired, re.I))
            for match in reversed(matches[1:]):
                repaired = repaired[: match.start()] + "the platform" + repaired[match.end() :]
        repaired_sentences.append(repaired)
    updated = " ".join(repaired_sentences)

    if list_mode:
        updated = dedupe_comma_list_items(updated)

    return normalize_spaces(updated)


def dedupe_comma_list_items(text: str) -> str:
    """Remove exact duplicate comma-separated items without changing order."""

    if text.count(",") < 1:
        return text
    parts = [part.strip() for part in text.split(",")]
    kept: list[str] = []
    seen: set[str] = set()
    for part in parts:
        key = re.sub(r"[^a-z0-9]+", " ", part.lower()).strip()
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        kept.append(part)
    return ", ".join(kept)


def substitution_safety_issues(text: str) -> tuple[str, ...]:
    """Return stable rule IDs for unsafe genericization artifacts."""

    issues: list[str] = []
    segments = [
        normalize_spaces(segment).lower()
        for segment in re.split(r"(?<=[.!?])\s+|[\r\n]+", text or "")
        if normalize_spaces(segment)
    ]
    lowered = "\n".join(segments)
    generic = "|".join(re.escape(item) for item in GENERIC_PLATFORM_PHRASES)
    if re.search(rf"\b(?P<label>{generic})\s+to\s+(?P=label)\b", lowered):
        issues.append("SUBSTITUTION_X_TO_X")
    for sentence in segments:
        for phrase in GENERIC_PLATFORM_PHRASES:
            if sentence.count(phrase) > 1:
                issues.append("SUBSTITUTION_DUPLICATE_GENERIC_TERM")
                break
    if re.search(rf"\b(?:around|through|during|within|across)\s+(?:{generic})\b", lowered):
        issues.append("SUBSTITUTION_MISSING_ARTICLE")
    return tuple(dict.fromkeys(issues))


def normalize_bullet_ending(text: str) -> str:
    cleaned = normalize_spaces(text)
    if not cleaned or cleaned[-1] in ".!?":
        return cleaned
    return cleaned.rstrip(";,:-") + "."


def dominant_header_words(value: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-z0-9]+", value.lower())
        if len(word) >= 5 and word not in HEADER_STOP_WORDS
    }


def dedupe_header_segments(segments: Iterable[str]) -> tuple[str, ...]:
    """Keep the first segment when later segments repeat a dominant concept."""

    kept: list[str] = []
    used: set[str] = set()
    for segment in segments:
        cleaned = normalize_spaces(segment)
        if not cleaned:
            continue
        words = dominant_header_words(cleaned)
        if words and words & used:
            continue
        kept.append(cleaned)
        used |= words
    return tuple(kept)
