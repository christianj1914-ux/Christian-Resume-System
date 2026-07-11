"""Shared sentence assembly, structural validation, repair, and spoken register."""

from __future__ import annotations

import re
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from collections.abc import Iterator
from typing import Callable

from config.language_rules import MANDATORY_REORG_SENTENCE
from text_safety import collision_safe_substitute, normalize_spaces, substitution_safety_issues


@dataclass(frozen=True)
class ValidationRule:
    rule_id: str
    artifacts: frozenset[str]
    severity: str
    check: Callable[[str], bool]
    message: str


@dataclass(frozen=True)
class ValidationFinding:
    rule_id: str
    severity: str
    message: str


@dataclass(frozen=True)
class RepairOutcome:
    text: str
    findings: tuple[ValidationFinding, ...]
    repairs: tuple[str, ...]
    converged: bool


_SPOKEN_REPAIR_ISSUES: ContextVar[list[str] | None] = ContextVar("spoken_repair_issues", default=None)


@contextmanager
def collect_spoken_repair_issues() -> Iterator[list[str]]:
    """Collect non-converged spoken rule IDs across one document build."""

    issues: list[str] = []
    token = _SPOKEN_REPAIR_ISSUES.set(issues)
    try:
        yield issues
    finally:
        _SPOKEN_REPAIR_ISSUES.reset(token)


def human_series(items: tuple[str, ...] | list[str]) -> str:
    cleaned = [normalize_spaces(item).strip(" ,;") for item in items if normalize_spaces(item)]
    cleaned = list(dict.fromkeys(cleaned))
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} and {cleaned[1]}"
    return ", ".join(cleaned[:-1]) + f", and {cleaned[-1]}"


def sentence(*clauses: str) -> str:
    text = normalize_spaces(" ".join(clause for clause in clauses if clause))
    if text and text[-1] not in ".!?":
        text += "."
    return text


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", normalize_spaces(text)) if part.strip()]


def _conjunction_overload(text: str) -> bool:
    # Three conjunctions can be natural across a scoped sentence with two
    # short series. Four or more is the reliable overload signal.
    return any(len(re.findall(r"\band\b", item, re.I)) >= 4 for item in _sentences(text))


def _nested_list(text: str) -> bool:
    return any(item.count(",") >= 4 and len(re.findall(r"\b(?:and|or|including)\b", item, re.I)) >= 3 for item in _sentences(text))


def _stacked_modifier(text: str) -> bool:
    # Allow common business compounds; flag only chains such as
    # "senior-technical-authority" with two or more hyphens in one token.
    return bool(re.search(r"\b[a-z]+-[a-z]+-[a-z]+\b", text, re.I))


def _resume_mandate_in_spoken(text: str) -> bool:
    return MANDATORY_REORG_SENTENCE.lower() in text.lower()


def _long_spoken_sentence(text: str) -> bool:
    return any(len(re.findall(r"\b[\w+.#'-]+\b", item)) > 28 for item in _sentences(text))


def _repeated_opening_verbs(text: str) -> bool:
    openings = []
    for item in _sentences(text):
        words = re.findall(r"\b[A-Za-z']+\b", item)
        if words:
            openings.append(words[0].lower())
    return any(openings.count(word) >= 3 for word in set(openings))


def _repeated_proof_clauses(text: str) -> bool:
    normalized = [re.sub(r"[^a-z0-9 ]+", "", item.lower()) for item in _sentences(text)]
    prefixes = [" ".join(item.split()[:6]) for item in normalized if len(item.split()) >= 6]
    return len(prefixes) != len(set(prefixes))


def _slot_template_overlap(text: str) -> bool:
    sentences = _sentences(text)
    for index, sentence in enumerate(sentences):
        tokens = set(re.findall(r"\b[a-z]{4,}\b", sentence.lower()))
        for other in sentences[index + 1 :]:
            other_tokens = set(re.findall(r"\b[a-z]{4,}\b", other.lower()))
            union = tokens | other_tokens
            if len(tokens) >= 8 and union and len(tokens & other_tokens) / len(union) >= 0.72:
                return True
    return False


