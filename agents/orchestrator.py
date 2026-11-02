from agents.retriever import evidence_status
from rl.environment import TERMINAL_ACTIONS, encode_state
from tools.risk_classifier import classify_risk

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
        feature_explanation = (
            self.feature_explainer.explain(patient)
            if self.feature_explainer is not None
            else {"method": "none", "features": []}
        )
        similar_cases = self.memory.find_similar(patient)
        retrieved_context = (
            self.retriever.retrieve(patient, risk, feature_explanation)
            if self.retriever is not None
            else []
        )

        explanation = self.explainer.explain(
            patient,
            prob,
            feature_explanation=feature_explanation,
            similar_cases=similar_cases,
        )
        status, safety, recommendation = self._advise(
            patient, prob, risk, retrieved_context, similar_cases
        )
        policy = None
        if self.support_policy is not None:
            retrieved_context, status, safety, recommendation, policy = self._choose_next_step(
                patient,
                prob,
                risk,
                feature_explanation,
                similar_cases,
                (retrieved_context, status, safety, recommendation),
            )

        self.memory.store(patient, prob, risk)

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
        }

    def _advise(self, patient, prob, risk, retrieved_context, similar_cases):
        """Safety rules then recommendation for the current evidence (rules never see the policy)."""
        status = evidence_status(retrieved_context)
        safety = (
            self.safety_guard.assess(patient, prob, risk, evidence_status=status)
            if self.safety_guard is not None
            else {
                "alerts": [],
                "rules": [],
                "conflicts": [],
                "effective_risk": risk,
                "escalation": "routine_followup",
                "confidence_score": 1.0,
                "confidence_label": "High",
                "disclaimers": [],
            }
        )
        recommendation = self.recommender.recommend(
            patient,
            safety["effective_risk"],
            retrieved_context=retrieved_context,
            similar_cases=similar_cases,
            safety=safety,
        )
        return status, safety, recommendation

    def _choose_next_step(self, patient, prob, risk, feature_explanation, similar_cases, current):
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
                retrieved_context = self.retriever.retrieve(
                    patient, risk, feature_explanation, broaden=True
                )
                status, safety, recommendation = self._advise(
                    patient, prob, risk, retrieved_context, similar_cases
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
