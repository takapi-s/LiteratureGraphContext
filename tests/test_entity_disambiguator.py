"""Tests for build-time LLM entity disambiguation (limited B)."""

from litgraph.graph.entity_disambiguator import EntityDisambiguator


class _FakeProvider:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def complete_json(self, system: str, user: str):
        self.calls.append((system, user))
        return self.response


def test_disambiguator_picks_candidate(monkeypatch):
    fake = _FakeProvider({"choice": "Graph Neural Network"})
    monkeypatch.setattr(
        "litgraph.graph.entity_disambiguator.get_provider",
        lambda *_args, **_kwargs: fake,
    )
    disambiguator = EntityDisambiguator({
        "disambiguation_enabled": True,
        "llm_provider": "openai",
    })
    result = disambiguator.disambiguate(
        "GNN",
        "method",
        ["Graph Neural Network", "Graph Convolutional Network"],
    )
    assert result == "Graph Neural Network"
    assert fake.calls


def test_disambiguator_new_returns_none(monkeypatch):
    fake = _FakeProvider({"choice": "NEW"})
    monkeypatch.setattr(
        "litgraph.graph.entity_disambiguator.get_provider",
        lambda *_args, **_kwargs: fake,
    )
    disambiguator = EntityDisambiguator({"disambiguation_enabled": True})
    assert disambiguator.disambiguate("STGCN", "method", ["Graph Neural Network"]) is None


def test_disambiguator_skips_when_disabled():
    disambiguator = EntityDisambiguator({"disambiguation_enabled": False})
    assert disambiguator.disambiguate("GNN", "method", ["Graph Neural Network"]) is None


def test_disambiguator_skips_on_provider_error(monkeypatch):
    def _raise(*_args, **_kwargs):
        raise RuntimeError("no api key")

    monkeypatch.setattr("litgraph.graph.entity_disambiguator.get_provider", _raise)
    disambiguator = EntityDisambiguator({"disambiguation_enabled": True})
    assert disambiguator.disambiguate("GNN", "method", ["Graph Neural Network"]) is None