VALIDATION_RULES: tuple[ValidationRule, ...] = (
    ValidationRule("PROSE_AND_CHAIN", frozenset({"summary", "cover", "spoken"}), "fail", _conjunction_overload, "Sentence contains an overloaded conjunction chain."),
    ValidationRule("PROSE_NESTED_LIST", frozenset({"summary", "cover", "spoken"}), "fail", _nested_list, "Sentence embeds one long list inside another."),
    ValidationRule("PROSE_STACKED_MODIFIER", frozenset({"summary", "cover", "spoken"}), "warn", _stacked_modifier, "Sentence contains a stacked hyphenated modifier."),
    ValidationRule("PROSE_REPEATED_OPENING", frozenset({"summary", "cover", "spoken"}), "warn", _repeated_opening_verbs, "Three or more sentences repeat the same opening word."),
    ValidationRule("PROSE_REPEATED_PROOF", frozenset({"summary", "cover", "spoken"}), "warn", _repeated_proof_clauses, "Two sentences repeat the same proof-clause opening."),
    ValidationRule("PROSE_SLOT_OVERLAP", frozenset({"summary", "cover", "spoken"}), "warn", _slot_template_overlap, "Two assembled sentences substantially overlap."),
    ValidationRule("SPOKEN_RESUME_MANDATE", frozenset({"spoken"}), "fail", _resume_mandate_in_spoken, "Spoken answer contains a resume-only compliance sentence."),
    ValidationRule("SPOKEN_SENTENCE_LENGTH", frozenset({"spoken"}), "fail", _long_spoken_sentence, "Spoken answer contains a sentence longer than 28 words."),
)


def validate_text(text: str, artifact: str) -> tuple[ValidationFinding, ...]:
    findings: list[ValidationFinding] = []
    for rule_id in substitution_safety_issues(text):
        findings.append(ValidationFinding(rule_id, "fail", "Unsafe generic-term substitution remains."))
    for rule in VALIDATION_RULES:
        if artifact in rule.artifacts and rule.check(text):
            findings.append(ValidationFinding(rule.rule_id, rule.severity, rule.message))
    return tuple(findings)


def _split_semicolons(text: str) -> str:
    return re.sub(r";\s+(?=[A-Za-z])", ". ", text)


def _repair_and_chain(text: str) -> str:
    repaired: list[str] = []
    for item in _sentences(text):
        conjunctions = list(re.finditer(r"\s+and\s+", item, re.I))
        if len(conjunctions) >= 4:
            verb_pattern = r"(?:supported|supporting|led|leading|built|building|delivered|delivering|managed|managing|coordinated|coordinating)\b"
            split = next(
                (match for match in conjunctions if re.match(verb_pattern, item[match.end() :].strip(), re.I)),
                conjunctions[1],
            )
            tail = item[split.end() :].strip()
            verb_match = re.match(rf"(?P<verb>{verb_pattern})(?P<rest>.*)", tail, re.I)
            gerunds = {
                "supported": "supporting", "led": "leading", "built": "building",
                "delivered": "delivering", "managed": "managing", "coordinated": "coordinating",
                "supporting": "supporting", "leading": "leading", "building": "building",
                "delivering": "delivering", "managing": "managing", "coordinating": "coordinating",
            }
            if verb_match:
                gerund = gerunds[verb_match.group("verb").lower()]
                item = item[: split.start()].rstrip() + f" while {gerund}{verb_match.group('rest')}"
            elif re.match(r"\d", tail):
                item = item[: split.start()].rstrip() + f" plus {tail}"
            else:
                first = item[: split.start()].rstrip(" ,;:.") + "."
                second = tail
                if second:
                    second = second[0].upper() + second[1:]
                    if second[-1] not in ".!?":
                        second += "."
                item = f"{first} {second}".strip()
        repaired.append(item)
    return " ".join(repaired)


