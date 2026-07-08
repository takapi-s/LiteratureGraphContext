"""Tests for LLM extraction normalization."""

from litgraph.extractor.llm_extractor import extract_paper, normalize_extraction_raw
from litgraph.extractor.prompts import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_TEMPLATE
from litgraph.extractor.schema import PaperExtraction
from litgraph.graph.entity_catalog import EntityCatalog


def test_extraction_prompts_include_entity_rules():
    assert "canonical English" in EXTRACTION_SYSTEM_PROMPT
    assert "verbatim" in EXTRACTION_SYSTEM_PROMPT.lower()
    assert "{known_entities}" in EXTRACTION_USER_TEMPLATE


def test_extract_paper_injects_entity_catalog(monkeypatch):
    catalog = EntityCatalog()
    catalog.add("method", "Graph Neural Network")

    class FakeProvider:
        def complete_json(self, system, user):
            assert "Known entities" in user
            assert "Graph Neural Network" in user
            return {
                "paper_id": "demo",
                "methods": ["GNN"],
                "tasks": [],
                "datasets": [],
                "metrics": [],
                "contributions": [],
                "claims": [],
                "limitations": [],
            }

    monkeypatch.setattr(
        "litgraph.extractor.llm_extractor.get_provider",
        lambda *_args, **_kwargs: FakeProvider(),
    )
    parsed = {
        "paper_id": "demo",
        "title": "Demo",
        "sections": [{"name": "Abstract", "text": "We use GNN.", "page_start": 1, "page_end": 1}],
    }
    model = extract_paper(parsed, "openai", entity_catalog=catalog)
    assert model.methods == ["GNN"]


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
