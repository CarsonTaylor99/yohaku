"""Disk cache for LLM stage outputs.

Keyed by (book_id, chapter, stage, provider, model, density) so re-runs are cheap and
the intermediate JSON stays inspectable. Provider+model are in the key so switching a
task's binding produces a fresh entry rather than reusing another provider's output.
Book_id namespaces the cache so two books with the same chapter index don't collide.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from ..config import ROOT

CACHE_DIR = ROOT / "data" / "cache"

_SAFE_ID = re.compile(r"[^A-Za-z0-9_.-]+")


def _safe(book_id: str) -> str:
    """Sanitize a book_id to be a safe directory name."""
    cleaned = _SAFE_ID.sub("_", book_id).strip("._")
    return cleaned or "_book"


def _book_dir(book_id: str) -> Path:
    return CACHE_DIR / _safe(book_id)


def _key(chapter: int, stage: str, provider: str, model: str, density: int | None) -> str:
    raw = f"{chapter}|{stage}|{provider}|{model}|{density}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
    return f"ch{chapter:04d}_{stage}_{digest}.json"


def _path(
    book_id: str, chapter: int, stage: str, provider: str, model: str, density: int | None
) -> Path:
    return _book_dir(book_id) / _key(chapter, stage, provider, model, density)


def get(
    book_id: str,
    chapter: int,
    stage: str,
    provider: str,
    model: str,
    density: int | None = None,
) -> Any | None:
    p = _path(book_id, chapter, stage, provider, model, density)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def put(
    book_id: str,
    chapter: int,
    stage: str,
    provider: str,
    model: str,
    value: Any,
    density: int | None = None,
) -> None:
    p = _path(book_id, chapter, stage, provider, model, density)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def book_dir(book_id: str) -> Path:
    """Public accessor for orchestrator/cost meter to write sibling files (e.g. cost.json)."""
    p = _book_dir(book_id)
    p.mkdir(parents=True, exist_ok=True)
    return p
