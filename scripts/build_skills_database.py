#!/usr/bin/env python3
"""Build a structured markdown skills database from the source resumes."""

from __future__ import annotations

import _bootstrap

_bootstrap.ensure_script_path()

import argparse
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from docx import Document


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT_ROOT / "source"
SCRATCH_DIR = PROJECT_ROOT / "scratch"
OUTPUT_PATH = SCRATCH_DIR / "skills_database.md"
SOURCE_FILES = (
    SOURCE_DIR / "Estrada_Resume_Implementation.docx",
    SOURCE_DIR / "Estrada_Resume_PreSales_CSM.docx",
)
MONTH_PATTERN = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
ROLE_HEADING_RE = re.compile(rf"^(?P<title>.+?)\s+(?P<dates>{MONTH_PATTERN}\s+\d{{4}}\s+to\s+(?:{MONTH_PATTERN}\s+\d{{4}}|Present))$")


@dataclass(frozen=True)
class ResumeRole:
    source_label: str
    title: str
    dates: str
    company_line: str
    context: str
    summary: str
    bullets: tuple[str, ...]


@dataclass(frozen=True)
class ResumeSnapshot:
    source_name: str
    source_label: str
    headline: str
    summary: str
    roles: tuple[ResumeRole, ...]
    competencies: dict[str, tuple[str, ...]]
    education: tuple[str, ...]
    professional_development: tuple[str, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a markdown skills database from the source resumes.")
    parser.add_argument("--refresh", action="store_true", help="Rebuild the file even if it already appears current.")
    return parser.parse_args()


def nonempty_paragraphs(path: Path) -> list[str]:
    doc = Document(str(path))
    lines: list[str] = []
    for paragraph in doc.paragraphs:
        text = re.sub(r"\s+", " ", paragraph.text).strip()
        if text:
            lines.append(text)
    return lines


def find_section_index(lines: list[str], label: str) -> int:
    try:
        return lines.index(label)
    except ValueError as error:
        raise SystemExit(f"Could not find section '{label}' in {label}.") from error


def parse_competencies(lines: list[str]) -> dict[str, tuple[str, ...]]:
    competencies: dict[str, tuple[str, ...]] = {}
    for line in lines:
        if ":" not in line:
            continue
        category, items_text = line.split(":", 1)
        items = tuple(item.strip() for item in items_text.split("|") if item.strip())
        if items:
            competencies[category.strip()] = items
    return competencies


def parse_roles(lines: list[str], source_label: str) -> tuple[ResumeRole, ...]:
    roles: list[ResumeRole] = []
    index = 0
    while index < len(lines):
        match = ROLE_HEADING_RE.match(lines[index])
        if not match:
            index += 1
            continue
        title = match.group("title").strip()
        dates = match.group("dates").strip()
        company_line = lines[index + 1] if index + 1 < len(lines) else ""
        index += 2
        body: list[str] = []
        while index < len(lines) and not ROLE_HEADING_RE.match(lines[index]):
            body.append(lines[index])
            index += 1
        company_name = company_line.split("|", 1)[0].strip()
        context = ""
        if body and company_name and body[0].lower().startswith(company_name.lower()):
            context = body[0]
            body = body[1:]
        summary = body[0] if body else ""
        bullets = tuple(body[1:]) if len(body) > 1 else ()
        roles.append(
            ResumeRole(
                source_label=source_label,
                title=title,
                dates=dates,
                company_line=company_line,
                context=context,
                summary=summary,
                bullets=bullets,
            )
        )
    return tuple(roles)


def parse_resume(path: Path) -> ResumeSnapshot:
    lines = nonempty_paragraphs(path)
    source_label = "Implementation" if "Implementation" in path.stem else "PreSales_CSM"
    try:
        summary_index = lines.index("Professional Summary")
        experience_index = lines.index("Professional Experience")
        education_index = lines.index("Education")
        competencies_index = lines.index("Core Competencies")
        development_index = lines.index("Professional Development")
    except ValueError as error:
        raise SystemExit(f"Missing expected resume section in {path.name}: {error}") from error

    headline = lines[1] if len(lines) > 1 else ""
    summary = lines[summary_index + 1] if summary_index + 1 < len(lines) else ""
    experience_lines = lines[experience_index + 1 : education_index]
    education = tuple(lines[education_index + 1 : competencies_index])
    competency_lines = lines[competencies_index + 1 : development_index]
    development_line = lines[development_index + 1] if development_index + 1 < len(lines) else ""
    professional_development = tuple(item.strip() for item in development_line.split("|") if item.strip())

    return ResumeSnapshot(
        source_name=path.name,
        source_label=source_label,
        headline=headline,
        summary=summary,
        roles=parse_roles(experience_lines, source_label),
        competencies=parse_competencies(competency_lines),
        education=education,
        professional_development=professional_development,
    )


def aggregate_competencies(snapshots: list[ResumeSnapshot]) -> dict[str, list[str]]:
    combined: dict[str, set[str]] = {}
    for snapshot in snapshots:
        for category, items in snapshot.competencies.items():
            combined.setdefault(category, set()).update(items)
    return {category: sorted(items) for category, items in combined.items()}


def render_markdown(snapshots: list[ResumeSnapshot]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Skills Database",
        "",
        f"Generated: {now}",
        "",
        "## Source Resumes",
    ]
    for snapshot in snapshots:
        lines.append(f"- {snapshot.source_name} ({snapshot.source_label})")
        lines.append(f"  Headline: {snapshot.headline}")
    lines.extend(("", "## Unified Core Competencies"))
    for category, items in aggregate_competencies(snapshots).items():
        lines.append(f"### {category}")
        for item in items:
            lines.append(f"- {item}")
        lines.append("")

    lines.append("## Role Evidence Map")
    grouped_roles: dict[tuple[str, str], list[ResumeRole]] = {}
    for snapshot in snapshots:
        for role in snapshot.roles:
            key = (role.title, role.company_line)
            grouped_roles.setdefault(key, []).append(role)

    for (title, company_line), roles in grouped_roles.items():
        lines.append(f"### {title} | {company_line}")
        for role in roles:
            lines.append(f"- Source: {role.source_label}")
            lines.append(f"- Dates: {role.dates}")
            if role.context:
                lines.append(f"- Company context: {role.context}")
            if role.summary:
                lines.append(f"- Summary: {role.summary}")
            for bullet in role.bullets[:4]:
                lines.append(f"- Evidence: {bullet}")
        lines.append("")

    lines.append("## Education")
    for snapshot in snapshots:
        lines.append(f"### {snapshot.source_label}")
        for item in snapshot.education:
            lines.append(f"- {item}")
    lines.extend(("", "## Professional Development"))
    combined_development = sorted({item for snapshot in snapshots for item in snapshot.professional_development})
    for item in combined_development:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def output_is_current(output_path: Path) -> bool:
    if not output_path.exists():
        return False
    output_mtime = output_path.stat().st_mtime
    return all(source.exists() and source.stat().st_mtime <= output_mtime for source in SOURCE_FILES)


def build_skills_database(output_path: Path = OUTPUT_PATH, force: bool = False) -> Path:
    if not force and output_is_current(output_path):
        print(f"Skills database already current: {output_path}")
        return output_path

    snapshots = [parse_resume(path) for path in SOURCE_FILES]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_markdown(snapshots), encoding="utf-8")
    print(f"Skills database written: {output_path}")
    return output_path


def main() -> None:
    args = parse_args()
    build_skills_database(force=args.refresh)


if __name__ == "__main__":
    main()
