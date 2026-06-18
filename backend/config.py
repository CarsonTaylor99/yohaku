"""Configuration loading: env keys + per-task provider/model binding map.

The binding map is load-bearing (see CLAUDE.md "LLM providers: per-task routing").
Every AI task resolves its provider+model here; no stage hardcodes either.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent

# Task names known to the pipeline. Extend as the pipeline grows.
TASKS = ("context", "rewrite", "beats", "translation", "image")

ENV_KEYS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
}


@dataclass(frozen=True)
class Binding:
    provider: str
    model: str


@dataclass
class Config:
    bindings: dict[str, Binding]
    density_tiers: list[int] = field(default_factory=lambda: [100, 60, 40])
    image_decision: dict = field(default_factory=dict)
    process_ahead: int = 3

    def binding(self, task: str) -> Binding:
        if task not in self.bindings:
            raise KeyError(f"No binding configured for task {task!r}. Known: {list(self.bindings)}")
        return self.bindings[task]

    def api_key(self, provider: str) -> str | None:
        return os.environ.get(ENV_KEYS.get(provider, ""))


def load_config(path: str | os.PathLike | None = None) -> Config:
    """Load the binding map. Falls back to the committed example if no real config exists."""
    path = Path(path or os.environ.get("YOHAKU_BINDINGS") or ROOT / "config" / "bindings.json")
    if not path.exists():
        path = ROOT / "config" / "bindings.example.json"

    raw = json.loads(path.read_text(encoding="utf-8"))
    bindings = {task: Binding(**b) for task, b in raw["bindings"].items()}
    return Config(
        bindings=bindings,
        density_tiers=raw.get("density_tiers", [100, 60, 40]),
        image_decision=raw.get("image_decision", {}),
        process_ahead=raw.get("process_ahead", 3),
    )
