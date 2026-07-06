"""LLM provider base interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class LLMProvider(ABC):
  name: str
  is_local: bool = False

  @abstractmethod
  def complete_json(self, system: str, user: str) -> Dict[str, Any]:
    ...
