"""Resolve a task binding -> a constructed Provider instance.

This is the single place that maps provider names to classes. Adding a provider
means adding one line here. Binding capability is validated on resolve so an
incapable binding (e.g. image gen on a text-only provider) fails with a clear message.
"""
from __future__ import annotations

from ..config import Binding, Config
from .anthropic_provider import AnthropicProvider
from .base import Provider, ProviderCapabilityError
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider

_PROVIDERS: dict[str, type[Provider]] = {
    "anthropic": AnthropicProvider,
    "google": GeminiProvider,
    "openai": OpenAIProvider,
}


def get_provider(binding: Binding, api_key: str | None) -> Provider:
    cls = _PROVIDERS.get(binding.provider)
    if cls is None:
        raise KeyError(f"Unknown provider {binding.provider!r}. Known: {list(_PROVIDERS)}")
    return cls(model=binding.model, api_key=api_key)


def resolve(config: Config, task: str) -> Provider:
    """Resolve the provider for a task, validating capability for the task."""
    binding = config.binding(task)
    provider = get_provider(binding, config.api_key(binding.provider))
    if task == "image" and not provider.supports_image:
        raise ProviderCapabilityError(
            f"Task 'image' is bound to {binding.provider}/{binding.model}, "
            "which does not support image generation. Rebind to a capable provider."
        )
    return provider
