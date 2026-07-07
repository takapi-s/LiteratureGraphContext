"""Demo extracted fixtures (no LLM required for graph/query tests)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from litgraph.cli.config_manager import ResolvedContext
from litgraph.graph.graph_builder import build_graph

FIXTURES = [
    {
        "paper_id": "mobility_gnn_2024",
        "title": "Mobility Prediction with Graph Neural Networks",
        "year": 2024,
        "source_path": "papers/mobility_gnn_2024.pdf",
        "source_stem": "mobility_gnn_2024",
        "tasks": ["mobility prediction"],
        "methods": ["Graph Neural Network", "GRU"],
        "datasets": ["GPS trajectory"],
        "metrics": ["MAE", "RMSE"],
        "contributions": [{
            "text": "Spatial-temporal GNN for mobility prediction",
            "evidence_text": "We propose a GNN-based model for mobility prediction",
            "page": 1,
            "section": "Abstract",
        }],
        "claims": [{
            "text": "The proposed model improves spatial-temporal prediction accuracy.",
            "evidence_text": "Our method improves spatial-temporal prediction accuracy on benchmark datasets.",
            "page": 1,
            "section": "Abstract",
        }],
        "limitations": [{
            "text": "The method does not explicitly consider event information.",
            "evidence_text": "does not explicitly consider event information",
            "page": 4,
            "section": "Conclusion",
        }],
    },
    {
        "paper_id": "event_forecasting_2025",
        "title": "Event-Aware Forecasting with Transformers",
        "year": 2025,
        "source_path": "papers/event_forecasting_2025.pdf",
        "source_stem": "event_forecasting_2025",
        "tasks": ["event forecasting"],
        "methods": ["Transformer"],
        "datasets": ["event logs"],
        "metrics": ["F1"],
        "contributions": [],
        "claims": [],
        "limitations": [{
            "text": "Limited spatial modeling.",
            "evidence_text": "has limited spatial modeling",
            "page": 4,
            "section": "Conclusion",
        }],
    },
    {
        "paper_id": "spatial_temporal_transformer_2025",
        "title": "Spatial-Temporal Transformer for Trajectory Modeling",
        "year": 2025,
        "source_path": "papers/spatial_temporal_transformer_2025.pdf",
        "source_stem": "spatial_temporal_transformer_2025",
        "tasks": ["trajectory prediction"],
        "methods": ["Transformer"],
        "datasets": ["GPS trajectory"],
        "metrics": ["RMSE"],
        "contributions": [],
        "claims": [],
        "limitations": [{
            "text": "Event context is not modeled explicitly.",
            "evidence_text": "event context is not modeled explicitly",
            "page": 4,
            "section": "Conclusion",
        }],
    },
    {
        "paper_id": "bysgnn_2023",
        "title": "BysGNN: Dynamic Graph Learning for POI Visit Forecasting",
        "year": 2023,
        "source_path": "papers/02_hajisafi2023_bysgnn.pdf",
        "source_stem": "02_hajisafi2023_bysgnn",
        "tasks": ["POI visit forecasting"],
        "methods": ["Graph Neural Network", "attention"],
        "datasets": ["SafeGraph POI"],
        "metrics": ["MAE", "RMSE"],
        "contributions": [{
            "text": "Multi-context dynamic graph for POI visits",
            "evidence_text": "we learn dynamic adjacency from spatial temporal and semantic context",
            "page": 1,
            "section": "Abstract",
        }],
        "claims": [{
            "text": "BysGNN outperforms static graph baselines.",
            "evidence_text": "BysGNN achieves lower MAE than STGCN",
            "page": 6,
            "section": "Experiments",
        }],
        "limitations": [{
            "text": "GCN aggregation is rigid.",
            "evidence_text": "GCN propagates with fixed neighborhood weights",
            "page": 7,
            "section": "Conclusion",
        }],
    },
    {
        "paper_id": "stgcn_2018",
        "title": "Spatio-Temporal Graph Convolutional Networks",
        "year": 2018,
        "source_path": "papers/06_yu2017_stgcn.pdf",
        "source_stem": "06_yu2017_stgcn",
        "tasks": ["traffic forecasting"],
        "methods": ["graph convolutional", "Graph Neural Network"],
        "datasets": ["METR-LA"],
        "metrics": ["MAE", "RMSE"],
        "contributions": [],
        "claims": [],
        "limitations": [{
            "text": "Static adjacency limits flexibility.",
            "evidence_text": "adjacency matrix is fixed during training",
            "page": 5,
            "section": "Discussion",
        }],
    },
    {
        "paper_id": "gman_2020",
        "title": "GMAN: Graph Multi-Attention Network for Traffic Prediction",
        "year": 2020,
        "source_path": "papers/09_zheng2020_gman.pdf",
        "source_stem": "09_zheng2020_gman",
        "tasks": ["traffic forecasting"],
        "methods": ["attention", "Graph Neural Network"],
        "datasets": ["METR-LA"],
        "metrics": ["MAE"],
        "contributions": [],
        "claims": [],
        "limitations": [],
    },
]

CITES_EDGES = [
    ("bysgnn_2023", "stgcn_2018"),
    ("bysgnn_2023", "gman_2020"),
    ("mobility_gnn_2024", "bysgnn_2023"),
]


def write_fixtures(target_dir: Path) -> None:
    import json
    target_dir.mkdir(parents=True, exist_ok=True)
    for item in FIXTURES:
        path = target_dir / f"{item['paper_id']}.json"
        path.write_text(json.dumps(item, indent=2, ensure_ascii=False), encoding="utf-8")


def build_fixture_graph(ctx: ResolvedContext, fixtures: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    fixtures = fixtures or FIXTURES
    result = build_graph(ctx, fixtures)
    store = __import__("litgraph.graph.db_factory", fromlist=["get_graph_store"]).get_graph_store(ctx.db_path)
    try:
        for citing, cited in CITES_EDGES:
            store.upsert_cites_edge(citing, cited)
    finally:
        store.close()
    return result


def primary_paper_id() -> str:
    return "mobility_gnn_2024"


def claim_id_for(paper_id: str, index: int = 0) -> str:
    from litgraph.utils.ids import claim_id
    return claim_id(paper_id, index)
