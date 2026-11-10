import hashlib
import logging
import re

from tools.chroma_client import create_persistent_client
from tools.neo4j_kb import KnowledgeGraph, create_driver
from tools.semantic_embeddings import SemanticEmbeddingModel
from tools.vietnamese import RISK_LABELS

logger = logging.getLogger(__name__)

MIN_RELEVANCE = 0.3  # cosine similarity below this is treated as off-topic
STRONG_RELEVANCE = 0.45
# Chat questions are free text, so unrelated ones must be refused; this floor was chosen on
# data/eval/retrieval_questions.json (see docs/danh_gia_truy_xuat_va_do_tre.md). Questions
# built from a patient profile score >= 0.6, so the 0.3 floor above is not what limits them.
CHAT_MIN_RELEVANCE = 0.4
GRAPH_BOOST = 0.15
BROAD_N_RESULTS = 5
BROAD_QUERY = (
    "Hướng dẫn tầm soát, chẩn đoán, phòng ngừa và điều trị đái tháo đường típ 2 ở người lớn,"
    " gồm xét nghiệm đường huyết, thay đổi lối sống và khi nào cần đi khám bác sĩ."
)


# Question keywords -> risk-factor keys, so a chat question can use the graph links as well.
QUESTION_FACTORS = {
    "BMI": ("bmi", "béo", "thừa cân", "cân nặng", "giảm cân", "gầy"),
    "HighBP": ("huyết áp", "tăng huyết"),
    "Age": ("tuổi", "cao tuổi", "người già", "lớn tuổi"),
    "glucose": ("đường huyết", "glucose", "hba1c", "đường máu", "đường trong máu"),
    "PhysActivity": ("vận động", "tập thể dục", "thể thao", "đi bộ"),
    "Smoker": ("hút thuốc", "thuốc lá", "bỏ thuốc"),
}
ANSWER_PASSAGES = 3
ANSWER_CHARS = 320
NO_ANSWER = (
    "Tôi không tìm thấy nội dung phù hợp trong cơ sở tri thức về đái tháo đường để trả lời "
    "câu hỏi này. Bạn có thể hỏi về triệu chứng, chẩn đoán, xét nghiệm, yếu tố nguy cơ, "
    "phòng ngừa hoặc điều trị đái tháo đường típ 2."
)


# Passages that give medication doses (e.g. insulin units, "điều chỉnh liều") stay in the KB but
# are never shown to users: the system must not prescribe medication or dosage. Glucose cut-offs
# in mg/dL are diagnostic criteria, not doses, so they are not matched.
DOSING_PATTERN = re.compile(
    r"(?<!\w)liều(?!\w)|đ\.?\s?v\s*/\s*kg|(?<!\w)đ\.?\s?v(?!\w)|\d+\s*đơn vị|(?<!\w)units?(?!\w)",
    re.IGNORECASE,
)


def is_dosing_text(text):
    """True when a passage contains medication-dose instructions."""
    return bool(DOSING_PATTERN.search(text or ""))


