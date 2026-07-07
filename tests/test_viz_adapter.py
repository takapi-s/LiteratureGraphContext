from litgraph.viz.api_adapter import to_playground_graph


def test_to_playground_graph_shapes_cgc_payload():
    payload = {
        "nodes": [
            {"type": "Paper", "id": "p1", "title": "Paper One", "year": 2024, "authors": "Smith"},
            {"type": "Method", "id": "m1", "name": "GNN", "paper_id": "p1"},
            {"type": "Claim", "id": "c1", "text": "claim", "paper_id": "p1"},
            {"type": "Limitation", "id": "l1", "text": "limit", "paper_id": "p1"},
        ],
        "edges": [
            {"type": "USES", "source": "p1", "target": "m1"},
            {"type": "HAS_CLAIM", "source": "p1", "target": "c1"},
            {"type": "HAS_LIMITATION", "source": "p1", "target": "l1"},
        ],
    }
    out = to_playground_graph(payload)
    assert len(out["nodes"]) == 4
    assert out["nodes"][0]["type"] == "Paper"
    assert out["nodes"][0]["val"] == 8
    assert out["links"][0]["type"] == "USES"
    assert out["files"] == ["papers/p1"]
    assert len(out["papers"]) == 1
    paper = out["papers"][0]
    assert paper["paper_id"] == "p1"
    assert paper["title"] == "Paper One"
    assert paper["claim_count"] == 1
    assert paper["limitation_count"] == 1
