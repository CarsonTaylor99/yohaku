# 余白 · yohaku

A reading tool that re-paces Japanese light novels for readers who prefer manga's rhythm.
It transforms LN prose into tighter, manga-paced reading — with chapter-level context,
typographic pacing, salience-scored beats, and (later) sparse illustration support.

> *Yohaku* (余白) is the Japanese term for the intentional empty space in a composition —
> the breathing room this reader tries to give dense prose.

> **Status:** scaffolding. Interfaces and data flow are in place; the LLM pipeline stages
> are stubbed (`NotImplementedError`) and land per the build order below.

## Why

Typical translations/MTL work line-by-line and lose discourse-level context. Every LLM
stage here instead operates on a **full chapter** with an accumulated **running context**
of the story so far, so the model never works blind on an isolated line. On top of that,
the reader attacks *boredom*, not just length — typographic pacing, a dialogue-forward
mode, and a beat strip give prose the visual rhythm a manga page has.

## Stack

- **Backend:** Python + FastAPI — the text pipeline (parse → LLM stages → structured
  output) is the heart of it, and a backend cleanly serves the live controls.
- **Frontend:** lightweight static HTML/CSS/JS reader with live controls (density selector,
  dialogue-forward mode, beat strip, per-task provider toggles).
- Local, single-user, no auth.

### Per-task LLM routing

Every AI task (`context`, `rewrite`, `beats`, `translation`, `image`) is bound
independently to a `{provider, model}` pair via [`config/bindings.json`](config/bindings.example.json).
Rebind one task when a better model ships for that job — no other code changes.
Providers (Anthropic, Google, OpenAI) implement one thin interface; adding another is
one new class.

## Pipeline (per chapter)

1. **Parse** — EPUB/`.txt` → ordered chapters; extract insert illustrations + positions.
2. **Context pass** — structured running context, carried forward across chapters & volumes.
3. **Density rewrite** — pre-baked tiers (100/60/40%); tightens prose, never summarizes.
4. **Beat detection** — salience-scored key moments (visual + narrative).
5. **Image decision** — select beats above a threshold for image slots (generation is Tier 4, stubbed).
6. **Render** — reader UI with density selector, inline art, beat strip, continuity popovers.

## Getting started

```bash
python -m venv .venv && . .venv/Scripts/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env                                # add your API keys
cp config/bindings.example.json config/bindings.json
uvicorn backend.main:app --reload
```

Then open http://127.0.0.1:8000.

## Build order

- **Tier 1:** parse + context-carry + density rewrite + reader with typographic pacing.
- **Tier 2:** beat detection + beat strip + reader slots + continuity popovers.
- **Tier 3:** detect & place official insert art inline.
- **Tier 4 (stubbed):** AI image generation for selected beats.

## Note

Personal-use tool. It processes copyrighted text through LLM APIs for the user's own
reading; no source text or processed output is committed (see `.gitignore`). No
redistribution or sharing of processed text.
