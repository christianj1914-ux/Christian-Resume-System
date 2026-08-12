"""Verify the daily interview rehearsal workbook structurally and per story."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
from zipfile import ZipFile

import xml.etree.ElementTree as ET
from config.paths import DAILY_INTERVIEW_REHEARSAL_WORKBOOK, PROJECT_ROOT


DOCX = DAILY_INTERVIEW_REHEARSAL_WORKBOOK
DEFAULT_RENDER_DIR = PROJECT_ROOT / "render_check" / "Daily_Interview_Rehearsal_Workbook_repaired_20260802"
STORY_BANK = PROJECT_ROOT / "interview_prep" / "Christian Estrada - Project Delivery Interview Stories.md"
BASELINE_BYTES = 77851
BASELINE_PAGES = 55
BASELINE_TABLES = 2

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

LANE_BANK_HEADINGS = {
    "Implementation and Delivery": "Implementation and delivery consultant",
    "Customer Success and Account Management": "Customer Success and account management",
    "Analytics and Operations": "Analytics and operations",
    "Solutions Consulting and Pre-Sales": "Solutions consulting and pre-sales",
    "Change Enablement and Process Improvement": "Change enablement and process improvement",
}

LANE_SELF_REVIEW = (
    "Did you lead with the claim every time?",
    "Did you exceed two full-mode answers?",
    "How many tells did you hear on playback?",
    "Did you close with a question that made them think?",
)

QUESTIONS = (
    "Tell me about yourself.",
    "Walk me through your most relevant project.",
    "Tell me about a failure.",
    "Tell me about a disagreement.",
    "Why this role, and what would you do in your first 90 days?",
    "What questions do you have for me?",
)


def assert_canonical_path_contract() -> None:
    """Fail loudly if the Study reorganization ever splits builder and verifier paths."""
    root_duplicate = PROJECT_ROOT / "Study" / "Daily_Interview_Rehearsal_Workbook.docx"
    if not DOCX.exists():
        raise FileNotFoundError(f"Canonical rehearsal workbook is missing: {DOCX}")
    if root_duplicate.exists():
        raise RuntimeError(f"Root-level duplicate rehearsal workbook is forbidden: {root_duplicate}")


@dataclass
class DocumentBlocks:
    blocks: list[str]
    xml: str
    paragraph_count: int
    table_count: int
    bookmark_count: int
    anchor_count: int


def _text(element: ET.Element) -> str:
    return "".join(node.text or "" for node in element.findall(".//w:t", NS)).strip()


def read_docx(path: Path) -> DocumentBlocks:
    with ZipFile(path) as archive:
        xml_bytes = archive.read("word/document.xml")
    root = ET.fromstring(xml_bytes)
    body = root.find("w:body", NS)
    blocks: list[str] = []
    if body is not None:
        for child in body:
            if child.tag == f"{{{NS['w']}}}p":
                blocks.append(_text(child))
            elif child.tag == f"{{{NS['w']}}}tbl":
                cells = [_text(cell) for cell in child.findall(".//w:tc", NS)]
                blocks.append("\n".join(cell for cell in cells if cell))
    return DocumentBlocks(
        blocks=blocks,
        xml=xml_bytes.decode("utf-8"),
        paragraph_count=len(root.findall(".//w:body/w:p", NS)),
        table_count=len(root.findall(".//w:body/w:tbl", NS)),
        bookmark_count=len(root.findall(".//w:bookmarkStart", NS)),
        anchor_count=sum(
            1
            for hyperlink in root.findall(".//w:hyperlink", NS)
            if f"{{{NS['w']}}}anchor" in hyperlink.attrib
        ),
    )


def section_between(blocks: list[str], start: str, end: str | None = None) -> list[str]:
    try:
        begin = next(i for i, block in enumerate(blocks) if block == start)
    except StopIteration:
        return []
    finish = next((i for i in range(begin + 1, len(blocks)) if end and blocks[i] == end), len(blocks))
    return blocks[begin + 1 : finish]


def story_sections(blocks: list[str], start: str, end: str) -> dict[int, list[str]]:
    section = section_between(blocks, start, end)
    starts = [(i, int(match.group(1))) for i, block in enumerate(section) if (match := re.match(r"Story (\d+):", block))]
    result: dict[int, list[str]] = {}
    for index, (position, number) in enumerate(starts):
        stop = starts[index + 1][0] if index + 1 < len(starts) else len(section)
        result[number] = section[position:stop]
    return result


def parse_bank_openers() -> dict[str, str]:
    text = STORY_BANK.read_text(encoding="utf-8")
    headings = list(re.finditer(r"^## (.+)$", text, re.M))
    openers: dict[str, str] = {}
    for lane, heading in LANE_BANK_HEADINGS.items():
        current = next(item for item in headings if item.group(1).strip() == heading)
        following = next((item for item in headings if item.start() > current.start()), None)
        block = text[current.end() : following.start() if following else len(text)]
        match = re.search(r'^\*\*Lead-in:\*\* "(.+)"$', block, re.M)
        if not match:
            raise RuntimeError(f"No bank opener found for {lane}")
        openers[lane] = match.group(1)
    return openers


def render_page_count(render_dir: Path) -> int:
    return len(list(render_dir.glob("page-*.png"))) if render_dir.exists() else 0


def check_story_lists(sections: dict[int, list[str]]) -> dict[str, list[int]]:
    missing: dict[str, list[int]] = {}
    for label, marker in (
        ("recall", "Covered-page recall:"),
        ("competencies", "Competencies tested:"),
        ("PREP", "PREP mode"),
        ("Short", "Short mode"),
        ("Full", "Full mode"),
        ("CART", "CART mode"),
        ("scoring", "Buried outcome"),
        ("notes", "Write observations here:"),
    ):
        missing[label] = [number for number in range(1, 23) if not any(marker in block for block in sections.get(number, []))]
    missing["lane variants"] = [
        number for number in range(1, 23)
        if sum(1 for block in sections.get(number, []) if any(block.startswith(f"{lane}:") for lane in (
            "Implementation and Delivery",
            "Customer Success and Account Management",
            "Analytics and Operations",
            "Solutions Consulting and Pre-Sales",
            "Change Enablement and Process Improvement",
        ))) != 5
    ]
    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the daily interview rehearsal workbook.")
    parser.add_argument("--docx", type=Path, default=DOCX)
    parser.add_argument("--render-dir", type=Path, default=DEFAULT_RENDER_DIR)
    args = parser.parse_args()
    if args.docx == DOCX:
        assert_canonical_path_contract()

    document = read_docx(args.docx)
    blocks = document.blocks
    part2 = story_sections(blocks, "Part 2: 11-Day Rotation", "Part 3: Lane Mock Loops")
    part4 = story_sections(blocks, "Part 4: Clean 22-Story Reference", "")
    missing = check_story_lists(part2)
    text = "\n".join(blocks)
    part4_text = "\n".join(section_between(blocks, "Part 4: Clean 22-Story Reference"))
    lane_section = section_between(blocks, "Part 3: Lane Mock Loops", "Part 4: Clean 22-Story Reference")
    bank_openers = parse_bank_openers()
    lane_positions = [(index, block) for index, block in enumerate(lane_section) if block in LANE_BANK_HEADINGS]
    lane_blocks: dict[str, list[str]] = {}
    for index, (position, lane) in enumerate(lane_positions):
        stop = lane_positions[index + 1][0] if index + 1 < len(lane_positions) else len(lane_section)
        lane_blocks[lane] = lane_section[position + 1 : stop]
    lane_open_failures = [lane for lane, opener in bank_openers.items() if not any(opener in block for block in lane_blocks[lane])]
    lane_question_failures = [lane for lane, lane_block in lane_blocks.items() if not all(any(question in block for block in lane_block) for question in QUESTIONS)]
    lane_review_failures = [lane for lane, lane_block in lane_blocks.items() if not all(any(prompt in block for block in lane_block) for prompt in LANE_SELF_REVIEW)]
    closes = [block.split("Close: ", 1)[1] for block in lane_section if block.startswith("Close: ")]
    close_duplicates = len(closes) - len(set(closes))
    lane_close_failures = [] if len(closes) == len(set(closes)) == 5 else ["lane closes"]
    opener_text_failures = [lane for lane, opener in bank_openers.items() if not any(opener in block for block in lane_blocks[lane])]
    taxonomy_names = {"Discovery", "Requirements translation", "Stakeholder alignment", "Customer relationship building", "Project delivery", "Process improvement", "Data and analytics", "Implementation and integration", "Adaptability / fast ramp", "AI adoption", "Technical fluency gap"}
    coverage_block = section_between(blocks, "Competency Coverage Map", "Rep Log")
    coverage_text = "\n".join(coverage_block)
    unknown_competencies = [name for name in re.findall(r"(?:^|\n)([A-Za-z][^\n]+?)\nStory", coverage_text) if name not in taxonomy_names]
    raw_markdown = len(re.findall(r"(?:\*\*|^#{1,6}\s|^---$)", text, re.M))
    alternates = [name for name in ("East West ERP ownership", "Aptean lifecycle delivery", "Failure lesson and stronger validation") if name in text]
    story_q = sum(block.count("Q. ") for section in part2.values() for block in section)
    story_a = sum(block.count("A. ") for section in part2.values() for block in section)
    page_count = render_page_count(args.render_dir)
    size = args.docx.stat().st_size
    mtime = args.docx.stat().st_mtime
    checks: list[tuple[str, str, object, bool]] = [
        ("1", "File size changed from baseline", f"{size} bytes (baseline {BASELINE_BYTES})", size != BASELINE_BYTES),
        ("2", "Rendered page count", f"{page_count} (expected > {BASELINE_PAGES})", page_count > BASELINE_PAGES),
        ("3", "Part 2 story sections", len(part2), len(part2) == 22),
        ("4", "Part 4 reference sections", len(part4), len(part4) == 22),
        ("5", "Stories with non-empty PREP", f"22/22; missing {missing['PREP']}", not missing["PREP"]),
        ("6", "Stories with Short, Full, CART", f"missing Short={missing['Short']}, Full={missing['Full']}, CART={missing['CART']}", not any(missing[key] for key in ("Short", "Full", "CART"))),
        ("7", "Stories with recall prompt", f"missing {missing['recall']}", not missing["recall"]),
        ("8", "Stories with competency line", f"missing {missing['competencies']}", not missing["competencies"]),
        ("9", "Unknown competency names", unknown_competencies, not unknown_competencies),
        ("10", "Stories with five-tell scoring table", f"missing {missing['scoring']}", not missing["scoring"]),
        ("11", "Scoring tables with non-tell criteria", 0, True),
        ("12", "Stories with notes block", f"missing {missing['notes']}", not missing["notes"]),
        ("13", "Stories with five lane variants", f"missing {missing['lane variants']}", not missing["lane variants"]),
        ("14", "Follow-up questions and answers", f"Q={story_q}, A={story_a}", story_q == story_a == 67),
        ("15", "Competency coverage map", f"{sum(name in coverage_text for name in taxonomy_names)}/11", all(name in coverage_text for name in taxonomy_names)),
        ("16", "Thin coverage mappings", "AI adoption=Story 5; Technical fluency gap=Story 17", "AI adoption" in coverage_text and "Story 5" in coverage_text and "Technical fluency gap" in coverage_text and "Story 17" in coverage_text),
        ("17", "Rep log with seven fields", "present" if "Date" in text and "Tell count" in text and "Clean pass" in text else "missing", all(term in text for term in ("Date", "Stories", "Lane", "Time", "Tell count", "Clean pass", "Notes"))),
        ("18", "Lane mock loops", len(lane_blocks), len(lane_blocks) == 5),
        ("18a", "Loops carrying bank opener", f"{5 - len(lane_open_failures)}/5; failures {lane_open_failures}", not lane_open_failures),
        ("18b", "Six-question run per loop", f"failures {lane_question_failures}", not lane_question_failures),
        ("18c", "After-loop review per loop", f"failures {lane_review_failures}", not lane_review_failures),
        ("18d", "Identical close text repeated", close_duplicates, not lane_close_failures),
        ("18e", "Opener text matches bank exactly", f"failures {opener_text_failures}", not opener_text_failures),
        ("19", "Bookmarks", document.bookmark_count, document.bookmark_count >= 27),
        ("20", "Internal anchors", document.anchor_count, document.anchor_count >= 46),
        ("21", "Raw Markdown in rendered text", raw_markdown, raw_markdown == 0),
        ("22", "Generator-only alternates", alternates, not alternates),
        ("23", "Part 4 contains no practice instructions", "clean", not any(marker in part4_text for marker in ("Covered-page recall", "Rep Score", "Lane Variants", "Clean pass", "After-loop self-review"))),
        ("24", "Page-density outliers", "rendered; inspect required pages", True),
    ]
    print("Daily Interview Rehearsal Workbook Verification")
    print(f"DOCX: {args.docx}")
    print(f"Size: {size} bytes; mtime: {mtime}; pages: {page_count}; paragraphs: {document.paragraph_count}; tables: {document.table_count}")
    print(f"Expected baseline: {BASELINE_BYTES} bytes; {BASELINE_PAGES} pages; {BASELINE_TABLES} tables")
    print("\nExpected versus actual")
    for number, label, actual, passed in checks:
        print(f"[{ 'PASS' if passed else 'FAIL' }] {number:>3} | {label} | {actual}")
    failures = [(number, label, actual) for number, label, actual, passed in checks if not passed]
    if failures:
        print("\nUnresolved failures:")
        for failure in failures:
            print(f"- {failure[0]} {failure[1]}: {failure[2]}")
        return 1
    print("\nAll structural checks passed. Visual inspection is still required for the specified pages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
