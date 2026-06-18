"""Google / Gemini provider. TODO: implement generate() against google-genai."""
from __future__ import annotations

from .base import Provider


class GeminiProvider(Provider):
    supports_image = False

    def generate(self, system: str, prompt: str, json_mode: bool = False) -> str:
        # TODO: call the Gemini API with self.model + self.api_key.
        raise NotImplementedError("GeminiProvider.generate")
