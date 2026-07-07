"""Tests for LLM extraction normalization."""

from litgraph.extractor.llm_extractor import normalize_extraction_raw
from litgraph.extractor.schema import PaperExtraction


def test_normalize_extraction_raw_coerces_method_dicts():
    raw = {
        "paper_id": "pearl2009",
        "methods": [
            {"text": "Using a one-dimensional model", "section": "Abstract"},
            {"text": "Numerical simulation", "section": "Computational Approach"},
        ],
        "tasks": [{"name": "causal inference"}],
        "datasets": "synthetic data",
        "metrics": None,
        "contributions": [],
        "claims": [],
        "limitations": [],
    }
    normalized = normalize_extraction_raw(raw)
    model = PaperExtraction.model_validate(normalized)

    assert model.methods == [
        "Using a one-dimensional model",
        "Numerical simulation",
    ]
    assert model.tasks == ["causal inference"]
    assert model.datasets == ["synthetic data"]
    assert model.metrics == []


def test_normalize_extraction_raw_keeps_string_lists():
    raw = {
        "paper_id": "x",
        "methods": ["GNN", "GRU"],
        "tasks": ["mobility prediction"],
        "datasets": ["GPS trajectory"],
        "metrics": ["MAE"],
        "contributions": [],
        "claims": [],
        "limitations": [],
    }
    model = PaperExtraction.model_validate(normalize_extraction_raw(raw))
    assert model.methods == ["GNN", "GRU"]
