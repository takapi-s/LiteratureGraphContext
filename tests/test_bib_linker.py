from litgraph.parser.bib_linker import link_bib_to_paper

SAMPLE_BIB = [{
    "bib_key": "mobility_gnn_2024",
    "title": "Mobility Prediction with Graph Neural Networks",
    "year": 2024,
    "authors": ["Alice Smith"],
    "venue": "NeurIPS",
    "doi": "10.1234/test",
    "source_stem": "mobility_gnn_2024",
}]


def test_link_by_stem():
    match = link_bib_to_paper(
        "mobility_gnn_2024",
        "papers/mobility_gnn_2024.pdf",
        "Some title",
        SAMPLE_BIB,
    )
    assert match is not None
    assert match["bib_key"] == "mobility_gnn_2024"


def test_link_by_title():
    match = link_bib_to_paper(
        "other_id",
        "papers/other.pdf",
        "Mobility Prediction with Graph Neural Networks",
        SAMPLE_BIB,
    )
    assert match is not None


def test_link_by_truncated_title_prefix():
    match = link_bib_to_paper(
        "p_uuid",
        None,
        "CausalGRIT: Causal Graph Reasoning for Traffic Congestion",
        [{
            "bib_key": "BRQQMQUI",
            "zotero_key": "BRQQMQUI",
            "title": (
                "CausalGRIT: Causal Graph Reasoning for Traffic Congestion "
                "Prediction – From Statistical Association to Casual Intervention"
            ),
            "doi": "10.1145/3748636.3762721",
        }],
    )
    assert match is not None
    assert match["bib_key"] == "BRQQMQUI"


def test_link_by_zotero_key_kwarg():
    match = link_bib_to_paper(
        "p_uuid",
        None,
        "Short title",
        [{
            "bib_key": "BRQQMQUI",
            "zotero_key": "BRQQMQUI",
            "title": "Full CausalGRIT title that does not match",
        }],
        zotero_key="BRQQMQUI",
    )
    assert match is not None
    assert match["bib_key"] == "BRQQMQUI"