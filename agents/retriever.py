import logging
import re

import numpy as np

from tools.neo4j_kb import KnowledgeGraph, create_driver
from tools.semantic_embeddings import SemanticEmbeddingModel
from tools.vietnamese import RISK_LABELS

logger = logging.getLogger(__name__)

# Thresholds are cosine scores of BAAI/bge-m3 and only mean something for that model. They come
# from score distributions on data/eval (labelled set, independent held-out chat questions and
# patient-profile queries), see docs/danh_gia_truy_xuat_va_do_tre.md:
# - MIN_RELEVANCE: patient-flow floor; unrelated questions top out at 0.45, profile queries'
#   5th passage never falls below 0.70.
# - CHAT_MIN_RELEVANCE: chat floor; near-topic out-of-scope questions (flu, lung cancer) top
#   out at 0.52, every labelled in-scope question scores at least 0.61.
# - STRONG_RELEVANCE: best passage needed for evidence_status "sufficient".
# - ASK_GRAPH_BOOST: chat graph boost; it only reorders near-ties (scores of the top ten sit
#   within ~0.08), a larger one let any graph-linked passage outrank the best match. The
#   patient flow keeps GRAPH_BOOST.
MIN_RELEVANCE = 0.5
CHAT_MIN_RELEVANCE = 0.55
STRONG_RELEVANCE = 0.6
ASK_GRAPH_BOOST = 0.03
GRAPH_BOOST = 0.15
BROAD_N_RESULTS = 5
BROAD_QUERY = (
    "Hướng dẫn tầm soát, chẩn đoán, phòng ngừa và điều trị đái tháo đường típ 2 ở người lớn,"
    " gồm xét nghiệm đường huyết, thay đổi lối sống và khi nào cần đi khám bác sĩ."
)
# Chat follows every graph link of the risk factors named in the question: INCREASES_RISK_OF
# (how the factor affects risk) and interventions / tests (what to do). Routing by the
# question's intent was tried twice (keyword lists; embedding examples, 28/30 intents right on
# the held-out set); neither answered better than following every link, so no intent is
# detected. See docs/danh_gia_truy_xuat_va_do_tre.md, section 3e.
ANSWER_PASSAGES = 3
ANSWER_CHARS = 320
SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+|\s+(?=-\s)")
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


def split_sentences(text):
    """Sentences and list items of a passage (split after . ! ? ; and before "- " bullets)."""
    return [s for s in SENTENCE_SPLIT.split(" ".join(text.split())) if s.strip()]


def focused_excerpt(text, question_vector, embed, limit=ANSWER_CHARS):
    """The sentences of `text` closest to the question, in passage order, about `limit` chars.

    A long passage often answers the question only in its middle, so cutting it from the start
    (`excerpt`) can drop exactly the part that was asked about; blind grading of whole answers
    preferred this on 11 held-out questions and the cut on 2. `embed` maps a list of
    sentences to unit vectors (the agent passes a per-passage cache).
    """
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    sentences = split_sentences(text)
    if len(sentences) < 2:
        return excerpt(text, limit)
    vectors = embed(sentences)
    scores = [sum(a * b for a, b in zip(v, question_vector)) for v in vectors]
    chosen, used = [], 0
    for index in sorted(range(len(sentences)), key=lambda i: scores[i], reverse=True):
        length = len(sentences[index]) + 1
        if chosen and used + length > limit:
            continue
        chosen.append(index)
        used += length
    if len(chosen) == 1 and len(sentences[chosen[0]]) > limit:
        return excerpt(sentences[chosen[0]], limit)
    chosen.sort()
    parts = []
    for position, index in enumerate(chosen):
        if position and index != chosen[position - 1] + 1:
            parts.append("…")
        parts.append(sentences[index])
    if chosen[0]:
        parts.insert(0, "…")
    if chosen[-1] != len(sentences) - 1:
        parts.append("…")
    return " ".join(parts)


