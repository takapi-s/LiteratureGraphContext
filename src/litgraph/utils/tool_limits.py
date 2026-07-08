"""MCP tool response limits and compact formatting."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

DEFAULT_MAX_TOKENS = 8000
EVIDENCE_TEXT_MAX_LEN = 200

COMPACT_TOOLS = frozenset({
    "compare_papers",
    "build_literature_matrix",
    "summarize_paper",
    "list_papers",
    "find_limitations",
})


def get_max_tool_tokens() -> int:
    raw = os.getenv("MAX_TOOL_RESPONSE_TOKENS", "")
    if raw.isdigit():
        value = int(raw)
        if value > 0:
            return value
    return DEFAULT_MAX_TOKENS


def _truncate_evidence_text(value: str, max_len: int = EVIDENCE_TEXT_MAX_LEN) -> str:
    if len(value) <= max_len:
        return value
    return value[: max_len - 3] + "..."


def _compact_evidence_items(items: Any) -> Any:
    if not isinstance(items, list):
        return items
    out = []
    for item in items:
        if not isinstance(item, dict):
            out.append(item)
            continue
        compact = dict(item)
        if "evidence_text" in compact and isinstance(compact["evidence_text"], str):
            compact["evidence_text"] = _truncate_evidence_text(compact["evidence_text"])
        for key in ("contributions", "limitations", "claims"):
            if key in compact and isinstance(compact[key], list):
                compact[key] = _compact_evidence_items(compact[key])
        out.append(compact)
    return out


def compact_tool_result(tool_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Reduce payload size for MCP responses."""
    if tool_name not in COMPACT_TOOLS:
        return data
    out = dict(data)
    for key in ("papers", "limitations"):
        if key in out and isinstance(out[key], list):
            out[key] = _compact_evidence_items(out[key])
    if "markdown_table" in out and isinstance(out["markdown_table"], str):
        if len(out["markdown_table"]) > 4000:
            out["markdown_table"] = out["markdown_table"][:3997] + "..."
    return out


def truncate_results(data: Any, max_items: int = 50) -> Any:
    if isinstance(data, list) and len(data) > max_items:
        return data[:max_items] + [{"_truncated": True, "total": len(data)}]
    if isinstance(data, dict):
        for key in ("papers", "limitations", "claims", "nodes", "results", "gaps"):
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
        return json.dumps(
            {"_truncated": True, "tool": tool_name, "preview": response_text[:char_limit]},
            ensure_ascii=False,
            indent=2,
        )

    truncated = truncate_results(data, max_items=20)
    text = json.dumps(truncated, ensure_ascii=False, indent=2)
    if estimate_tokens(text) > limit:
        char_limit = limit * 4
        return json.dumps(
            {"_truncated": True, "tool": tool_name, "preview": text[:char_limit]},
            ensure_ascii=False,
            indent=2,
        )
    truncated["_response_truncated"] = True
    truncated["_tool"] = tool_name
    return json.dumps(truncated, ensure_ascii=False, indent=2)
