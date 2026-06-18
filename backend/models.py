"""Core data models shared across pipeline stages.

Source addressability (CLAUDE.md "Data model requirements") is baked in now:
every rewritten span carries a SourceSpan back to its original text, so a future
toggle can reveal the original line under any rewritten/translated sentence.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SourceSpan:
    """Pointer back into the original chapter text for one output span."""
    char_start: int
    char_end: int


@dataclass
class Illustration:
    """An official insert illustration plus its approximate position in reading flow."""
    src: str                 # original image reference / extracted path
    position: float          # normalized 0.0-1.0 within the chapter's flow


@dataclass
class Chapter:
    index: int
    title: str
    text: str                # cleaned plaintext
    illustrations: list[Illustration] = field(default_factory=list)


@dataclass
class ContextObject:
    """Stage 2 output, carried forward into every later stage and across volumes."""
    running_summary: str = ""
    characters: dict[str, str] = field(default_factory=dict)  # name -> brief descriptor
    setting: str = ""
    tone: str = ""           # tone / honorific conventions


@dataclass
class RewriteSpan:
    """One span of rewritten prose mapped back to its source (trust mechanism)."""
    text: str
    source: SourceSpan


@dataclass
class Rewrite:
    density: int             # e.g. 100 / 60 / 40
    spans: list[RewriteSpan] = field(default_factory=list)


@dataclass
class Beat:
    """Stage 4 salience-scored key moment."""
    anchor: str              # verbatim snippet from rewritten text, for placement
    description: str         # usable as an image-prompt seed
    visual_score: float      # 0-1
    narrative_score: float   # 0-1


@dataclass
class ImageSlot:
    """A beat selected for an image (Stage 5). Generation itself is Tier 4 / stubbed."""
    beat: Beat
    prompt: str
    image_path: str | None = None
