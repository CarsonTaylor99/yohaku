"""Stage 3 - Density rewrite.

Compress/tighten prose at a chosen density level. Collapse purple description and
redundant internal monologue; PRESERVE dialogue and plot beats. Use the ContextObject
for name/tone consistency. Density is user-tunable.

HARD FLOOR: the lowest density is still *tightened prose*, never a summary/synopsis.
If output reads like a plot recap, the floor is too low.

Source addressability: paragraph-level. We number source paragraphs, the LLM emits
each output paragraph with the list of source indices it covers, and we compute the
SourceSpan char range from the known source paragraph offsets. Char-level offsets
emitted by the LLM directly would be unreliable; paragraph indices are exact.
"""
from __future__ import annotations

import json
from dataclasses import asdict

from ..models import Chapter, ContextObject, Rewrite, RewriteSpan, SourceSpan
from ..providers import GenerateResult, Provider
from ..util import ModelJSONError, parse_json

_SYSTEM_TEMPLATE = """You are tightening the prose of a light novel chapter to roughly \
{density}% of its original length, for a reader who prefers manga's pacing.

HARD RULES (do not violate):
- Preserve all dialogue verbatim or near-verbatim. Never paraphrase character speech beyond minor cleanup.
- Preserve all plot beats and emotional moments.
- Collapse purple description, redundant internal monologue, and filler beats.
- Output is TIGHTENED PROSE in full sentences. Never a synopsis, never bullet points, never \
"X then Y then Z." If you find yourself summarizing, stop and rewrite as prose. The reader \
is reading a story, not a recap.
- Use the carried context for character names, honorifics, and tone consistency.

Input format: source paragraphs prefixed with [N] where N is a 1-based index.

Output: a single JSON array. Each element:
{{
  "text": "rewritten paragraph (full prose sentences)",
  "source": [1-based source paragraph indices this rewrite covers],
  "kind": "dialogue" | "narration" | "beat"
}}

Where kind is:
- "dialogue" - paragraph is primarily a character speaking (contains 「...」 or "...").
- "beat" - short, set-apart emotional moment that should get extra breathing room.
- "narration" - everything else.

Target: roughly {density}% of source character count. JSON only. No code fences. No commentary."""


def run_rewrite(
    provider: Provider, chapter: Chapter, context: ContextObject, density: int
) -> tuple[Rewrite, GenerateResult]:
    paragraphs, ranges = _split_paragraphs(chapter.text)
    if not paragraphs:
        return Rewrite(density=density, spans=[]), GenerateResult(text="")

    indexed = "\n\n".join(f"[{i + 1}] {p}" for i, p in enumerate(paragraphs))
    cached_system = _carried_block(context)
    system = _SYSTEM_TEMPLATE.format(density=density)

    result = provider.generate(
        system=system,
        prompt=indexed,
        json_mode=True,
        cached_system=cached_system,
    )

    data = parse_json(result.text)
    if not isinstance(data, list):
        raise ModelJSONError(
            f"Rewrite stage expected a JSON array, got {type(data).__name__}"
        )

    spans: list[RewriteSpan] = []
    full_end = len(chapter.text)
    for item in data:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        if not text:
            continue

        source_indices = item.get("source") or []
        if not isinstance(source_indices, list):
            source_indices = []
        valid = sorted(
            i - 1
            for i in source_indices
            if isinstance(i, int) and 1 <= i <= len(paragraphs)
        )
        if valid:
            char_start = ranges[valid[0]][0]
            char_end = ranges[valid[-1]][1]
        else:
            # Model didn't give us mappable indices - point at the whole chapter
            # rather than dropping the span. Trust mechanism degrades gracefully.
            char_start, char_end = 0, full_end

        kind = item.get("kind", "narration")
        if kind not in {"dialogue", "narration", "beat"}:
            kind = "narration"

        spans.append(
            RewriteSpan(
                text=text,
                source=SourceSpan(char_start=char_start, char_end=char_end),
                kind=kind,
            )
        )

    return Rewrite(density=density, spans=spans), result


def _split_paragraphs(text: str) -> tuple[list[str], list[tuple[int, int]]]:
    """Split on double-newline; return paragraphs + (char_start, char_end) for each.

    Walks the text manually so each paragraph's char_start/char_end are real offsets
    into `text`, valid for slicing chapter.text[char_start:char_end] later.
    """
    paragraphs: list[str] = []
    ranges: list[tuple[int, int]] = []
    cursor = 0
    for raw_para in text.split("\n\n"):
        if not raw_para:
            cursor += 2
            continue
        start = cursor
        end = cursor + len(raw_para)
        paragraphs.append(raw_para)
        ranges.append((start, end))
        cursor = end + 2
    return paragraphs, ranges


def _carried_block(ctx: ContextObject) -> str:
    payload = json.dumps(asdict(ctx), ensure_ascii=False, indent=2)
    return f"Carried context (names, tone, summary so far):\n\n{payload}"
