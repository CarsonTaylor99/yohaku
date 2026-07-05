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

_SYSTEM_TEMPLATE = """You are RE-PACING a light novel chapter for a reader who finds dense \
prose tiring. You rewrite it as flowing in-scene prose at a target length. You are NOT a \
summarizer. The reader reads your output AS the story, line by line.

LENGTH TARGET (this is the most important instruction):
- The source chapter is {source_chars} characters.
- Your output must be approximately {target_chars} characters ({density}% of the source).
- This is a hard floor: output shorter than {min_chars} characters is a FAILURE. When unsure, \
write MORE, never less. Do not compress harder than asked.

What the {density}% level means:
- 100% = reproduce essentially the ENTIRE chapter. Every scene, every line of dialogue, every \
action. Change almost nothing except: split walls of text into shorter paragraphs, fix awkward \
phrasing, and cut only literal repetition. The length stays about the same as the source.
- 60% = keep ALL dialogue and ALL plot/action beats. Trim only long scenic description and \
repetitive internal monologue, by roughly a third.
- 40% = keep ALL dialogue and every plot beat; cut description and monologue harder — but still \
write full narrative prose, not notes.

ABSOLUTE RULES (violating these fails the task):
- NEVER summarize, recap, or narrate the story from the outside. BANNED sentence shapes: \
"X analyzed his surroundings", "he realized that...", "her panic was palpable", "concluding \
that...", "X noted the...". Instead, render the actual moment in-scene the way the author did.
- Preserve EVERY line of dialogue close to verbatim. Never fuse two spoken lines into a paraphrase. \
Keep the original speech punctuation (「」 or "").
- Keep the original narration voice, tense, names, and honorifics (use the carried context).

Input format: source paragraphs prefixed with [N] where N is a 1-based index.

Output: a single JSON array. Each element:
{{
  "text": "rewritten paragraph (full prose sentences, in-scene)",
  "source": [1-based source paragraph indices this rewrite covers],
  "kind": "dialogue" | "narration" | "beat"
}}

Where kind is:
- "dialogue" - paragraph is primarily a character speaking (contains 「...」 or "...").
- "beat" - short, set-apart emotional moment that should get extra breathing room.
- "narration" - everything else.

JSON only. No code fences. No commentary. Remember: aim for {target_chars} characters, err long."""


# Structured-output schema for the rewrite: a top-level ARRAY of paragraph objects.
# Passed to providers that support constrained decoding (Ollama) so small local models
# reliably emit the array instead of a single object. Cloud providers ignore it.
_REWRITE_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "source": {"type": "array", "items": {"type": "integer"}},
            "kind": {"type": "string", "enum": ["dialogue", "narration", "beat"]},
        },
        "required": ["text", "source", "kind"],
    },
}


def run_rewrite(
    provider: Provider, chapter: Chapter, context: ContextObject, density: int
) -> tuple[Rewrite, GenerateResult]:
    paragraphs, ranges = _split_paragraphs(chapter.text)
    if not paragraphs:
        return Rewrite(density=density, spans=[]), GenerateResult(text="")

    indexed = "\n\n".join(f"[{i + 1}] {p}" for i, p in enumerate(paragraphs))
    cached_system = _carried_block(context)
    source_chars = len(chapter.text)
    target_chars = round(source_chars * density / 100)
    system = _SYSTEM_TEMPLATE.format(
        density=density,
        source_chars=source_chars,
        target_chars=target_chars,
        min_chars=round(target_chars * 0.75),
    )

    result = provider.generate(
        system=system,
        prompt=indexed,
        json_mode=True,
        cached_system=cached_system,
        json_schema=_REWRITE_SCHEMA,
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