def excerpt(text, limit=ANSWER_CHARS):
    """Shorten a passage to about `limit` characters, ending at a sentence if one fits."""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("; "))
    return (cut[: end + 1] if end > limit // 2 else cut.rsplit(" ", 1)[0]) + "…"


def evidence_status(contexts):
    """none / limited / sufficient, judged from how many passages are relevant and how strongly."""
    if not contexts:
        return "none"
    if len(contexts) < 2 or contexts[0]["relevance"] < STRONG_RELEVANCE:
        return "limited"
    return "sufficient"


class RetrievalAgent:
    """Semantic search over the diabetes KB evidence, boosted by the graph's risk-factor links.

    Application startup requires Neo4j via `from_settings`. Tests and offline evaluation
    may inject another knowledge base explicitly; startup errors never switch to JSON.
    """

    def __init__(
        self,
        knowledge_base,
        embedding_model,
        chroma_path,
        min_relevance=MIN_RELEVANCE,
        ask_min_relevance=None,
    ):
        self.embedding_model = embedding_model
        self.min_relevance = min_relevance
        self.ask_min_relevance = min_relevance if ask_min_relevance is None else ask_min_relevance
        self.kb = knowledge_base
        self.kb_source = type(knowledge_base).__name__
        evidence = self.kb.all_evidence()

        self.factor_names = self.kb.risk_factor_names()
        self.evidence = {item["evidence_id"]: item for item in evidence}
        self.withheld = {i for i, item in self.evidence.items() if is_dosing_text(item["text"])}
        self.client = create_persistent_client(chroma_path)
        self.collection = self._sync_collection(evidence)

    @classmethod
    def from_settings(cls, settings, chroma_path):
        """Require configured Neo4j; JSON is only a source for loading and offline tools."""
        if not settings.neo4j_password:
            raise ValueError(
                "Thiếu NEO4J_PASSWORD. Ứng dụng bắt buộc dùng Neo4j; "
                "hãy cấu hình và nạp biến môi trường trước khi khởi chạy."
            )
        driver = create_driver(settings)
        try:
            return cls(
                KnowledgeGraph(driver, settings.neo4j_database),
                SemanticEmbeddingModel(),
                chroma_path,
                ask_min_relevance=CHAT_MIN_RELEVANCE,
            )
        except Exception:
            driver.close()
            raise

    def _sync_collection(self, evidence):
        # The name hashes model + corpus, so changed KB text or a new model builds a fresh index.
        digest = hashlib.sha1(self.embedding_model.name.encode("utf-8"))
        for item in evidence:
            digest.update(f"{item['evidence_id']}\n{item['text']}\n".encode())
        name = f"kb_evidence_{digest.hexdigest()[:16]}"
        collection = self.client.get_or_create_collection(name, metadata={"hnsw:space": "cosine"})
        if collection.count():
            try:
                probe = self.embedding_model.embed_text("probe")
                collection.query(query_embeddings=[probe], n_results=1)
            except Exception as exc:
                logger.warning("Evidence index %s unreadable (%s); rebuilding", name, exc)
                self.client.delete_collection(name)
                collection = self.client.get_or_create_collection(
                    name, metadata={"hnsw:space": "cosine"}
                )
        if evidence and collection.count() != len(evidence):
            collection.upsert(
                ids=[item["evidence_id"] for item in evidence],
                documents=[item["text"] for item in evidence],
                embeddings=self.embedding_model.embed_texts(
                    [f"{item['section'] or ''}. {item['text']}" for item in evidence]
                ),
            )
        return collection

    def retrieve(self, patient_data, risk, feature_explanation, n_results=3, broaden=False):
        """Top passages above the relevance floor; `broaden` adds a general-guidance query.

        The broadened search keeps each passage's best score over both queries, so it can
        surface passages the patient-specific query missed (used when evidence is thin).
        """
        count = self.collection.count()
        if count == 0:
            return []

        factors = self._risk_factors(patient_data, feature_explanation)
        queries = [self._query_text(patient_data, risk, factors)]
        if broaden:
            queries.append(BROAD_QUERY)
            n_results = max(n_results, BROAD_N_RESULTS)
        relevance = {}
        for query in queries:
            results = self.collection.query(
                query_embeddings=[self.embedding_model.embed_text(query)],
                n_results=count,
                include=["distances"],
            )
            for evidence_id, distance in zip(results["ids"][0], results["distances"][0]):
                score = 1.0 - float(distance)
                relevance[evidence_id] = max(score, relevance.get(evidence_id, score))
        linked = self._graph_links(factors)

        contexts = []
        for evidence_id, score in relevance.items():
            if score < self.min_relevance or evidence_id in self.withheld:
                continue
            rows = linked.get(evidence_id, [])
            contexts.append(
                {
                    **self.citation(evidence_id),
                    "relevance": round(score, 3),
                    "via": "graph+semantic" if rows else "semantic",
                    "supports": list(dict.fromkeys(row["support_name"] for row in rows)),
                    # Model features whose graph links lead to this passage.
                    "factors": sorted({row["factor_key"] for row in rows}),
                }
            )

        contexts.sort(
            key=lambda c: c["relevance"] + (GRAPH_BOOST if c["supports"] else 0.0), reverse=True
        )
        return contexts[:n_results]

    def ask(self, question, n_results=5):
        """Answer a free-text question from the KB and return the full retrieval trace.

        Steps: embed the question, rank every passage by cosine similarity, drop those below
        the relevance floor, then boost passages that the graph links to risk factors named in
        the question. The answer is stitched from the top passages (no LLM), each cited.
        """
        question = " ".join(str(question).split())
        factors = self._question_factors(question)
        trace = {
            "question": question,
            "embedding_model": self.embedding_model.name,
            "kb_source": self.kb_source,
            "passages_in_index": self.collection.count(),
            "min_relevance": self.ask_min_relevance,
            "graph_factors": factors,
            "graph_boost": GRAPH_BOOST,
            "withheld_dosing_passages": len(self.withheld),
        }
        if not question or not trace["passages_in_index"]:
            return {"answer": NO_ANSWER, "citations": [], "status": "none", "trace": trace}

        results = self.collection.query(
            query_embeddings=[self.embedding_model.embed_text(question)],
            n_results=trace["passages_in_index"],
            include=["distances"],
        )
        semantic = {
            evidence_id: 1.0 - float(distance)
            for evidence_id, distance in zip(results["ids"][0], results["distances"][0])
        }
        trace["best_score"] = round(max(semantic.values()), 3)
        linked = self._graph_links(factors)

        ranked = []
        for evidence_id, score in semantic.items():
            if score < self.ask_min_relevance or evidence_id in self.withheld:
                continue
            rows = linked.get(evidence_id, [])
            boost = GRAPH_BOOST if rows else 0.0
            ranked.append(
                {
                    **self.citation(evidence_id),
                    "relevance": round(score, 3),
                    "graph_boost": boost,
                    "final_score": round(score + boost, 3),
                    "via": "graph+semantic" if rows else "semantic",
                    "supports": list(dict.fromkeys(row["support_name"] for row in rows)),
                }
            )
        ranked.sort(key=lambda c: c["final_score"], reverse=True)
        citations = ranked[:n_results]
        trace["passages_above_floor"] = len(ranked)
        trace["graph_linked"] = sum(1 for c in ranked if c["graph_boost"])

        if not citations:
            return {"answer": NO_ANSWER, "citations": [], "status": "none", "trace": trace}
        status = evidence_status(citations)
        lines = ["Theo các tài liệu y khoa trong cơ sở tri thức:"]
        for number, item in enumerate(citations[:ANSWER_PASSAGES], start=1):
            lines.append(f"- {excerpt(item['text'])} [{number}]")
        if status == "limited":
            lines.append("(Bằng chứng tìm được còn hạn chế; hãy hỏi bác sĩ để được tư vấn thêm.)")
        answer = chr(10).join(lines)
        return {"answer": answer, "citations": citations, "status": status, "trace": trace}

    def _question_factors(self, question):
        lowered = question.lower()
        return [
            key
            for key, words in QUESTION_FACTORS.items()
            if key in self.factor_names and any(word in lowered for word in words)
        ]

    def citation(self, evidence_id):
        """Display fields of one KB passage (no relevance score); None if the id is unknown."""
        item = self.evidence.get(evidence_id)
        if item is None:
            return None
        return {
            "evidence_id": evidence_id,
            "title": f"{item['source_title']} — {item['section']}",
            "text": item["text"],
            "source_id": item["source_id"],
            "source_title": item["source_title"],
            "publisher": item.get("publisher"),
            "year": item.get("year"),
            "url": item.get("url"),
        }

    def _risk_factors(self, patient_data, feature_explanation):
        factors = []
        for item in feature_explanation.get("features", []):
            feature = item["feature"]
            if feature in self.factor_names and item["impact"] > 0 and feature not in factors:
                factors.append(feature)
        # Glucose is not a model input, so it is judged from the raw value.
        if "glucose" not in factors and (
            not patient_data.get("glucose_measured", True) or patient_data.get("glucose", 0) >= 100
        ):
            factors.append("glucose")
        return factors

    def _graph_links(self, factors):
        """evidence_id -> graph rows (risk factor key + intervention/test name) that cite it."""
        if not factors:
            return {}
        try:
            rows = self.kb.support_for_risk_factors(factors)
        except Exception as exc:
            logger.warning("Graph lookup failed (%s); using semantic search only", exc)
            return {}
        linked = {}
        for row in rows:
            linked.setdefault(row["evidence_id"], []).append(row)
        return linked

    def _query_text(self, patient_data, risk, factors):
        parts = [f"Nguy cơ đái tháo đường típ 2 ở mức {RISK_LABELS.get(risk, risk).lower()}."]
        if factors:
            parts.append(
                "Yếu tố nguy cơ: " + ", ".join(self.factor_names[f].lower() for f in factors) + "."
            )
        if not patient_data.get("glucose_measured", True):
            parts.append("Chưa đo đường huyết nên cần xét nghiệm.")
        parts.append("Nên tầm soát, xét nghiệm, thay đổi lối sống hoặc can thiệp y khoa nào?")
        return " ".join(parts)
