"""Cost meter + dry-run estimate (CLAUDE.md "Performance & cost UX").

Track per-book token usage/cost as stages run, and offer a pre-processing dry-run
estimate — important for long multi-volume series and token-conscious use.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CostMeter:
    input_tokens: int = 0
    output_tokens: int = 0
    usd: float = 0.0
    by_task: dict[str, float] = field(default_factory=dict)

    def add(self, task: str, input_tokens: int, output_tokens: int, usd: float) -> None:
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.usd += usd
        self.by_task[task] = self.by_task.get(task, 0.0) + usd


def estimate_book(chapter_char_counts: list[int]) -> dict:
    """Dry-run estimate before processing a novel.

    TODO: estimate tokens per stage from char counts and per-task model pricing,
    summing across density tiers. Return a per-task + total USD/token breakdown.
    """
    raise NotImplementedError("estimate_book")
