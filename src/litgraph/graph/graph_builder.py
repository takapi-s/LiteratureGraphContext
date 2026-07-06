"""Build graph from extracted papers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from litgraph.graph.kuzu_store import get_graph_store
from litgraph.graph.normalizer import EntityNormalizer
from litgraph.cli.config_manager import ResolvedContext
from litgraph.parser.bib_linker import link_bib_to_paper
from litgraph.parser.bib_parser import load_all_bib_entries


def build_graph(ctx: ResolvedContext, extractions: List[Dict[str, Any]], export_json: bool = True) -> Dict[str, Any]:
    store = get_graph_store(ctx.db_path)
    store.initialize_schema()
    normalizer = EntityNormalizer(ctx.aliases_path)
    bib_entries = load_all_bib_entries(ctx.bib_cache_dir)

    for raw in extractions:
        normalized = normalizer.normalize_extraction(raw)
        store.upsert_paper_graph(normalized)
        bib_match = link_bib_to_paper(
            normalized["paper_id"],
            raw.get("path"),
            normalized.get("title"),
            bib_entries,
        )
        if bib_match:
            store.upsert_paper_metadata(normalized["paper_id"], bib_match)

    graph_json = store.export_graph_json()
    if export_json:
        out_path = ctx.litgraph_dir / "graph.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(graph_json, f, indent=2, ensure_ascii=False)

    return {
        "papers_indexed": len(extractions),
        "nodes": len(graph_json.get("nodes", [])),
        "bib_entries_linked": sum(
            1
            for raw in extractions
            if link_bib_to_paper(raw["paper_id"], raw.get("path"), raw.get("title"), bib_entries)
        ),
    }
