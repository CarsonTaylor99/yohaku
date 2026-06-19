"""OpenAI / ChatGPT provider. supports_image=True (gpt-image-1, Tier 4 stub)."""
from __future__ import annotations

from openai import OpenAI

from .base import GenerateResult, Provider


class OpenAIProvider(Provider):
    supports_image = True

    def __init__(self, model: str, api_key: str | None):
        super().__init__(model, api_key)
        self._client = OpenAI(api_key=api_key) if api_key else None

    def generate(
        self,
        system: str,
        prompt: str,
        json_mode: bool = False,
        cached_system: str | None = None,
    ) -> GenerateResult:
        if self._client is None:
            raise RuntimeError("OPENAI_API_KEY is not set; add it to .env")

        if json_mode:
            system = (
                system
                + "\n\nRespond with ONLY valid JSON. No commentary, no markdown code fences."
            )

        full_system = system if not cached_system else f"{system}\n\n{cached_system}"

        kwargs: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": full_system},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 16000,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = self._client.chat.completions.create(**kwargs)

        text = response.choices[0].message.content or ""
        usage = response.usage
        cached = 0
        details = getattr(usage, "prompt_tokens_details", None)
        if details is not None:
            cached = getattr(details, "cached_tokens", 0) or 0

        return GenerateResult(
            text=text,
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            cached_input_tokens=cached,
        )

    def generate_image(self, prompt: str, **kwargs) -> bytes:
        # Tier 4 stub — off by default; validate the text pipeline first.
        raise NotImplementedError("OpenAIProvider.generate_image (Tier 4 stub)")
