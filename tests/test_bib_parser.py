from pathlib import Path

from litgraph.parser.bib_parser import parse_bib_file


def test_bib_parser_fields():
    path = Path(__file__).parent / "fixtures" / "sample.bib"
    entries = parse_bib_file(path)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["bib_key"] == "mobility_gnn_2024"
    assert "Graph Neural Network" in entry["title"]
    assert entry["year"] == 2024
    assert len(entry["authors"]) == 2
    assert entry["doi"] == "10.1234/mobility.gnn"
