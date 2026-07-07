"""Configuration management for LiteratureGraph."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv

GLOBAL_CONFIG_DIR = Path.home() / ".litgraph"
GLOBAL_ENV_FILE = GLOBAL_CONFIG_DIR / ".env"
PROJECT_DIR_NAME = ".litgraph"

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
}


@dataclass
class ResolvedContext:
    project_root: Path
    litgraph_dir: Path
    config: Dict[str, Any]
    db_path: Path
    cache_dir: Path

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
    def aliases_path(self) -> Path:
        return self.litgraph_dir / "aliases.yaml"

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
    local_env = find_project_litgraph_dir() / ".env"
    if local_env.exists():
        load_dotenv(local_env, override=True)
    load_dotenv(override=True)


def find_project_litgraph_dir(cwd: Optional[Path] = None) -> Path:
    cwd = cwd or Path.cwd()
    current = cwd.resolve()
    for _ in range(10):
        candidate = current / PROJECT_DIR_NAME
        if candidate.is_dir():
            return candidate
        if current.parent == current:
            break
        current = current.parent
    return cwd.resolve() / PROJECT_DIR_NAME


def resolve_context(cwd: Optional[Path] = None, init: bool = False) -> ResolvedContext:
    cwd = cwd or Path.cwd()
    project_root = cwd.resolve()
    litgraph_dir = project_root / PROJECT_DIR_NAME

    if init or not litgraph_dir.exists():
        init_project(project_root)

    config = load_project_config(litgraph_dir)
    cache_dir = litgraph_dir / "cache"
    db_path = litgraph_dir / "db" / "literature.kuzu"
    cache_dir.mkdir(parents=True, exist_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    (litgraph_dir / "cache" / "parsed").mkdir(parents=True, exist_ok=True)
    (litgraph_dir / "cache" / "extracted").mkdir(parents=True, exist_ok=True)
    (litgraph_dir / "cache" / "bib").mkdir(parents=True, exist_ok=True)

    return ResolvedContext(
        project_root=project_root,
        litgraph_dir=litgraph_dir,
        config=config,
        db_path=db_path,
        cache_dir=cache_dir,
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

    aliases_path = litgraph_dir / "aliases.yaml"
    if not aliases_path.exists():
        with open(aliases_path, "w", encoding="utf-8") as f:
            yaml.safe_dump({
                "methods": {
                    "Graph Neural Network": ["GNN", "graph neural networks", "graph neural network"],
                    "Graph Attention Network": ["GAT", "graph attention", "graph attention network"],
                    "Graph Convolutional Network": [
                        "GCN",
                        "graph convolutional network",
                        "graph convolution",
                    ],
                },
                "datasets": {
                    "GPS trajectory": ["GPS trajectories", "trajectory data"],
                },
                "tasks": {
                    "Traffic prediction": [
                        "traffic forecasting",
                        "traffic prediction",
                        "交通予測",
                    ],
                    "Consumption prediction": [
                        "consumption forecasting",
                        "consumption prediction",
                        "消費予測",
                    ],
                    "Mobility prediction": [
                        "mobility forecasting",
                        "mobility prediction",
                        "人流予測",
                    ],
                },
            }, f)

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
