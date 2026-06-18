"""Thin provider interface. Every provider implements this; adding a new provider
later means one new subclass and nothing else changes (see CLAUDE.md)."""
from __future__ import annotations

import abc


class ProviderCapabilityError(RuntimeError):
    """Raised when a binding asks a provider to do something it can't (e.g. image gen)."""


class Provider(abc.ABC):
    """Base for all LLM providers.

    Concrete providers are constructed with a resolved model name + api key.
    `supports_image` advertises whether `generate_image` is usable, so a binding
    can be validated when it is set rather than failing deep in the pipeline.
    """

    supports_image: bool = False

    def __init__(self, model: str, api_key: str | None):
        self.model = model
        self.api_key = api_key

    @abc.abstractmethod
    def generate(self, system: str, prompt: str, json_mode: bool = False) -> str:
        """Return raw model text. When json_mode is True, request strict JSON.

        Callers parse defensively (strip code fences, retry/error on malformed output).
        """
        raise NotImplementedError

    def generate_image(self, prompt: str, **kwargs) -> bytes:
        """Return image bytes. Only providers with supports_image=True implement this."""
        raise ProviderCapabilityError(
            f"{type(self).__name__} (model {self.model!r}) does not support image generation"
        )
