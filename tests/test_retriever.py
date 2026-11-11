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
def retriever(knowledge_graph):
    return RetrievalAgent(knowledge_graph, WordEmbeddings(), min_relevance=0.1)


FEATURES = {"features": [{"feature": "BMI", "impact": 0.4}, {"feature": "HighBP", "impact": 0.2}]}


def test_retrieve_returns_cited_evidence(retriever):
    contexts = retriever.retrieve({}, "High", FEATURES)

    assert contexts
    for item in contexts:
        assert item["evidence_id"] and item["source_title"] and item["text"]
        assert 0.1 <= item["relevance"] <= 1.0
    relevances = [item["relevance"] for item in contexts]
    assert relevances == sorted(relevances, reverse=True) or any(c["supports"] for c in contexts)


def test_graph_links_mark_evidence(retriever):
    contexts = retriever.retrieve({"bp": 120}, "High", FEATURES, n_results=10)

    assert any(item["via"] == "graph+semantic" and item["supports"] for item in contexts)


def test_min_relevance_filters_everything_when_too_strict(knowledge_graph):
    strict = RetrievalAgent(knowledge_graph, WordEmbeddings(), min_relevance=0.99)

    assert strict.retrieve({}, "Low", {"features": []}) == []


def test_startup_fails_when_graph_is_down():
    class DownGraph:
        def all_evidence(self):
            raise ConnectionError("neo4j unreachable")

    with pytest.raises(ConnectionError, match="neo4j unreachable"):
        RetrievalAgent(DownGraph(), WordEmbeddings())


def test_from_settings_requires_neo4j_password(monkeypatch):
    from core.config import get_settings

    monkeypatch.setenv("NEO4J_PASSWORD", "")
    with pytest.raises(ValueError, match="NEO4J_PASSWORD"):
        RetrievalAgent.from_settings(get_settings())


def test_from_settings_uses_neo4j(knowledge_graph, monkeypatch):
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

    agent = RetrievalAgent.from_settings(get_settings())

    graph_factory.assert_called_once_with(driver, get_settings().neo4j_database)
    assert agent.kb is graph
    assert len(agent.ids) == len(knowledge_graph.all_evidence())
    driver.close.assert_not_called()


def test_from_settings_propagates_neo4j_error_and_closes_driver(monkeypatch):
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
        RetrievalAgent.from_settings(get_settings())
    driver.close.assert_called_once()


def test_graph_error_at_query_time_degrades_to_semantic_only(knowledge_graph):
    class FlakyKB:
        def risk_factor_names(self):
            return knowledge_graph.risk_factor_names()

        def all_evidence(self):
            return knowledge_graph.all_evidence()

        def support_for_risk_factors(self, keys):
            raise ConnectionError("lost connection")

    agent = RetrievalAgent(FlakyKB(), WordEmbeddings(), min_relevance=0.1)
    contexts = agent.retrieve({"bp": 120}, "High", FEATURES)

    assert contexts and all(item["via"] == "semantic" for item in contexts)


def test_evidence_status_levels():
    strong = {"relevance": 0.6}
    assert evidence_status([]) == "none"
    assert evidence_status([strong]) == "limited"
    assert evidence_status([{"relevance": 0.35}, strong]) == "limited"
    assert evidence_status([strong, {"relevance": 0.5}]) == "sufficient"


def test_recommendation_cites_numbered_sources(retriever):
    contexts = retriever.retrieve({"bp": 120}, "High", FEATURES)
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

    assert reply["trace"]["graph_factors"] == ["smoking"]
    assert any(c["graph_boost"] for c in reply["citations"])


def test_ask_declines_when_nothing_is_relevant(knowledge_graph):
    strict = RetrievalAgent(knowledge_graph, WordEmbeddings(), min_relevance=0.95)
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
    patient = {}
    contexts = retriever.retrieve(patient, "High", FEATURES, n_results=50, broaden=True)
    assert not {c["evidence_id"] for c in contexts} & retriever.withheld

    answer = retriever.ask("Liều insulin khởi đầu là bao nhiêu?", n_results=50)
    assert not {c["evidence_id"] for c in answer["citations"]} & retriever.withheld
    assert answer["trace"]["withheld_dosing_passages"] == len(retriever.withheld)


