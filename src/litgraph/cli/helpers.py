"""CLI command implementations."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from litgraph.cli.config_manager import ResolvedContext, get_config_value, resolve_context, save_papers_dir
from litgraph.core.jobs import JobManager, JobStatus
from litgraph.extractor.llm_extractor import extract_paper
from litgraph.extractor.providers import get_provider
from litgraph.graph.entity_catalog import EntityCatalog
from litgraph.graph.graph_builder import build_graph, _neo4j_config
from litgraph.graph.db_factory import get_graph_store
from litgraph.parser.dispatcher import collect_parse_targets, parse_file
from litgraph.parser.pdf_parser import EmptyPdfError
from litgraph.query.paper_finder import PaperFinder
from litgraph.parser.bib_linker import link_bib_to_paper
from litgraph.parser.bib_parser import load_all_bib_entries
from litgraph.scanner.file_scanner import discover_papers
from litgraph.scanner.hash_cache import find_removed_files, file_sha256, load_cache, remove_from_cache, scan_and_update
from litgraph.utils.paper_registry import assign_paper_id, get_paper_id_for_path, load_registry, save_registry
from litgraph.utils.ids import paper_id_from_path
from litgraph.utils.file_ready import wait_for_file_ready
from litgraph.utils.logging import get_logger
from litgraph.utils.paper_identity import load_paper_id_map, resolve_canonical_paper_id

console = Console()
_job_manager = JobManager()
EXTRACTION_MAX_RETRIES = 3
logger = get_logger(__name__)


def get_job_manager() -> JobManager:
    return _job_manager


def _finder(ctx: ResolvedContext, *, read_only: bool = True) -> PaperFinder:
    backend = str(get_config_value(ctx, "database", "LITGRAPH_DATABASE"))
    return PaperFinder(
        ctx.db_path,
        backend=backend,
        neo4j_config=_neo4j_config(ctx),
        read_only=read_only,
        project_config=ctx.config,
        workspace_id=ctx.workspace_id,
    )


def _graph_store(ctx: ResolvedContext):
    backend = str(get_config_value(ctx, "database", "LITGRAPH_DATABASE"))
    return get_graph_store(
        ctx.db_path,
        backend=backend,
        neo4j_config=_neo4j_config(ctx),
        workspace_id=ctx.workspace_id,
    )


def _rel_path(ctx: ResolvedContext, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ctx.project_root))
    except ValueError:
        return str(path.resolve())


def _try_parse_file(
    ctx: ResolvedContext,
    file_path: Path,
    *,
    file_cache: Dict[str, Any],
    wait_for_ready: bool = False,
) -> tuple[str, str, Optional[str]]:
    """Parse one file, returning (kind, paper_id, skip_reason)."""
    if wait_for_ready and not wait_for_file_ready(file_path):
        rel = _rel_path(ctx, file_path)
        if file_path.exists() and file_path.stat().st_size == 0:
            return "skip", "", f"empty file: {rel}"
        return "skip", "", f"file not ready: {rel}"

    rel = _rel_path(ctx, file_path)
    try:
        sha = file_sha256(file_path)
    except OSError as exc:
        logger.warning("Skipping %s: %s", rel, exc)
        return "skip", "", str(exc)
    try:
        kind, paper_id = parse_file(
            file_path,
            ctx.bib_cache_dir,
            ctx.parsed_cache_dir,
            litgraph_dir=ctx.litgraph_dir,
            project_root=ctx.project_root,
            content_hash=sha,
        )
    except (EmptyPdfError, OSError) as exc:
        logger.warning("Skipping %s: %s", rel, exc)
        return "skip", "", str(exc)
    except Exception as exc:
        if exc.__class__.__module__.startswith("fitz"):
            logger.warning("Skipping %s: %s", rel, exc)
            return "skip", "", str(exc)
        raise
    return kind, paper_id, None


def scan_papers(
    ctx: ResolvedContext,
    path: Optional[Path] = None,
    persist_dir: bool = True,
) -> Dict[str, Any]:
    target = (path or ctx.papers_dir).resolve()
    if persist_dir and path is not None:
        save_papers_dir(ctx, target)
    files = discover_papers(target)
    cache, changed = scan_and_update(files, ctx.files_cache_path, ctx.project_root)
    for file_path in files:
        if file_path.suffix.lower() in (".pdf", ".md"):
            rel = _rel_path(ctx, file_path)
            sha = (cache.get(rel) or {}).get("sha256", "")
            assign_paper_id(ctx.litgraph_dir, rel, sha, workspace_id=ctx.workspace_id)
    return {
        "total": len(files),
        "changed": len(changed),
        "files": [_rel_path(ctx, f) for f in files],
        "papers_dir": str(ctx.papers_dir),
    }


def parse_papers(ctx: ResolvedContext, only_changed: bool = True, *, verbose: bool = False) -> Dict[str, Any]:
    target = ctx.papers_dir
    ctx.bib_cache_dir.mkdir(parents=True, exist_ok=True)
    files = discover_papers(target)
    _, changed = scan_and_update(files, ctx.files_cache_path, ctx.project_root)
    to_parse = collect_parse_targets(files, only_changed, changed)
    file_cache = load_cache(ctx.files_cache_path)

    parsed_ids: List[str] = []
    bib_files = 0
    parse_details: List[Dict[str, Any]] = []
    for file_path in to_parse:
        kind, paper_id, skip_reason = _try_parse_file(ctx, file_path, file_cache=file_cache)
        if skip_reason:
            continue
        if kind in ("pdf", "md") and paper_id:
            parsed_ids.append(paper_id)
            if verbose and kind == "pdf":
                detail = _parse_verbose_detail(ctx, paper_id)
                if detail:
                    parse_details.append(detail)
        elif kind == "bib":
            bib_files += 1

    if verbose:
        for detail in parse_details:
            pid = detail.get("paper_id", "")
            sections = ", ".join(detail.get("sections") or []) or "(none)"
            fallback = detail.get("fallback_fulltext", False)
            ref_count = detail.get("reference_count", 0)
            line = f"  {pid}: sections=[{sections}] references={ref_count}"
            if fallback:
                console.print(f"[yellow]{line} (FullText fallback)[/yellow]")
            else:
                console.print(line)

    return {
        "parsed": len(parsed_ids),
        "bib_files": bib_files,
        "paper_ids": parsed_ids,
    }


def _parse_verbose_detail(ctx: ResolvedContext, paper_id: str) -> Optional[Dict[str, Any]]:
    path = ctx.parsed_cache_dir / f"{paper_id}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    meta = data.get("section_meta") or {}
    ref_meta = data.get("reference_meta") or {}
    return {
        "paper_id": paper_id,
        "sections": meta.get("section_names") or [s.get("name") for s in data.get("sections", [])],
        "fallback_fulltext": meta.get("fallback_fulltext", False),
        "reference_count": ref_meta.get("count", len(data.get("references") or [])),
    }


def _needs_extraction(ctx: ResolvedContext, paper_id: str, *, force: bool = False) -> bool:
    if force:
        return True
    extracted_path = ctx.extracted_cache_dir / f"{paper_id}.json"
    parsed_path = ctx.parsed_cache_dir / f"{paper_id}.json"
    if not extracted_path.exists():
        return True
    if not parsed_path.exists():
        return False

    try:
        parsed = json.loads(parsed_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return parsed_path.stat().st_mtime > extracted_path.stat().st_mtime

    content_hash = str(parsed.get("content_hash") or "")
    source_path = str(parsed.get("source_path") or "")
    if content_hash and source_path:
        cached_sha = (load_cache(ctx.files_cache_path).get(source_path) or {}).get("sha256", "")
        if cached_sha and content_hash == cached_sha:
            return False

    return parsed_path.stat().st_mtime > extracted_path.stat().st_mtime


def _should_skip_unchanged_parse(
    ctx: ResolvedContext,
    file_path: Path,
    *,
    file_cache: Dict[str, Any],
) -> bool:
    rel = _rel_path(ctx, file_path)
    try:
        sha = file_sha256(file_path)
    except OSError:
        return False
    cached_sha = (file_cache.get(rel) or {}).get("sha256", "")
    if not cached_sha or sha != cached_sha:
        return False
    paper_id = get_paper_id_for_path(
        ctx.litgraph_dir,
        rel,
        workspace_id=ctx.workspace_id,
    )
    if not paper_id:
        return False
    return (ctx.parsed_cache_dir / f"{paper_id}.json").exists()


def _confirm_external_api(ctx: ResolvedContext, provider_name: str, section_count: int, skip: bool) -> bool:
    if skip:
        return True
    confirm = get_config_value(ctx, "confirm_external_api")
    if isinstance(confirm, str):
        confirm = confirm.lower() in ("1", "true", "yes", "on")
    if not confirm:
        return True
    provider = get_provider(provider_name, model=str(get_config_value(ctx, "llm_model")))
    if provider.is_local:
        return True
    answer = console.input(
        f"Send {section_count} paper section(s) to external provider '{provider_name}'? [y/N]: "
    )
    return answer.strip().lower() in ("y", "yes")


def _run_extractions(
    ctx: ResolvedContext,
    parsed_docs: List[Dict[str, Any]],
    provider_name: str,
    model_name: Optional[str] = None,
    *,
    job_id: Optional[str] = None,
    show_progress: bool = False,
) -> Dict[str, Any]:
    extracted_ids: List[str] = []
    failed: List[Dict[str, str]] = []
    total = len(parsed_docs)

    def _extract_one(doc: Dict[str, Any], index: int) -> None:
        parse_paper_id = str(doc.get("paper_id", ""))
        if job_id:
            _job_manager.update_job(
                job_id,
                current_item=parse_paper_id,
                processed_items=index - 1,
                message=f"Extracting {parse_paper_id}",
            )

        bib_entries = load_all_bib_entries(ctx.bib_cache_dir)
        bib_match = link_bib_to_paper(
            parse_paper_id,
            doc.get("path"),
            doc.get("title"),
            bib_entries,
        )
        bib_doi = bib_match.get("doi") if bib_match else None

        last_error: Optional[Exception] = None
        entity_catalog = EntityCatalog.load(ctx.litgraph_dir, workspace_id=ctx.workspace_id)
        for attempt in range(1, EXTRACTION_MAX_RETRIES + 1):
            try:
                try:
                    extraction = extract_paper(
                        doc,
                        provider_name,
                        model=model_name,
                        doi=bib_doi,
                        entity_catalog=entity_catalog,
                    )
                except TypeError as exc:
                    # Backward-compatible for tests/mocks that patch extract_paper.
                    if "entity_catalog" not in str(exc):
                        raise
                    extraction = extract_paper(
                        doc,
                        provider_name,
                        model=model_name,
                        doi=bib_doi,
                    )
                data = extraction.model_dump()
                paper_id = str(data["paper_id"])
                out_path = ctx.extracted_cache_dir / f"{paper_id}.json"
                out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                extracted_ids.append(paper_id)
                if job_id:
                    _job_manager.update_job(job_id, processed_items=index)
                return
            except Exception as exc:
                last_error = exc
                if attempt < EXTRACTION_MAX_RETRIES:
                    console.print(
                        f"[yellow]Extraction failed for {parse_paper_id} "
                        f"(attempt {attempt}/{EXTRACTION_MAX_RETRIES}): {exc}[/yellow]"
                    )

        failed.append({"paper_id": parse_paper_id, "error": str(last_error)})
        console.print(
            f"[red]Failed to extract {parse_paper_id} after {EXTRACTION_MAX_RETRIES} attempts: "
            f"{last_error}[/red]"
        )

    if show_progress and not job_id and total > 0:
        if total == 1:
            console.print(f"[cyan]Extracting[/cyan] {parsed_docs[0].get('paper_id')}...")
            _extract_one(parsed_docs[0], 1)
        else:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=console,
                transient=False,
            ) as progress:
                task = progress.add_task("Extracting papers", total=total)
                for i, doc in enumerate(parsed_docs, start=1):
                    progress.update(task, description=f"[cyan]{doc.get('paper_id')}[/cyan]")
                    _extract_one(doc, i)
                    progress.advance(task)
    else:
        for i, doc in enumerate(parsed_docs, start=1):
            _extract_one(doc, i)

    if job_id:
        _job_manager.update_job(job_id, processed_items=total, current_item=None)

    return {"extracted_ids": extracted_ids, "failed": failed}


def extract_papers(
    ctx: ResolvedContext,
    skip_confirm: bool = False,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    job_id: Optional[str] = None,
    force: bool = False,
    show_progress: bool = False,
) -> Dict[str, Any]:
    provider_name = provider or str(get_config_value(ctx, "llm_provider", "LLM_PROVIDER"))
    model_name = model or str(get_config_value(ctx, "llm_model", "LLM_MODEL"))
    parsed_files = sorted(ctx.parsed_cache_dir.glob("*.json"))
    if not parsed_files:
        return {"extracted": 0, "skipped": 0, "message": "No parsed papers found. Run litgraph parse first."}

    parsed_docs = []
    skipped = 0
    for pf in parsed_files:
        with open(pf, encoding="utf-8") as f:
            doc = json.load(f)
        if _needs_extraction(ctx, doc["paper_id"], force=force):
            parsed_docs.append(doc)
        else:
            skipped += 1

    if not parsed_docs:
        return {
            "extracted": 0,
            "skipped": skipped,
            "paper_ids": [],
            "provider": provider_name,
        }

    total_sections = sum(len(doc.get("sections", [])) for doc in parsed_docs)
    if not _confirm_external_api(ctx, provider_name, total_sections, skip_confirm):
        return {"extracted": 0, "skipped": skipped, "cancelled": True}

    if job_id:
        _job_manager.update_job(
            job_id,
            status=JobStatus.RUNNING,
            total_items=len(parsed_docs),
            processed_items=0,
            message="Extracting papers",
        )

    extraction_result = _run_extractions(
        ctx,
        parsed_docs,
        provider_name,
        model_name,
        job_id=job_id,
        show_progress=show_progress,
    )
    extracted_ids = extraction_result["extracted_ids"]
    failed = extraction_result["failed"]

    return {
        "extracted": len(extracted_ids),
        "skipped": skipped,
        "paper_ids": extracted_ids,
        "failed": failed,
        "provider": provider_name,
    }


def extract_paper_ids(
    ctx: ResolvedContext,
    paper_ids: List[str],
    skip_confirm: bool = False,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    force: bool = False,
    show_progress: bool = False,
) -> Dict[str, Any]:
    provider_name = provider or str(get_config_value(ctx, "llm_provider", "LLM_PROVIDER"))
    model_name = model or str(get_config_value(ctx, "llm_model", "LLM_MODEL"))
    docs = []
    skipped = 0
    for paper_id in paper_ids:
        parsed_path = ctx.parsed_cache_dir / f"{paper_id}.json"
        if not parsed_path.exists():
            continue
        if not _needs_extraction(ctx, paper_id, force=force):
            skipped += 1
            continue
        docs.append(json.loads(parsed_path.read_text(encoding="utf-8")))

    if not docs:
        return {"extracted": 0, "skipped": skipped, "paper_ids": [], "provider": provider_name}

    total_sections = sum(len(doc.get("sections", [])) for doc in docs)
    if not _confirm_external_api(ctx, provider_name, total_sections, skip_confirm):
        return {"extracted": 0, "skipped": skipped, "cancelled": True, "paper_ids": []}

    extraction_result = _run_extractions(
        ctx,
        docs,
        provider_name,
        model_name,
        show_progress=show_progress,
    )
    extracted_ids = extraction_result["extracted_ids"]
    failed = extraction_result["failed"]

    return {
        "extracted": len(extracted_ids),
        "skipped": skipped,
        "paper_ids": extracted_ids,
        "failed": failed,
        "provider": provider_name,
    }


def remove_paper_artifacts(ctx: ResolvedContext, file_path: Path, paper_id: Optional[str] = None) -> str:
    rel = _rel_path(ctx, file_path)
    pid = paper_id or get_paper_id_for_path(ctx.litgraph_dir, rel) or paper_id_from_path(file_path)
    pid = resolve_canonical_paper_id(ctx.litgraph_dir, pid)
    for cache_file in (
        ctx.parsed_cache_dir / f"{pid}.json",
        ctx.extracted_cache_dir / f"{pid}.json",
    ):
        if cache_file.exists():
            cache_file.unlink()
    mapping = load_paper_id_map(ctx.litgraph_dir)
    for parse_id, canonical_id in mapping.items():
        if canonical_id == pid or parse_id == pid:
            for cache_file in (
                ctx.parsed_cache_dir / f"{parse_id}.json",
                ctx.extracted_cache_dir / f"{parse_id}.json",
            ):
                if cache_file.exists():
                    cache_file.unlink()
    registry = load_registry(ctx.litgraph_dir)
    if rel in registry:
        del registry[rel]
        save_registry(ctx.litgraph_dir, registry)
    remove_from_cache(ctx.files_cache_path, rel)
    return pid


def _handle_deleted_paths(ctx: ResolvedContext, deleted_paths: List[Path]) -> Dict[str, Any]:
    removed_paper_ids: List[str] = []
    bib_removed = 0
    store = _graph_store(ctx)
    try:
        for path in deleted_paths:
            suffix = path.suffix.lower()
            if suffix == ".bib":
                bib_cache = ctx.bib_cache_dir / f"{path.stem}.json"
                if bib_cache.exists():
                    bib_cache.unlink()
                    bib_removed += 1
                remove_from_cache(ctx.files_cache_path, _rel_path(ctx, path))
            elif suffix in (".pdf", ".md"):
                paper_id = remove_paper_artifacts(ctx, path)
                store.delete_paper(paper_id)
                removed_paper_ids.append(paper_id)
    finally:
        store.close()
    return {"removed_paper_ids": removed_paper_ids, "bib_files_removed": bib_removed}


def process_watch_changes(
    ctx: ResolvedContext,
    changed_paths: List[Path],
    deleted_paths: List[Path],
    auto_extract: bool = False,
    auto_build: bool = True,
    skip_confirm: bool = False,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    enrich_s2: bool = False,
) -> Dict[str, Any]:
    """Process filesystem changes from the papers watcher."""
    ctx.parsed_cache_dir.mkdir(parents=True, exist_ok=True)
    ctx.bib_cache_dir.mkdir(parents=True, exist_ok=True)

    delete_info = _handle_deleted_paths(ctx, deleted_paths)

    parsed_ids: List[str] = []
    parse_skipped: List[Dict[str, str]] = []
    bib_changed = delete_info["bib_files_removed"] > 0
    file_cache = load_cache(ctx.files_cache_path)
    for path in changed_paths:
        if not path.exists():
            continue
        if _should_skip_unchanged_parse(ctx, path, file_cache=file_cache):
            continue
        kind, paper_id, skip_reason = _try_parse_file(
            ctx,
            path,
            file_cache=file_cache,
            wait_for_ready=True,
        )
        if skip_reason:
            parse_skipped.append({"path": _rel_path(ctx, path), "reason": skip_reason})
            continue
        if kind == "bib":
            bib_changed = True
        elif kind in ("pdf", "md") and paper_id:
            parsed_ids.append(paper_id)

    files = discover_papers(ctx.papers_dir)
    scan_and_update(files, ctx.files_cache_path, ctx.project_root)

    pending_extract = [pid for pid in parsed_ids if _needs_extraction(ctx, pid)]
    extracted = 0
    extract_skipped = 0
    effective_skip_confirm = skip_confirm or auto_extract
    if auto_extract and pending_extract:
        extract_result = extract_paper_ids(
            ctx,
            pending_extract,
            skip_confirm=effective_skip_confirm,
            provider=provider,
            model=model,
            show_progress=True,
        )
        if extract_result.get("cancelled"):
            return {
                "parsed": len(parsed_ids),
                "paper_ids": parsed_ids,
                "pending_extract": pending_extract,
                "bib_updated": bib_changed,
                "cancelled": True,
            }
        extracted = extract_result.get("extracted", 0)
        extract_skipped = extract_result.get("skipped", 0)
        pending_extract = [pid for pid in parsed_ids if _needs_extraction(ctx, pid)]

    build_result: Dict[str, Any] = {}
    if auto_build and (bib_changed or parsed_ids or deleted_paths):
        build_result = build_paper_graph(ctx, enrich_s2=enrich_s2)

    return {
        "parsed": len(parsed_ids),
        "paper_ids": parsed_ids,
        "parse_skipped": parse_skipped,
        "extracted": extracted,
        "extract_skipped": extract_skipped,
        "pending_extract": pending_extract,
        "bib_updated": bib_changed,
        "removed_paper_ids": delete_info["removed_paper_ids"],
        "papers_indexed": build_result.get("papers_indexed", 0),
    }


def sync_papers_directory(
    ctx: ResolvedContext,
    auto_extract: bool = False,
    auto_build: bool = True,
    skip_confirm: bool = False,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    enrich_s2: bool = False,
) -> Dict[str, Any]:
    """Scan the papers directory and process all changed or removed files."""
    files = discover_papers(ctx.papers_dir)
    removed = find_removed_files(files, ctx.files_cache_path, ctx.project_root)
    _, changed = scan_and_update(files, ctx.files_cache_path, ctx.project_root)
    return process_watch_changes(
        ctx,
        changed_paths=changed,
        deleted_paths=removed,
        auto_extract=auto_extract,
        auto_build=auto_build,
        skip_confirm=skip_confirm,
        provider=provider,
        model=model,
        enrich_s2=enrich_s2,
    )


def run_papers_watcher(
    ctx: ResolvedContext,
    auto_extract: bool = False,
    auto_build: bool = True,
    sync_on_start: bool = False,
    skip_confirm: bool = False,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    enrich_s2: bool = False,
    polling: Optional[bool] = None,
    on_result: Optional[Any] = None,
) -> None:
    from litgraph.core.watcher import PapersWatcher, WatchOptions

    options = WatchOptions(
        auto_extract=auto_extract,
        auto_build=auto_build,
        sync_on_start=sync_on_start,
        skip_confirm=skip_confirm,
        provider=provider,
        model=model,
        enrich_s2=enrich_s2,
        on_result=on_result,
    )
    watcher = PapersWatcher(ctx, options=options, use_polling=polling)
    watcher.start(block=True)


def extract_papers_async(
    ctx: ResolvedContext,
    skip_confirm: bool = False,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    force: bool = False,
) -> str:
    job_id = _job_manager.create_job()

    def _run() -> None:
        try:
            result = extract_papers(
                ctx,
                skip_confirm=skip_confirm,
                provider=provider,
                model=model,
                job_id=job_id,
                force=force,
            )
            if result.get("cancelled"):
                _job_manager.fail_job(job_id, "cancelled by user")
            else:
                _job_manager.complete_job(job_id, result)
        except Exception as exc:
            _job_manager.fail_job(job_id, str(exc))

    threading.Thread(target=_run, daemon=True).start()
    return job_id


def build_paper_graph(ctx: ResolvedContext, enrich_s2: bool = False) -> Dict[str, Any]:
    extractions: List[Dict[str, Any]] = []
    for ef in sorted(ctx.extracted_cache_dir.glob("*.json")):
        extractions.append(json.loads(ef.read_text(encoding="utf-8")))
    if not extractions and not list(ctx.bib_cache_dir.glob("*.json")):
        return {"papers_indexed": 0, "message": "No extracted papers or bib cache found."}
    return build_graph(ctx, extractions, enrich_s2=enrich_s2)


def list_jobs() -> List[Dict[str, Any]]:
    return [_job_manager.job_to_dict(j) for j in _job_manager.list_jobs()]


def check_job_status(job_id: str) -> Dict[str, Any]:
    job = _job_manager.get_job(job_id)
    if not job:
        return {"error": f"Job not found: {job_id}"}
    return _job_manager.job_to_dict(job)


def run_query(
    ctx: ResolvedContext,
    query_type: str,
    method: Optional[str] = None,
    task: Optional[str] = None,
    topic: Optional[str] = None,
    paper_id: Optional[str] = None,
    claim_id: Optional[str] = None,
    paper_ids: Optional[List[str]] = None,
    include_summary: bool = False,
) -> Dict[str, Any]:
    finder = _finder(ctx)
    if query_type == "papers":
        if method:
            return {"papers": finder.find_papers_by_method(method)}
        if task:
            return {"papers": finder.find_papers_by_task(task)}
        return {"papers": finder.list_papers()}
    if query_type == "limitations":
        return finder.find_limitations(topic=topic or "", paper_id=paper_id)
    if query_type == "paper":
        return finder.summarize_paper(paper_id or "")
    if query_type == "claim":
        return finder.get_evidence_for_claim(claim_id or "")
    if query_type == "compare":
        return finder.compare_papers(paper_ids or [])
    if query_type == "matrix":
        return finder.build_literature_matrix(topic or "")
    if query_type == "neighbors":
        return finder.get_paper_neighbors(
            paper_id or "",
            include_summary=include_summary,
        )
    if query_type == "search":
        return finder.search_papers(
            topic or "",
            top_k=10,
        )
    if query_type == "expand":
        return finder.expand_paper_graph(
            paper_id or "",
            hops=2,
        )
    if query_type == "outline":
        return finder.related_work_outline(topic or "")
    return {"error": f"Unknown query type: {query_type}"}


def launch_visualizer(ctx: ResolvedContext, port: int = 8765, open_browser: bool = True) -> None:
    from litgraph.viz.server import run_viz_server

    run_viz_server(ctx, host="127.0.0.1", port=port, open_browser=open_browser)


def print_query_result(result: Dict[str, Any]) -> None:
    if "error" in result:
        console.print(f"[red]Error:[/red] {result['error']}")
        if result.get("hint"):
            console.print(f"[yellow]Hint:[/yellow] {result['hint']}")
        details = {k: v for k, v in result.items() if k not in ("error", "hint") and v}
        if details:
            console.print_json(json.dumps(details, ensure_ascii=False))
        return
    if "markdown_table" in result:
        console.print(result["markdown_table"])
        if result.get("missing_ids"):
            console.print(f"[yellow]Missing paper_ids:[/yellow] {', '.join(result['missing_ids'])}")
            if result.get("hint"):
                console.print(f"[yellow]Hint:[/yellow] {result['hint']}")
        return
    if "markdown_outline" in result:
        console.print(result["markdown_outline"])
        return
    if "neighbors" in result:
        table = Table(title=f"Neighbors: {result.get('paper_id', '')}")
        table.add_column("Paper")
        table.add_column("Relationship")
        table.add_column("Direction")
        for n in result.get("neighbors", []):
            table.add_row(
                f"{n.get('paper_id')} ({n.get('title', '')[:40]})",
                str(n.get("relationship", "")),
                str(n.get("direction", "")),
            )
        console.print(table)
        return
    if "limitations" in result:
        table = Table(title="Limitations")
        table.add_column("Paper")
        table.add_column("Limitation")
        table.add_column("Page")
        table.add_column("Section")
        for item in result["limitations"]:
            table.add_row(
                str(item.get("title", item.get("paper_id", ""))),
                str(item.get("limitation", "")),
                str(item.get("page", "")),
                str(item.get("section", "")),
            )
        console.print(table)
        return
    console.print_json(json.dumps(result, ensure_ascii=False))
