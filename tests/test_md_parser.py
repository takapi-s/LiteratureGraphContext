from pathlib import Path

from litgraph.parser.md_parser import parse_md


def test_md_parser_sections():
    path = Path(__file__).parent / "fixtures" / "sample_note.md"
    parsed = parse_md(path)
    names = [s["name"] for s in parsed["sections"]]
    assert parsed["source_type"] == "md"
    assert "Abstract" in names
    assert "Conclusion" in names
    assert parsed["paper_id"] == "sample_note"
