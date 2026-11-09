from agents.retriever import evidence_status
from tools.vietnamese import EVIDENCE_LABELS


class AdvisorAgent:
    """Turns a diagnosis into advice: RAG over the Neo4j KB, then recommendation and explanation.

    Every step is optional; a failure is noted in the run log and replaced by a fixed text or
    by the previous evidence, so the advice never blocks the diagnosis.
    """

    def __init__(self, retriever, recommender, explainer):
        self.retriever = retriever
        self.recommender = recommender
        self.explainer = explainer

    def retrieve(self, patient, risk, feature_explanation, log, broaden=False, previous=()):
        """Evidence search; if it fails, keep the `previous` passages instead of losing them."""
        if self.retriever is None:
            return list(previous)
        return log.guard(
            "retriever",
            lambda: self.retriever.retrieve(patient, risk, feature_explanation, broaden=broaden),
            list(previous),
            detail=lambda value: (
                f"{'tìm mở rộng, ' if broaden else ''}{len(value)} đoạn bằng chứng"
                f" ({EVIDENCE_LABELS[evidence_status(value)]})"
            ),
            on_failure="giữ các đoạn bằng chứng trước đó",
        )

    def recommend(
        self, patient, safety, retrieved_context, similar_cases, feature_explanation, log
    ):
        return log.guard(
            "recommender",
            lambda: self.recommender.recommend(
                patient,
                safety["effective_risk"],
                retrieved_context=retrieved_context,
                similar_cases=similar_cases,
                safety=safety,
                feature_explanation=feature_explanation,
            ),
            "Không tạo được khuyến nghị; hãy khám bác sĩ để được theo dõi.",
            detail=lambda value: "đã tạo khuyến nghị",
            on_failure="dùng văn bản cố định",
        )

    def explain(self, patient, prob, feature_explanation, similar_cases, safety, status, log):
        return log.guard(
            "explainer",
            lambda: self.explainer.explain(
                patient,
                prob,
                feature_explanation=feature_explanation,
                similar_cases=similar_cases,
                safety=safety,
                evidence_status=status,
            ),
            "Không tạo được giải thích; xem phần tác động đặc trưng để biết các yếu tố ảnh hưởng đến mô hình.",
            detail=lambda value: "đã tạo giải thích",
            on_failure="dùng văn bản cố định",
        )
