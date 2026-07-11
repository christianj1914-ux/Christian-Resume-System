#!/usr/bin/env python3
"""WordprocessingML formatting helpers for generated resumes."""

from __future__ import annotations

import math
import re
import shutil
import subprocess
import sys
import time
import uuid
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from utils import debug_print, fail

PROJECT_ROOT = Path(__file__).resolve().parents[1]

WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"
RELS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
ET.register_namespace("w", WORD_NS)
W = f"{{{WORD_NS}}}"
R_PKG = f"{{{RELS_NS}}}"
XML_SPACE = f"{{{XML_NS}}}space"

STYLE_PARTS = (
    "word/styles.xml",
    "word/stylesWithEffects.xml",
    "word/theme/theme1.xml",
    "word/fontTable.xml",
    "word/settings.xml",
    "word/webSettings.xml",
)

SECTION_LAYOUT_TAGS = {
    f"{W}pgSz",
    f"{W}pgMar",
    f"{W}cols",
    f"{W}docGrid",
}

SINGLE_LINE_SPACING = "240"
ZERO_SPACING = "0"
RESUME_FONT = "Calibri"
BRAND_BLUE = "1F4E79"
BODY_GRAY = "595959"
LINK_BLUE = "0563C1"
CONTACT_EMAIL = "christianj1914@gmail.com"
LINKEDIN_URL = "https://www.linkedin.com/in/cjne/"
BODY_FONT_SIZE_HP = "20"
SECTION_SEPARATOR_FONT_SIZE_HP = "20"
CORE_COMPETENCY_ROW_SEPARATOR_FONT_SIZE_HP = "6"
SECTION_FONT_SIZE_HP = "21"
NAME_FONT_SIZE_HP = "44"
TITLE_LINE_FONT_SIZE_HP = "21"
XML_PARAGRAPHS_PER_PAGE = 38
XML_WORDS_PER_PAGE = 540
XML_CALIBRATION_BODY_HP = 20.0
XML_CALIBRATION_SEPARATOR_HP = 20.0
XML_COMPETENCY_TARGET = 23
XML_OVERFLOW_COMPETENCY_WORD_PENALTY = 8
FIT_PROFILES = (
    ("20", "21", "20"),
    ("19.6", "21", "20"),
    ("19.6", "21", "19.6"),
    ("20", "21", "19"),
    ("19.6", "21", "19"),
    ("19.2", "20", "19.2"),
    ("20", "21", "18"),
    ("19.6", "21", "18"),
    ("19.2", "20", "18"),
    ("20", "21", "16"),
    ("19.6", "21", "16"),
    ("19.2", "20", "16"),
    ("20", "21", "14"),
    ("19.6", "21", "14"),
    ("19.2", "20", "14"),
    ("19.2", "20", "12"),
)
TARGET_PAGE_COUNT = 2
SKILLS_SECTION_HEADING = "Skills"
LEGACY_SKILLS_SECTION_HEADING = "Core Competencies"
SKILLS_SECTION_ALIASES = (SKILLS_SECTION_HEADING, LEGACY_SKILLS_SECTION_HEADING)
REQUIRED_SECTIONS = (
    "Professional Summary",
    "Professional Experience",
    "Education",
    SKILLS_SECTION_HEADING,
    "Professional Development",
)
MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def paragraph_text(element: ET.Element) -> str:
    return "".join(node.text or "" for node in element.findall(f".//{W}t"))


def title_line_paragraph(paragraphs: list[ET.Element]) -> ET.Element | None:
    nonempty = [
        paragraph
        for paragraph in paragraphs
        if re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
    ]
    return nonempty[1] if len(nonempty) >= 2 else None


def is_bullet(paragraph: ET.Element) -> bool:
    return paragraph.find(f"{W}pPr/{W}numPr") is not None