def test_chat_uses_its_own_relevance_floor(knowledge_graph):
    lenient = RetrievalAgent(knowledge_graph, WordEmbeddings(), min_relevance=0.1)
    strict = RetrievalAgent(
        knowledge_graph, WordEmbeddings(), min_relevance=0.1, ask_min_relevance=0.99
    )
    question = "HbA1c bao nhiêu thì chẩn đoán đái tháo đường?"

    assert lenient.ask(question)["citations"]
    refused = strict.ask(question)
    assert refused["citations"] == [] and refused["trace"]["min_relevance"] == 0.99
    assert strict.retrieve({}, "Low", {"features": []})  # the patient flow keeps its own floor


def test_focused_excerpt_keeps_the_sentence_that_answers_the_question():
    from agents.retriever import excerpt, focused_excerpt

    filler = "Đái tháo đường là bệnh mạn tính phổ biến ở người lớn hiện nay. " * 4
    text = filler + "Càng nhiều mô mỡ quanh bụng thì tế bào càng đề kháng insulin. " + filler

    def embed(sentences):  # only the sentence about fat matches the question vector [1, 0]
        return [[1.0, 0.0] if "mỡ" in s else [0.0, 1.0] for s in sentences]

    focused = focused_excerpt(text, [1.0, 0.0], embed, limit=160)

    assert "mô mỡ quanh bụng" in focused and len(focused) <= 170
    assert " … Càng nhiều mô mỡ" in focused and focused.endswith("…")  # gaps are marked
    assert "mô mỡ" not in excerpt(text, 160)  # the old cut from the start lost the answer
    assert focused_excerpt("Ngắn gọn.", [1.0, 0.0], embed) == "Ngắn gọn."


def linked_evidence(kb, factor):
    risk = {r["evidence_id"] for r in kb.risk_evidence_for_factors([factor])}
    support = {r["evidence_id"] for r in kb.support_for_factor_ids([factor])}
    return risk, support


@pytest.mark.parametrize(
    "question, factor",
    [
        ("Béo phì ảnh hưởng đến nguy cơ tiểu đường thế nào?", "high_bmi"),
        # family history has no model feature key, so only id-based lookups reach it
        ("Tiền sử gia đình có làm tăng nguy cơ tiểu đường không?", "family_history"),
    ],
)
def test_chat_boosts_exactly_the_factor_graph_links(knowledge_graph, question, factor):
    agent = RetrievalAgent(knowledge_graph, WordEmbeddings(), min_relevance=0.0)
    reply = agent.ask(question, n_results=200)

    risk, support = linked_evidence(knowledge_graph, factor)
    boosted = {c["evidence_id"] for c in reply["citations"] if c["graph_boost"]}
    assert reply["trace"]["graph_factors"] == [factor]
    assert risk and support and boosted == (risk | support) - agent.withheld
    assert reply["answer"].startswith("Theo các tài liệu")


def test_risk_lookup_error_keeps_the_other_graph_links(knowledge_graph):
    class NoRiskKB:
        def __getattr__(self, name):
            return getattr(knowledge_graph, name)

        def risk_evidence_for_factors(self, ids):
            raise ConnectionError("lost connection")

    agent = RetrievalAgent(NoRiskKB(), WordEmbeddings(), min_relevance=0.0)
    reply = agent.ask("Hút thuốc lá có làm tăng nguy cơ tiểu đường không?", n_results=200)

    _, support = linked_evidence(knowledge_graph, "smoking")
    boosted = {c["evidence_id"] for c in reply["citations"] if c["graph_boost"]}
    assert reply["trace"]["graph_factors"] == ["smoking"]
    assert boosted == support - agent.withheld  # only the lookup that worked


def test_sentence_vectors_are_embedded_once_per_passage(knowledge_graph):
    agent = RetrievalAgent(knowledge_graph, WordEmbeddings(), min_relevance=0.1)
    question = "Béo phì ảnh hưởng đến nguy cơ tiểu đường thế nào?"
    first = agent.ask(question)
    agent.embedding_model.embed_texts = None  # any further batch embedding would fail

    assert agent.ask(question)["answer"] == first["answer"]


def test_question_factors_come_from_kb_names_and_aliases(retriever, knowledge_graph):
    terms = knowledge_graph.risk_factor_terms()
    assert all(row["aliases"] for row in terms.values())  # every factor carries KB synonyms

    found = retriever._question_factors
    assert found("Mập có dễ bị tiểu đường không?") == ["high_bmi"]  # colloquial alias
    assert found("Bố mẹ tôi đều bị tiểu đường thì tôi có bị không?") == ["family_history"]
    assert found("Tôi bị tăng huyết áp") == ["high_bp"]  # the factor's own name also counts
    assert found("Tiểu đường típ 1 với típ 2 khác nhau chỗ nào?") == []
    assert found("Người bị gầy") == []  # whole words only: "gầy" is not an alias of anything
