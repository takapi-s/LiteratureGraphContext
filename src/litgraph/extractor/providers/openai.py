"""OpenAI provider."""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from openai import OpenAI

from .base import LLMProvider


class OpenAIProvider(LLMProvider):
    name = "openai"
    is_local = False

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def complete_json(self, system: str, user: str) -> Dict[str, Any]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)
