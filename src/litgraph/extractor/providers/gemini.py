"""Google Gemini provider."""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from .base import LLMProvider


class GeminiProvider(LLMProvider):
    name = "gemini"
    is_local = False

    def __init__(self, model: str | None = None) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set")
        self._configured = False
        self._model_name = model or os.getenv("LLM_MODEL", "gemini-1.5-flash")
        self.model = None

    def _get_model(self):
        if self.model is None:
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            self.model = genai.GenerativeModel(self._model_name)
            self._configured = True
        return self.model

    def complete_json(self, system: str, user: str) -> Dict[str, Any]:
        model = self._get_model()
        response = model.generate_content(
            f"{system}\n\n{user}\n\nRespond with JSON only.",
            generation_config={"response_mime_type": "application/json"},
        )
        return json.loads(response.text or "{}")
