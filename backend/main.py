"""FastAPI app - reader backend.

Serves the frontend reader and exposes endpoints for the live controls: per-task
provider/model bindings, density tiers, image-decision knobs, cost meter.

Processing is synchronous for Tier 1 - one chapter at a time on the request thread.
The CLAUDE.md process-ahead queue is a later optimization once Tier 1 reads work end-to-end.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import cache
from .config import ROOT, TASKS, Binding, load_config
from .cost import CostMeter, estimate_book
from .models import ContextObject
from .pipeline.orchestrator import process_chapter
from .pipeline.parse import parse
from .providers.registry import _PROVIDERS

app = FastAPI(title="yohaku", description="Light-novel density reader")

config = load_config()

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
BOOKS_DIR = ROOT / "data" / "books"
BINDINGS_PATH = ROOT / "config" / "bindings.json"


# ---------- bindings ----------


class BindingUpdate(BaseModel):
    provider: str
    model: str


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/bindings")
def get_bindings() -> dict:
    """Current per-task provider/model bindings (the live-toggle source of truth)."""
    return {
        "bindings": {task: asdict(b) for task, b in config.bindings.items()},
        "density_tiers": config.density_tiers,
        "image_decision": config.image_decision,
        "process_ahead": config.process_ahead,
        "known_providers": list(_PROVIDERS.keys()),
        "tasks": list(TASKS),
    }


@app.put("/api/bindings/{task}")
def set_binding(task: str, update: BindingUpdate) -> dict:
    """Rebind a single task without touching others. Persists to bindings.json."""
    if task not in TASKS:
        raise HTTPException(404, f"Unknown task {task!r}. Known: {list(TASKS)}")
    cls = _PROVIDERS.get(update.provider)
    if cls is None:
        raise HTTPException(400, f"Unknown provider {update.provider!r}. Known: {list(_PROVIDERS)}")
    if task == "image" and not cls.supports_image:
        raise HTTPException(
            400,
            f"Provider {update.provider!r} doesn't support image generation; "
            "bind 'image' to a provider with supports_image=True.",
        )
    config.bindings[task] = Binding(provider=update.provider, model=update.model)
    _persist_bindings()
    return {"task": task, "binding": asdict(config.bindings[task])}


def _persist_bindings() -> None:
    out = {
        "_comment": "Saved by yohaku UI. Edit by hand or via PUT /api/bindings/{task}.",
        "bindings": {t: asdict(b) for t, b in config.bindings.items()},
        "density_tiers": config.density_tiers,
        "image_decision": config.image_decision,
        "process_ahead": config.process_ahead,
    }
    BINDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    BINDINGS_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------- books ----------

_SOURCE_EXTS = {".epub", ".txt"}


def _iter_books():
    """Yield (book_id, source_path) for every detectable book.

    Two layouts are accepted:
      - data/books/<id>/source.epub  (or source.txt) -> book_id = <id>
      - data/books/<name>.epub        (or .txt)       -> book_id = <name>

    The second is friendlier when you just drop a file in without renaming.
    """
    if not BOOKS_DIR.exists():
        return
    seen: set[str] = set()
    for entry in sorted(BOOKS_DIR.iterdir()):
        name = entry.name
        if name.startswith(".") or ":Zone.Identifier" in name:
            continue
        if entry.is_dir():
            for src_name in ("source.epub", "source.txt"):
                p = entry / src_name
                if p.exists():
                    book_id = entry.name
                    if book_id not in seen:
                        seen.add(book_id)
                        yield book_id, p
                    break
        elif entry.is_file() and entry.suffix.lower() in _SOURCE_EXTS:
            book_id = entry.stem
            if book_id not in seen:
                seen.add(book_id)
                yield book_id, entry


@app.get("/api/books")
def list_books() -> list[dict]:
    """List every detectable book with processing status."""
    out = []
    for book_id, _src in _iter_books():
        meta = _read_meta(book_id)
        out.append({
            "id": book_id,
            "title": (meta.get("title") if meta else None) or book_id,
            "chapters": meta.get("chapters", 0) if meta else 0,
            "processed": meta is not None,
        })
    return out


@app.post("/api/books/{book_id}/process")
def process_book(book_id: str) -> dict:
    """Run the pipeline over every chapter, caching as we go. Synchronous for Tier 1."""
    source = _find_source(book_id)
    chapters = parse(source)

    meter = CostMeter.load(_cost_path(book_id))
    prior_context: ContextObject | None = None

    for ch in chapters:
        print(f"[yohaku] processing {book_id} ch {ch.index + 1}/{len(chapters)}: {ch.title}", flush=True)
        bundle = process_chapter(config, book_id, ch, prior_context, meter)
        prior_context = bundle["context"]

    meta = {
        "title": book_id,
        "chapters": len(chapters),
        "chapter_titles": [ch.title for ch in chapters],
        "illustrations": [
            [{"src": ill.src, "position": ill.position} for ill in ch.illustrations]
            for ch in chapters
        ],
    }
    _meta_path(book_id).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    meter.save(_cost_path(book_id))

    return {
        "book_id": book_id,
        "chapters": len(chapters),
        "cost": meter.to_dict(),
    }


@app.get("/api/books/{book_id}/estimate")
def estimate(book_id: str) -> dict:
    """Pre-processing dry-run estimate (CLAUDE.md cost UX)."""
    source = _find_source(book_id)
    chapters = parse(source)
    return estimate_book([len(ch.text) for ch in chapters])


@app.get("/api/books/{book_id}/chapters/{index}")
def get_chapter(book_id: str, index: int) -> dict[str, Any]:
    """Return all baked density tiers + carried context for the reader to render."""
    meta = _read_meta(book_id)
    if meta is None:
        raise HTTPException(
            404,
            f"Book {book_id!r} hasn't been processed yet. "
            f"POST /api/books/{book_id}/process first.",
        )
    total = meta["chapters"]
    if not (0 <= index < total):
        raise HTTPException(404, f"Chapter {index} out of range 0..{total - 1}")

    rw = config.binding("rewrite")
    ctx = config.binding("context")

    rewrites: dict[str, Any] = {}
    for density in config.density_tiers:
        cached = cache.get(book_id, index, "rewrite", rw.provider, rw.model, density)
        if cached is None:
            raise HTTPException(
                404,
                f"Density {density}% not cached for chapter {index} - re-process the book.",
            )
        rewrites[str(density)] = cached

    return {
        "book_id": book_id,
        "index": index,
        "title": meta["chapter_titles"][index],
        "chapters_count": total,
        "rewrites": rewrites,
        "context": cache.get(book_id, index, "context", ctx.provider, ctx.model),
        "illustrations": meta.get("illustrations", [[]])[index] if index < len(meta.get("illustrations", [])) else [],
    }


@app.get("/api/books/{book_id}/cost")
def get_cost(book_id: str) -> dict:
    return CostMeter.load(_cost_path(book_id)).to_dict()


# ---------- helpers ----------


def _find_source(book_id: str) -> Path:
    for known_id, path in _iter_books():
        if known_id == book_id:
            return path
    raise HTTPException(
        404,
        f"No source for book {book_id!r}. Drop an .epub or .txt under data/books/ "
        f"as either data/books/{book_id}.epub or data/books/{book_id}/source.epub.",
    )


def _meta_path(book_id: str) -> Path:
    return cache.book_dir(book_id) / "meta.json"


def _cost_path(book_id: str) -> Path:
    return cache.book_dir(book_id) / "cost.json"


def _read_meta(book_id: str) -> dict | None:
    p = _meta_path(book_id)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


# Serve the static reader UI at the root. Keep this mount last.
if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="frontend")
