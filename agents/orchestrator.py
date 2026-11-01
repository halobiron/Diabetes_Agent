from tools.risk_classifier import classify_risk


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
    ):
        self.model = model
        self.explainer = explanation_agent
        self.recommender = recommendation_agent
        self.memory = memory_agent
        self.feature_explainer = feature_explainer
        self.retriever = retrieval_agent
        self.safety_guard = safety_guard

    def run(self, patient_data):
        prob, patient = self.model.assess(patient_data)
        risk = classify_risk(prob, self.model.artifact_metadata.get("risk_bands"))
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
        safety = (
            self.safety_guard.assess(patient, prob, risk)
            if self.safety_guard is not None
            else {
                "alerts": [],
                "escalation": "routine_followup",
                "confidence_score": 1.0,
                "confidence_label": "High",
                "disclaimers": [],
            }
        )
        recommendation = self.recommender.recommend(
            patient,
            risk,
            retrieved_context=retrieved_context,
            similar_cases=similar_cases,
            safety=safety,
        )

        self.memory.store(patient, prob, risk)

        return {
            "probability": prob,
            "risk": risk,
            "patient": patient,
            "feature_explanation": feature_explanation,
            "retrieved_context": retrieved_context,
            "similar_cases": similar_cases,
            "safety": safety,
            "explanation": explanation,
            "recommendation": recommendation,
            "model": self.model.artifact_metadata,
        }
