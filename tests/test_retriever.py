import pytest

from agents.recommender import RecommendationAgent
from agents.retriever import RetrievalAgent, evidence_status
from tools.local_embeddings import LocalEmbeddingModel


class WordEmbeddings(LocalEmbeddingModel):
    """Offline stand-in for the sentence-transformer: hashed bag of words, unit length."""

    name = "test-words"

    def __init__(self):
        super().__init__(dimensions=512)

    def embed_texts(self, texts):
        return [self.embed_text(text) for text in texts]


@pytest.fixture
def retriever(knowledge_graph, tmp_path):
    return RetrievalAgent(knowledge_graph, WordEmbeddings(), tmp_path, min_relevance=0.1)


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


def test_min_relevance_filters_everything_when_too_strict(knowledge_graph, tmp_path):
    strict = RetrievalAgent(knowledge_graph, WordEmbeddings(), tmp_path, min_relevance=0.99)

    assert strict.retrieve({}, "Low", {"features": []}) == []


def test_startup_fails_when_graph_is_down(tmp_path):
    class DownGraph:
        def all_evidence(self):
            raise ConnectionError("neo4j unreachable")

    with pytest.raises(ConnectionError, match="neo4j unreachable"):
        RetrievalAgent(DownGraph(), WordEmbeddings(), tmp_path)


def test_from_settings_requires_neo4j_password(tmp_path, monkeypatch):
    from core.config import get_settings

    monkeypatch.setenv("NEO4J_PASSWORD", "")
    with pytest.raises(ValueError, match="NEO4J_PASSWORD"):
        RetrievalAgent.from_settings(get_settings(), tmp_path / "chroma")


def test_from_settings_uses_neo4j(knowledge_graph, tmp_path, monkeypatch):
    from unittest.mock import Mock

    import agents.retriever as module
    from core.config import get_settings

    driver = Mock()
    graph = Mock(wraps=knowledge_graph)
    graph_factory = Mock(return_value=graph)
    monkeypatch.setenv("NEO4J_PASSWORD", "test-password")
    monkeypatch.setattr(module, "create_driver", lambda settings: driver)
    monkeypatch.setattr(module, "KnowledgeGraph", graph_factory)
    monkeypatch.setattr(module, "SemanticEmbeddingModel", WordEmbeddings)

    agent = RetrievalAgent.from_settings(get_settings(), tmp_path / "chroma")

    graph_factory.assert_called_once_with(driver, get_settings().neo4j_database)
    assert agent.kb is graph
    assert agent.collection.count() == len(knowledge_graph.all_evidence())
    driver.close.assert_not_called()


def test_from_settings_propagates_neo4j_error_and_closes_driver(tmp_path, monkeypatch):
    from unittest.mock import Mock

    import agents.retriever as module
    from core.config import get_settings

    driver = Mock()
    graph = Mock()
    graph.all_evidence.side_effect = ConnectionError("neo4j unreachable")
    monkeypatch.setenv("NEO4J_PASSWORD", "test-password")
    monkeypatch.setattr(module, "create_driver", lambda settings: driver)
    monkeypatch.setattr(module, "KnowledgeGraph", lambda *args: graph)

    with pytest.raises(ConnectionError, match="neo4j unreachable"):
        RetrievalAgent.from_settings(get_settings(), tmp_path / "chroma")
    driver.close.assert_called_once()


def test_graph_error_at_query_time_degrades_to_semantic_only(knowledge_graph, tmp_path):
    class FlakyKB:
        def risk_factor_names(self):
            return knowledge_graph.risk_factor_names()

        def all_evidence(self):
            return knowledge_graph.all_evidence()

        def support_for_risk_factors(self, keys):
            raise ConnectionError("lost connection")

    agent = RetrievalAgent(FlakyKB(), WordEmbeddings(), tmp_path, min_relevance=0.1)
    contexts = agent.retrieve({"glucose": 90}, "High", FEATURES)

    assert contexts and all(item["via"] == "semantic" for item in contexts)


