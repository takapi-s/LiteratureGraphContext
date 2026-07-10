"""Programmatic API context for LiteratureGraphContext."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from litgraph.cli import helpers
from litgraph.cli.config_manager import (
    ProjectNotFoundError,
    ResolvedContext,
    load_env,
    load_project_config,
    resolve_context,
)
from litgraph.ingest.dedup import resolve_existing_paper_id
from litgraph.ingest.registry import resolve_ingest_payload
from litgraph.parser.dispatcher import parse_file
from litgraph.query.paper_finder import PaperFinder
from litgraph.scanner.hash_cache import update_cache_entry
from litgraph.utils.paper_registry import assign_paper_id, update_registry_entry
from litgraph.utils.workspace import DEFAULT_WORKSPACE, normalize_workspace_id

INGEST_SUBDIR = "ingest"


def _ensure_cache_dirs(cache_path: Path) -> None:
    cache_path.mkdir(parents=True, exist_ok=True)
    (cache_path / "parsed").mkdir(parents=True, exist_ok=True)
    (cache_path / "extracted").mkdir(parents=True, exist_ok=True)
    (cache_path / "bib").mkdir(parents=True, exist_ok=True)


@dataclass
class IngestResult:
    paper_id: str
    source_path: str
    source_ref: Optional[str] = None
    parsed: bool = False
    extracted: bool = False
    built: bool = False
    skipped_extract: bool = False
    cancelled: bool = False
    errors: List[str] = field(default_factory=list)


class LitgraphContext:
    """Injectable, cwd-independent execution context for LGC."""

    def __init__(
        self,
        project_root: Optional[Union[str, Path]] = None,
        workspace_id: str = DEFAULT_WORKSPACE,
        config_overrides: Optional[Dict[str, Any]] = None,
        load_env_files: bool = True,
        graph_store: Any = None,
        cache_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        self.workspace_id = normalize_workspace_id(workspace_id)
        self._injected_store = graph_store

        if load_env_files:
            load_env()

        if project_root is not None:
            root = Path(project_root).expanduser().resolve()
            litgraph_dir = root / ".litgraph"
            if not (litgraph_dir / "config.yaml").is_file():
                raise ProjectNotFoundError(root)
            # Keep cache paths identical to CLI resolve_context (avoids split-brain
            # between legacy .litgraph/cache and .litgraph/cache/{workspace}).
            self._ctx = resolve_context(root, workspace_id=self.workspace_id)
            if config_overrides:
                self._ctx.config.update(config_overrides)
            if cache_dir is not None:
                cache_path = Path(cache_dir).resolve()
                _ensure_cache_dirs(cache_path)
                self._ctx = ResolvedContext(
                    project_root=self._ctx.project_root,
                    litgraph_dir=self._ctx.litgraph_dir,
                    config=self._ctx.config,
                    db_path=self._ctx.db_path,
                    cache_dir=cache_path,
                    workspace_id=self._ctx.workspace_id,
                )
            else:
                _ensure_cache_dirs(self._ctx.cache_dir)
        else:
            self._ctx = resolve_context(workspace_id=self.workspace_id)
            if config_overrides:
                self._ctx.config.update(config_overrides)
            if cache_dir is not None:
                cache_path = Path(cache_dir).resolve()
                _ensure_cache_dirs(cache_path)
                self._ctx = ResolvedContext(
                    project_root=self._ctx.project_root,
                    litgraph_dir=self._ctx.litgraph_dir,
                    config=self._ctx.config,
                    db_path=self._ctx.db_path,
                    cache_dir=cache_path,
                    workspace_id=self.workspace_id,
                )

    @classmethod
    def from_env(cls, **kwargs: Any) -> "LitgraphContext":
        """Create context using LITGRAPH_PROJECT_ROOT / cwd walk-up."""
        return cls(project_root=None, **kwargs)

    @property
    def ctx(self) -> ResolvedContext:
        return self._ctx

    @property
    def project_root(self) -> Path:
        return self._ctx.project_root

    @property
    def litgraph_dir(self) -> Path:
        return self._ctx.litgraph_dir

    def _ingest_dir(self) -> Path:
        path = self._ctx.litgraph_dir / INGEST_SUBDIR / self.workspace_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _rel_path(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(self._ctx.project_root))
        except ValueError:
            return str(path.resolve())

    def finder(self, *, read_only: bool = True) -> PaperFinder:
        return helpers._finder(self._ctx, read_only=read_only)

    def ingest_from_path(
        self,
        path: Union[str, Path],
        *,
        extract: bool = True,
        build: bool = True,
        skip_confirm: bool = True,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> IngestResult:
        file_path = Path(path).expanduser().resolve()
        if not file_path.is_file():
            raise FileNotFoundError(f"File not found: {path}")
        source_ref = f"file://{file_path}"
        return self._ingest_file(
            file_path,
            source_ref=source_ref,
            extract=extract,
            build=build,
            skip_confirm=skip_confirm,
            provider=provider,
            model=model,
        )

    def ingest_from_bytes(
        self,
        data: bytes,
        *,
        filename: str = "ingest.pdf",
        source_ref: Optional[str] = None,
        extract: bool = True,
        build: bool = True,
        skip_confirm: bool = True,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> IngestResult:
        ref = source_ref or f"bytes://{filename}"
        payload = resolve_ingest_payload(ref, data=data, filename=filename)
        dest = self._ingest_dir() / payload.filename
        dest.write_bytes(payload.data)
        return self._ingest_file(
            dest,
            source_ref=payload.source_ref,
            extract=extract,
            build=build,
            skip_confirm=skip_confirm,
            provider=provider,
            model=model,
            content_hash=hashlib.sha256(payload.data).hexdigest(),
        )

    def ingest_from_source_ref(
        self,
        source_ref: str,
        *,
        extract: bool = True,
        build: bool = True,
        skip_confirm: bool = True,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> IngestResult:
        payload = resolve_ingest_payload(source_ref)
        dest = self._ingest_dir() / payload.filename
        dest.write_bytes(payload.data)
        return self._ingest_file(
            dest,
            source_ref=payload.source_ref,
            extract=extract,
            build=build,
            skip_confirm=skip_confirm,
            provider=provider,
            model=model,
            content_hash=hashlib.sha256(payload.data).hexdigest(),
        )

    def _ingest_file(
        self,
        file_path: Path,
        *,
        source_ref: str,
        extract: bool,
        build: bool,
        skip_confirm: bool,
        provider: Optional[str],
        model: Optional[str],
        content_hash: str = "",
    ) -> IngestResult:
        rel = self._rel_path(file_path)
        if not content_hash:
            content_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()

        existing = resolve_existing_paper_id(
            self._ctx.litgraph_dir,
            workspace_id=self.workspace_id,
            source_ref=source_ref,
            content_hash=content_hash,
        )
        paper_id = existing or assign_paper_id(
            self._ctx.litgraph_dir,
            rel,
            content_hash,
            workspace_id=self.workspace_id,
            source_ref=source_ref,
        )
        update_registry_entry(
            self._ctx.litgraph_dir,
            rel,
            paper_id,
            content_hash,
            workspace_id=self.workspace_id,
            source_ref=source_ref,
        )
        update_cache_entry(
            self._ctx.files_cache_path,
            rel,
            content_hash,
            file_path.stat().st_size,
        )

        kind, parsed_id = parse_file(
            file_path,
            self._ctx.bib_cache_dir,
            self._ctx.parsed_cache_dir,
            litgraph_dir=self._ctx.litgraph_dir,
            project_root=self._ctx.project_root,
            content_hash=content_hash,
            source_ref=source_ref,
            workspace_id=self.workspace_id,
        )
        result = IngestResult(
            paper_id=parsed_id or paper_id,
            source_path=rel,
            source_ref=source_ref,
            parsed=kind in ("pdf", "md"),
        )
        if kind not in ("pdf", "md") or not parsed_id:
            return result

        if extract:
            extract_result = helpers.extract_paper_ids(
                self._ctx,
                [parsed_id],
                skip_confirm=skip_confirm,
                provider=provider,
                model=model,
                show_progress=False,
            )
            if extract_result.get("cancelled"):
                result.cancelled = True
                return result
            result.extracted = bool(extract_result.get("extracted"))
            result.skipped_extract = extract_result.get("skipped", 0) > 0 and not result.extracted
            if extract_result.get("failed"):
                result.errors.extend(
                    f"{item['paper_id']}: {item['error']}" for item in extract_result["failed"]
                )

        if build and (result.extracted or not extract):
            build_result = helpers.build_paper_graph(self._ctx)
            result.built = build_result.get("papers_indexed", 0) >= 0
        return result

    def search_papers(
        self,
        query: str,
        *,
        top_k: int = 10,
        center_paper_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        finder = self.finder(read_only=True)
        try:
            return finder.search_papers(query, top_k=top_k, center_paper_id=center_paper_id)
        finally:
            finder.close()

    def summarize_paper(self, paper_id: str) -> Dict[str, Any]:
        finder = self.finder(read_only=True)
        try:
            return finder.summarize_paper(paper_id)
        finally:
            finder.close()

    def compare_papers(self, paper_ids: List[str]) -> Dict[str, Any]:
        finder = self.finder(read_only=True)
        try:
            return finder.compare_papers(paper_ids)
        finally:
            finder.close()

    def find_limitations(
        self,
        *,
        topic: str = "",
        paper_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        finder = self.finder(read_only=True)
        try:
            return finder.find_limitations(topic=topic, paper_id=paper_id)
        finally:
            finder.close()

    def list_papers(self) -> List[Dict[str, Any]]:
        finder = self.finder(read_only=True)
        try:
            return finder.list_papers()
        finally:
            finder.close()

    def explore_paper_graph(
        self,
        paper_id: str,
        *,
        hops: int = 1,
        relationships: Optional[List[str]] = None,
        include_summary: bool = False,
    ) -> List[Dict[str, Any]]:
        finder = self.finder(read_only=True)
        try:
            return finder.explore_paper_graph(
                paper_id,
                hops=hops,
                relationships=relationships,
                include_summary=include_summary,
            )
        finally:
            finder.close()
