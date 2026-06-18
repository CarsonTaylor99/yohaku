"""FastAPI app — reader backend.

Serves the frontend reader and exposes endpoints for the live controls: per-task
provider/model bindings, density tiers, image-decision knobs, cost meter. Route
bodies are stubs for now (scaffolding); the pipeline lands behind them later.

Run: uvicorn backend.main:app --reload
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import TASKS, load_config

app = FastAPI(title="yohaku", description="Light-novel density reader")

config = load_config()

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/bindings")
def get_bindings() -> dict:
    """Current per-task provider/model bindings (the live-toggle source of truth)."""
    return {task: vars(b) for task, b in config.bindings.items()}


@app.put("/api/bindings/{task}")
def set_binding(task: str, provider: str, model: str) -> dict:
    """Rebind a single task without touching others. TODO: persist + validate capability."""
    if task not in TASKS:
        raise HTTPException(404, f"Unknown task {task!r}. Known: {list(TASKS)}")
    raise HTTPException(501, "set_binding not implemented yet")


@app.get("/api/books")
def list_books() -> list:
    # TODO: list ingested books under data/books with processing status.
    raise HTTPException(501, "list_books not implemented yet")


@app.post("/api/books/{book_id}/process")
def process_book(book_id: str) -> dict:
    # TODO: kick off the pipeline (with process-ahead queue) for this book.
    raise HTTPException(501, "process_book not implemented yet")


@app.get("/api/books/{book_id}/chapters/{index}")
def get_chapter(book_id: str, index: int) -> dict:
    # TODO: return baked rewrite tiers + beats + illustrations for the reader.
    raise HTTPException(501, "get_chapter not implemented yet")


@app.get("/api/books/{book_id}/cost")
def get_cost(book_id: str) -> dict:
    # TODO: return the running cost meter for this book.
    raise HTTPException(501, "get_cost not implemented yet")


# Serve the static reader UI at the root. Keep this mount last.
if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="frontend")
