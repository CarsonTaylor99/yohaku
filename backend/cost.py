"""Cost meter + dry-run estimate (CLAUDE.md "Performance & cost UX").

Track per-book token usage/cost as stages run, and offer a pre-processing dry-run
estimate. Pricing is user-tunable — update PRICING as models or rates change.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

# Approximate prices per million tokens. Update as model pricing changes or new
# models get bound. Bindings that miss this map fall back to a generic mid-tier.
PRICING: dict[tuple[str, str], dict[str, float]] = {
    ("anthropic", "claude-haiku-4-5-20251001"): {"input": 1.0, "output": 5.0},
    ("anthropic", "claude-haiku-4-5"):           {"input": 1.0, "output": 5.0},
    ("anthropic", "claude-sonnet-4-6"):          {"input": 3.0, "output": 15.0},
    ("anthropic", "claude-sonnet-4-7"):          {"input": 3.0, "output": 15.0},
    ("anthropic", "claude-opus-4-7"):            {"input": 15.0, "output": 75.0},
    ("google",    "gemini-2.0-flash"):           {"input": 0.10, "output": 0.40},
    ("google",    "gemini-2.5-flash"):           {"input": 0.15, "output": 0.60},
    ("google",    "gemini-2.5-pro"):             {"input": 1.25, "output": 5.0},
    ("openai",    "gpt-4o"):                     {"input": 2.50, "output": 10.0},
    ("openai",    "gpt-4o-mini"):                {"input": 0.15, "output": 0.60},
    ("openai",    "gpt-4.1"):                    {"input": 2.00, "output": 8.0},
    ("openai",    "gpt-4.1-mini"):               {"input": 0.40, "output": 1.60},
}

_FALLBACK = {"input": 3.0, "output": 15.0}


def compute_usd(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
) -> float:
    """Approximate USD cost for one call.

    Treats cached input at 10% of the normal input rate (typical for Anthropic/OpenAI
    cache reads). Doesn't try to model cache-creation surcharges — slight under-count
    on first chapter, accurate enough thereafter.
    """
    # Ollama runs locally on the user's own hardware — no per-token cost. Tokens are
    # still tracked upstream for perf; the dollar figure is simply zero.
    if provider == "ollama":
        return 0.0

    rates = PRICING.get((provider, model), _FALLBACK)
    uncached_input = max(0, input_tokens - cached_input_tokens)
    return (
        uncached_input * rates["input"] / 1_000_000
        + cached_input_tokens * rates["input"] * 0.1 / 1_000_000
        + output_tokens * rates["output"] / 1_000_000
    )


@dataclass
class CostMeter:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    usd: float = 0.0
    by_task: dict[str, float] = field(default_factory=dict)

    def add(
        self,
        task: str,
        input_tokens: int,
        output_tokens: int,
        cached_input_tokens: int,
        usd: float,
    ) -> None:
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.cached_input_tokens += cached_input_tokens
        self.usd += usd
        self.by_task[task] = self.by_task.get(task, 0.0) + usd

    def to_dict(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_input_tokens": self.cached_input_tokens,
            "usd": round(self.usd, 6),
            "by_task": {k: round(v, 6) for k, v in self.by_task.items()},
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "CostMeter":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        m = cls(
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            cached_input_tokens=data.get("cached_input_tokens", 0),
            usd=data.get("usd", 0.0),
        )
        m.by_task = dict(data.get("by_task") or {})
        return m


def estimate_book(chapter_char_counts: list[int]) -> dict:
    """Dry-run estimate before processing a novel.

    Rough token estimate: ~4 chars/token for English, ~2 chars/token for Japanese.
    We use 3 as a midpoint and apply it across all stages. The numbers are a
    sanity check, not a quote.
    """
    total_chars = sum(chapter_char_counts)
    est_tokens = total_chars / 3
    # Context: ~ input only, small output (1k tokens of structured context)
    # Rewrite: input * density tiers, output ~ density * input
    # Beats (Tier 2) skipped here.
    return {
        "chapters": len(chapter_char_counts),
        "approx_input_tokens": int(est_tokens * 4),  # context (1x) + rewrite (3 tiers)
        "approx_output_tokens": int(est_tokens * 2.0),  # rewrite output ~ avg 67% across 100/60/40
        "note": "Rough estimate for budgeting only. Real cost depends on bound models and prompt caching.",
    }
