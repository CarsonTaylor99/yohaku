"""Anthropic / Claude provider. TODO: implement generate() against the Anthropic SDK."""
from __future__ import annotations

from .base import Provider


class AnthropicProvider(Provider):
    supports_image = False

    def generate(self, system: str, prompt: str, json_mode: bool = False) -> str:
        # TODO: call the Anthropic Messages API with self.model + self.api_key.
        # Use prompt caching for the carried-forward context object.
        raise NotImplementedError("AnthropicProvider.generate")
