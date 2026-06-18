"""Stage 5 — Image decision (salience-scored, NOT fixed cadence).

Combine visual + narrative scores (visual weighted slightly higher), select beats
above a threshold, cap by max-per-chapter. A quiet chapter may yield zero; a climactic
one several. Do NOT key images to pages — EPUB is reflowable. Key to beats/text anchors.

For now this only DECIDES and MARKS slots + produces prompts. Actual generation is a
clearly-marked, off-by-default Tier 4 stub.
"""
from __future__ import annotations

from ..models import Beat, ImageSlot
from ..providers import Provider


def select_slots(
    beats: list[Beat],
    *,
    visual_weight: float = 0.6,
    narrative_weight: float = 0.4,
    threshold: float = 0.55,
    max_per_chapter: int = 4,
) -> list[ImageSlot]:
    scored = sorted(
        beats,
        key=lambda b: visual_weight * b.visual_score + narrative_weight * b.narrative_score,
        reverse=True,
    )
    slots: list[ImageSlot] = []
    for beat in scored:
        score = visual_weight * beat.visual_score + narrative_weight * beat.narrative_score
        if score < threshold or len(slots) >= max_per_chapter:
            break
        slots.append(ImageSlot(beat=beat, prompt=beat.description))
    return slots


def generate_images(provider: Provider, slots: list[ImageSlot]) -> list[ImageSlot]:
    # Tier 4 — OFF BY DEFAULT. Validate the text pipeline first.
    raise NotImplementedError("generate_images (Tier 4 stub)")