def test_index_rebuilds_when_corpus_changes(knowledge_graph, tmp_path):
    first = RetrievalAgent(knowledge_graph, WordEmbeddings(), tmp_path)

    class ShrunkKB:
        def risk_factor_names(self):
            return {}

        def all_evidence(self):
            return knowledge_graph.all_evidence()[:3]

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

    assert "[1]" in text and "Nguồn tham khảo:" in text and contexts[0]["source_title"] in text


def test_recommendation_admits_missing_evidence():
    text = RecommendationAgent()._fallback_recommendation({}, "Medium", [])

    assert "Chưa truy xuất được bằng chứng hướng dẫn đủ phù hợp" in text
    assert "Nguồn tham khảo:" not in text


def test_ask_answers_with_citations_and_trace(retriever):
    reply = retriever.ask("Xét nghiệm nào dùng để chẩn đoán đái tháo đường?")

    assert reply["citations"] and reply["status"] in {"limited", "sufficient"}
    assert "[1]" in reply["answer"]
    scores = [c["final_score"] for c in reply["citations"]]
    assert scores == sorted(scores, reverse=True)
    trace = reply["trace"]
    assert trace["passages_in_index"] == len(retriever.evidence)
    assert trace["passages_above_floor"] >= len(reply["citations"])


def test_ask_uses_graph_factors_from_the_question(retriever):
    reply = retriever.ask("Hút thuốc lá có làm tăng nguy cơ tiểu đường không?", n_results=10)

    assert reply["trace"]["graph_factors"] == ["Smoker"]
    assert any(c["graph_boost"] for c in reply["citations"])


def test_ask_declines_when_nothing_is_relevant(knowledge_graph, tmp_path):
    strict = RetrievalAgent(knowledge_graph, WordEmbeddings(), tmp_path, min_relevance=0.95)
    reply = strict.ask("zzzz qqqq")

    assert reply["citations"] == [] and reply["status"] == "none"


def test_dosing_passages_are_detected_but_diagnostic_cutoffs_are_not():
    from agents.retriever import is_dosing_text

    assert is_dosing_text("Bắt đầu điều trị: 10 đ.v/ ngày hoặc 0,1-0,2 đv/kg/ngày")
    assert is_dosing_text("Dùng bắt đầu bằng liều 500mg x 2 lần /ngày")
    assert not is_dosing_text("Chẩn đoán đái tháo đường khi FPG ≥ 126 mg/dL hoặc HbA1c ≥ 6,5%")
    assert not is_dosing_text("community-based programs")


def test_dosing_passages_are_never_returned_to_users(retriever):
    assert retriever.withheld
    patient = {"glucose_measured": False}
    contexts = retriever.retrieve(patient, "High", FEATURES, n_results=50, broaden=True)
    assert not {c["evidence_id"] for c in contexts} & retriever.withheld

    answer = retriever.ask("Liều insulin khởi đầu là bao nhiêu?", n_results=50)
    assert not {c["evidence_id"] for c in answer["citations"]} & retriever.withheld
    assert answer["trace"]["withheld_dosing_passages"] == len(retriever.withheld)


def test_chat_uses_its_own_relevance_floor(knowledge_graph, tmp_path):
    lenient = RetrievalAgent(knowledge_graph, WordEmbeddings(), tmp_path / "a", min_relevance=0.1)
    strict = RetrievalAgent(
        knowledge_graph, WordEmbeddings(), tmp_path / "b", min_relevance=0.1, ask_min_relevance=0.99
    )
    question = "HbA1c bao nhiêu thì chẩn đoán đái tháo đường?"

    assert lenient.ask(question)["citations"]
    refused = strict.ask(question)
    assert refused["citations"] == [] and refused["trace"]["min_relevance"] == 0.99
    assert strict.retrieve({}, "Low", {"features": []})  # the patient flow keeps its own floor