def _split_long_spoken(text: str) -> str:
    output: list[str] = []
    for item in _sentences(text):
        words = item.split()
        if len(words) <= 28:
            output.append(item)
            continue
        conjunction_at = next(
            (index for index in range(16, min(27, len(words))) if words[index].lower().strip(",") in {"and", "while", "which", "so"}),
            None,
        )
        punctuation_breaks = [
            index + 1
            for index in range(12, min(27, len(words)))
            if words[index].endswith((",", ";", ":"))
        ]
        if conjunction_at is not None:
            split_at = conjunction_at
        elif punctuation_breaks:
            split_at = min(punctuation_breaks, key=lambda index: abs(index - 22))
        else:
            split_at = min(22, len(words) - 1)
            while split_at > 16 and words[split_at - 1].lower().strip(",;:.") in {
                "a", "an", "the", "of", "to", "in", "for", "with", "by", "from", "on", "and", "or",
            }:
                split_at -= 1
        first = " ".join(words[:split_at]).rstrip(" ,;:.") + "."
        second = " ".join(words[split_at:]).strip()
        # str.lstrip("and ") removes any leading a/n/d characters, not the
        # conjunction as a token (for example, "dollars" became "Ollars").
        second = re.sub(r"^(?:and|while|which|so)\s+", "", second, flags=re.I)
        if second:
            second = second[0].upper() + second[1:]
            if second[-1] not in ".!?":
                second += "."
        output.extend((first, second))
    return normalize_spaces(" ".join(output))


def repair_text(text: str, artifact: str, *, max_passes: int = 3) -> RepairOutcome:
    current = normalize_spaces(text)
    repairs: list[str] = []
    for _pass in range(max_passes):
        findings = validate_text(current, artifact)
        hard = {finding.rule_id for finding in findings if finding.severity == "fail"}
        if not hard:
            return RepairOutcome(current, findings, tuple(repairs), True)
        before = current
        if any(rule.startswith("SUBSTITUTION_") for rule in hard):
            current = collision_safe_substitute(current, ())
            repairs.append("SUBSTITUTION_REPAIR")
        if "SPOKEN_RESUME_MANDATE" in hard:
            current = normalize_spaces(
                re.sub(
                    re.escape(MANDATORY_REORG_SENTENCE),
                    "The position ended because of a company reorganization.",
                    current,
                    flags=re.I,
                )
            )
            repairs.append("SPOKEN_REGISTER_REPAIR")
        if "SPOKEN_SENTENCE_LENGTH" in hard:
            current = _split_long_spoken(current)
            repairs.append("SPOKEN_SENTENCE_SPLIT")
        if "PROSE_AND_CHAIN" in hard or "PROSE_NESTED_LIST" in hard:
            current = _repair_and_chain(_split_semicolons(current))
            repairs.append("CLAUSE_DENSITY_REPAIR")
        if current == before:
            break
    findings = validate_text(current, artifact)
    return RepairOutcome(current, findings, tuple(dict.fromkeys(repairs)), not any(item.severity == "fail" for item in findings))


def spoken_register(text: str) -> RepairOutcome:
    cleaned = normalize_spaces(text)
    cleaned = re.sub(r"\bPosition impacted by company reorganization\.\s*", "The position ended because of a company reorganization. ", cleaned, flags=re.I)
    outcome = repair_text(cleaned, "spoken")
    if not outcome.converged:
        rule_ids = ", ".join(
            dict.fromkeys(finding.rule_id for finding in outcome.findings if finding.severity == "fail")
        ) or "UNKNOWN"
        issue = f"Spoken prose repair did not converge. Rule IDs: {rule_ids}"
        collector = _SPOKEN_REPAIR_ISSUES.get()
        if collector is not None and issue not in collector:
            collector.append(issue)
    return outcome
