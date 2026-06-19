"""Stage 1 - Parse. EPUB (primary) + plain .txt -> ordered list of Chapters.

Extract official insert illustrations AND their approximate position within the
chapter's reading flow (normalized 0.0-1.0 from where the <img> sits in the HTML).
Clean prose to readable plaintext (strip markup, fix whitespace/entities).
"""
from __future__ import annotations

import re
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag
from ebooklib import ITEM_DOCUMENT, epub

from ..models import Chapter, Illustration

# Block-level tags that get a paragraph break after.
_BLOCK_TAGS = {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "section"}

# Spine items shorter than this (after cleaning) are assumed to be cover/copyright/TOC pages.
_MIN_CHAPTER_CHARS = 200

# Chapter heading patterns for .txt split: Japanese "第N章/話", "Chapter N", or
# markdown "# ...". Allows trailing title text on the same line, e.g. "Chapter 1: Foo".
_TXT_CHAPTER_RE = re.compile(
    r"^\s*(?:第[一二三四五六七八九十百千万0-9０-９]+[章話篇部]|Chapter\s+\d+|#{1,2}\s+).*$",
    re.MULTILINE,
)

# Minimum body length to keep a .txt chapter (skip stray heading-only TOC lines).
_MIN_TXT_CHAPTER_CHARS = 30


def parse(path: str | Path) -> list[Chapter]:
    suffix = Path(path).suffix.lower()
    if suffix == ".epub":
        return parse_epub(path)
    if suffix == ".txt":
        return parse_txt(path)
    raise ValueError(f"Unsupported source format: {suffix!r} (expected .epub or .txt)")


def parse_epub(path: str | Path) -> list[Chapter]:
    book = epub.read_epub(str(path))

    items_by_id = {item.id: item for item in book.get_items_of_type(ITEM_DOCUMENT)}
    ordered_items = []
    for spine_entry in book.spine:
        item_id = spine_entry[0] if isinstance(spine_entry, tuple) else spine_entry
        item = items_by_id.get(item_id)
        if item is not None:
            ordered_items.append(item)

    if not ordered_items:
        ordered_items = list(items_by_id.values())

    chapters: list[Chapter] = []
    for item in ordered_items:
        soup = BeautifulSoup(item.get_content(), "lxml")
        text, illustrations = _extract_text_and_images(soup)
        if len(text) < _MIN_CHAPTER_CHARS:
            continue
        title = _extract_title(soup) or f"Chapter {len(chapters) + 1}"
        chapters.append(
            Chapter(
                index=len(chapters),
                title=title,
                text=text,
                illustrations=illustrations,
            )
        )

    if not chapters:
        raise ValueError(f"No chapters found in {path!r} (all spine items below {_MIN_CHAPTER_CHARS} chars)")
    return chapters


def parse_txt(path: str | Path) -> list[Chapter]:
    raw = Path(path).read_text(encoding="utf-8")

    matches = list(_TXT_CHAPTER_RE.finditer(raw))
    if not matches:
        return [Chapter(index=0, title="Chapter 1", text=_normalize_whitespace(raw), illustrations=[])]

    chapters: list[Chapter] = []
    for i, m in enumerate(matches):
        title = m.group(0).strip().lstrip("#").strip()
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        body = _normalize_whitespace(raw[body_start:body_end])
        if len(body) < _MIN_TXT_CHAPTER_CHARS:
            continue
        chapters.append(
            Chapter(
                index=len(chapters),
                title=title,
                text=body,
                illustrations=[],
            )
        )

    if not chapters:
        return [Chapter(index=0, title="Chapter 1", text=_normalize_whitespace(raw), illustrations=[])]
    return chapters


def _extract_title(soup: BeautifulSoup) -> str | None:
    heading = soup.find(["h1", "h2", "h3"])
    if heading:
        text = heading.get_text(strip=True)
        if text:
            return text
    title_tag = soup.find("title")
    if title_tag:
        text = title_tag.get_text(strip=True)
        if text:
            return text
    return None


def _extract_text_and_images(soup: BeautifulSoup) -> tuple[str, list[Illustration]]:
    """Walk the document in order. Track text + <img> positions as fractions of raw length."""
    parts: list[str] = []
    img_positions: list[tuple[str, int]] = []  # (src, raw char pos when img encountered)

    def walk(node) -> None:
        if isinstance(node, NavigableString):
            parts.append(str(node))
            return
        if not isinstance(node, Tag):
            return
        name = node.name.lower() if node.name else ""
        if name == "img":
            src = node.get("src", "") or ""
            pos = sum(len(p) for p in parts)
            img_positions.append((src, pos))
            return
        if name == "br":
            parts.append("\n")
            return
        if name in {"script", "style"}:
            return
        for child in node.children:
            walk(child)
        if name in _BLOCK_TAGS:
            parts.append("\n\n")

    root = soup.body if soup.body else soup
    walk(root)

    raw_text = "".join(parts)
    total_raw = max(len(raw_text), 1)
    illustrations = [
        Illustration(src=src, position=min(1.0, pos / total_raw))
        for src, pos in img_positions
    ]
    return _normalize_whitespace(raw_text), illustrations


def _normalize_whitespace(text: str) -> str:
    """Collapse whitespace inside paragraphs; preserve paragraph breaks."""
    paragraphs: list[str] = []
    for raw_para in text.split("\n\n"):
        joined = " ".join(raw_para.split())
        if joined:
            paragraphs.append(joined)
    return "\n\n".join(paragraphs).strip()
