"""Stage 4 — Beat detection + salience scoring.

Model returns JSON: ~3-8 key moments per chapter, each with a verbatim anchor snippet
(from the rewritten text, for placement), a description usable as an image-prompt seed,
a visual_score (0-1) and a narrative_score (0-1). Let the chapter decide the count.
"""
from __future__ import annotations

from ..models import Beat, Rewrite
from ..providers import Provider


def run_beats(provider: Provider, rewrite: Rewrite) -> list[Beat]:
    # TODO: prompt over rewritten text; request strict JSON; parse into Beats.
    raise NotImplementedError("run_beats")
