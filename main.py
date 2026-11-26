import json
import os
from pathlib import Path

from agents.explainer import ExplanationAgent
from agents.orchestrator import Orchestrator
from agents.recommender import RecommendationAgent
from agents.retriever import RetrievalAgent
from core.config import get_settings
from memory.store import MemoryAgent
from models.risk_model import RiskModel
from rl.policy import QPolicy
from tools.explainability import FeatureExplainer
from tools.safety import SafetyGuard
from tools.what_if import WhatIfSimulator

BASE_DIR = Path(__file__).resolve().parent
CHROMA_PATH = Path(os.getenv("CHROMA_PATH", str(BASE_DIR / "data" / "chroma")))


def build_agent():
    settings = get_settings()
    model = RiskModel()
    model.load_artifact(settings.model_artifact_path)

    explainer = ExplanationAgent()
    recommender = RecommendationAgent()
    # Patient history is looked up by ID; it does not need similarity scales.
    memory = MemoryAgent(CHROMA_PATH)
    feature_explainer = FeatureExplainer(model)
    retriever = RetrievalAgent.from_settings(settings)
    safety_guard = SafetyGuard(max_defaulted_penalty=settings.data_quality_max_penalty)

    support_policy = None
    if settings.support_policy_path.exists():
        support_policy = QPolicy.load(settings.support_policy_path)

    return Orchestrator(
        model,
        explainer,
        recommender,
        memory,
        feature_explainer=feature_explainer,
        retrieval_agent=retriever,
        safety_guard=safety_guard,
        support_policy=support_policy,
        what_if=WhatIfSimulator(model),
    )


def build_symptom_agent(base_agent):
    """Separate immutable model instance; reuse the existing KB and patient store."""
    from models.symptoms import SYMPTOM_ARTIFACT, SymptomRiskModel

    model = SymptomRiskModel().load_artifact(
        os.getenv("SYMPTOM_MODEL_ARTIFACT_PATH", str(SYMPTOM_ARTIFACT))
    )
    return Orchestrator(
        model,
        base_agent.explainer,
        base_agent.recommender,
        base_agent.memory,
        feature_explainer=FeatureExplainer(model),
        retrieval_agent=base_agent.retriever,
        safety_guard=base_agent.safety_guard,
        support_policy=base_agent.support_policy,
        what_if=WhatIfSimulator(model),
    )


if __name__ == "__main__":
    patient = {
        "age": 45,
        "height_cm": 170,
        "weight_kg": 82.4,
        "bp": 130,
    }
    result = build_agent().run(patient)
    print(json.dumps(result, indent=2))
