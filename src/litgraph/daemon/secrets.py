"""Read/write API keys and LLM settings for the daemon settings UI."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from litgraph.cli.config_manager import (
    GLOBAL_ENV_FILE,
    ResolvedContext,
    clear_env_value,
    ensure_global_config_dir,
    load_env,
    save_config_value,
    upsert_env_value,
)

SECRET_ENV_KEYS: tuple[str, ...] = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "ZOTERO_API_KEY",
    "ZOTERO_USER_ID",
)

_LLM_PROVIDERS = ("openai", "anthropic", "gemini", "ollama")


def _mask_secret(value: str) -> Optional[str]:
    raw = (value or "").strip()
    if not raw:
        return None
    if len(raw) <= 4:
        return "****"
    return f"…{raw[-4:]}"


def secrets_status(ctx: ResolvedContext) -> Dict[str, Any]:
    """Return configured flags and masked hints — never full secret values."""
    load_env()
    keys: Dict[str, Any] = {}
    for name in SECRET_ENV_KEYS:
        current = (os.getenv(name) or "").strip()
        keys[name] = {
            "configured": bool(current),
            "hint": _mask_secret(current),
        }
    return {
        "env_file": str(GLOBAL_ENV_FILE),
        "llm_provider": str(ctx.config.get("llm_provider") or "openai"),
        "llm_model": str(ctx.config.get("llm_model") or ""),
        "keys": keys,
    }


def apply_secrets_update(
    ctx: ResolvedContext,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Apply LLM config and optional secret writes to ``~/.litgraph/.env``.

    Blank secret fields are ignored (leave unchanged). Keys listed in
    ``clear`` are removed from the env file.
    """
    ensure_global_config_dir()
    load_env()

    provider = payload.get("llm_provider")
    if isinstance(provider, str) and provider.strip():
        name = provider.strip().lower()
        if name not in _LLM_PROVIDERS:
            raise ValueError(f"Unsupported llm_provider: {provider}")
        save_config_value(ctx.litgraph_dir, "llm_provider", name, ctx.project_root)
        ctx.config["llm_provider"] = name

    model = payload.get("llm_model")
    if isinstance(model, str) and model.strip():
        save_config_value(
            ctx.litgraph_dir, "llm_model", model.strip(), ctx.project_root
        )
        ctx.config["llm_model"] = model.strip()

    clear_keys = payload.get("clear")
    to_clear: List[str] = []
    if isinstance(clear_keys, list):
        to_clear = [str(k) for k in clear_keys if str(k) in SECRET_ENV_KEYS]

    for key in to_clear:
        clear_env_value(GLOBAL_ENV_FILE, key)

    for key in SECRET_ENV_KEYS:
        if key not in payload:
            continue
        raw = payload.get(key)
        if raw is None:
            continue
        value = str(raw).strip()
        if not value:
            continue
        upsert_env_value(GLOBAL_ENV_FILE, key, value)

    zotero_key = (os.getenv("ZOTERO_API_KEY") or "").strip()
    zotero_uid = (os.getenv("ZOTERO_USER_ID") or "").strip()
    if zotero_key and not zotero_uid:
        try:
            from litgraph.integrations.zotero import resolve_user_id_from_api_key

            uid = resolve_user_id_from_api_key(zotero_key)
            upsert_env_value(GLOBAL_ENV_FILE, "ZOTERO_USER_ID", uid)
        except Exception:
            pass

    return secrets_status(ctx)
