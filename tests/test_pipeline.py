import json
from pathlib import Path

import pytest

from litgraph.cli.config_manager import init_project, resolve_context
from litgraph.graph.graph_builder import build_graph
from litgraph.parser.section_splitter import split_sections
from litgraph.query.paper_finder import PaperFinder
from litgraph.scanner.hash_cache import file_sha256, scan_and_update
from litgraph.scanner.file_scanner import discover_papers
from litgraph.extractor.schema import PaperExtraction
from tests.fixtures.extracted_fixtures import FIXTURES, write_fixtures


def test_paper_extraction_schema():
    data = FIXTURES[0]
    model = PaperExtraction.model_validate(data)
    assert model.paper_id == "mobility_gnn_2024"
    assert model.claims[0].evidence_text


def test_section_splitter():
    parsed = {
        "paper_id": "x",
        "pages": [{"page": 1, "text": "Title\n\nAbstract\nWe do stuff.\n\n1. Introduction\nIntro.\n\n4. Conclusion\nLimitations here."}],
        "full_text": "Title\n\nAbstract\nWe do stuff.\n\n1. Introduction\nIntro.\n\n4. Conclusion\nLimitations here.",
    }
    out = split_sections(parsed)
    names = [s["name"] for s in out["sections"]]
    assert "Abstract" in names
    assert "Conclusion" in names


def test_hash_cache_stable(project_tmp):
    pdf = project_tmp / "papers" / "a.pdf"
    pdf.write_bytes(b"%PDF-demo")
    files = discover_papers(project_tmp / "papers")
    ctx = resolve_context(project_tmp)
    _, changed1 = scan_and_update(files, ctx.files_cache_path, ctx.project_root)
    _, changed2 = scan_and_update(files, ctx.files_cache_path, ctx.project_root)
    assert len(changed1) == 1
    assert len(changed2) == 0


def test_build_and_query(project_tmp):
    from litgraph.cli.config_manager import init_project

    init_project(project_tmp)
    write_fixtures(project_tmp / ".litgraph" / "cache" / "extracted")
    ctx = resolve_context(project_tmp)
    result = build_graph(ctx, FIXTURES)
    assert result["papers_indexed"] == len(FIXTURES)

    finder = PaperFinder(ctx.db_path, project_config=ctx.config)
    gnn = finder.find_papers_by_method("GNN")
    assert any("mobility_gnn_2024" == p.get("paper_id") for p in gnn)

    limitations = finder.find_limitations("event")
    assert limitations["limitations"]
    assert any("mobility_gnn_2024" == l.get("paper_id") for l in limitations["limitations"])

    compare = finder.compare_papers(["mobility_gnn_2024", "event_forecasting_2025"])
    assert "markdown_table" in compare
    assert "GNN" in compare["markdown_table"] or "Graph Neural Network" in compare["markdown_table"]


def test_entity_resolution_merges_gnn_variants(project_tmp):
    from litgraph.cli.config_manager import init_project
    from litgraph.graph.db_factory import get_graph_store

    init_project(project_tmp)
    ctx = resolve_context(project_tmp)
    variants = [
        {
            "paper_id": "gnn_a",
            "title": "Paper A",
            "methods": ["Graph Neural Network"],
            "tasks": [],
            "datasets": [],
            "metrics": [],
            "contributions": [],
            "claims": [],
            "limitations": [],
        },
        {
            "paper_id": "gnn_b",
            "title": "Paper B",
            "methods": ["GNN"],
            "tasks": [],
            "datasets": [],
            "metrics": [],
            "contributions": [],
            "claims": [],
            "limitations": [],
        },
    ]
    build_graph(ctx, variants)
    store = get_graph_store(ctx.db_path)
    try:
        method_names = store.list_entity_names("Method")
    finally:
        store.close()
    gnn_names = [n for n in method_names if "graph neural" in n.lower() or n.upper() == "GNN"]
    assert len(gnn_names) == 1
    assert gnn_names[0] == "Graph Neural Network"


def test_bib_metadata_merged(project_tmp):
    import yaml
    from litgraph.parser.bib_parser import parse_bib_file, save_bib_cache

    init_project(project_tmp)
    write_fixtures(project_tmp / ".litgraph" / "cache" / "extracted")
    bib_path = Path(__file__).parent / "fixtures" / "sample.bib"
    entries = parse_bib_file(bib_path)
    save_bib_cache(project_tmp / ".litgraph" / "cache" / "bib" / "mobility_gnn_2024.json", entries)

    ctx = resolve_context(project_tmp)
    build_graph(ctx, [FIXTURES[0]])

    finder = PaperFinder(ctx.db_path)
    paper = finder.get_paper("mobility_gnn_2024")
    assert paper is not None
    assert "Smith" in (paper.get("authors") or "")
    assert paper.get("doi") == "10.1234/mobility.gnn"


def test_save_papers_dir(project_tmp):
    from litgraph.cli.config_manager import save_papers_dir

    init_project(project_tmp)
    ctx = resolve_context(project_tmp)
    stored = save_papers_dir(ctx, project_tmp / "custom-papers")
    assert stored == "custom-papers"
    assert ctx.papers_dir == project_tmp / "custom-papers"
