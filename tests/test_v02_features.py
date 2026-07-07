from litgraph.graph.citation_builder import bib_only_entries, build_citation_pairs
from litgraph.graph.reasoning import infer_contrasts_and_extends
from litgraph.query.comparison import build_comparison_rows, build_literature_matrix_rows


def test_citation_pairs():
    bib = [
        {"bib_key": "a", "source_stem": "a", "citations": "b, c"},
        {"bib_key": "b", "source_stem": "b", "citations": ""},
        {"bib_key": "c", "source_stem": "c", "citations": ""},
    ]
    pairs = build_citation_pairs(bib, {"a", "b", "c"})
    assert ("a", "b") in pairs
    assert ("a", "c") in pairs


def test_bib_only_entries():
    bib = [
        {"bib_key": "indexed", "source_stem": "indexed", "title": "Indexed"},
        {"bib_key": "orphan", "source_stem": "orphan", "title": "Orphan"},
    ]
    only = bib_only_entries(bib, {"indexed"})
    assert len(only) == 1
    assert only[0]["paper_id"] == "orphan"


def test_compare_and_matrix():
    papers = [
        {
            "paper_id": "p1",
            "title": "Paper 1",
            "tasks": ["mobility"],
            "methods": ["GNN"],
            "datasets": ["GPS"],
            "metrics": ["MAE"],
            "contributions": [{"text": "contrib", "evidence_text": "e", "page": 1, "section": "Abs"}],
            "limitations": [{"text": "no events", "evidence_text": "e", "page": 2, "section": "Con"}],
        },
        {
            "paper_id": "p2",
            "title": "Paper 2",
            "tasks": ["mobility"],
            "methods": ["Transformer"],
            "datasets": ["GPS"],
            "metrics": ["RMSE"],
            "contributions": [],
            "limitations": [],
        },
    ]
    rows = build_comparison_rows(papers)
    assert rows[0]["metric"] == "MAE"
    assert rows[0]["difference"]
    matrix = build_literature_matrix_rows("GNN", papers)
    assert len(matrix) == 1
    contrasts, extends = infer_contrasts_and_extends(papers, [("p2", "p1")])
    assert ("p1", "p2") in contrasts
