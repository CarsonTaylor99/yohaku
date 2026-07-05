"""Google / Gemini provider.

Caching: Gemini supports CachedContent but via a separate API surface; for Tier 1
the carried context is concatenated into the system instruction. TODO: wire
CachedContent when this binding gets used heavily.
"""
from __future__ import annotations

from google import genai
from google.genai import types

from .base import GenerateResult, Provider


class GeminiProvider(Provider):
    supports_image = False

    def __init__(self, model: str, api_key: str | None):
        super().__init__(model, api_key)
        self._client = genai.Client(api_key=api_key) if api_key else None

    def generate(
        self,
        system: str,
        prompt: str,
        json_mode: bool = False,
        cached_system: str | None = None,
        json_schema: dict | None = None,  # ignored — Gemini follows the array instruction
    ) -> GenerateResult:
        if self._client is None:
            raise RuntimeError("GEMINI_API_KEY is not set; add it to .env")

        full_system = system if not cached_system else f"{system}\n\n{cached_system}"

        config = types.GenerateContentConfig(
            system_instruction=full_system,
            response_mime_type="application/json" if json_mode else "text/plain",
        )

        response = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )

        usage = getattr(response, "usage_metadata", None)
        return GenerateResult(
            text=response.text or "",
            input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
            cached_input_tokens=getattr(usage, "cached_content_token_count", 0) or 0,
        )
