"""Per-chapter pipeline orchestration.

Runs stages in order, carrying the ContextObject forward, pre-baking density tiers,
and caching every stage output. Resolves each task's provider via the binding map -
no stage hardcodes a provider/model.

Tier 1: context + rewrite. Beats (Tier 2) and image generation (Tier 4) are skipped
here; the bundle still includes empty `beats` and `image_slots` so the API shape
stays stable when those stages land later.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .. import cache, cost
from ..config import Config
from ..models import Chapter, ContextObject, Rewrite, RewriteSpan, SourceSpan
from ..providers import resolve
from .context import run_context
from .rewrite import run_rewrite


def process_chapter(
    config: Config,
    book_id: str,
    chapter: Chapter,
    prior_context: ContextObject | None,
    meter: cost.CostMeter | None = None,
) -> dict[str, Any]:
    """Process one chapter end to end. Cache hits skip LLM calls and billing."""
    context = _stage_context(config, book_id, chapter, prior_context, meter)
    rewrites = _stage_rewrites(config, book_id, chapter, context, meter)

    return {
        "context": context,
        "rewrites": rewrites,
        "beats": [],          # Tier 2
        "image_slots": [],    # Tier 4
    }


def _stage_context(
    config: Config,
    book_id: str,
    chapter: Chapter,
    prior: ContextObject | None,
    meter: cost.CostMeter | None,
) -> ContextObject:
    binding = config.binding("context")
    cached = cache.get(
        book_id, chapter.index, "context", binding.provider, binding.model
    )
    if cached is not None:
        return ContextObject(**cached)

    provider = resolve(config, "context")
    context, result = run_context(provider, chapter, prior)

    cache.put(
        book_id, chapter.index, "context",
        binding.provider, binding.model, asdict(context),
    )
    if meter is not None:
        meter.add(
            "context",
            result.input_tokens, result.output_tokens, result.cached_input_tokens,
            cost.compute_usd(
                binding.provider, binding.model,
                result.input_tokens, result.output_tokens, result.cached_input_tokens,
            ),
        )
    return context


def _stage_rewrites(
    config: Config,
    book_id: str,
    chapter: Chapter,
    context: ContextObject,
    meter: cost.CostMeter | None,
) -> dict[int, Rewrite]:
    binding = config.binding("rewrite")
    rewrites: dict[int, Rewrite] = {}

    for density in config.density_tiers:
        cached = cache.get(
            book_id, chapter.index, "rewrite",
            binding.provider, binding.model, density,
        )
        if cached is not None:
            rewrites[density] = _hydrate_rewrite(cached)
            continue

        provider = resolve(config, "rewrite")
        rw, result = run_rewrite(provider, chapter, context, density)

        cache.put(
            book_id, chapter.index, "rewrite",
            binding.provider, binding.model, asdict(rw), density,
        )
        rewrites[density] = rw

        if meter is not None:
            meter.add(
                "rewrite",
                result.input_tokens, result.output_tokens, result.cached_input_tokens,
                cost.compute_usd(
                    binding.provider, binding.model,
                    result.input_tokens, result.output_tokens, result.cached_input_tokens,
                ),
            )
    return rewrites


def _hydrate_rewrite(data: dict) -> Rewrite:
    """Reconstruct a Rewrite from its asdict-ed cache form (nested dataclasses)."""
    spans = [
        RewriteSpan(
            text=s["text"],
            source=SourceSpan(**s["source"]),
            kind=s.get("kind", "narration"),
        )
        for s in data.get("spans", [])
    ]
    return Rewrite(density=data["density"], spans=spans)
