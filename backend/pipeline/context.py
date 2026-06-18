"""Stage 2 — Context pass (load-bearing).

Model reads the FULL chapter and emits a structured ContextObject (running summary,
character roster, setting, tone/honorifics). The object is carried forward into every
subsequent chapter's stages and persisted across volumes. This is the fix for
line-by-line context loss; the model should never operate blind on an isolated line.
"""
from __future__ import annotations

from ..models import Chapter, ContextObject
from ..providers import Provider


def run_context(
    provider: Provider, chapter: Chapter, prior: ContextObject | None = None
) -> ContextObject:
    # TODO: prompt with full chapter text + prior context; request strict JSON;
    # parse defensively into ContextObject. Merge roster/glossary with `prior`.
    raise NotImplementedError("run_context")
