from litgraph.parser.bib_parser import parse_bib_text


def test_bib_nested_braces():
    text = """
@article{deep_gnn,
  title={Graph {Neural} Networks for {Mobility}},
  author={Smith, Alice and {van der Berg}, Jan},
  journal={NeurIPS},
  year={2024},
  citations={mobility_gnn_2024, other_paper}
}
"""
    entries = parse_bib_text(text)
    assert len(entries) == 1
    assert entries[0]["title"] == "Graph {Neural} Networks for {Mobility}"
    assert "van der Berg" in entries[0]["authors"][1]
    assert "mobility_gnn_2024" in entries[0]["citations"]
