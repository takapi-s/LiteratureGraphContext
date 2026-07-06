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
