"""Stage 2 - Context pass (load-bearing).

Model reads the FULL chapter and emits a structured ContextObject (running summary,
character roster, setting, tone/honorifics). The object is carried forward into every
subsequent chapter's stages and persisted across volumes. This is the fix for
line-by-line context loss; the model should never operate blind on an isolated line.
"""
from __future__ import annotations

import json
from dataclasses import asdict

from ..models import Chapter, ContextObject
from ..providers import GenerateResult, Provider
from ..util import ModelJSONError, parse_json

_SYSTEM = """You extract structured story context from a light novel chapter. \
The context object is carried forward to all later chapters and across volumes - \
be precise, terse, and avoid spoilery future-tense claims.

Emit a single JSON object with exactly these fields:
{
  "running_summary": "A coherent up-to-now summary of the story so far, refreshed to include this chapter. Past tense. 3-6 sentences. Do not log per-chapter - emit one consolidated state.",
  "characters": { "Name": "brief role / current status descriptor", ... },
  "setting": "current place/situation as of the end of this chapter",
  "tone": "narration style, honorifics convention (e.g. 'casual first-person, retains -san/-chan')"
}

Roster rule: include EVERY character from the prior roster plus any new ones from this \
chapter. Update descriptors when their role/status changes. Do not drop known characters."""


def run_context(
    provider: Provider, chapter: Chapter, prior: ContextObject | None = None
) -> tuple[ContextObject, GenerateResult]:
    cached_system = _carried_block(prior) if prior else None
    user = f"Chapter {chapter.index + 1}: {chapter.title}\n\n{chapter.text}"

    result = provider.generate(
        system=_SYSTEM,
        prompt=user,
        json_mode=True,
        cached_system=cached_system,
    )

    data = parse_json(result.text)
    if not isinstance(data, dict):
        raise ModelJSONError(
            f"Context stage expected a JSON object, got {type(data).__name__}"
        )

    # Defensive roster merge: never lose a known character even if the model drops it.
    characters: dict[str, str] = dict(prior.characters) if prior else {}
    for name, descriptor in (data.get("characters") or {}).items():
        characters[str(name)] = str(descriptor).strip()

    obj = ContextObject(
        running_summary=str(data.get("running_summary", "")).strip(),
        characters=characters,
        setting=str(data.get("setting", "")).strip(),
        tone=str(data.get("tone", "")).strip(),
    )
    return obj, result


def _carried_block(prior: ContextObject) -> str:
    """Cached system block - Anthropic caches this; saves tokens on every chapter after ch 1."""
    payload = json.dumps(asdict(prior), ensure_ascii=False, indent=2)
    return (
        "Carried context from prior chapters - use it for character continuity, "
        "summary continuation, and tone preservation:\n\n"
        + payload
    )
