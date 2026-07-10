"""Tests for canonical paper identity."""

from pathlib import Path

from litgraph.utils.ids import new_paper_id, paper_id_from_path, paper_slug_from_metadata
from litgraph.utils.paper_identity import finalize_extraction_identity
from litgraph.utils.paper_registry import assign_paper_id, load_registry


def test_new_paper_id_is_opaque():
    pid = new_paper_id()
    assert pid.startswith("p_")
    assert pid != new_paper_id()


def test_paper_slug_from_metadata_uses_doi():
    slug = paper_slug_from_metadata(
        "Some Title",
        doi="10.1234/example.2024",
        year=2024,
        authors=["Smith, J."],
    )
    assert slug.startswith("doi_")


def test_paper_slug_from_metadata_accepts_string_year():
    slug = paper_slug_from_metadata(
        "Graph WaveNet",
        year="2019",
        authors=["Wu, Z."],
    )
    assert "2019" in slug
    assert "wu" in slug.lower()


def test_normalize_extraction_raw_coerces_year_and_page():
    from litgraph.extractor.llm_extractor import normalize_extraction_raw

    raw = normalize_extraction_raw(
        {
            "year": "2019",
            "methods": ["GWN"],
            "claims": [{"text": "x", "evidence_text": "y", "page": "2", "section": "Intro"}],
        }
    )
    assert raw["year"] == 2019
    assert raw["claims"][0]["page"] == 2


def test_finalize_extraction_identity_keeps_registry_id():
    parse_id = "p_abc123-def4"
    parsed = {"paper_id": parse_id, "path": "/papers/wrong_filename.pdf", "source_stem": "wrong_filename"}
    extraction = {"title": "BysGNN", "year": 2023, "methods": ["GNN"]}
    out = finalize_extraction_identity(parsed, extraction, doi=None)
    assert out["paper_id"] == parse_id
    assert out["source_stem"] == "wrong_filename"
    assert "slug" in out


def test_paper_registry_assigns_stable_id(project_tmp):
    litgraph_dir = project_tmp / ".litgraph"
    litgraph_dir.mkdir(parents=True, exist_ok=True)
    first = assign_paper_id(litgraph_dir, "papers/a.pdf", "hash1")
    second = assign_paper_id(litgraph_dir, "papers/a.pdf", "hash1")
    assert first == second
    registry = load_registry(litgraph_dir)
    assert registry["papers/a.pdf"]["paper_id"] == first


def test_paper_id_from_path_deprecated_still_works():
    assert paper_id_from_path(Path("11_zhang2017_stresnet.pdf")) == "11_zhang2017_stresnet"
