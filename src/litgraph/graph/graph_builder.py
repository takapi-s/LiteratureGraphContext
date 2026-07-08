"""Build graph from extracted papers."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Set

from litgraph.cli.config_manager import ResolvedContext, get_config_value
from litgraph.graph.citation_builder import bib_only_entries, build_citation_pairs, merge_citation_pairs
from litgraph.graph.db_factory import get_graph_store
from litgraph.graph.entity_catalog import EntityCatalog
from litgraph.graph.entity_resolver import EntityResolver
from litgraph.graph.reasoning import infer_contrasts_and_extends
from litgraph.graph.reference_linker import build_all_reference_citation_pairs
from litgraph.integrations.semantic_scholar import enrich_metadata
from litgraph.parser.bib_linker import link_bib_to_paper
from litgraph.parser.bib_parser import load_all_bib_entries
from litgraph.query.embedding_store import index_paper_embeddings


def _neo4j_config(ctx: ResolvedContext) -> Dict[str, Any]:
    return {
        "uri": os.getenv("NEO4J_URI") or get_config_value(ctx, "neo4j_uri", "NEO4J_URI"),
        "user": os.getenv("NEO4J_USER") or get_config_value(ctx, "neo4j_user", "NEO4J_USER"),
        "password": os.getenv("NEO4J_PASSWORD") or get_config_value(ctx, "neo4j_password", "NEO4J_PASSWORD"),
        "database": os.getenv("NEO4J_DATABASE") or get_config_value(ctx, "neo4j_database", "NEO4J_DATABASE"),
    }


def _store_for(ctx: ResolvedContext, *, read_only: bool = False):
    backend = str(get_config_value(ctx, "database", "LITGRAPH_DATABASE"))
    return get_graph_store(
        ctx.db_path,
        backend=backend,
        neo4j_config=_neo4j_config(ctx),
        read_only=read_only,
    )


def build_graph(
    ctx: ResolvedContext,
    extractions: List[Dict[str, Any]],
    export_json: bool = True,
    enrich_s2: bool = False,
) -> Dict[str, Any]:
    store = _store_for(ctx)
    store.initialize_schema()
    catalog = EntityCatalog.from_store(store)
    resolver = EntityResolver(ctx.config)
    bib_entries = load_all_bib_entries(ctx.bib_cache_dir)
    indexed_ids: Set[str] = set()

    for raw in extractions:
        normalized = resolver.normalize_extraction(raw, catalog)
        store.upsert_paper_graph(normalized)
        catalog.ingest_extraction(normalized)
        indexed_ids.add(normalized["paper_id"])
        bib_match = link_bib_to_paper(
            normalized["paper_id"],
            raw.get("path"),
            normalized.get("title"),
            bib_entries,
        )
        if bib_match:
            metadata = dict(bib_match)
            if enrich_s2:
                extra = enrich_metadata(metadata.get("title", ""), metadata.get("doi"))
                if extra:
                    metadata.update({k: v for k, v in extra.items() if v})
            store.upsert_paper_metadata(normalized["paper_id"], metadata)

    catalog.save(ctx.litgraph_dir)

    extraction_ids = {raw["paper_id"] for raw in extractions}
    bib_only = bib_only_entries(bib_entries, extraction_ids)

    for entry in bib_only:
        pid = entry["paper_id"]
        metadata = dict(entry)
        if enrich_s2:
            extra = enrich_metadata(metadata.get("title", ""), metadata.get("doi"))
            if extra:
                metadata.update({k: v for k, v in extra.items() if v})
        store.upsert_bib_only_paper(pid, metadata)
        indexed_ids.add(pid)

    paper_metadata = [store.get_paper(pid) for pid in sorted(indexed_ids)]
    paper_metadata = [p for p in paper_metadata if p]
    bib_pairs = build_citation_pairs(bib_entries, indexed_ids)
    ref_pairs, cites_from_references = build_all_reference_citation_pairs(
        ctx.parsed_cache_dir,
        indexed_ids,
        paper_metadata,
    )
    all_cites_pairs = merge_citation_pairs(bib_pairs, ref_pairs)
    for citing, cited in all_cites_pairs:
        store.upsert_cites_edge(citing, cited)

    all_papers = paper_metadata
    contrasts, extends = infer_contrasts_and_extends(all_papers, all_cites_pairs)
    for a, b in contrasts:
        store.upsert_paper_relationship(a, b, "CONTRASTS_WITH")
        store.upsert_paper_relationship(b, a, "CONTRASTS_WITH")
    for a, b in extends:
        store.upsert_paper_relationship(a, b, "EXTENDS")

    graph_json = store.export_graph_json()
    if export_json:
        out_path = ctx.litgraph_dir / "graph.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(graph_json, f, indent=2, ensure_ascii=False)

    embedding_result = index_paper_embeddings(ctx.litgraph_dir, paper_metadata)

    store.close()
    return {
        "papers_indexed": len(indexed_ids),
        "nodes": len(graph_json.get("nodes", [])),
        "edges": len(graph_json.get("edges", [])),
        "entities_resolved": resolver.stats.get("resolved", 0),
        "entities_disambiguated": resolver.stats.get("disambiguated", 0),
        "entities_new": resolver.stats.get("new", 0),
        "bib_entries_linked": sum(
            1
            for raw in extractions
            if link_bib_to_paper(raw["paper_id"], raw.get("path"), raw.get("title"), bib_entries)
        ),
        "bib_only_papers": len(bib_only),
        "cites_edges": len(all_cites_pairs),
        "cites_from_bib": len(bib_pairs),
        "cites_from_references": cites_from_references,
        "contrasts_edges": len(contrasts),
        "extends_edges": len(extends),
        "embeddings_indexed": embedding_result.get("indexed", 0),
    }
