"""Configuration management for LiteratureGraph."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv

from litgraph.utils.workspace import DEFAULT_WORKSPACE, normalize_workspace_id, workspace_from_env

GLOBAL_CONFIG_DIR = Path.home() / ".litgraph"
GLOBAL_ENV_FILE = GLOBAL_CONFIG_DIR / ".env"
PROJECT_DIR_NAME = ".litgraph"

class ProjectNotFoundError(FileNotFoundError):
    """Raised when no initialized ``.litgraph`` project can be resolved."""

    def __init__(
        self,
        searched_from: Path,
        *,
        env_root: Optional[str] = None,
    ) -> None:
        self.searched_from = searched_from.resolve()
        self.env_root = env_root
        if env_root:
            message = (
                f"LITGRAPH_PROJECT_ROOT is set to {env_root!r} but no "
                f".litgraph/config.yaml exists there.\n\n"
                "Initialize the project:\n"
                f"  cd {env_root}\n"
                "  litgraph init --papers-dir ./papers"
            )
        else:
            message = (
                f"No LiteratureGraph project found (searched from {self.searched_from}).\n\n"
                "Initialize a project in your repository:\n"
                f"  cd {self.searched_from}\n"
                "  litgraph init --papers-dir ./papers"
            )
        super().__init__(message)


DEFAULT_PROJECT_CONFIG: Dict[str, Any] = {
    "papers_dir": "examples/papers",
    "database": "kuzu",
    "neo4j_uri": "bolt://localhost:7687",
    "neo4j_user": "neo4j",
    "neo4j_password": "",
    "neo4j_database": "neo4j",
    "llm_provider": "openai",
    "llm_model": "gpt-4o-mini",
    "confirm_external_api": True,
    "ollama_base_url": "http://localhost:11434",
    "ollama_model": "llama3.2",
    "local_llm_recommendations": {
        "ollama": ["llama3.2", "mistral", "qwen2.5:7b"],
        "default_provider": "ollama",
    },
    "zotero_user_id": "",
    "zotero_api_key": "",
    "entity_resolution": {
        "auto_merge_threshold": 0.92,
        "candidate_threshold": 0.82,
        "disambiguation_enabled": True,
    },
}


@dataclass
class ResolvedContext:
    project_root: Path
    litgraph_dir: Path
    config: Dict[str, Any]
    db_path: Path
    cache_dir: Path
    workspace_id: str = DEFAULT_WORKSPACE

    @property
    def files_cache_path(self) -> Path:
        return self.cache_dir / "files.json"

    @property
    def parsed_cache_dir(self) -> Path:
        return self.cache_dir / "parsed"

    @property
    def extracted_cache_dir(self) -> Path:
        return self.cache_dir / "extracted"

    @property
    def bib_cache_dir(self) -> Path:
        return self.cache_dir / "bib"

    @property
    def papers_dir(self) -> Path:
        raw = self.config.get("papers_dir", "papers")
        path = Path(raw)
        if not path.is_absolute():
            path = self.project_root / path
        return path


def ensure_global_config_dir() -> None:
    GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (GLOBAL_CONFIG_DIR / "logs").mkdir(parents=True, exist_ok=True)


def load_env() -> None:
    ensure_global_config_dir()
    if GLOBAL_ENV_FILE.exists():
        load_dotenv(GLOBAL_ENV_FILE)
    litgraph_dir = find_project_litgraph_dir()
    if litgraph_dir is not None:
        local_env = litgraph_dir / ".env"
        if local_env.exists():
            load_dotenv(local_env, override=True)
    load_dotenv(override=True)


def _is_valid_project_dir(litgraph_dir: Path) -> bool:
    """True when ``litgraph_dir`` is an initialized project (has config.yaml)."""
    return (litgraph_dir / "config.yaml").is_file()


def _walk_up_litgraph_dir(start: Path) -> Optional[Path]:
    """Return initialized ``.litgraph`` directory by walking up from ``start``.

    Skips ``~/.litgraph`` (global config only, not a project).
    """
    global_dir = GLOBAL_CONFIG_DIR.resolve()
    current = start.resolve()
    for _ in range(10):
        candidate = (current / PROJECT_DIR_NAME).resolve()
        if (
            candidate != global_dir
            and candidate.is_dir()
            and _is_valid_project_dir(candidate)
        ):
            return candidate
        if current.parent == current:
            break
        current = current.parent
    return None


def find_project_litgraph_dir(cwd: Optional[Path] = None) -> Optional[Path]:
    start = cwd if cwd is not None else Path.cwd()
    return _walk_up_litgraph_dir(start)


def _validate_project_root(
    project_root: Path,
    *,
    env_root: Optional[str] = None,
) -> Path:
    litgraph_dir = project_root / PROJECT_DIR_NAME
    if not _is_valid_project_dir(litgraph_dir):
        raise ProjectNotFoundError(project_root, env_root=env_root)
    return project_root.resolve()


def resolve_project_root(cwd: Optional[Path] = None) -> Path:
    """Resolve the LGC project root for CLI and MCP.

    Priority:
    1. Explicit ``cwd`` argument (tests, programmatic callers)
    2. ``LITGRAPH_PROJECT_ROOT`` environment variable (MCP / IDE config)
    3. Walk up from the process cwd to find ``.litgraph/config.yaml``

    Raises:
        ProjectNotFoundError: No initialized project was found.
    """
    load_env()
    if cwd is not None:
        return _validate_project_root(cwd.resolve())

    env_root = os.getenv("LITGRAPH_PROJECT_ROOT", "").strip()
    if env_root:
        return _validate_project_root(
            Path(env_root).expanduser().resolve(),
            env_root=env_root,
        )

    litgraph_dir = find_project_litgraph_dir()
    if litgraph_dir is not None:
        return litgraph_dir.parent.resolve()

    raise ProjectNotFoundError(Path.cwd())


def resolve_context(
    cwd: Optional[Path] = None,
    *,
    workspace_id: Optional[str] = None,
) -> ResolvedContext:
    project_root = resolve_project_root(cwd)
    litgraph_dir = project_root / PROJECT_DIR_NAME
    ws = normalize_workspace_id(workspace_id or workspace_from_env())

    config = load_project_config(litgraph_dir)
    cache_dir = litgraph_dir / "cache" / ws
    legacy_cache = litgraph_dir / "cache"
    if ws == DEFAULT_WORKSPACE and not (cache_dir / "parsed").exists():
        if (legacy_cache / "parsed").exists() or (legacy_cache / "files.json").exists():
            cache_dir = legacy_cache
    db_path = litgraph_dir / "db" / "literature.kuzu"
    cache_dir.mkdir(parents=True, exist_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    (cache_dir / "parsed").mkdir(parents=True, exist_ok=True)
    (cache_dir / "extracted").mkdir(parents=True, exist_ok=True)
    (cache_dir / "bib").mkdir(parents=True, exist_ok=True)

    return ResolvedContext(
        project_root=project_root,
        litgraph_dir=litgraph_dir,
        config=config,
        db_path=db_path,
        cache_dir=cache_dir,
        workspace_id=ws,
    )


def load_project_config(litgraph_dir: Path) -> Dict[str, Any]:
    config_path = litgraph_dir / "config.yaml"
    if not config_path.exists():
        return DEFAULT_PROJECT_CONFIG.copy()
    with open(config_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    merged = DEFAULT_PROJECT_CONFIG.copy()
    merged.update(raw)
    return merged


def init_project(project_root: Path, papers_dir: Optional[str] = None) -> Path:
    litgraph_dir = project_root / PROJECT_DIR_NAME
    litgraph_dir.mkdir(parents=True, exist_ok=True)
    (litgraph_dir / "cache" / "parsed").mkdir(parents=True, exist_ok=True)
    (litgraph_dir / "cache" / "extracted").mkdir(parents=True, exist_ok=True)
    (litgraph_dir / "cache" / "bib").mkdir(parents=True, exist_ok=True)
    (litgraph_dir / "db").mkdir(parents=True, exist_ok=True)

    config_path = litgraph_dir / "config.yaml"
    if not config_path.exists():
        config = DEFAULT_PROJECT_CONFIG.copy()
        if papers_dir:
            config["papers_dir"] = _path_for_config(Path(papers_dir), project_root)
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)
    elif papers_dir:
        save_config_value(litgraph_dir, "papers_dir", papers_dir, project_root)

    return litgraph_dir


def _path_for_config(path: Path, project_root: Path) -> str:
    resolved = path.resolve()
    try:
        rel = resolved.relative_to(project_root.resolve())
        return str(rel)
    except ValueError:
        return str(resolved)


def save_config_value(
    litgraph_dir: Path,
    key: str,
    value: Any,
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    config = load_project_config(litgraph_dir)
    if key == "papers_dir" and project_root is not None:
        value = _path_for_config(Path(str(value)), project_root)
    config[key] = value
    config_path = litgraph_dir / "config.yaml"
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)
    return config


def save_papers_dir(ctx: ResolvedContext, papers_path: Path) -> str:
    stored = save_config_value(
        ctx.litgraph_dir,
        "papers_dir",
        papers_path,
        ctx.project_root,
    )
    ctx.config["papers_dir"] = stored["papers_dir"]
    return str(stored["papers_dir"])


def get_env_bool(key: str, default: bool = False) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def get_config_value(ctx: ResolvedContext, key: str, env_key: Optional[str] = None) -> Any:
    load_env()
    if env_key and os.getenv(env_key) is not None:
        return os.getenv(env_key)
    if key in ctx.config:
        return ctx.config[key]
    return DEFAULT_PROJECT_CONFIG.get(key)
