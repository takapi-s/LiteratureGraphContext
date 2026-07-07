"""Tests for PDF reference linking to CITES edges."""

import json

from litgraph.graph.reference_linker import (
    build_reference_citation_pairs,
    build_all_reference_citation_pairs,
)
from litgraph.parser.reference_parser import parse_references_section


def test_build_reference_citation_pairs_by_doi():
    references = parse_references_section(
        "[1] Smith, A. Prior Work on GNN. 2020. doi:10.1234/cited.paper"
    )["references"]
    papers = [
        {
            "paper_id": "citing_paper",
            "title": "New Paper",
            "year": 2024,
            "doi": "",
            "authors": "Alice",
        },
        {
            "paper_id": "cited_paper",
            "title": "Prior Work on GNN",
            "year": 2020,
            "doi": "10.1234/cited.paper",
            "authors": "Smith, A.",
        },
    ]
    pairs = build_reference_citation_pairs("citing_paper", references, papers)
    assert ("citing_paper", "cited_paper") in pairs


def test_build_all_reference_citation_pairs_from_cache(project_tmp):
    parsed_dir = project_tmp / ".litgraph" / "cache" / "parsed"
    parsed_dir.mkdir(parents=True, exist_ok=True)
    refs = parse_references_section(
        "[1] Lee, B. Event Forecasting. 2021. doi:10.1234/event.2021"
    )["references"]
    (parsed_dir / "paper_a.json").write_text(
        json.dumps({"paper_id": "paper_a", "references": refs}),
        encoding="utf-8",
    )
    papers = [
        {"paper_id": "paper_a", "title": "Paper A", "year": 2024, "doi": "", "authors": ""},
        {"paper_id": "paper_b", "title": "Event Forecasting", "year": 2021, "doi": "10.1234/event.2021", "authors": "Lee"},
    ]
    pairs, resolved = build_all_reference_citation_pairs(
        parsed_dir,
        {"paper_a", "paper_b"},
        papers,
    )
    assert resolved == 1
    assert ("paper_a", "paper_b") in pairs
