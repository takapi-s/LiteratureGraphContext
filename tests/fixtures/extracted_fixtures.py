"""Demo extracted fixtures (no LLM required for graph/query tests)."""

from __future__ import annotations

from pathlib import Path

FIXTURES = [
    {
        "paper_id": "mobility_gnn_2024",
        "title": "Mobility Prediction with Graph Neural Networks",
        "year": 2024,
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
]


def write_fixtures(target_dir: Path) -> None:
    import json
    target_dir.mkdir(parents=True, exist_ok=True)
    for item in FIXTURES:
        path = target_dir / f"{item['paper_id']}.json"
        path.write_text(json.dumps(item, indent=2), encoding="utf-8")
