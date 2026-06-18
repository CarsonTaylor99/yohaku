# CLAUDE.md — Light Novel Reader / Simplifier

## What this project is

A personal reading tool that makes Japanese light novels more readable for someone who
prefers manga's pacing — too much prose at once is boring. The core move is to transform
LN prose into tighter, manga-paced reading, with optional sparse illustration support.

This is a **personal-use tool**. It processes copyrighted text through LLM APIs for the
user's own reading. Do not build distribution, sharing, or republishing features.

## Core principle: chapter-level context, never line-by-line

The central insight driving the whole design: typical translations/MTL work line-by-line
and lose discourse-level context, leaving the reader to decipher meaning. Every LLM stage
here works on a **full chapter** with an accumulated **running context** of the story so
far. The model should never operate blind on an isolated line. This matters for the density
rewrite now and for translation features later.

## Stack

**Open decision — choose pragmatically and document the choice in a top-level comment.**
Constraints to weigh:
- The text pipeline (parse → LLM stages → structured output) is the heart of it.
- The output is a clean, readable reader UI with a couple of live controls (see below).
- Should run locally, single user, no auth/multi-tenant concerns.
- Favor something maintainable by one person, easy to iterate on in Claude Code.

A Python pipeline emitting a self-contained HTML reader is a reasonable default; a
Python backend + lightweight frontend is also fine if the live controls justify it. Pick
one, justify it briefly, move on. Don't over-engineer.

## LLM providers: per-task routing (load-bearing)

Every AI-using task is independently bound to a provider + model, swappable by config and
ideally toggleable in the UI. This is a core requirement, not a nice-to-have: when a better
model ships for one specific job, the user wants to rebind *that task only* without touching
any other code. Do not use a single global provider switch.

**Provider abstraction.** A thin interface every provider implements, e.g.
`generate(system, prompt, json_mode: bool) -> str`, plus an image variant
`generate_image(prompt, ...)` for providers that support it. Implement at minimum:
- **Anthropic / Claude**
- **Google / Gemini**
- **OpenAI / ChatGPT**
Adding a new provider later = one new class implementing the interface. Nothing else changes.

**Task → binding map.** Maintain a config object mapping each AI task to
`{ provider, model }`. Tasks (extend as the pipeline grows):
- `context` — chapter context pass
- `rewrite` — density rewrite
- `beats` — beat detection / salience scoring
- `translation` — (planned) full-scene translation
- `image` — (Tier 4 stub) image generation

Resolve the binding per call; **no stage hardcodes a provider or model.** Not every provider
supports every task (e.g. image gen) — validate a binding is capable when it's set, and fail
with a clear message otherwise. Where it makes sense, expose these bindings as UI toggles so
the user can switch, say, translation between Claude / Gemini / ChatGPT live.

**Defaults for early testing** (override anytime via the binding map):
- `translation` → **Claude Haiku** (cheap tokens while iterating)
- Leave the others sensibly defaulted (cheap/fast tiers are fine for dev); the point is they
  are all config, not constants.

**Keys & config.** Read keys from env (`ANTHROPIC_API_KEY`, `GEMINI_API_KEY`,
`OPENAI_API_KEY`). Never commit keys. Model names are config, per binding. All structured
stages request strict JSON and parse defensively (strip code fences, retry or error clearly
on malformed output).

## Pipeline stages (per chapter)

1. **Parse** — Ingest EPUB (primary) and plain `.txt`. Split into an ordered chapter list.
   Extract official insert illustrations *and* their approximate position within the
   chapter's reading flow (normalized 0.0–1.0 based on where the `<img>` sits in the HTML).
   Clean prose to readable plaintext (strip markup, fix whitespace/entities).

2. **Context pass** — Model reads the full chapter and emits a structured context object:
   running summary, character roster (name → brief descriptor), current setting, tone /
   honorific conventions. This object is **carried forward** and fed into every subsequent
   chapter's stages. This is the line-by-line-context fix; treat it as load-bearing.

3. **Density rewrite** — Compress/tighten the prose at a chosen **density level** (e.g.
   100% / 60% / 40% of original length). Collapse purple description and redundant internal
   monologue; **preserve dialogue and plot beats**. Use the context object for name/tone
   consistency. Density is a **user-tunable knob**, not a fixed value.
   **Hard floor: the lowest density is still *tightened prose*, never a summary or synopsis.**
   The point is to make reading faster, not to replace reading. No "just tell me what
   happened" mode. If output starts reading like a plot recap, the floor is too low.

4. **Beat detection + salience scoring** — Model returns JSON: a list of key moments, each
   with an anchor snippet (verbatim from the rewritten text, for placement), a description
   usable as an image-prompt seed, a `visual_score` (0–1), and a `narrative_score` (0–1).
   Aim for ~3–8 beats/chapter; let the chapter decide.

