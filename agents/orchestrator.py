import logging

from agents.retriever import evidence_status
from rl.environment import TERMINAL_ACTIONS, encode_state
from tools.risk_classifier import classify_risk

logger = logging.getLogger(__name__)

MAX_POLICY_STEPS = 3


class Orchestrator:
    def __init__(
        self,
        model,
        explanation_agent,
        recommendation_agent,
        memory_agent,
        feature_explainer=None,
        retrieval_agent=None,
        safety_guard=None,
        support_policy=None,
    ):
        self.model = model
        self.explainer = explanation_agent
        self.recommender = recommendation_agent
        self.memory = memory_agent
        self.feature_explainer = feature_explainer
        self.retriever = retrieval_agent
        self.safety_guard = safety_guard
        self.support_policy = support_policy

    def run(self, patient_data):
        prob, patient = self.model.assess(patient_data)
        risk = classify_risk(prob, self.model.risk_bands)
        threshold = self.model.decision_threshold
        prediction = {
            "probability": prob,
            # 1 = flagged by the binary threshold chosen on validation; None when unknown.
            "label": int(prob >= threshold) if threshold is not None else None,
            "threshold": threshold,
            "risk_level": risk,
            "model": self.model.artifact_metadata.get("selected_model"),
            "model_version": self.model.model_version,
        }
        degraded = []
        feature_explanation = self._guard(
            degraded,
            "feature_explainer",
            lambda: (
                self.feature_explainer.explain(patient)
                if self.feature_explainer is not None
                else {"method": "none", "features": []}
            ),
            {"method": "none", "features": []},
        )
        similar_cases = self._guard(
            degraded, "memory_search", lambda: self.memory.find_similar(patient), []
        )
        retrieved_context = self._retrieve(patient, risk, feature_explanation, degraded)

        status, safety, recommendation = self._advise(
            patient, prob, risk, retrieved_context, similar_cases, feature_explanation, degraded
        )
        policy = None
        if self.support_policy is not None:
            retrieved_context, status, safety, recommendation, policy = self._guard(
                degraded,
                "support_policy",
                lambda: self._choose_next_step(
                    patient,
                    prob,
                    risk,
                    feature_explanation,
                    similar_cases,
                    (retrieved_context, status, safety, recommendation),
                    degraded,
                ),
                (retrieved_context, status, safety, recommendation, None),
            )

        # Explained last so it sees the final evidence status and safety outcome.
        explanation = self._guard(
            degraded,
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
        )
        self._guard(degraded, "memory_store", lambda: self.memory.store(patient, prob, risk), None)

        if degraded:
            safety = {
                **safety,
                "disclaimers": [
                    *safety["disclaimers"],
                    "Một số thành phần gặp lỗi ("
                    + ", ".join(item["component"] for item in degraded)
                    + "); kết quả này chưa đầy đủ.",
                ],
            }

        return {
            "probability": prob,
            "risk": risk,
            "prediction": prediction,
            "patient": patient,
            "feature_explanation": feature_explanation,
            "retrieved_context": retrieved_context,
            "evidence_status": status,
            "similar_cases": similar_cases,
            "safety": safety,
            "explanation": explanation,
            "recommendation": recommendation,
            "model": self.model.artifact_metadata,
            "policy": policy,
            "degraded": degraded,
        }

    @staticmethod
    def _guard(degraded, component, call, fallback):
        """Run an optional step; on failure record it in `degraded` and return `fallback`."""
        try:
            return call()
        except Exception as exc:
            logger.warning("%s failed: %s", component, exc)
            degraded.append({"component": component, "error": f"{type(exc).__name__}: {exc}"})
            return fallback

    def _retrieve(self, patient, risk, feature_explanation, degraded, broaden=False, previous=()):
        """Evidence search; if it fails, keep the `previous` passages instead of losing them."""
        if self.retriever is None:
            return list(previous)
        return self._guard(
            degraded,
            "retriever",
            lambda: self.retriever.retrieve(patient, risk, feature_explanation, broaden=broaden),
            list(previous),
        )

    def _advise(
        self,
        patient,
        prob,
        risk,
        retrieved_context,
        similar_cases,
        feature_explanation,
        degraded,
    ):
        """Safety rules then recommendation for the current evidence (rules never see the policy)."""
        status = evidence_status(retrieved_context)
        if self.safety_guard is None:
            safety = {
                "alerts": [],
                "rules": [],
                "conflicts": [],
                "effective_risk": risk,
                "escalation": "routine_followup",
                "confidence_score": 1.0,
                "confidence_label": "High",
                "disclaimers": [],
            }
        else:
            # A failed rule check must not read as "all clear": fail toward clinician review.
            safety = self._guard(
                degraded,
                "safety_guard",
                lambda: self.safety_guard.assess(patient, prob, risk, evidence_status=status),
                {
                    "alerts": ["Không kiểm tra được các luật an toàn; cần được bác sĩ đánh giá."],
                    "rules": [],
                    "conflicts": [],
                    "effective_risk": risk,
                    "escalation": "prompt_clinician_followup",
                    "confidence_score": 0.0,
                    "confidence_label": "Low",
                    "disclaimers": [],
                },
            )
        recommendation = self._guard(
            degraded,
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
        )
        return status, safety, recommendation

    def _choose_next_step(
        self, patient, prob, risk, feature_explanation, similar_cases, current, degraded
    ):
        """Let the support policy pick the next step; only evidence retrieval is acted on here.

        Requesting glucose cannot be done inside one API call, so it is reported as the
        next step. The rules keep precedence: a policy answer below the rules' escalation
        is replaced by escalation.
        """
        retrieved_context, status, safety, recommendation = current
        retrieved_more = False
        steps = []
        for _ in range(MAX_POLICY_STEPS):
            glucose = "unmeasured"
            if patient.get("glucose_measured", True):
                codes = {rule["code"] for rule in safety["rules"]}
                glucose = "elevated" if codes & {"GLU-200", "GLU-300"} else "normal"
            state = encode_state(risk, glucose, status, retrieved_more=retrieved_more)
            decision = self.support_policy.decide(state)
            action = decision["action"]
            step = {"action": action, "state": list(state), "source": decision["source"]}
            steps.append(step)
            if action == "retrieve_more_evidence" and self.retriever is not None:
                retrieved_more = True
                retrieved_context = self._retrieve(
                    patient,
                    risk,
                    feature_explanation,
                    degraded,
                    broaden=True,
                    previous=retrieved_context,
                )
                status, safety, recommendation = self._advise(
                    patient,
                    prob,
                    risk,
                    retrieved_context,
                    similar_cases,
                    feature_explanation,
                    degraded,
                )
                step["evidence_status_after"] = status
                continue
            break

        next_step = steps[-1]["action"]
        if next_step == "retrieve_more_evidence":  # no retriever configured
            next_step = "recommend_followup"
        overridden = (
            next_step in TERMINAL_ACTIONS
            and next_step != "escalate_to_clinician"
            and safety["escalation"] != "routine_followup"
        )
        if overridden:
            next_step = "escalate_to_clinician"
        policy = {
            "next_step": next_step,
            "overridden_by_rules": overridden,
            "steps": steps,
            "q_values": decision["q_values"],
            "version": self.support_policy.metadata.get("version"),
            "feedback": self.support_policy.metadata.get("feedback", "simulated"),
        }
        return retrieved_context, status, safety, recommendation, policy
