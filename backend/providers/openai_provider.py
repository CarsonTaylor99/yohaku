"""OpenAI / ChatGPT provider. supports_image=True (DALL·E / gpt-image-1).
TODO: implement generate() and generate_image() against the OpenAI SDK."""
from __future__ import annotations

from .base import Provider


class OpenAIProvider(Provider):
    supports_image = True

    def generate(self, system: str, prompt: str, json_mode: bool = False) -> str:
        # TODO: call the OpenAI Chat Completions / Responses API.
        raise NotImplementedError("OpenAIProvider.generate")

    def generate_image(self, prompt: str, **kwargs) -> bytes:
        # TODO: call the OpenAI image endpoint. Off-by-default (Tier 4).
        raise NotImplementedError("OpenAIProvider.generate_image")
