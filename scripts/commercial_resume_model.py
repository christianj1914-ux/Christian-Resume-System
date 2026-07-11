"""Provenance-bearing commercial resume content model and render boundary.

The legacy tailoring helpers may still prepare candidate text, but summary,
role-summary, and bullet content crosses this model before the final formatting
passes.  Each modeled line points back to the approved source role that
authorized it; the renderer then writes those three content surfaces once.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from xml.etree import ElementTree as ET

from resume_analysis import normalize_compare, normalize_title
from resume_format import W, is_bullet, paragraph_text, set_paragraph_text


MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)
ROLE_DATE_RE = re.compile(rf"(?:{'|'.join(MONTHS)})\s+\d{{4}}", re.I)


@dataclass(frozen=True)
class SourceRef:
    source_path: str
    role_title: str
    employer: str
    paragraph_kind: str
    paragraph_index: int
    source_text: str
    transformation: str


@dataclass(frozen=True)
class ProvenancedText:
    text: str
    provenance: tuple[SourceRef, ...]


@dataclass(frozen=True)
class CommercialRoleModel:
    title: str
    employer: str
    company_context: str
    summaries: tuple[ProvenancedText, ...]
    bullets: tuple[ProvenancedText, ...]


@dataclass(frozen=True)
class CommercialResumeModel:
    source_path: str
    summary: tuple[ProvenancedText, ...]
    roles: tuple[CommercialRoleModel, ...]
    content_hash: str


@dataclass(frozen=True)
class _RoleBlock:
    title: str
    employer: str
    company_context: str
    summaries: tuple[tuple[int, str], ...]
    bullets: tuple[tuple[int, str], ...]


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _is_role_heading(text: str) -> bool:
    match = ROLE_DATE_RE.search(text)
    return bool(match and match.start() >= 12)


def _paragraphs(document_xml: Path) -> list[ET.Element]:
    return ET.parse(document_xml).getroot().findall(f".//{W}p")


def _section_index(paragraphs: list[ET.Element], heading: str) -> int | None:
    wanted = normalize_compare(heading)
    for index, paragraph in enumerate(paragraphs):
        if normalize_compare(_clean(paragraph_text(paragraph))) == wanted:
            return index
    return None


def _summary_lines(paragraphs: list[ET.Element]) -> tuple[tuple[int, str], ...]:
    start = _section_index(paragraphs, "Professional Summary")
    end = _section_index(paragraphs, "Professional Experience")
    if start is None or end is None or end <= start:
        return ()
    return tuple(
        (index, _clean(paragraph_text(paragraphs[index])))
        for index in range(start + 1, end)
        if _clean(paragraph_text(paragraphs[index]))
    )


def _looks_like_context(text: str, employer: str) -> bool:
    lowered = text.lower()
    employer_words = [word for word in re.findall(r"[a-z0-9]+", employer.lower()) if len(word) > 2]
    return bool(
        employer_words
        and sum(word in lowered for word in employer_words) >= max(1, len(employer_words) - 1)
        and re.search(r"\b(?:is|was|provides|operates|serves)\b", lowered)
    )


def _role_blocks(paragraphs: list[ET.Element]) -> tuple[_RoleBlock, ...]:
    start = _section_index(paragraphs, "Professional Experience")
    end = _section_index(paragraphs, "Education")
    if start is None or end is None or end <= start:
        return ()
    headings = [
        index
        for index in range(start + 1, end)
        if not is_bullet(paragraphs[index]) and _is_role_heading(_clean(paragraph_text(paragraphs[index])))
    ]
    blocks: list[_RoleBlock] = []
    for position, heading_index in enumerate(headings):
        block_end = headings[position + 1] if position + 1 < len(headings) else end
        heading_text = _clean(paragraph_text(paragraphs[heading_index]))
        title = normalize_title(heading_text)
        employer = ""
        company_index: int | None = None
        for index in range(heading_index + 1, block_end):
            text = _clean(paragraph_text(paragraphs[index]))
            if text and not is_bullet(paragraphs[index]):
                employer = text.split("|", 1)[0].strip()
                company_index = index
                break
        context = ""
        summaries: list[tuple[int, str]] = []
        bullets: list[tuple[int, str]] = []
        if company_index is not None:
            for index in range(company_index + 1, block_end):
                text = _clean(paragraph_text(paragraphs[index]))
                if not text:
                    continue
                if is_bullet(paragraphs[index]):
                    bullets.append((index, text))
                elif not context and _looks_like_context(text, employer):
                    context = text
                else:
                    summaries.append((index, text))
        blocks.append(
            _RoleBlock(
                title=title,
                employer=employer,
                company_context=context,
                summaries=tuple(summaries),
                bullets=tuple(bullets),
            )
        )
    return tuple(blocks)


def _tokens(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-z0-9]+", text.lower()) if len(word) > 2}


def _best_source_ref(
    final_text: str,
    source_items: tuple[tuple[int, str], ...],
    *,
    source_path: str,
    title: str,
    employer: str,
    kind: str,
    transformation: str,
) -> tuple[SourceRef, ...]:
    if not source_items:
        return ()
    final_tokens = _tokens(final_text)
    scored: list[tuple[float, int, str]] = []
    for index, source_text in source_items:
        source_tokens = _tokens(source_text)
        union = final_tokens | source_tokens
        score = len(final_tokens & source_tokens) / len(union) if union else 0.0
        if normalize_compare(final_text) == normalize_compare(source_text):
            score = 1.0
        scored.append((score, index, source_text))
    score, index, source_text = max(scored, key=lambda item: (item[0], -item[1]))
    return (
        SourceRef(
            source_path=source_path,
            role_title=title,
            employer=employer,
            paragraph_kind=kind,
            paragraph_index=index,
            source_text=source_text,
            transformation="source-exact" if score == 1.0 else transformation,
        ),
    )


def build_content_model(source_path: Path, source_xml: Path, staged_xml: Path) -> CommercialResumeModel:
    source_paragraphs = _paragraphs(source_xml)
    staged_paragraphs = _paragraphs(staged_xml)
    source_summary = _summary_lines(source_paragraphs)
    staged_summary = _summary_lines(staged_paragraphs)
    summary = tuple(
        ProvenancedText(
            text=text,
            provenance=_best_source_ref(
                text,
                source_summary,
                source_path=str(source_path),
                title="",
                employer="",
                kind="professional-summary",
                transformation="summary-composer",
            ),
        )
        for _, text in staged_summary
    )

    source_roles = {
        (normalize_compare(role.title), normalize_compare(role.employer)): role
        for role in _role_blocks(source_paragraphs)
    }
    modeled_roles: list[CommercialRoleModel] = []
    for role in _role_blocks(staged_paragraphs):
        key = (normalize_compare(role.title), normalize_compare(role.employer))
        source_role = source_roles.get(key)
        if source_role is None:
            raise ValueError(f"MODEL_ROLE_WITHOUT_SOURCE:{role.title}:{role.employer}")
        summaries = tuple(
            ProvenancedText(
                text=text,
                provenance=_best_source_ref(
                    text,
                    source_role.summaries,
                    source_path=str(source_path),
                    title=role.title,
                    employer=role.employer,
                    kind="role-summary",
                    transformation="role-summary-composer",
                ),
            )
            for _, text in role.summaries
        )
        bullets = tuple(
            ProvenancedText(
                text=text,
                provenance=_best_source_ref(
                    text,
                    source_role.bullets,
                    source_path=str(source_path),
                    title=role.title,
                    employer=role.employer,
                    kind="bullet",
                    transformation="supported-bullet-selection-or-rewrite",
                ),
            )
            for _, text in role.bullets
        )
        modeled_roles.append(
            CommercialRoleModel(
                title=role.title,
                employer=role.employer,
                company_context=role.company_context,
                summaries=summaries,
                bullets=bullets,
            )
        )
    payload = "\n".join(
        [*(item.text for item in summary), *(item.text for role in modeled_roles for item in (*role.summaries, *role.bullets))]
    )
    model = CommercialResumeModel(
        source_path=str(source_path),
        summary=summary,
        roles=tuple(modeled_roles),
        content_hash=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
    )
    validate_content_model(model)
    return model


def validate_content_model(model: CommercialResumeModel) -> None:
    problems: list[str] = []
    if not model.summary or any(not item.provenance for item in model.summary):
        problems.append("MODEL_SUMMARY_PROVENANCE_MISSING")
    for role in model.roles:
        if not role.title or not role.employer:
            problems.append("MODEL_ROLE_IDENTITY_MISSING")
        for item in (*role.summaries, *role.bullets):
            if not item.provenance:
                problems.append(f"MODEL_PROVENANCE_MISSING:{role.employer}:{item.text[:50]}")
                continue
            if any(normalize_compare(ref.employer) != normalize_compare(role.employer) for ref in item.provenance):
                problems.append(f"MODEL_CROSS_EMPLOYER_PROVENANCE:{role.employer}:{item.text[:50]}")
    if problems:
        raise ValueError("; ".join(problems))


def with_composed_summaries(
    model: CommercialResumeModel,
    professional_summary: str,
    role_summaries: dict[str, str],
) -> CommercialResumeModel:
    """Replace summary surfaces in the model without mutating Word XML."""
    if len(model.summary) != 1:
        raise ValueError("MODEL_COMPOSER_EXPECTED_ONE_PROFESSIONAL_SUMMARY")
    summary = (replace(model.summary[0], text=_clean(professional_summary)),)
    roles: list[CommercialRoleModel] = []
    normalized_replacements = {normalize_compare(key): _clean(value) for key, value in role_summaries.items()}
    for role in model.roles:
        replacement_text = normalized_replacements.get(normalize_compare(role.employer))
        summaries = role.summaries
        if replacement_text:
            if len(summaries) != 1:
                raise ValueError(f"MODEL_COMPOSER_EXPECTED_ONE_ROLE_SUMMARY:{role.employer}")
            summaries = (replace(summaries[0], text=replacement_text),)
        roles.append(replace(role, summaries=summaries))
    payload = "\n".join(
        [*(item.text for item in summary), *(item.text for role in roles for item in (*role.summaries, *role.bullets))]
    )
    updated = replace(
        model,
        summary=summary,
        roles=tuple(roles),
        content_hash=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
    )
    validate_content_model(updated)
    return updated


def render_content_model(document_xml: Path, model: CommercialResumeModel) -> None:
    """Write modeled summary, role-summary, and bullet text exactly once."""
    tree = ET.parse(document_xml)
    paragraphs = tree.getroot().findall(f".//{W}p")
    summary_nodes = _summary_lines(paragraphs)
    if len(summary_nodes) != len(model.summary):
        raise ValueError("MODEL_RENDER_SUMMARY_COUNT_MISMATCH")
    for (index, _), item in zip(summary_nodes, model.summary):
        set_paragraph_text(paragraphs[index], item.text)

    blocks = {
        (normalize_compare(role.title), normalize_compare(role.employer)): role
        for role in _role_blocks(paragraphs)
    }
    for role in model.roles:
        key = (normalize_compare(role.title), normalize_compare(role.employer))
        block = blocks.get(key)
        if block is None:
            raise ValueError(f"MODEL_RENDER_ROLE_MISSING:{role.title}:{role.employer}")
        if len(block.summaries) != len(role.summaries) or len(block.bullets) != len(role.bullets):
            raise ValueError(f"MODEL_RENDER_ROLE_COUNT_MISMATCH:{role.title}:{role.employer}")
        for (index, _), item in zip(block.summaries, role.summaries):
            set_paragraph_text(paragraphs[index], item.text)
        for (index, _), item in zip(block.bullets, role.bullets):
            set_paragraph_text(paragraphs[index], item.text)
    tree.write(document_xml, encoding="utf-8", xml_declaration=True)


def write_manifest(model: CommercialResumeModel, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(asdict(model), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path
