"""Maintain the editable canonical combined flashcard text without touching Anki binaries."""

from __future__ import annotations

from config.paths import STUDY_FLASHCARDS_DIR


INTERVIEW_SOURCE = STUDY_FLASHCARDS_DIR / "IT_Flashcards_InterviewStories.txt"
COMBINED = STUDY_FLASHCARDS_DIR / "IT_Flashcards_ALL.txt"
SENTINEL = "What makes a story a Builder story?"


def build() -> None:
    combined = COMBINED.read_text(encoding="utf-8")
    source = INTERVIEW_SOURCE.read_text(encoding="utf-8").strip()
    if SENTINEL in combined:
        return
    COMBINED.write_text(combined.rstrip() + "\n" + source + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()