def normalize_compare(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def normalize_section_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def section_aliases(section: str) -> tuple[str, ...]:
    if section == SKILLS_SECTION_HEADING:
        return SKILLS_SECTION_ALIASES
    return (section,)


def section_matches(text: str, section: str) -> bool:
    normalized = normalize_section_text(text).lower()
    return any(normalized == alias.lower() for alias in section_aliases(section))


def normalize_required_section_name(text: str) -> str | None:
    for section in REQUIRED_SECTIONS:
        if section_matches(text, section):
            return section
    return None


def is_skills_section_heading(text: str) -> bool:
    return section_matches(text, SKILLS_SECTION_HEADING)


def is_company_context_paragraph(company: str, text: str) -> bool:
    company_key = normalize_compare(company)
    text_key = normalize_compare(text)
    if not company_key or not text_key.startswith(company_key):
        return False
    remainder = text_key[len(company_key) :].strip()
    return remainder.startswith(("is ", "provides ", "operates ", "serves "))


def is_role_heading(text: str) -> bool:
    month_pattern = "|".join(MONTHS)
    role_date_pattern = re.compile(
        rf"(?<!\bin\s)(?<!\bsince\s)(?<!\bfrom\s)(?<!\bby\s)(?<!\bduring\s)(?<!\buntil\s)(?<!\bthrough\s)(?:{month_pattern})\s+\d{{4}}",
        re.I,
    )
    date_match = role_date_pattern.search(text)
    return bool(date_match and date_match.start() >= 15)


def unpack_docx(path: Path, target: Path) -> None:
    """Extract DOCX file (which is a ZIP archive) to a target directory.
    
    Raises RuntimeError if the DOCX file is corrupted or cannot be opened.
    """
    try:
        with zipfile.ZipFile(path) as archive:
            # Test the archive integrity first
            bad_file = archive.testzip()
            if bad_file:
                raise RuntimeError(f"DOCX package validation failed at {bad_file}: archive may be corrupted")
            archive.extractall(target)
    except zipfile.BadZipFile as e:
        raise RuntimeError(f"Cannot unpack DOCX file {path}: {e}. The file may be corrupted or not a valid Word document.") from e
    except FileNotFoundError as e:
        raise RuntimeError(f"DOCX file not found: {path}") from e
    except Exception as e:
        raise RuntimeError(f"Error unpacking DOCX file {path}: {e}") from e

def pack_docx(source: Path, target: Path) -> None:
    """Create a DOCX file (ZIP archive) from a source directory.
    
    Raises RuntimeError if the ZIP creation fails or the output cannot be written.
    """
    try:
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(source.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(source).as_posix())
        
        # Verify the created archive is readable
        with zipfile.ZipFile(target) as verify:
            bad_file = verify.testzip()
            if bad_file:
                raise RuntimeError(f"DOCX package validation failed at {bad_file}: created archive may be corrupted")
    except OSError as e:
        raise RuntimeError(f"Cannot write DOCX file to {target}: {e}. Check disk space and file permissions.") from e
    except Exception as e:
        raise RuntimeError(f"Error creating DOCX file {target}: {e}") from e

def pack_docx_with_page_fit(work_dir: Path, output_docx: Path, document_xml: Path, temp_root: Path) -> int | None:
    last_page_count: int | None = None
    candidate_docx = temp_root / "fit_candidate.docx"
    under_target_docx = temp_root / "fit_under_target.docx"
    under_target_page_count: int | None = None

    def might_render_more_pages(profile: tuple[str, str, str], current_profile: tuple[str, str, str]) -> bool:
        return any(
            float(candidate_size) > float(current_size)
            for candidate_size, current_size in zip(profile, current_profile)
        )

    profiles_to_try = list(FIT_PROFILES)
    while profiles_to_try:
        current_profile = profiles_to_try.pop(0)
        body_size, section_size, separator_size = current_profile
        apply_fit_font_sizing(
            document_xml,
            body_size_hp=body_size,
            section_size_hp=section_size,
            separator_size_hp=separator_size,
        )
        pack_docx(work_dir, candidate_docx)
        started = time.monotonic()
        page_count = rendered_page_count(
            candidate_docx,
            temp_root,
            document_xml,
            body_size_hp=float(body_size),
            separator_size_hp=float(separator_size),
        )
        elapsed = time.monotonic() - started
        page_label = "unknown" if page_count is None else str(page_count)
        remaining_profiles = profiles_to_try
        if page_count == TARGET_PAGE_COUNT or page_count is None:
            remaining_profiles = []
        elif page_count < TARGET_PAGE_COUNT:
            # Once a profile renders under target, fully more compact profiles cannot add pages back.
            remaining_profiles = [
                profile for profile in profiles_to_try if might_render_more_pages(profile, current_profile)
            ]
        print(
            "Fit render: "
            f"body={body_size} section={section_size} separator={separator_size} "
            f"pages={page_label} elapsed={elapsed:.1f}s remaining_profiles={len(remaining_profiles)}"
        )
        if page_count is None:
            shutil.copy2(candidate_docx, output_docx)
            return None
        last_page_count = page_count
        if page_count == TARGET_PAGE_COUNT:
            shutil.copy2(candidate_docx, output_docx)
            return page_count
        if page_count < TARGET_PAGE_COUNT:
            if under_target_page_count is None or page_count > under_target_page_count:
                shutil.copy2(candidate_docx, under_target_docx)
                under_target_page_count = page_count
            profiles_to_try = remaining_profiles

    if under_target_page_count is not None:
        shutil.copy2(under_target_docx, output_docx)
        return under_target_page_count

    fail(
        f"resume still renders to {last_page_count} pages after fitting; "
        "refusing to save a resume over two pages without dropping body text below 10pt"
    )

def apply_font_and_size_pass(
    document_xml: Path,
    font_name: str = RESUME_FONT,
    header_title_line: str = "",
) -> None:
    debug_print("[pass] font and size pass starting", flag="DEBUG_RESUME_LAYOUT")
    tree = ET.parse(document_xml)
    root = tree.getroot()
    title_paragraph = title_line_paragraph(root.findall(f".//{W}p"))
    for run in root.findall(f".//{W}r"):
        r_pr = run.find(f"{W}rPr")
        if r_pr is None:
            r_pr = ET.Element(f"{W}rPr")
            run.insert(0, r_pr)
        set_run_font(r_pr, font_name)

    for paragraph in root.findall(f".//{W}p"):
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        if not text:
            continue
        if text == "Christian Estrada":
            target_size = NAME_FONT_SIZE_HP
        elif paragraph is title_paragraph or (header_title_line and text == header_title_line):
            target_size = TITLE_LINE_FONT_SIZE_HP
        elif normalize_required_section_name(text):
            target_size = SECTION_FONT_SIZE_HP
        else:
            target_size = BODY_FONT_SIZE_HP
        for run in paragraph.findall(f".//{W}r"):
            r_pr = run.find(f"{W}rPr")
            if r_pr is None:
                r_pr = ET.Element(f"{W}rPr")
                run.insert(0, r_pr)
            set_run_size(r_pr, target_size)
            if paragraph is title_paragraph or (header_title_line and text == header_title_line):
                set_bool_prop(r_pr, f"{W}b", False)
                set_bool_prop(r_pr, f"{W}bCs", False)
    tree.write(document_xml, encoding="utf-8", xml_declaration=True)

def collapse_redundant_blank_paragraphs_before_role_headings(body: ET.Element) -> int:
    """Keep at most one blank separator immediately before each experience role heading."""
    removed = 0
    in_experience = False
    children = list(body)
    for index, child in enumerate(children):
        if child.tag != f"{W}p":
            continue
        text = re.sub(r"\s+", " ", paragraph_text(child)).strip()
        normalized_section = normalize_required_section_name(text)
        if normalized_section:
            in_experience = normalized_section == "Professional Experience"
            continue
        if text == "Education":
            in_experience = False
            continue
        if not in_experience or not is_role_heading(text):
            continue

        blanks: list[ET.Element] = []
        scan = index - 1
        current_children = list(body)
        while scan >= 0:
            previous = current_children[scan]
            if previous.tag != f"{W}p":
                break
            if is_blank_paragraph(previous):
                blanks.append(previous)
                scan -= 1
            else:
                break
        if len(blanks) > 1:
            for extra in blanks[1:]:
                body.remove(extra)
                removed += 1

    return removed


def apply_spacing_and_layout_pass(document_xml: Path) -> None:
    debug_print("[pass] spacing and layout pass starting", flag="DEBUG_RESUME_LAYOUT")
    tree = ET.parse(document_xml)
    root = tree.getroot()
    body = root.find(f"{W}body")
    if body is not None:
        collapsed = collapse_redundant_blank_paragraphs_before_role_headings(body)
        if collapsed:
            debug_print(
                f"[pass] collapsed {collapsed} redundant blank paragraph(s) before role headings",
                flag="DEBUG_RESUME_LAYOUT",
            )
    title_paragraph = title_line_paragraph(root.findall(f".//{W}p"))

    for paragraph in root.findall(f".//{W}p"):
        p_pr = paragraph.find(f"{W}pPr")
        if p_pr is None:
            p_pr = ET.Element(f"{W}pPr")
            paragraph.insert(0, p_pr)
        spacing = p_pr.find(f"{W}spacing")
        if spacing is None:
            spacing = ET.SubElement(p_pr, f"{W}spacing")
        set_single_spacing(spacing)

    body = root.find(f"{W}body")
    if body is not None:
        paragraphs = body.findall(f"{W}p")
        in_experience = False
        experience_role_count = 0
        for paragraph in paragraphs:
            text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
            set_paragraph_spacing_values(paragraph)
            if paragraph is title_paragraph:
                set_paragraph_spacing_values(paragraph, after="20")
            if is_blank_paragraph(paragraph):
                normalize_separator_paragraph(paragraph)
                continue
            if not text:
                continue

            normalized_section = normalize_required_section_name(text)
            if normalized_section:
                set_paragraph_spacing_values(paragraph)
                in_experience = normalized_section == "Professional Experience"
                experience_role_count = 0
                continue

            if in_experience and is_role_heading(text):
                experience_role_count += 1
                set_paragraph_spacing_values(paragraph)
                continue

            if text == "Education":
                in_experience = False

        children = list(body)
        in_experience = False
        experience_role_count = 0
        insert_before: list[ET.Element] = []
        for child in children:
            if child.tag != f"{W}p":
                continue
            text = re.sub(r"\s+", " ", paragraph_text(child)).strip()
            normalized_section = normalize_required_section_name(text)
            if normalized_section:
                insert_before.append(child)
                in_experience = normalized_section == "Professional Experience"
                experience_role_count = 0
                continue
            if in_experience and is_role_heading(text):
                experience_role_count += 1
                if experience_role_count > 1:
                    insert_before.append(child)
                continue
            if text == "Education":
                in_experience = False

        for child in insert_before:
            current_children = list(body)
            index = current_children.index(child)
            previous = current_children[index - 1] if index > 0 else None
            if previous is not None and previous.tag == f"{W}p" and is_blank_paragraph(previous):
                normalize_separator_paragraph(previous)
                continue
            body.insert(index, make_separator_paragraph())

        children = list(body)
        core_index = None
        development_index = None
        for index, child in enumerate(children):
            if child.tag != f"{W}p":
                continue
            text = re.sub(r"\s+", " ", paragraph_text(child)).strip()
            if is_skills_section_heading(text):
                core_index = index
            elif text == "PROFESSIONAL DEVELOPMENT":
                development_index = index
                break

        if core_index is not None and development_index is not None and development_index > core_index:
            block = children[core_index + 1 : development_index]
            competency_rows = [
                child
                for child in block
                if child.tag == f"{W}p" and re.sub(r"\s+", " ", paragraph_text(child)).strip()
            ]
            if len(competency_rows) >= 2:
                for row in competency_rows[:-1]:
                    current_children = list(body)
                    row_index = current_children.index(row)
                    next_child = current_children[row_index + 1] if row_index + 1 < len(current_children) else None
                    if next_child is not None and next_child.tag == f"{W}p" and is_blank_paragraph(next_child):
                        normalize_separator_paragraph(next_child, CORE_COMPETENCY_ROW_SEPARATOR_FONT_SIZE_HP)
                        continue
                    body.insert(row_index + 1, make_separator_paragraph(CORE_COMPETENCY_ROW_SEPARATOR_FONT_SIZE_HP))

    paragraphs = root.findall(f".//{W}p")
    current_section = ""
    in_experience = False
    for paragraph in paragraphs:
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        section = normalize_required_section_name(text)
        if section:
            current_section = section
            in_experience = section == "Professional Experience"
            set_paragraph_alignment(paragraph, "center")
            continue
        if not text:
            if in_experience:
                set_paragraph_alignment(paragraph, "left")
            continue
        if in_experience:
            set_paragraph_alignment(paragraph, "left")
            continue
        if current_section == "Professional Summary":
            set_paragraph_alignment(paragraph, "both")
        elif current_section in {"Education", SKILLS_SECTION_HEADING, "Professional Development"}:
            set_paragraph_alignment(paragraph, "center")

    tree.write(document_xml, encoding="utf-8", xml_declaration=True)

def force_document_font(document_xml: Path, font_name: str = RESUME_FONT) -> None:
    tree = ET.parse(document_xml)
    for run in tree.getroot().findall(f".//{W}r"):
        r_pr = run.find(f"{W}rPr")
        if r_pr is None:
            r_pr = ET.Element(f"{W}rPr")
            run.insert(0, r_pr)
        set_run_font(r_pr, font_name)
    tree.write(document_xml, encoding="utf-8", xml_declaration=True)

def force_styles_font(styles_xml: Path, font_name: str = RESUME_FONT) -> None:
    if not styles_xml.is_file():
        return
    tree = ET.parse(styles_xml)
    root = tree.getroot()
    for tag in (f".//{W}rPr", f".//{W}docDefaults/{W}rPrDefault/{W}rPr"):
        for r_pr in root.findall(tag):
            set_run_font(r_pr, font_name)
    for style in root.findall(f".//{W}style"):
        r_pr = style.find(f"{W}rPr")
        if r_pr is None:
            r_pr = ET.SubElement(style, f"{W}rPr")
        set_run_font(r_pr, font_name)
    tree.write(styles_xml, encoding="utf-8", xml_declaration=True)

def apply_dense_font_sizing(document_xml: Path) -> None:
    tree = ET.parse(document_xml)
    for paragraph in tree.getroot().findall(f".//{W}p"):
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        if not text:
            continue
        if text == "Christian Estrada":
            target_size = NAME_FONT_SIZE_HP
        elif normalize_required_section_name(text):
            target_size = SECTION_FONT_SIZE_HP
        else:
            target_size = BODY_FONT_SIZE_HP
        for run in paragraph.findall(f".//{W}r"):
            r_pr = run.find(f"{W}rPr")
            if r_pr is None:
                r_pr = ET.Element(f"{W}rPr")
                run.insert(0, r_pr)
            set_run_size(r_pr, target_size)
    tree.write(document_xml, encoding="utf-8", xml_declaration=True)

def apply_fit_font_sizing(
    document_xml: Path,
    *,
    body_size_hp: str,
    section_size_hp: str,
    separator_size_hp: str,
) -> None:
    tree = ET.parse(document_xml)
    for paragraph in tree.getroot().findall(f".//{W}p"):
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        if not text:
            # Blank paragraphs: check if they have any font sizes defined
            sizes = [size.get(w_attr("val")) for size in paragraph.findall(f".//{W}sz") if size.get(w_attr("val")) is not None]
            target_size = CORE_COMPETENCY_ROW_SEPARATOR_FONT_SIZE_HP if sizes and CORE_COMPETENCY_ROW_SEPARATOR_FONT_SIZE_HP in sizes else separator_size_hp
        elif text == "Christian Estrada":
            target_size = NAME_FONT_SIZE_HP
        elif normalize_required_section_name(text):
            target_size = section_size_hp
        else:
            target_size = body_size_hp
        for run in paragraph.findall(f".//{W}r"):
            r_pr = run.find(f"{W}rPr")
            if r_pr is None:
                r_pr = ET.Element(f"{W}rPr")
                run.insert(0, r_pr)
            set_run_size(r_pr, target_size)
    tree.write(document_xml, encoding="utf-8", xml_declaration=True)

def force_paragraph_single_spacing(document_xml: Path) -> None:
    tree = ET.parse(document_xml)
    for paragraph in tree.getroot().findall(f".//{W}p"):
        p_pr = paragraph.find(f"{W}pPr")
        if p_pr is None:
            p_pr = ET.Element(f"{W}pPr")
            paragraph.insert(0, p_pr)
        spacing = p_pr.find(f"{W}spacing")
        if spacing is None:
            spacing = ET.SubElement(p_pr, f"{W}spacing")
        set_single_spacing(spacing)
    tree.write(document_xml, encoding="utf-8", xml_declaration=True)

def force_style_single_spacing(styles_xml: Path) -> None:
    if not styles_xml.is_file():
        return
    tree = ET.parse(styles_xml)
    for style in tree.getroot().findall(f".//{W}style"):
        p_pr = style.find(f"{W}pPr")
        if p_pr is None:
            p_pr = ET.SubElement(style, f"{W}pPr")
        spacing = p_pr.find(f"{W}spacing")
        if spacing is None:
            spacing = ET.SubElement(p_pr, f"{W}spacing")
        set_single_spacing(spacing)
    tree.write(styles_xml, encoding="utf-8", xml_declaration=True)

def apply_resume_alignment(document_xml: Path) -> None:
    tree = ET.parse(document_xml)
    paragraphs = tree.getroot().findall(f".//{W}p")
    current_section = ""
    in_experience = False

    for paragraph in paragraphs:
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        section = normalize_required_section_name(text)
        if section:
            current_section = section
            in_experience = section == "Professional Experience"
            set_paragraph_alignment(paragraph, "center")
            continue
        if not text:
            if in_experience:
                set_paragraph_alignment(paragraph, "left")
            continue
        if in_experience:
            set_paragraph_alignment(paragraph, "left")
            continue
        if current_section == "Professional Summary":
            set_paragraph_alignment(paragraph, "both")
        elif current_section in {"Education", SKILLS_SECTION_HEADING, "Professional Development"}:
            set_paragraph_alignment(paragraph, "center")

    tree.write(document_xml, encoding="utf-8", xml_declaration=True)

def apply_resume_spacing_rhythm(document_xml: Path) -> None:
    tree = ET.parse(document_xml)
    root = tree.getroot()
    body = root.find(f"{W}body")
    if body is None:
        return
    paragraphs = body.findall(f"{W}p")
    in_experience = False
    experience_role_count = 0

    for paragraph in paragraphs:
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        set_paragraph_spacing_values(paragraph)
        if is_blank_paragraph(paragraph):
            normalize_separator_paragraph(paragraph)
            continue
        if not text:
            continue

        normalized_section = normalize_required_section_name(text)
        if normalized_section:
            set_paragraph_spacing_values(paragraph)
            in_experience = normalized_section == "Professional Experience"
            experience_role_count = 0
            continue

        if in_experience and is_role_heading(text):
            experience_role_count += 1
            set_paragraph_spacing_values(paragraph)
            continue

        if text == "Education":
            in_experience = False

    children = list(body)
    in_experience = False
    experience_role_count = 0
    insert_before: list[ET.Element] = []
    for child in children:
        if child.tag != f"{W}p":
            continue
        text = re.sub(r"\s+", " ", paragraph_text(child)).strip()
        normalized_section = normalize_required_section_name(text)
        if normalized_section:
            insert_before.append(child)
            in_experience = normalized_section == "Professional Experience"
            experience_role_count = 0
            continue
        if in_experience and is_role_heading(text):
            experience_role_count += 1
            if experience_role_count > 1:
                insert_before.append(child)
            continue
        if text == "Education":
            in_experience = False

    for child in insert_before:
        current_children = list(body)
        index = current_children.index(child)
        previous = current_children[index - 1] if index > 0 else None
        if previous is not None and previous.tag == f"{W}p" and is_blank_paragraph(previous):
            normalize_separator_paragraph(previous)
            continue
        body.insert(index, make_separator_paragraph())

    tree.write(document_xml, encoding="utf-8", xml_declaration=True)

def apply_core_competency_row_spacing(document_xml: Path) -> None:
    tree = ET.parse(document_xml)
    root = tree.getroot()
    body = root.find(f"{W}body")
    if body is None:
        return

    children = list(body)
    core_index = None
    development_index = None
    for index, child in enumerate(children):
        if child.tag != f"{W}p":
            continue
        text = re.sub(r"\s+", " ", paragraph_text(child)).strip()
        if is_skills_section_heading(text):
            core_index = index
        elif text == "PROFESSIONAL DEVELOPMENT":
            development_index = index
            break

    if core_index is None or development_index is None or development_index <= core_index:
        return

    block = children[core_index + 1 : development_index]
    competency_rows = [
        child
        for child in block
        if child.tag == f"{W}p" and re.sub(r"\s+", " ", paragraph_text(child)).strip()
    ]
    if len(competency_rows) < 2:
        return

    for row in competency_rows[:-1]:
        current_children = list(body)
        row_index = current_children.index(row)
        next_child = current_children[row_index + 1] if row_index + 1 < len(current_children) else None
        if next_child is not None and next_child.tag == f"{W}p" and is_blank_paragraph(next_child):
            normalize_separator_paragraph(next_child, CORE_COMPETENCY_ROW_SEPARATOR_FONT_SIZE_HP)
            continue
        body.insert(row_index + 1, make_separator_paragraph(CORE_COMPETENCY_ROW_SEPARATOR_FONT_SIZE_HP))

    tree.write(document_xml, encoding="utf-8", xml_declaration=True)

def force_resume_visual_branding(document_xml: Path, header_title_line: str = "") -> None:
    tree = ET.parse(document_xml)
    paragraphs = tree.getroot().findall(f".//{W}p")
    title_paragraph = title_line_paragraph(paragraphs)
    next_company_line = False
    next_summary_line = False
    summary_company = ""

    for paragraph in paragraphs:
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        if not text:
            continue

        if paragraph is title_paragraph:
            if header_title_line and text != header_title_line:
                set_paragraph_text(paragraph, header_title_line)
                text = header_title_line
            set_paragraph_alignment(paragraph, "center")
            set_paragraph_spacing_values(paragraph, after="20")
            for run in paragraph.findall(f"{W}r"):
                r_pr = run.find(f"{W}rPr")
                if r_pr is None:
                    r_pr = ET.Element(f"{W}rPr")
                    run.insert(0, r_pr)
                set_run_font(r_pr, RESUME_FONT)
                set_run_size(r_pr, TITLE_LINE_FONT_SIZE_HP)
                set_bool_prop(r_pr, f"{W}b", False)
                set_bool_prop(r_pr, f"{W}bCs", False)
                set_bool_prop(r_pr, f"{W}i", False)
                set_bool_prop(r_pr, f"{W}iCs", False)
            continue

        section = normalize_required_section_name(text)
        if section:
            if text != section.upper():
                set_paragraph_text(paragraph, section.upper())
            for run in paragraph.findall(f"{W}r"):
                r_pr = run.find(f"{W}rPr")
                if r_pr is None:
                    r_pr = ET.Element(f"{W}rPr")
                    run.insert(0, r_pr)
                set_run_font(r_pr, RESUME_FONT)
                set_run_size(r_pr, SECTION_FONT_SIZE_HP)
                set_run_color(r_pr, BRAND_BLUE)
                set_bool_prop(r_pr, f"{W}b", True)
                set_bool_prop(r_pr, f"{W}bCs", True)
                set_bool_prop(r_pr, f"{W}i", False)
                set_bool_prop(r_pr, f"{W}iCs", False)
            next_company_line = False
            next_summary_line = False
            summary_company = ""
            continue

        if text == "Christian Estrada":
            for run in paragraph.findall(f"{W}r"):
                r_pr = run.find(f"{W}rPr")
                if r_pr is None:
                    r_pr = ET.Element(f"{W}rPr")
                    run.insert(0, r_pr)
                set_run_font(r_pr, RESUME_FONT)
                set_run_size(r_pr, NAME_FONT_SIZE_HP)
                set_run_color(r_pr, BRAND_BLUE)
                set_bool_prop(r_pr, f"{W}b", True)
                set_bool_prop(r_pr, f"{W}bCs", True)
            continue

        if is_role_heading(text):
            for run in paragraph.findall(f"{W}r"):
                run_text = "".join(t.text or "" for t in run.findall(f".//{W}t"))
                r_pr = run.find(f"{W}rPr")
                if r_pr is None:
                    r_pr = ET.Element(f"{W}rPr")
                    run.insert(0, r_pr)
                set_run_font(r_pr, RESUME_FONT)
                set_run_size(r_pr, BODY_FONT_SIZE_HP)
                if re.search(rf"(?:{'|'.join(MONTHS)})\s+\d{{4}}", run_text):
                    set_bool_prop(r_pr, f"{W}b", False)
                    set_bool_prop(r_pr, f"{W}bCs", False)
                    set_bool_prop(r_pr, f"{W}i", True)
                    set_bool_prop(r_pr, f"{W}iCs", True)
                else:
                    set_bool_prop(r_pr, f"{W}b", True)
                    set_bool_prop(r_pr, f"{W}bCs", True)
                    set_bool_prop(r_pr, f"{W}i", False)
                    set_bool_prop(r_pr, f"{W}iCs", False)
            next_company_line = True
            next_summary_line = False
            summary_company = ""
            continue

        if next_company_line:
            summary_company = text.split("|", 1)[0].strip()
            for run in paragraph.findall(f"{W}r"):
                r_pr = run.find(f"{W}rPr")
                if r_pr is None:
                    r_pr = ET.Element(f"{W}rPr")
                    run.insert(0, r_pr)
                set_run_font(r_pr, RESUME_FONT)
                set_run_size(r_pr, BODY_FONT_SIZE_HP)
                set_bool_prop(r_pr, f"{W}b", False)
                set_bool_prop(r_pr, f"{W}bCs", False)
                set_bool_prop(r_pr, f"{W}i", False)
                set_bool_prop(r_pr, f"{W}iCs", False)
                set_run_color(r_pr, BODY_GRAY)
            next_company_line = False
            next_summary_line = True
            continue

        if next_summary_line:
            if is_bullet(paragraph):
                next_summary_line = False
                summary_company = ""
                continue
            is_company_context = bool(summary_company and is_company_context_paragraph(summary_company, text))
            for run in paragraph.findall(f"{W}r"):
                r_pr = run.find(f"{W}rPr")
                if r_pr is None:
                    r_pr = ET.Element(f"{W}rPr")
                    run.insert(0, r_pr)
                set_run_font(r_pr, RESUME_FONT)
                set_run_size(r_pr, BODY_FONT_SIZE_HP)
                set_bool_prop(r_pr, f"{W}i", is_company_context)
                set_bool_prop(r_pr, f"{W}iCs", is_company_context)
            if is_company_context:
                continue
            next_summary_line = False
            summary_company = ""

    tree.write(document_xml, encoding="utf-8", xml_declaration=True)

def ensure_header_gap_after_contact(document_xml: Path) -> None:
    tree = ET.parse(document_xml)
    root = tree.getroot()
    body = root.find(f"{W}body")
    if body is None:
        return
    paragraphs = body.findall(f"{W}p")
    for index, paragraph in enumerate(paragraphs[:-1]):
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        next_text = re.sub(r"\s+", " ", paragraph_text(paragraphs[index + 1])).strip()
        if CONTACT_EMAIL not in text:
            continue
        if not next_text and index + 2 < len(paragraphs):
            following_text = re.sub(r"\s+", " ", paragraph_text(paragraphs[index + 2])).strip()
            if following_text.lower() == "professional summary":
                normalize_separator_paragraph(paragraphs[index + 1])
                tree.write(document_xml, encoding="utf-8", xml_declaration=True)
                return
        if next_text.lower() == "professional summary":
            body.insert(list(body).index(paragraph) + 1, make_separator_paragraph())
            tree.write(document_xml, encoding="utf-8", xml_declaration=True)
            return

def normalize_linkedin_hyperlink_targets(work_dir: Path) -> int:
    changed = 0
    for rels_path in work_dir.rglob("*.rels"):
        original = rels_path.read_text(encoding="utf-8")
        updated = re.sub(
            r'Target="(?:https?://(?:www\.)?)?linkedin\.com/in/cjne/?"',
            f'Target="{LINKEDIN_URL}"',
            original,
            flags=re.I,
        )
        if updated != original:
            rels_path.write_text(updated, encoding="utf-8", newline="")
            changed += 1
    return changed

def copy_visual_parts(work_dir: Path, visual_dir: Path) -> int:
    applied = 0
    for part in STYLE_PARTS:
        source = visual_dir / part
        target = work_dir / part
        if source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            applied += 1
    return applied

def apply_section_layout(work_document: Path, visual_document: Path) -> bool:
    work_tree = ET.parse(work_document)
    visual_tree = ET.parse(visual_document)
    work_body = work_tree.getroot().find(f"{W}body")
    visual_body = visual_tree.getroot().find(f"{W}body")
    if work_body is None or visual_body is None:
        return False
    work_sect = work_body.find(f"{W}sectPr")
    visual_sect = visual_body.find(f"{W}sectPr")
    if work_sect is None or visual_sect is None:
        return False

    for child in list(work_sect):
        if child.tag in SECTION_LAYOUT_TAGS:
            work_sect.remove(child)
    insert_at = 0
    for child in list(visual_sect):
        if child.tag in SECTION_LAYOUT_TAGS:
            work_sect.insert(insert_at, child)
            insert_at += 1

    work_tree.write(work_document, encoding="utf-8", xml_declaration=True)
    return True

def make_separator_paragraph(font_size_hp: str = SECTION_SEPARATOR_FONT_SIZE_HP) -> ET.Element:
    paragraph = ET.Element(f"{W}p")
    p_pr = ET.SubElement(paragraph, f"{W}pPr")
    spacing = ET.SubElement(p_pr, f"{W}spacing")
    set_single_spacing(spacing)

    run = ET.SubElement(paragraph, f"{W}r")
    r_pr = ET.SubElement(run, f"{W}rPr")
    set_run_font(r_pr, RESUME_FONT)
    set_run_size(r_pr, font_size_hp)
    text_node = ET.SubElement(run, f"{W}t")
    text_node.set(XML_SPACE, "preserve")
    text_node.text = " "
    return paragraph

def normalize_separator_paragraph(paragraph: ET.Element, font_size_hp: str = SECTION_SEPARATOR_FONT_SIZE_HP) -> None:
    for child in list(paragraph):
        if child.tag != f"{W}pPr":
            paragraph.remove(child)
    p_pr = paragraph.find(f"{W}pPr")
    if p_pr is None:
        p_pr = ET.Element(f"{W}pPr")
        paragraph.insert(0, p_pr)
    spacing = p_pr.find(f"{W}spacing")
    if spacing is None:
        spacing = ET.SubElement(p_pr, f"{W}spacing")
    set_single_spacing(spacing)

    run = ET.SubElement(paragraph, f"{W}r")
    r_pr = ET.SubElement(run, f"{W}rPr")
    set_run_font(r_pr, RESUME_FONT)
    set_run_size(r_pr, font_size_hp)
    text_node = ET.SubElement(run, f"{W}t")
    text_node.set(XML_SPACE, "preserve")
    text_node.text = " "

def is_blank_paragraph(paragraph: ET.Element) -> bool:
    return not re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()

def set_paragraph_spacing_values(paragraph: ET.Element, *, before: str = ZERO_SPACING, after: str = ZERO_SPACING) -> None:
    p_pr = paragraph.find(f"{W}pPr")
    if p_pr is None:
        p_pr = ET.Element(f"{W}pPr")
        paragraph.insert(0, p_pr)
    spacing = p_pr.find(f"{W}spacing")
    if spacing is None:
        spacing = ET.SubElement(p_pr, f"{W}spacing")
    for attr in ("beforeAutospacing", "afterAutospacing"):
        spacing.attrib.pop(w_attr(attr), None)
    spacing.set(w_attr("before"), before)
    spacing.set(w_attr("after"), after)
    spacing.set(w_attr("line"), SINGLE_LINE_SPACING)
    spacing.set(w_attr("lineRule"), "auto")

def set_paragraph_alignment(paragraph: ET.Element, value: str) -> None:
    p_pr = paragraph.find(f"{W}pPr")
    if p_pr is None:
        p_pr = ET.Element(f"{W}pPr")
        paragraph.insert(0, p_pr)
    jc = p_pr.find(f"{W}jc")
    if jc is None:
        jc = ET.SubElement(p_pr, f"{W}jc")
    jc.set(w_attr("val"), value)

def set_single_spacing(spacing: ET.Element) -> None:
    for attr in ("beforeAutospacing", "afterAutospacing"):
        spacing.attrib.pop(w_attr(attr), None)
    spacing.set(w_attr("before"), ZERO_SPACING)
    spacing.set(w_attr("after"), ZERO_SPACING)
    spacing.set(w_attr("line"), SINGLE_LINE_SPACING)
    spacing.set(w_attr("lineRule"), "auto")

def set_run_font(r_pr: ET.Element, font_name: str) -> None:
    fonts = r_pr.find(f"{W}rFonts")
    if fonts is None:
        fonts = ET.SubElement(r_pr, f"{W}rFonts")
    for attr in ("ascii", "hAnsi", "cs", "eastAsia"):
        fonts.set(w_attr(attr), font_name)

def set_run_size(r_pr: ET.Element, half_points: str) -> None:
    for tag in (f"{W}sz", f"{W}szCs"):
        size = r_pr.find(tag)
        if size is None:
            size = ET.SubElement(r_pr, tag)
        size.set(w_attr("val"), half_points)

def set_run_color(r_pr: ET.Element, color_value: str) -> None:
    color = r_pr.find(f"{W}color")
    if color is None:
        color = ET.SubElement(r_pr, f"{W}color")
    color.set(w_attr("val"), color_value)

def set_bool_prop(r_pr: ET.Element, tag: str, enabled: bool) -> None:
    element = r_pr.find(tag)
    if element is None:
        element = ET.SubElement(r_pr, tag)
    element.set(w_attr("val"), "1" if enabled else "0")

def w_attr(name: str) -> str:
    return f"{W}{name}"

def ensure_child(parent: ET.Element, tag: str) -> ET.Element:
    child = parent.find(tag)
    if child is None:
        child = ET.Element(tag)
        parent.insert(0, child)
    return child

def append_run(paragraph: ET.Element, text: str, *, italic: bool = False, bold: bool = False) -> None:
    run = ET.SubElement(paragraph, f"{W}r")
    r_pr = ET.SubElement(run, f"{W}rPr")
    set_run_font(r_pr, RESUME_FONT)
    set_bool_prop(r_pr, f"{W}b", bold)
    set_bool_prop(r_pr, f"{W}bCs", bold)
    set_bool_prop(r_pr, f"{W}i", italic)
    set_bool_prop(r_pr, f"{W}iCs", italic)
    text_node = ET.SubElement(run, f"{W}t")
    text_node.set(XML_SPACE, "preserve")
    text_node.text = text

def remove_runs(paragraph: ET.Element) -> None:
    for child in list(paragraph):
        if child.tag == f"{W}r":
            paragraph.remove(child)

def set_paragraph_text(paragraph: ET.Element, text: str) -> None:
    text_nodes = paragraph.findall(f".//{W}t")
    if not text_nodes:
        run = paragraph.find(f"{W}r")
        if run is None:
            run = ET.SubElement(paragraph, f"{W}r")
        text_node = ET.SubElement(run, f"{W}t")
        text_nodes = [text_node]
    text_nodes[0].text = text
    for text_node in text_nodes[1:]:
        text_node.text = ""

def find_render_docx_script() -> Path | None:
    if sys.platform == "win32":
        local_override = PROJECT_ROOT / "scripts" / "render_docx_windows.py"
        if local_override.exists():
            return local_override
    root = Path.home() / ".codex" / "plugins" / "cache" / "openai-primary-runtime" / "documents"
    if not root.is_dir():
        return None
    matches = sorted(root.glob("*/skills/documents/render_docx.py"))
    return matches[-1] if matches else None


def render_python_executable() -> str:
    candidates = [
        Path(sys.executable),
        Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "python" / "python.exe",
    ]
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate).lower()
        if key in seen or not candidate.exists():
            continue
        seen.add(key)
        result = subprocess.run(
            [str(candidate), "-c", "import pdf2image"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            return str(candidate)
    return sys.executable


def estimate_page_count_from_xml(
    document_xml: Path,
    *,
    body_size_hp: float = XML_CALIBRATION_BODY_HP,
    separator_size_hp: float = XML_CALIBRATION_SEPARATOR_HP,
) -> int:
    # Conservative fallback used only when visual rendering is unavailable.
    # Paragraph count alone can under-estimate dense resumes, so combine it
    # with a visible-word estimate. Oversized competency sections get a small
    # synthetic word penalty because they tend to wrap more in Word than raw
    # paragraph count suggests.
    root = ET.parse(document_xml).getroot()
    paragraph_count = 0
    blank_paragraph_count = 0
    word_count = 0
    competency_item_count = 0
    in_core_competencies = False
    for paragraph in root.findall(f".//{W}p"):
        text = re.sub(r"\s+", " ", paragraph_text(paragraph)).strip()
        if text:
            paragraph_count += 1
            word_count += len(re.findall(r"\b[\w+.#'-]+\b", text))
            if is_skills_section_heading(text):
                in_core_competencies = True
                continue
            if text == "Professional Development":
                in_core_competencies = False
                continue
            if in_core_competencies and ":" in text:
                _label, items_text = text.split(":", 1)
                competency_item_count += len(
                    [
                        item.strip()
                        for item in re.split(r"\s+\|\s+|;", items_text.strip())
                        if item.strip()
                    ]
                )
        else:
            blank_paragraph_count += 1
    overflow_competencies = max(0, competency_item_count - XML_COMPETENCY_TARGET)
    adjusted_word_count = word_count + (overflow_competencies * XML_OVERFLOW_COMPETENCY_WORD_PENALTY)
    safe_body_size_hp = max(body_size_hp, 0.1)
    safe_separator_size_hp = max(separator_size_hp, 0.0)
    adjusted_words_per_page = max(1, round(XML_WORDS_PER_PAGE * XML_CALIBRATION_BODY_HP / safe_body_size_hp))
    adjusted_paragraphs_per_page = max(
        1,
        round(XML_PARAGRAPHS_PER_PAGE * XML_CALIBRATION_BODY_HP / safe_body_size_hp),
    )
    blank_adjustment = blank_paragraph_count * (1.0 - safe_separator_size_hp / XML_CALIBRATION_SEPARATOR_HP)
    effective_paragraph_count = max(0.0, paragraph_count - blank_adjustment)
    paragraph_estimate = max(1, math.ceil(effective_paragraph_count / adjusted_paragraphs_per_page))
    word_estimate = max(1, math.ceil(adjusted_word_count / adjusted_words_per_page))
    return max(1, paragraph_estimate, word_estimate)


def rendered_page_count(
    docx_path: Path,
    temp_root: Path,
    document_xml: Path | None = None,
    *,
    body_size_hp: float = XML_CALIBRATION_BODY_HP,
    separator_size_hp: float = XML_CALIBRATION_SEPARATOR_HP,
) -> int | None:
    render_script = find_render_docx_script()
    if render_script is None:
        if document_xml is not None:
            estimated = estimate_page_count_from_xml(
                document_xml,
                body_size_hp=body_size_hp,
                separator_size_hp=separator_size_hp,
            )
            print(f"Page count: estimated {estimated} pages (render unavailable, using XML fallback estimate)")
            return estimated
        return None
    output_dir = temp_root / f"render_{uuid.uuid4().hex}"
    output_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            render_python_executable(),
            str(render_script),
            str(docx_path),
            "--output_dir",
            str(output_dir),
        ],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        if detail:
            detail = detail.splitlines()[-1][:300]
            print(f"Render failure detail (exit {result.returncode}): {detail}")
        if document_xml is not None:
            estimated = estimate_page_count_from_xml(
                document_xml,
                body_size_hp=body_size_hp,
                separator_size_hp=separator_size_hp,
            )
            print(f"Page count: estimated {estimated} pages (render failed, using XML fallback estimate)")
            return estimated
        return None
    page_count = len(list(output_dir.glob("page-*.png")))
    if page_count == 0 and document_xml is not None:
        estimated = estimate_page_count_from_xml(
            document_xml,
            body_size_hp=body_size_hp,
            separator_size_hp=separator_size_hp,
        )
        print(f"Page count: estimated {estimated} pages (render produced no page images, using XML fallback estimate)")
        return estimated
    return page_count
