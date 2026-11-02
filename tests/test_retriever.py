import pytest

from agents.recommender import RecommendationAgent
from agents.retriever import RetrievalAgent, evidence_status
from tools.local_embeddings import LocalEmbeddingModel
from tools.neo4j_kb import FileKnowledgeBase, load_kb_file


class WordEmbeddings(LocalEmbeddingModel):
    """Offline stand-in for the sentence-transformer: hashed bag of words, unit length."""

    name = "test-words"

    def __init__(self):
        super().__init__(dimensions=512)

    def embed_texts(self, texts):
        return [self.embed_text(text) for text in texts]


@pytest.fixture(scope="module")
def file_kb():
    from core.config import get_settings

    return FileKnowledgeBase(load_kb_file(get_settings().kb_path))


@pytest.fixture
def retriever(file_kb, tmp_path):
    return RetrievalAgent(file_kb, WordEmbeddings(), tmp_path, min_relevance=0.1)


FEATURES = {"features": [{"feature": "BMI", "impact": 0.4}, {"feature": "HighBP", "impact": 0.2}]}


def test_retrieve_returns_cited_evidence(retriever):
    contexts = retriever.retrieve({"glucose_measured": False}, "High", FEATURES)

    assert contexts
    for item in contexts:
        assert item["evidence_id"] and item["source_title"] and item["text"]
        assert 0.1 <= item["relevance"] <= 1.0
    relevances = [item["relevance"] for item in contexts]
    assert relevances == sorted(relevances, reverse=True) or any(c["supports"] for c in contexts)


def test_graph_links_mark_evidence(retriever):
    contexts = retriever.retrieve({"glucose": 90}, "High", FEATURES, n_results=10)

    assert any(item["via"] == "graph+semantic" and item["supports"] for item in contexts)


def test_min_relevance_filters_everything_when_too_strict(file_kb, tmp_path):
    strict = RetrievalAgent(file_kb, WordEmbeddings(), tmp_path, min_relevance=0.99)

    assert strict.retrieve({}, "Low", {"features": []}) == []


def test_falls_back_to_file_kb_when_graph_is_down(file_kb, tmp_path):
    class DownGraph:
        def all_evidence(self):
            raise ConnectionError("neo4j unreachable")

    agent = RetrievalAgent(
        DownGraph(), WordEmbeddings(), tmp_path, fallback_kb=file_kb, min_relevance=0.1
    )

    assert agent.kb_source == "FileKnowledgeBase"
    assert agent.collection.count() == len(file_kb.all_evidence())


def test_graph_error_at_query_time_degrades_to_semantic_only(file_kb, tmp_path):
    class FlakyKB:
        def risk_factor_names(self):
            return file_kb.risk_factor_names()

        def all_evidence(self):
            return file_kb.all_evidence()

        def support_for_risk_factors(self, keys):
            raise ConnectionError("lost connection")

    agent = RetrievalAgent(FlakyKB(), WordEmbeddings(), tmp_path, min_relevance=0.1)
    contexts = agent.retrieve({"glucose": 90}, "High", FEATURES)

    assert contexts and all(item["via"] == "semantic" for item in contexts)


def test_index_rebuilds_when_corpus_changes(file_kb, tmp_path):
    first = RetrievalAgent(file_kb, WordEmbeddings(), tmp_path)

    class ShrunkKB:
        def risk_factor_names(self):
            return {}

        def all_evidence(self):
            return file_kb.all_evidence()[:3]

    second = RetrievalAgent(ShrunkKB(), WordEmbeddings(), tmp_path)

    assert first.collection.name != second.collection.name
    assert second.collection.count() == 3


def test_evidence_status_levels():
    strong = {"relevance": 0.6}
    assert evidence_status([]) == "none"
    assert evidence_status([strong]) == "limited"
    assert evidence_status([{"relevance": 0.35}, strong]) == "limited"
    assert evidence_status([strong, {"relevance": 0.5}]) == "sufficient"


def test_recommendation_cites_numbered_sources(retriever):
    contexts = retriever.retrieve({"glucose": 90}, "High", FEATURES)
    text = RecommendationAgent()._fallback_recommendation({}, "High", contexts)

    assert "[1]" in text and "Sources:" in text and contexts[0]["source_title"] in text


def test_recommendation_admits_missing_evidence():
    text = RecommendationAgent()._fallback_recommendation({}, "Medium", [])

    assert "No sufficiently relevant guideline evidence" in text
    assert "Sources:" not in text
