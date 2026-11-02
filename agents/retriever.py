import hashlib
import logging

from tools.chroma_client import create_persistent_client
from tools.neo4j_kb import FileKnowledgeBase, KnowledgeGraph, create_driver, load_kb_file
from tools.semantic_embeddings import SemanticEmbeddingModel

logger = logging.getLogger(__name__)

MIN_RELEVANCE = 0.3  # cosine similarity below this is treated as off-topic
STRONG_RELEVANCE = 0.45
GRAPH_BOOST = 0.15
BROAD_N_RESULTS = 5
BROAD_QUERY = (
    "Type 2 diabetes screening, diagnosis, prevention and management guidance for adults,"
    " including blood glucose testing, lifestyle changes and when to see a clinician."
)


def evidence_status(contexts):
    """none / limited / sufficient, judged from how many passages are relevant and how strongly."""
    if not contexts:
        return "none"
    if len(contexts) < 2 or contexts[0]["relevance"] < STRONG_RELEVANCE:
        return "limited"
    return "sufficient"


class RetrievalAgent:
    """Semantic search over the diabetes KB evidence, boosted by the graph's risk-factor links.

    `knowledge_base` is a KnowledgeGraph (Neo4j) or FileKnowledgeBase; if the graph is
    unreachable at startup we fall back to `fallback_kb` (the same KB read from the JSON file).
    """

    def __init__(
        self,
        knowledge_base,
        embedding_model,
        chroma_path,
        fallback_kb=None,
        min_relevance=MIN_RELEVANCE,
    ):
        self.embedding_model = embedding_model
        self.min_relevance = min_relevance
        self.kb = knowledge_base
        self.kb_source = type(knowledge_base).__name__
        try:
            evidence = self.kb.all_evidence()
        except Exception as exc:
            if fallback_kb is None:
                raise
            logger.warning("Knowledge graph unavailable (%s); using KB file instead", exc)
            self.kb = fallback_kb
            self.kb_source = type(fallback_kb).__name__
            evidence = self.kb.all_evidence()

        self.factor_names = self.kb.risk_factor_names()
        self.evidence = {item["evidence_id"]: item for item in evidence}
        self.client = create_persistent_client(chroma_path)
        self.collection = self._sync_collection(evidence)

    @classmethod
    def from_settings(cls, settings, chroma_path):
        """Neo4j when NEO4J_PASSWORD is set, otherwise the KB file; the file is also the fallback."""
        file_kb = FileKnowledgeBase(load_kb_file(settings.kb_path))
        kb = file_kb
        if settings.neo4j_password:
            kb = KnowledgeGraph(create_driver(settings), settings.neo4j_database)
        return cls(kb, SemanticEmbeddingModel(), chroma_path, fallback_kb=file_kb)

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
            if score < self.min_relevance:
                continue
            item = self.evidence[evidence_id]
            supports = linked.get(evidence_id, [])
            contexts.append(
                {
                    "evidence_id": evidence_id,
                    "title": f"{item['source_title']} — {item['section']}",
                    "text": item["text"],
                    "source_id": item["source_id"],
                    "source_title": item["source_title"],
                    "publisher": item.get("publisher"),
                    "year": item.get("year"),
                    "url": item.get("url"),
                    "relevance": round(score, 3),
                    "via": "graph+semantic" if supports else "semantic",
                    "supports": supports,
                }
            )

        contexts.sort(
            key=lambda c: c["relevance"] + (GRAPH_BOOST if c["supports"] else 0.0), reverse=True
        )
        return contexts[:n_results]

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
        """evidence_id -> names of interventions/tests the graph ties to the patient's risk factors."""
        if not factors:
            return {}
        try:
            rows = self.kb.support_for_risk_factors(factors)
        except Exception as exc:
            logger.warning("Graph lookup failed (%s); using semantic search only", exc)
            return {}
        linked = {}
        for row in rows:
            names = linked.setdefault(row["evidence_id"], [])
            if row["support_name"] not in names:
                names.append(row["support_name"])
        return linked

    def _query_text(self, patient_data, risk, factors):
        parts = [f"Type 2 diabetes risk is {risk.lower()}."]
        if factors:
            parts.append(
                "Risk factors: " + ", ".join(self.factor_names[f].lower() for f in factors) + "."
            )
        if not patient_data.get("glucose_measured", True):
            parts.append("Blood glucose has not been measured, so testing is needed.")
        parts.append("What screening, testing, and lifestyle or clinical steps are recommended?")
        return " ".join(parts)
