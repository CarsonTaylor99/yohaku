"""Ollama / local-model provider.

Talks to a locally running Ollama server over its REST API (`/api/chat`). No API key
and no per-token cost — the "key" slot is repurposed as the server base URL (OLLAMA_HOST).

Two things matter here that don't for the cloud providers:

- **num_ctx must be set explicitly and large.** Ollama defaults to a small context window
  (often 4096) and *silently truncates* anything past it. This project feeds a full chapter
  plus an accumulated running-context object into every call (CLAUDE.md "chapter-level
  context, never line-by-line"), so a small window would quietly gut the core design with no
  error. We pass an explicit large num_ctx (OLLAMA_NUM_CTX). The bound model must actually
  support a window that large.
- **No prompt caching API.** The Anthropic path caches the carried-forward context block;
  Ollama has no equivalent (it reuses KV cache implicitly when the prefix is stable). Since
  there is no bill, `cached_system` is just concatenated into the system prompt.
"""
from __future__ import annotations

import json
import os

import httpx

from .base import GenerateResult, Provider

_DEFAULT_HOST = "http://localhost:11434"
_DEFAULT_NUM_CTX = 16384
_DEFAULT_TIMEOUT = 600.0  # local generation (esp. first model load) is slow; be generous


class OllamaProvider(Provider):
    supports_image = False  # Ollama does not do image generation

    def __init__(self, model: str, api_key: str | None):
        # `api_key` carries the server base URL here (from OLLAMA_HOST), not a secret.
        super().__init__(model, api_key)
        self.base_url = (api_key or os.environ.get("OLLAMA_HOST") or _DEFAULT_HOST).rstrip("/")
        self.num_ctx = int(os.environ.get("OLLAMA_NUM_CTX", _DEFAULT_NUM_CTX))
        self.timeout = float(os.environ.get("OLLAMA_TIMEOUT", _DEFAULT_TIMEOUT))

    def generate(
        self,
        system: str,
        prompt: str,
        json_mode: bool = False,
        cached_system: str | None = None,
        json_schema: dict | None = None,
    ) -> GenerateResult:
        if json_mode:
            system = (
                system
                + "\n\nRespond with ONLY valid JSON. No commentary, no markdown code fences."
            )

        # No caching API — the carried-forward context is just part of the system prompt.
        full_system = system if not cached_system else f"{system}\n\n{cached_system}"

        payload: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": full_system},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {"num_ctx": self.num_ctx},
        }
        # Structured outputs: a JSON schema in `format` constrains decoding to that exact
        # shape. Load-bearing for small local models — without it they tend to emit a
        # single object instead of the required top-level array. Falls back to plain
        # JSON mode when no schema is given.
        if json_schema is not None:
            payload["format"] = json_schema
        elif json_mode:
            payload["format"] = "json"

        try:
            response = httpx.post(
                f"{self.base_url}/api/chat", json=payload, timeout=self.timeout
            )
            response.raise_for_status()
        except httpx.ConnectError as e:
            raise RuntimeError(
                f"Cannot reach Ollama at {self.base_url}. Is it running? "
                "Start it with `ollama serve` (or set OLLAMA_HOST)."
            ) from e
        except httpx.HTTPStatusError as e:
            body = e.response.text[:500]
            raise RuntimeError(
                f"Ollama returned {e.response.status_code} for model {self.model!r}: {body}. "
                f"Is the model pulled? Try `ollama pull {self.model}`."
            ) from e

        data = response.json()
        text = data.get("message", {}).get("content", "") or ""
        # Ollama reports token counts; there is no cost, but tokens are useful for perf.
        return GenerateResult(
            text=text,
            input_tokens=data.get("prompt_eval_count", 0) or 0,
            output_tokens=data.get("eval_count", 0) or 0,
            cached_input_tokens=0,
        )
