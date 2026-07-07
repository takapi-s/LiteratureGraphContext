from litgraph.query.gap_analysis import find_research_gaps
from litgraph.query.related_work import generate_related_work_outline


def test_find_research_gaps_clusters():
    limitations = [
        {
            "paper_id": "p1",
            "title": "Paper 1",
            "limitation": "does not consider event information",
            "evidence_text": "event information is not modeled",
            "page": 8,
            "section": "Conclusion",
        },
        {
            "paper_id": "p2",
            "title": "Paper 2",
            "limitation": "event information is not explicitly considered",
            "evidence_text": "we do not model events",
            "page": 5,
            "section": "Discussion",
        },
        {
            "paper_id": "p3",
            "title": "Paper 3",
            "limitation": "limited spatial modeling",
            "evidence_text": "spatial context is weak",
            "page": 3,
            "section": "Conclusion",
        },
    ]
    result = find_research_gaps("event", limitations, min_papers=1)
    assert result["gap_count"] >= 1
    event_gaps = [g for g in result["gaps"] if "event" in g["gap"].lower()]
    assert event_gaps
    assert len(event_gaps[0]["evidence"]) >= 1


def test_related_work_outline():
    papers = [
        {
            "paper_id": "p1",
            "title": "GNN Mobility",
            "tasks": ["mobility prediction"],
            "methods": ["GNN"],
            "datasets": ["GPS"],
            "limitations": [{"text": "no events"}],
        },
        {
            "paper_id": "p2",
            "title": "Transformer Events",
            "tasks": ["event forecasting"],
            "methods": ["Transformer"],
            "datasets": ["logs"],
            "limitations": [],
        },
    ]
    result = generate_related_work_outline("mobility", papers)
    assert "markdown_outline" in result
    assert len(result["sections"]) >= 2
    assert "Related Work Outline" in result["markdown_outline"]
