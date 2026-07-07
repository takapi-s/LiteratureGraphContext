"""MCP tool response limits."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

DEFAULT_MAX_TOKENS = 8000


def get_max_tool_tokens() -> int:
    raw = os.getenv("MAX_TOOL_RESPONSE_TOKENS", "")
    if raw.isdigit():
        return int(raw)
    return DEFAULT_MAX_TOKENS


def truncate_results(data: Any, max_items: int = 50) -> Any:
    if isinstance(data, list) and len(data) > max_items:
        return data[:max_items] + [{"_truncated": True, "total": len(data)}]
    if isinstance(data, dict):
        for key in ("papers", "limitations", "claims", "results", "gaps"):
            if key in data and isinstance(data[key], list) and len(data[key]) > max_items:
                out = dict(data)
                out[key] = data[key][:max_items]
                out["_truncated"] = {"field": key, "total": len(data[key])}
                return out
    return data


def estimate_tokens(obj: Any) -> int:
    return len(json.dumps(obj, ensure_ascii=False)) // 4


def apply_response_token_limit(tool_name: str, response_text: str, max_tokens: Optional[int] = None) -> str:
    """Truncate JSON response text to approximate token budget."""
    limit = max_tokens or get_max_tool_tokens()
    if estimate_tokens(response_text) <= limit:
        return response_text
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        char_limit = limit * 4
        return response_text[:char_limit] + "\n... [truncated]"

    truncated = truncate_results(data, max_items=20)
    text = json.dumps(truncated, ensure_ascii=False, indent=2)
    if estimate_tokens(text) > limit:
        char_limit = limit * 4
        return text[:char_limit] + "\n... [truncated]"
    truncated["_response_truncated"] = True
    truncated["_tool"] = tool_name
    return json.dumps(truncated, ensure_ascii=False, indent=2)