5. **Image decision (salience-scored, NOT fixed cadence)** — Combine the two scores
   (visual weighted slightly higher) and select beats above a **threshold**, capped by a
   **max-per-chapter** limit. A quiet chapter may yield zero images; a climactic one,
   several. Both threshold and cap are user-tunable. **Do NOT key images to "pages"** —
   EPUB is reflowable and pages don't exist; key to beats/text anchors instead.
   For now, this stage only *decides and marks slots* and produces image prompts. Leave
   actual image generation as a clearly-marked, off-by-default stub (Tier 4). Validate the
   text pipeline first, then bolt on whichever image model is chosen.

6. **Render** — A clean reader UI showing the rewritten chapter, with:
   - a **density selector** (see pre-baked tiers below),
   - **inline official illustrations** placed at their extracted positions,
   - **placeholder slots** at selected beats where generated images will later go,
   - a **beat strip** (see Reading experience).

## Reading experience (on-thesis: attack the boredom, not just length)

The premise is that prose bores the reader where manga's pacing doesn't. Length is only part
of it — undifferentiated wall-of-text with no visual rhythm is the real problem. Prioritize:

- **Typographic pacing.** Render dialogue with clear speaker separation; give major emotional
  beats their own breathing room (short, set-apart lines); break long internal monologue into
  shorter visual chunks. This is mostly CSS/a formatting pass and likely does as much for
  readability as the density cut. High priority, cheap.
- **Dialogue-forward mode.** A reading mode (separate from the density slider) that foregrounds
  dialogue at full weight and demotes narration (lighter, smaller, optionally collapsible), so
  the eye locks onto the talking the way it does on a manga page.
- **Beat strip.** A horizontal row of cards at the top of each chapter rendering the
  salience-scored beats (stage 4) as a storyboard/contents-at-a-glance — the chapter's visual
  *shape* before reading a wall of text. Reuses stage-4 data; no extra LLM cost.
- **Continuity popovers (sleeper feature, nearly free).** The stage-2 context object is already
  generated — expose it. Tap a character name → "who is this, last seen doing X" from the
  running roster. Optional per-chapter "previously" recap and a spoiler-safe glossary of
  terms/places. Persist the glossary/roster **across volumes of a series**, not just one book,
  so later volumes don't re-introduce known characters.

Do **not** add a full-summary / synopsis mode — it defeats the purpose of reading (see the
density hard floor). No TTS/audio.

## Performance & cost UX (makes it usable daily)

- **Pre-baked density tiers.** Process 2–3 density tiers at processing time and store them;
  the slider switches between baked tiers instantly. Do **not** re-bill the LLM on every
  slider move. (Decided: pre-bake, don't live-regenerate.)
- **Process-ahead queue.** When reading chapter N, silently process N+1..N+a few in the
  background so the reader rarely hits a spinner.
- **Cost meter + dry-run estimate.** Show a running per-book token/cost readout, and offer a
  "estimate cost before processing this novel" dry run — important for long (multi-volume)
  series and token-conscious use.

## Data model requirements

- **Source addressability (bake in now, even though translation comes later).** Every output
  sentence/span must be able to point back to its original source span. Store the mapping from
  the start so a future toggle can reveal the original line under any rewritten/translated
  sentence (hover or tap). This is the trust mechanism for "is this weird line the author or
  the model?" — cheap to design in now, painful to retrofit.

## Caching

Cache every LLM stage's output to disk keyed by (chapter, stage, provider, model, density)
so re-runs are cheap and intermediate JSON is inspectable. Because each task is bound to its
own provider/model, include both in the key — switching a task's binding should produce a
fresh cache entry rather than silently reusing another provider's output. Iterating on
prompts should not re-bill the whole book.

## Build order (do not skip ahead)

- **Tier 1:** parse + context-carry + density rewrite (pre-baked tiers) + basic reader with
  typographic pacing. Ship this first.
- **Tier 2:** beat detection / salience JSON + beat strip + reader placeholder slots +
  continuity popovers (reuse stage-2 data).
- **Tier 3:** detect-and-place official insert art inline at correct positions.
- **Tier 4 (later, stubbed):** actual AI image generation for selected beats only.

## Explicit non-goals

- **Full LN→manga generation.** Not feasible now — the blocker is the director layer
  (paneling, sequential character consistency, legible bubbles), not just art quality.
  Don't attempt it.
- No fixed "one image per page" cadence (see stage 5).
- No redistribution / sharing of processed text.

## Notes / future hooks

- Translation is a planned downstream feature; the chapter-level context design exists
  partly to serve it (translate with full-scene context, not line-by-line). Keep stage
  boundaries clean so a translation stage can slot in alongside the rewrite.
- Honorifics and Japanese name order/tone should be preserved by the context+tone fields.
