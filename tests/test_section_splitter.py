"""Tests for section splitting and heading detection."""

import json

from litgraph.parser.heading_detector import find_block_section_starts
from litgraph.parser.reference_parser import parse_reference_entry, parse_references_section
from litgraph.parser.section_splitter import split_sections


def test_section_splitter_expanded_patterns():
    parsed = {
        "paper_id": "x",
        "pages": [{
            "page": 1,
            "text": (
                "Mobility GNN Paper\n\nAbstract\nWe do stuff.\n\n"
                "Introduction\nIntro text.\n\n"
                "Related Work\nPrior art.\n\n"
                "1. Method\nOur method.\n\n"
                "4. Conclusion\nLimits here.\n\n"
                "References\n[1] Smith, A. Old Paper. 2020."
            ),
            "dict": {"blocks": []},
        }],
        "full_text": (
            "Mobility GNN Paper\n\nAbstract\nWe do stuff.\n\n"
            "Introduction\nIntro text.\n\n"
            "Related Work\nPrior art.\n\n"
            "1. Method\nOur method.\n\n"
            "4. Conclusion\nLimits here.\n\n"
            "References\n[1] Smith, A. Old Paper. 2020."
        ),
    }
    out = split_sections(parsed)
    names = [s["name"] for s in out["sections"]]
    assert "Abstract" in names
    assert "Introduction" in names
    assert "RelatedWork" in names
    assert "Method" in names
    assert "Conclusion" in names
    assert "References" in names
    assert out["section_meta"]["fallback_fulltext"] is False


def test_section_splitter_fallback_fulltext():
    parsed = {
        "paper_id": "y",
        "pages": [{"page": 1, "text": "Just some unstructured text without headings.", "dict": {"blocks": []}}],
        "full_text": "Just some unstructured text without headings.",
    }
    out = split_sections(parsed)
    assert out["sections"][0]["name"] == "FullText"
    assert out["section_meta"]["fallback_fulltext"] is True


def test_block_heading_detection():
    full_text = "Title\n\nAbstract\nBody\n\nRelated Work\nMore"
    pages = [{
        "page": 1,
        "text": full_text,
        "dict": {
            "blocks": [
                {
                    "type": 0,
                    "lines": [
                        {
                            "spans": [{"text": "Related Work", "size": 14.0, "bbox": [0, 0, 0, 0]}],
                            "bbox": [0, 0, 0, 0],
                        },
                        {
                            "spans": [{"text": "Body line", "size": 10.0, "bbox": [0, 0, 0, 0]}],
                            "bbox": [0, 0, 0, 0],
                        },
                    ],
                }
            ],
        },
    }]
    starts, names = find_block_section_starts(full_text, pages)
    assert any(name == "RelatedWork" for name, _ in starts)


def test_parse_references_section():
    text = (
        "References\n"
        "[1] Smith, A. Deep Learning for Mobility. NeurIPS, 2020. doi:10.1234/mobility.old\n"
        "[2] Lee, B. Event Forecasting. 2021."
    )
    result = parse_references_section(text)
    assert result["reference_meta"]["count"] == 2
    assert result["references"][0]["doi"] == "10.1234/mobility.old"
    assert result["references"][0]["year"] == 2020


def test_parse_reference_entry_doi():
    ref = parse_reference_entry("Jones, C. Graph Models. 2019. https://doi.org/10.5555/test.1")
    assert ref["doi"] == "10.5555/test.1"
    assert ref["year"] == 2019


def test_split_sections_strips_non_json_layout_dict():
    parsed = {
        "paper_id": "img",
        "pages": [{
            "page": 1,
            "text": "Title\n\nAbstract\nBody text.",
            "dict": {
                "blocks": [
                    {"type": 1, "image": b"\x89PNG\r\n\x1a\n"},
                    {
                        "type": 0,
                        "lines": [{
                            "spans": [{"text": "Abstract", "size": 14.0, "bbox": [0, 0, 0, 0]}],
                            "bbox": [0, 0, 0, 0],
                        }],
                    },
                ],
            },
        }],
        "full_text": "Title\n\nAbstract\nBody text.",
    }
    out = split_sections(parsed)
    assert "dict" not in out["pages"][0]
    json.dumps(out)
