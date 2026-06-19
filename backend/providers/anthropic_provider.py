"""Anthropic / Claude provider.

Uses prompt caching on the carried-forward context block — that's the load-bearing
cost optimization (CLAUDE.md "Use prompt caching for the carried-forward context object").
"""
from __future__ import annotations

from anthropic import Anthropic

from .base import GenerateResult, Provider


class AnthropicProvider(Provider):
    supports_image = False

    def __init__(self, model: str, api_key: str | None):
        super().__init__(model, api_key)
        self._client = Anthropic(api_key=api_key) if api_key else None

    def generate(
        self,
        system: str,
        prompt: str,
        json_mode: bool = False,
        cached_system: str | None = None,
    ) -> GenerateResult:
        if self._client is None:
            raise RuntimeError("ANTHROPIC_API_KEY is not set; add it to .env")

        if json_mode:
            system = (
                system
                + "\n\nRespond with ONLY valid JSON. No commentary, no markdown code fences."
            )

        if cached_system:
            system_blocks: list[dict] | str = [
                {"type": "text", "text": system},
                {
                    "type": "text",
                    "text": cached_system,
                    "cache_control": {"type": "ephemeral"},
                },
            ]
        else:
            system_blocks = system

        response = self._client.messages.create(
            model=self.model,
            max_tokens=16000,
            system=system_blocks,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text
        usage = response.usage
        return GenerateResult(
            text=text,
            input_tokens=getattr(usage, "input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
            cached_input_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
        )
