"""Anthropic provider."""

from __future__ import annotations

import json
import os
from typing import Any, Dict

import anthropic

from .base import LLMProvider


class AnthropicProvider(LLMProvider):
    name = "anthropic"
    is_local = False

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.getenv("LLM_MODEL", "claude-3-5-sonnet-latest")
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def complete_json(self, system: str, user: str) -> Dict[str, Any]:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = response.content[0].text
        return json.loads(text)
