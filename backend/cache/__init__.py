"""Disk cache for LLM stage outputs.

Keyed by (chapter, stage, provider, model, density) so re-runs are cheap and the
intermediate JSON stays inspectable. Provider+model are in the key so switching a
task's binding produces a fresh entry rather than reusing another provider's output.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ..config import ROOT

CACHE_DIR = ROOT / "data" / "cache"


def _key(chapter: int, stage: str, provider: str, model: str, density: int | None) -> str:
    raw = f"{chapter}|{stage}|{provider}|{model}|{density}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
    return f"ch{chapter:04d}_{stage}_{digest}.json"


def _path(chapter: int, stage: str, provider: str, model: str, density: int | None) -> Path:
    return CACHE_DIR / _key(chapter, stage, provider, model, density)


def get(chapter: int, stage: str, provider: str, model: str, density: int | None = None) -> Any | None:
    p = _path(chapter, stage, provider, model, density)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def put(chapter: int, stage: str, provider: str, model: str, value: Any, density: int | None = None) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    p = _path(chapter, stage, provider, model, density)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
