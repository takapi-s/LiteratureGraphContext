"""MCP tool response limits."""

from __future__ import annotations

import json
from typing import Any, Dict, List


def truncate_results(data: Any, max_items: int = 50) -> Any:
    if isinstance(data, list) and len(data) > max_items:
        return data[:max_items] + [{"_truncated": True, "total": len(data)}]
    if isinstance(data, dict):
        for key in ("papers", "limitations", "claims", "results"):
            if key in data and isinstance(data[key], list) and len(data[key]) > max_items:
                out = dict(data)
                out[key] = data[key][:max_items]
                out["_truncated"] = {"field": key, "total": len(data[key])}
                return out
    return data


def estimate_tokens(obj: Any) -> int:
    return len(json.dumps(obj, ensure_ascii=False)) // 4
