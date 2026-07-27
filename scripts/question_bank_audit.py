"""Read-only question-bank audit helpers.

The audit reports functional redundancy: prompts that collapse to the same
question_prep.question_category() and therefore receive the same answer path.
It never edits, reorders, or deletes source bank content.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import business_context
import question_prep
from config.paths import APPLICATION_QUESTIONS, JOB_DESCRIPTION, JOBS_DIR, PROJECT_ROOT
from utils import optional_text, read_text


APPLICATION_QUESTIONS_BANK = JOBS_DIR / "application_questions_bank.txt"
INTERVIEW_PREP_DIR = PROJECT_ROOT / "interview_prep"
GENERIC_NEAR_DUPLICATE_THRESHOLD = 0.6
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "can",
    "could",
    "did",
    "do",
    "does",
    "for",
    "from",
    "give",
    "have",
    "how",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "me",
    "my",
    "of",
    "on",
    "or",
    "please",
    "related",
    "tell",
    "the",
    "this",
    "through",
    "to",
    "us",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
    "you",
    "your",
    "about",
    "all",
    "any",
    "currently",
    "directly",
    "either",
    "else",
    "example",
    "specific",
    "position",
    "role",
    "company",
    "job",
    "duties",
    "briefly",
    "describe",
}


@dataclass(frozen=True)
class QuestionBankAuditRow:
    prompt: str
    category: str
    sources: tuple[str, ...]
    theme_track_refs: tuple[str, ...]


@dataclass(frozen=True)
class QuestionBankAudit:
    rows: tuple[QuestionBankAuditRow, ...]
    exact_duplicate_groups: tuple[tuple[str, ...], ...]
    category_collisions: dict[str, tuple[str, ...]]
    unmapped_prompts: tuple[str, ...]
    application_near_duplicates: tuple[tuple[str, str, float], ...]
    interview_corpus_rows: tuple[QuestionBankAuditRow, ...] = ()
    interview_near_duplicates: tuple[tuple[str, str, float], ...] = ()

    @property
    def near_duplicate_pairs(self) -> tuple[tuple[str, str, float], ...]:
        return self.application_near_duplicates


def theme_tracks(category: str) -> tuple[str, ...]:
    try:
        import interview_intelligence

        return interview_intelligence.question_theme_tracks(category)
    except (ImportError, AttributeError):
        return ()


def prompt_tokens(prompt: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", prompt.lower()) if token not in STOPWORDS}


def jaccard_similarity(first: str, second: str) -> float:
    first_tokens = prompt_tokens(first)
    second_tokens = prompt_tokens(second)
    if not first_tokens and not second_tokens:
        return 0.0
    return len(first_tokens & second_tokens) / max(1, len(first_tokens | second_tokens))


def label_prompt_source(path: Path, prompt: str) -> str:
    try:
        relative = path.relative_to(PROJECT_ROOT)
        return str(relative).replace("\\", "/")
    except ValueError:
        return path.name or prompt[:40]


def application_bank_prompts(path: Path = APPLICATION_QUESTIONS_BANK) -> tuple[tuple[str, str], ...]:
    if not path.exists():
        return ()
    return tuple((prompt, label_prompt_source(path, prompt)) for prompt in question_prep.parse_question_blocks(read_text(path)))


def active_application_prompts(path: Path = APPLICATION_QUESTIONS) -> tuple[tuple[str, str], ...]:
    if not path.exists():
        return ()
    state = question_prep.load_application_prompt_state(path)
    if state.uses_default_questions:
        return ()
    return tuple((prompt, label_prompt_source(path, prompt)) for prompt in state.explicit_prompts)


QUESTION_LEAD_RE = re.compile(
    r"^(?:Tell|Describe|Give|Can|Could|Walk|Why|What|How|Do|Does|Are|Is|Who|Where|When)\b",
    re.I,
)
ENUMERATED_QUESTION_RE = re.compile(r"^\d+[.)]\s+")


def normalize_markdown_question_line(raw_line: str) -> str:
    line = re.sub(r"^[>\s#*\-]+", "", raw_line).strip()
    line = re.sub(r"^\*\*(.+?)\*\*$", r"\1", line).strip()
    line = line.strip().strip('"')
    line = re.split(r"\s+->\s+|\s+Lead:\s+", line, maxsplit=1)[0].strip()
    return question_prep.normalize_spaces(line)


def is_markdown_interview_question(line: str) -> bool:
    if not line or len(line) < 8:
        return False
    enumerated = bool(ENUMERATED_QUESTION_RE.match(line))
    prompt_text = ENUMERATED_QUESTION_RE.sub("", line).strip()
    if not prompt_text:
        return False
    if not enumerated and prompt_text[:1].islower():
        return False
    if not QUESTION_LEAD_RE.search(prompt_text):
        return False
    if enumerated:
        return True
    return prompt_text.endswith("?")


def markdown_question_prompts(prep_dir: Path = INTERVIEW_PREP_DIR) -> tuple[tuple[str, str], ...]:
    if not prep_dir.exists():
        return ()
    prompts: list[tuple[str, str]] = []
    for path in sorted(prep_dir.glob("*.md")):
        for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
            cleaned = normalize_markdown_question_line(raw_line)
            if is_markdown_interview_question(cleaned):
                prompts.append((cleaned, label_prompt_source(path, cleaned)))
    return tuple(prompts)


def business_context_prompts(job_description: str = "") -> tuple[tuple[str, str], ...]:
    if not job_description.strip() and JOB_DESCRIPTION.exists():
        job_description = optional_text(JOB_DESCRIPTION)
    if not job_description.strip():
        return ()
    try:
        questions = business_context.business_interview_questions(job_description, limit=10)
    except (OSError, ValueError, AttributeError):
        return ()
    return tuple((item.question, "generated/business_context") for item in questions if getattr(item, "question", ""))


def embedded_application_prompts(job_description: str = "") -> tuple[tuple[str, str], ...]:
    if not job_description.strip() and JOB_DESCRIPTION.exists():
        job_description = optional_text(JOB_DESCRIPTION)
    if not job_description.strip():
        return ()
    try:
        import job_context_archive

        parser = getattr(job_context_archive, "parse_embedded_application_questions")
    except (ImportError, AttributeError):
        return ()
    prompts = parser(job_description)
    return tuple((prompt, "jobs/job_description.txt#Application Questions") for prompt in prompts)


def collect_question_prompts(job_description: str = "") -> tuple[tuple[str, str], ...]:
    return (
        *application_bank_prompts(),
        *active_application_prompts(),
        *embedded_application_prompts(job_description),
        *markdown_question_prompts(),
        *business_context_prompts(job_description),
    )


def collect_application_input_prompts(job_description: str = "") -> tuple[tuple[str, str], ...]:
    return (
        *application_bank_prompts(),
        *active_application_prompts(),
        *embedded_application_prompts(job_description),
    )


def collect_interview_corpus_prompts(job_description: str = "") -> tuple[tuple[str, str], ...]:
    return (
        *markdown_question_prompts(),
        *business_context_prompts(job_description),
    )


def dedupe_prompt_sources(collected: tuple[tuple[str, str], ...]) -> tuple[dict[str, tuple[str, list[str]]], tuple[tuple[str, ...], ...]]:
    by_normalized: dict[str, tuple[str, list[str]]] = {}
    for prompt, source in collected:
        cleaned = question_prep.normalize_spaces(prompt)
        if not cleaned:
            continue
        key = question_prep.normalize_question(cleaned)
        if key not in by_normalized:
            by_normalized[key] = (cleaned, [])
        by_normalized[key][1].append(source)
    exact_duplicate_groups: list[tuple[str, ...]] = []
    for prompt, sources in by_normalized.values():
        repeated_sources = tuple(source for source in dict.fromkeys(sources) if sources.count(source) > 1)
        if repeated_sources:
            exact_duplicate_groups.append((prompt, *repeated_sources))
    return by_normalized, tuple(exact_duplicate_groups)


def application_rows_and_duplicates(collected: tuple[tuple[str, str], ...]) -> tuple[tuple[QuestionBankAuditRow, ...], tuple[tuple[str, ...], ...]]:
    by_normalized, exact_duplicate_groups = dedupe_prompt_sources(collected)
    rows: list[QuestionBankAuditRow] = []
    for prompt, sources in by_normalized.values():
        unique_sources = tuple(dict.fromkeys(sources))
        category = question_prep.question_category(prompt)
        rows.append(
            QuestionBankAuditRow(
                prompt=prompt,
                category=category,
                sources=unique_sources,
                theme_track_refs=theme_tracks(category),
            )
        )
    return tuple(rows), exact_duplicate_groups


def interview_rows(collected: tuple[tuple[str, str], ...]) -> tuple[QuestionBankAuditRow, ...]:
    by_normalized, _exact_duplicate_groups = dedupe_prompt_sources(collected)
    rows: list[QuestionBankAuditRow] = []
    for prompt, sources in by_normalized.values():
        rows.append(
            QuestionBankAuditRow(
                prompt=prompt,
                category="interview_reference",
                sources=tuple(dict.fromkeys(sources)),
                theme_track_refs=(),
            )
        )
    return tuple(rows)


def generic_near_duplicates(rows: tuple[QuestionBankAuditRow, ...]) -> tuple[tuple[str, str, float], ...]:
    by_category: dict[str, list[str]] = {}
    for row in rows:
        by_category.setdefault(row.category, []).append(row.prompt)
    generic_prompts = by_category.get("generic_bridge", [])
    near_pairs: list[tuple[str, str, float]] = []
    for index, first in enumerate(generic_prompts):
        for second in generic_prompts[index + 1 :]:
            score = jaccard_similarity(first, second)
            if score >= GENERIC_NEAR_DUPLICATE_THRESHOLD:
                near_pairs.append((first, second, score))
    return tuple(near_pairs)


def near_duplicates(rows: tuple[QuestionBankAuditRow, ...]) -> tuple[tuple[str, str, float], ...]:
    prompts = tuple(row.prompt for row in rows)
    near_pairs: list[tuple[str, str, float]] = []
    for index, first in enumerate(prompts):
        for second in prompts[index + 1 :]:
            score = jaccard_similarity(first, second)
            if score >= GENERIC_NEAR_DUPLICATE_THRESHOLD:
                near_pairs.append((first, second, score))
    return tuple(near_pairs)


def build_audit(
    rows_with_sources: tuple[tuple[str, str], ...] | None = None,
    job_description: str = "",
    interview_rows_with_sources: tuple[tuple[str, str], ...] | None = None,
) -> QuestionBankAudit:
    application_collected = collect_application_input_prompts(job_description) if rows_with_sources is None else rows_with_sources
    interview_collected = collect_interview_corpus_prompts(job_description) if rows_with_sources is None else (interview_rows_with_sources or ())
    rows, exact_duplicate_groups = application_rows_and_duplicates(application_collected)
    interview_corpus_rows = interview_rows(interview_collected)
    by_category: dict[str, list[str]] = {}
    for row in rows:
        by_category.setdefault(row.category, []).append(row.prompt)
    category_collisions = {
        category: tuple(prompts)
        for category, prompts in by_category.items()
        if category != "generic_bridge" and len(prompts) > 1
    }
    return QuestionBankAudit(
        rows=rows,
        exact_duplicate_groups=exact_duplicate_groups,
        category_collisions=category_collisions,
        unmapped_prompts=tuple(row.prompt for row in rows if row.category == "generic_bridge"),
        application_near_duplicates=generic_near_duplicates(rows),
        interview_corpus_rows=interview_corpus_rows,
        interview_near_duplicates=near_duplicates(interview_corpus_rows),
    )


def audit_application_bank(path: Path = APPLICATION_QUESTIONS_BANK) -> QuestionBankAudit:
    return build_audit(application_bank_prompts(path))


def audit_application_inputs(job_description: str = "") -> QuestionBankAudit:
    return build_audit(collect_application_input_prompts(job_description))
