"""Stage 3 — Density rewrite.

Compress/tighten prose at a chosen density level. Collapse purple description and
redundant internal monologue; PRESERVE dialogue and plot beats. Use the ContextObject
for name/tone consistency. Density is user-tunable.

HARD FLOOR: the lowest density is still *tightened prose*, never a summary/synopsis.
If output reads like a plot recap, the floor is too low.
"""
from __future__ import annotations

from ..models import Chapter, ContextObject, Rewrite
from ..providers import Provider


def run_rewrite(
    provider: Provider, chapter: Chapter, context: ContextObject, density: int
) -> Rewrite:
    # TODO: prompt for tightened prose at `density`%. Emit spans with SourceSpan
    # mappings back into chapter.text (source addressability).
    raise NotImplementedError("run_rewrite")
