from litgraph.viz.api_adapter import to_playground_graph


def test_to_playground_graph_shapes_cgc_payload():
    payload = {
        "nodes": [
            {"type": "Paper", "id": "p1", "title": "Paper One", "year": 2024},
            {"type": "Method", "id": "m1", "name": "GNN", "paper_id": "p1"},
        ],
        "edges": [
            {"type": "USES", "source": "p1", "target": "m1"},
        ],
    }
    out = to_playground_graph(payload)
    assert len(out["nodes"]) == 2
    assert out["nodes"][0]["type"] == "Paper"
    assert out["nodes"][0]["val"] == 8
    assert out["links"][0]["type"] == "USES"
    assert out["files"] == ["papers/p1"]
