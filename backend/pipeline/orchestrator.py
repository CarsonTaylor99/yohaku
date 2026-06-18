"""Per-chapter pipeline orchestration.

Runs stages in order, carrying the ContextObject forward, pre-baking density tiers,
and caching every stage output. Resolves each task's provider via the binding map —
no stage hardcodes a provider/model.
"""
from __future__ import annotations

from ..config import Config
from ..models import Chapter, ContextObject
from ..providers import resolve
from .beats import run_beats
from .context import run_context
from .images import select_slots
from .rewrite import run_rewrite


def process_chapter(
    config: Config, chapter: Chapter, prior_context: ContextObject | None
) -> dict:
    """Process one chapter end to end. Returns a result bundle for the reader.

    TODO: wrap each stage call in the disk cache (backend.cache) keyed by
    (chapter, stage, provider, model, density). Pre-bake all config.density_tiers.
    """
    context = run_context(resolve(config, "context"), chapter, prior_context)

    rewrites = {
        density: run_rewrite(resolve(config, "rewrite"), chapter, context, density)
        for density in config.density_tiers
    }

    # Beats run on the canonical (100%) tier.
    canonical = rewrites[max(config.density_tiers)]
    beats = run_beats(resolve(config, "beats"), canonical)

    slots = select_slots(beats, **{k: v for k, v in config.image_decision.items() if k != "enabled"}) \
        if config.image_decision.get("enabled") else []

    return {
        "context": context,
        "rewrites": rewrites,
        "beats": beats,
        "image_slots": slots,
    }
