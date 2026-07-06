"""Generate minimal demo PDFs for examples."""

from __future__ import annotations

from pathlib import Path

import fitz

PAPERS = {
    "mobility_gnn_2024.pdf": """
Mobility Prediction with Graph Neural Networks

Abstract
We propose a GNN-based model for mobility prediction using GPS trajectory data.
Our method improves spatial-temporal prediction accuracy on benchmark datasets.

1. Introduction
Human mobility prediction is important for urban planning.

2. Method
We use Graph Neural Network and GRU encoders.

3. Experiment
We evaluate on GPS trajectory data with MAE and RMSE metrics.

4. Conclusion
The proposed model improves accuracy but does not explicitly consider event information.
Future work should integrate event-aware signals.
""",
    "event_forecasting_2025.pdf": """
Event-Aware Forecasting with Transformers

Abstract
We present a Transformer model for event forecasting using event logs.

1. Introduction
Events shape human behavior in cities.

2. Method
We use Transformer architectures with event embeddings.

3. Experiment
Evaluated on event logs with F1 score.

4. Conclusion
Our approach captures event dynamics but has limited spatial modeling.
""",
    "spatial_temporal_transformer_2025.pdf": """
Spatial-Temporal Transformer for Trajectory Modeling

Abstract
A spatial-temporal Transformer for trajectory prediction.

1. Introduction
Trajectory modeling requires joint spatial and temporal reasoning.

2. Method
Transformer encoders over spatial grids.

3. Experiment
GPS trajectory benchmarks with RMSE.

4. Conclusion
Strong spatial modeling; event context is not modeled explicitly.
""",
}


def main() -> None:
    out_dir = Path(__file__).resolve().parent.parent / "examples" / "papers"
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, text in PAPERS.items():
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), text.strip(), fontsize=11)
        doc.save(out_dir / name)
        doc.close()
    print(f"Wrote {len(PAPERS)} PDFs to {out_dir}")


if __name__ == "__main__":
    main()
