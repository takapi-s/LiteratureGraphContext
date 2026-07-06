"""Provider factory."""

from __future__ import annotations

from litgraph.extractor.providers.anthropic import AnthropicProvider
from litgraph.extractor.providers.base import LLMProvider
from litgraph.extractor.providers.gemini import GeminiProvider
from litgraph.extractor.providers.ollama import OllamaProvider
from litgraph.extractor.providers.openai import OpenAIProvider


def get_provider(name: str, model: str | None = None) -> LLMProvider:
    providers = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "gemini": GeminiProvider,
        "ollama": OllamaProvider,
    }
    cls = providers.get(name.lower())
    if not cls:
        raise ValueError(f"Unknown LLM provider: {name}")
    return cls(model=model)
