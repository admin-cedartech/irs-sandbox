"""PDF ingestion + text extraction and section location."""
from __future__ import annotations

import io
import re
from typing import Optional

from pypdf import PdfReader


def extract_text_from_pdf(data: bytes) -> str:
    """Extract all text from a PDF byte stream."""
    reader = PdfReader(io.BytesIO(data))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
    return "\n".join(pages)


def locate_section(full_text: str, section: str) -> Optional[str]:
    """Return the slice of text starting at a given IRM section heading.

    Best-effort: finds the first occurrence of the section number as a heading
    and returns from there to the next same-or-higher-level section, or end.
    Returns None if the section is not found.
    """
    # Escape dots so "21.6.6.2.21" is matched literally.
    pat = re.compile(rf"(?m)^\s*{re.escape(section)}\b")
    match = pat.search(full_text)
    if not match:
        # Fall back to a looser search anywhere in the text.
        loose = re.search(re.escape(section), full_text)
        if not loose:
            return None
        start = loose.start()
    else:
        start = match.start()

    # Find the next top-level-ish section heading after start to bound the slice.
    tail = full_text[start + len(section):]
    next_heading = re.search(r"(?m)^\s*21\.6\.6\.\d", tail)
    if next_heading:
        end = start + len(section) + next_heading.start()
        return full_text[start:end]
    return full_text[start:]


def prepare_source_text(data: bytes, section: Optional[str] = None) -> str:
    """Extract text and optionally narrow to a target section.

    If the section can't be located, returns the full text so extraction can
    still proceed (the LLM + grounding guardrail handle the rest).
    """
    full = extract_text_from_pdf(data)
    if section:
        sliced = locate_section(full, section)
        if sliced:
            return sliced
    return full
