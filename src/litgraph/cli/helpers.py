"""CLI command implementations."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table

from litgraph.cli.config_manager import ResolvedContext, get_config_value, resolve_context, save_papers_dir
from litgraph.core.jobs import JobManager, JobStatus
from litgraph.extractor.llm_extractor import extract_paper, save_extraction
from litgraph.extractor.providers import get_provider
from litgraph.graph.graph_builder import build_graph
from litgraph.parser.dispatcher import collect_parse_targets, parse_file
from litgraph.query.paper_finder import PaperFinder
from litgraph.scanner.file_scanner import discover_papers
from litgraph.scanner.hash_cache import scan_and_update

console = Console()
_job_manager = JobManager()


def _rel_path(ctx: ResolvedContext, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ctx.project_root))
    except ValueError:
        return str(path.resolve())


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
    return {
        "total": len(files),
        "changed": len(changed),
        "files": [_rel_path(ctx, f) for f in files],
        "papers_dir": str(ctx.papers_dir),
    }


def parse_papers(ctx: ResolvedContext, only_changed: bool = True) -> Dict[str, Any]:
    target = ctx.papers_dir
    ctx.bib_cache_dir.mkdir(parents=True, exist_ok=True)
    files = discover_papers(target)
    _, changed = scan_and_update(files, ctx.files_cache_path, ctx.project_root)
    to_parse = collect_parse_targets(files, only_changed, changed)

    parsed_ids: List[str] = []
    bib_files = 0
    for file_path in to_parse:
        kind, paper_id = parse_file(file_path, ctx.bib_cache_dir, ctx.parsed_cache_dir)
        if kind in ("pdf", "md") and paper_id:
            parsed_ids.append(paper_id)
        elif kind == "bib":
            bib_files += 1

    return {
        "parsed": len(parsed_ids),
        "bib_files": bib_files,
        "paper_ids": parsed_ids,
    }


def _confirm_external_api(ctx: ResolvedContext, provider_name: str, section_count: int, skip: bool) -> bool:
    provider = get_provider(provider_name, model=str(get_config_value(ctx, "llm_model")))
    if provider.is_local:
        return True
    confirm = get_config_value(ctx, "confirm_external_api")
    if isinstance(confirm, str):
        confirm = confirm.lower() in ("1", "true", "yes", "on")
    if skip or not confirm:
        return True
    answer = console.input(
        f"Send {section_count} paper section(s) to external provider '{provider_name}'? [y/N]: "
    )
    return answer.strip().lower() in ("y", "yes")


def extract_papers(
    ctx: ResolvedContext,
    skip_confirm: bool = False,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    provider_name = provider or str(get_config_value(ctx, "llm_provider", "LLM_PROVIDER"))
    model_name = model or str(get_config_value(ctx, "llm_model", "LLM_MODEL"))
    parsed_files = sorted(ctx.parsed_cache_dir.glob("*.json"))
    if not parsed_files:
        return {"extracted": 0, "message": "No parsed papers found. Run litgraph parse first."}

    total_sections = 0
    parsed_docs = []
    for pf in parsed_files:
        with open(pf, encoding="utf-8") as f:
            doc = json.load(f)
        parsed_docs.append(doc)
        total_sections += len(doc.get("sections", []))

    if not _confirm_external_api(ctx, provider_name, total_sections, skip_confirm):
        return {"extracted": 0, "cancelled": True}

    extracted_ids = []
    for doc in parsed_docs:
        extraction = extract_paper(doc, provider_name, model=model_name)
        out = ctx.extracted_cache_dir / f"{doc['paper_id']}.json"
        save_extraction(out, extraction)
        extracted_ids.append(doc["paper_id"])
    return {"extracted": len(extracted_ids), "paper_ids": extracted_ids, "provider": provider_name}


def extract_papers_async(
    ctx: ResolvedContext,
    skip_confirm: bool = False,
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> str:
    job_id = _job_manager.create_job()

    def _run() -> None:
        _job_manager.update_job(job_id, status=JobStatus.RUNNING)
        try:
            result = extract_papers(ctx, skip_confirm=skip_confirm, provider=provider, model=model)
            _job_manager.complete_job(job_id, result)
        except Exception as exc:
            _job_manager.fail_job(job_id, str(exc))

    threading.Thread(target=_run, daemon=True).start()
    return job_id


def build_paper_graph(ctx: ResolvedContext) -> Dict[str, Any]:
    extractions: List[Dict[str, Any]] = []
    for ef in sorted(ctx.extracted_cache_dir.glob("*.json")):
        extractions.append(json.loads(ef.read_text(encoding="utf-8")))
    if not extractions:
        return {"papers_indexed": 0, "message": "No extracted papers found. Run litgraph extract first."}
    return build_graph(ctx, extractions)


def run_query(
    ctx: ResolvedContext,
    query_type: str,
    method: Optional[str] = None,
    task: Optional[str] = None,
    topic: Optional[str] = None,
    paper_id: Optional[str] = None,
    claim_id: Optional[str] = None,
    paper_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    finder = PaperFinder(ctx.db_path)
    if query_type == "papers":
        if method:
            return {"papers": finder.find_papers_by_method(method)}
        if task:
            return {"papers": finder.find_papers_by_task(task)}
        return {"papers": finder.list_papers()}
    if query_type == "limitations":
        return finder.find_limitations(topic or "")
    if query_type == "paper":
        return finder.summarize_paper(paper_id or "")
    if query_type == "claim":
        return finder.get_evidence_for_claim(claim_id or "")
    if query_type == "compare":
        return finder.compare_papers(paper_ids or [])
    return {"error": f"Unknown query type: {query_type}"}


def print_query_result(result: Dict[str, Any]) -> None:
    if "markdown_table" in result:
        console.print(result["markdown_table"])
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