def term_pattern(terms):
    """Whole-word, case-insensitive match of any term (longest first, so phrases win)."""
    terms = sorted({t.strip().lower() for t in terms if t and t.strip()}, key=len, reverse=True)
    if not terms:
        return None
    return re.compile(r"(?<!\w)(?:" + "|".join(map(re.escape, terms)) + r")(?!\w)", re.IGNORECASE)


def evidence_status(contexts):
    """none / limited / sufficient, judged from how many passages are relevant and how strongly."""
    if not contexts:
        return "none"
    if len(contexts) < 2 or contexts[0]["relevance"] < STRONG_RELEVANCE:
        return "limited"
    return "sufficient"


class RetrievalAgent:
    """Semantic search over the diabetes KB evidence, boosted by the graph's risk-factor links.

    Applications, evaluation and integration tests read knowledge from Neo4j.
    Unit tests may inject doubles; startup errors propagate to the caller.
    """

    def __init__(
        self,
        knowledge_base,
        embedding_model,
        min_relevance=MIN_RELEVANCE,
        ask_min_relevance=None,
    ):
        """`ask_min_relevance` defaults to `min_relevance`; from_settings sets the chat floor."""
        self.embedding_model = embedding_model
        self.min_relevance = min_relevance
        self.ask_min_relevance = min_relevance if ask_min_relevance is None else ask_min_relevance
        self.kb = knowledge_base
        self.kb_source = type(knowledge_base).__name__
        evidence = self.kb.all_evidence()

        self.factor_names = self.kb.risk_factor_names()
        # Chat questions are matched against each risk factor's name and KB `aliases`, so the
        # vocabulary is knowledge-base data; factors without a model key are found as well.
        terms = getattr(self.kb, "risk_factor_terms", dict)()
        self.factor_patterns = {
            factor_id: pattern
            for factor_id, row in terms.items()
            if (pattern := term_pattern([row["name"], *row.get("aliases", [])]))
        }
        self.evidence = {item["evidence_id"]: item for item in evidence}
        self.withheld = {i for i, item in self.evidence.items() if is_dosing_text(item["text"])}
        # evidence_id -> sentence vectors; the KB text is fixed for the agent's lifetime, so each
        # passage is split and embedded once, the first time it is shown in a chat answer.
        self._sentence_vectors = {}
        # The KB is small (~150 passages), so the index is a matrix of unit vectors built at
        # startup (well under a second on GPU) and searched by one matrix product.
        self.ids = [item["evidence_id"] for item in evidence]
        self.matrix = np.array(
            self.embedding_model.embed_texts(
                [f"{item['section'] or ''}. {item['text']}" for item in evidence]
            )
            if evidence
            else [],
            dtype=np.float32,
        )

    @classmethod
    def from_settings(cls, settings):
        """Initialize retrieval from the configured Neo4j database."""
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
                ask_min_relevance=CHAT_MIN_RELEVANCE,
            )
        except Exception:
            driver.close()
            raise

    def _scores(self, query_vector):
        """evidence_id -> cosine similarity with the query, for every indexed passage."""
        scores = self.matrix @ np.asarray(query_vector, dtype=np.float32)
        return dict(zip(self.ids, scores.tolist()))

    def retrieve(self, patient_data, risk, feature_explanation, n_results=3, broaden=False):
        """Top passages above the relevance floor; `broaden` adds a general-guidance query.

        The broadened search keeps each passage's best score over both queries, so it can
        surface passages the patient-specific query missed (used when evidence is thin).
        """
        if not self.ids:
            return []

        factors = self._risk_factors(patient_data, feature_explanation)
        queries = [self._query_text(patient_data, risk, factors)]
        if broaden:
            queries.append(BROAD_QUERY)
            n_results = max(n_results, BROAD_N_RESULTS)
        relevance = {}
        for query in queries:
            for evidence_id, score in self._scores(self.embedding_model.embed_text(query)).items():
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
        the question (risk links and intervention / test links). The answer is stitched from the
        question-closest sentences of the top passages (no LLM), each cited.
        """
        question = " ".join(str(question).split())
        factors = self._question_factors(question)
        trace = {
            "question": question,
            "embedding_model": self.embedding_model.name,
            "kb_source": self.kb_source,
            "passages_in_index": len(self.ids),
            "min_relevance": self.ask_min_relevance,
            "graph_factors": factors,
            "graph_boost": ASK_GRAPH_BOOST,
            "withheld_dosing_passages": len(self.withheld),
        }
        if not question or not trace["passages_in_index"]:
            return {"answer": NO_ANSWER, "citations": [], "status": "none", "trace": trace}

        question_vector = self.embedding_model.embed_text(question)
        semantic = self._scores(question_vector)
        trace["best_score"] = round(max(semantic.values()), 3)
        linked = self._graph_links(factors, by_id=True)
        risk_rows = self._risk_links(factors)
        for row in risk_rows:
            linked.setdefault(row["evidence_id"], []).append(
                {**row, "support_name": f"{row['factor_name']} → {row['condition_name']}"}
            )

        ranked = []
        for evidence_id, score in semantic.items():
            if score < self.ask_min_relevance or evidence_id in self.withheld:
                continue
            rows = linked.get(evidence_id, [])
            boost = ASK_GRAPH_BOOST if rows else 0.0
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
        shown = citations[:ANSWER_PASSAGES]
        lines = ["Theo các tài liệu y khoa trong cơ sở tri thức:"]
        for number, item in enumerate(shown, start=1):
            text = focused_excerpt(
                item["text"], question_vector, self._sentence_embedder(item["evidence_id"])
            )
            lines.append(f"- {text} [{number}]")
        if status == "limited":
            lines.append("(Bằng chứng tìm được còn hạn chế; hãy hỏi bác sĩ để được tư vấn thêm.)")
        answer = chr(10).join(lines)
        return {"answer": answer, "citations": citations, "status": status, "trace": trace}

    def _question_factors(self, question):
        """Ids of the risk factors whose name or KB alias appears in the question."""
        return [fid for fid, pattern in self.factor_patterns.items() if pattern.search(question)]

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
        return factors

    def _graph_links(self, factors, by_id=False):
        """evidence_id -> graph rows (risk factor + intervention/test name) that cite it.

        The patient flow passes model feature keys; chat passes risk-factor entity ids.
        """
        if not factors:
            return {}
        try:
            if by_id:
                rows = self.kb.support_for_factor_ids(factors)
            else:
                rows = self.kb.support_for_risk_factors(factors)
        except Exception as exc:
            logger.warning("Graph lookup failed (%s); using semantic search only", exc)
            return {}
        linked = {}
        for row in rows:
            linked.setdefault(row["evidence_id"], []).append(row)
        return linked

    def _sentence_embedder(self, evidence_id):
        def embed(sentences):
            if evidence_id not in self._sentence_vectors:
                self._sentence_vectors[evidence_id] = self.embedding_model.embed_texts(sentences)
            return self._sentence_vectors[evidence_id]

        return embed

    def _risk_links(self, factors):
        """INCREASES_RISK_OF rows for factor ids; [] when there are none or the graph fails."""
        if not factors or not hasattr(self.kb, "risk_evidence_for_factors"):
            return []
        try:
            return self.kb.risk_evidence_for_factors(factors)
        except Exception as exc:
            logger.warning("Graph risk lookup failed (%s); using semantic search only", exc)
            return []

    def _query_text(self, patient_data, risk, factors):
        parts = [f"Nguy cơ đái tháo đường típ 2 ở mức {RISK_LABELS.get(risk, risk).lower()}."]
        if factors:
            parts.append(
                "Yếu tố nguy cơ: " + ", ".join(self.factor_names[f].lower() for f in factors) + "."
            )
        parts.append("Nên tầm soát, xét nghiệm, thay đổi lối sống hoặc can thiệp y khoa nào?")
        return " ".join(parts)
