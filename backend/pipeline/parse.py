"""Stage 1 — Parse. EPUB (primary) + plain .txt -> ordered list of Chapters.

Extract official insert illustrations AND their approximate position within the
chapter's reading flow (normalized 0.0-1.0 from where the <img> sits in the HTML).
Clean prose to readable plaintext (strip markup, fix whitespace/entities).
"""
from __future__ import annotations

from pathlib import Path

from ..models import Chapter


def parse_epub(path: str | Path) -> list[Chapter]:
    # TODO: use ebooklib + BeautifulSoup. Walk spine in order; per document,
    # record <img> positions as normalized offsets into the text flow.
    raise NotImplementedError("parse_epub")


def parse_txt(path: str | Path) -> list[Chapter]:
    # TODO: split plaintext into chapters (heuristic / configurable delimiter).
    raise NotImplementedError("parse_txt")


def parse(path: str | Path) -> list[Chapter]:
    suffix = Path(path).suffix.lower()
    if suffix == ".epub":
        return parse_epub(path)
    if suffix == ".txt":
        return parse_txt(path)
    raise ValueError(f"Unsupported source format: {suffix!r} (expected .epub or .txt)")
