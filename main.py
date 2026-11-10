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
    # Age/BMI spreads come from the training data; bp has none, so use settings.
    scales = {
        "bp": settings.similarity_bp_scale,
        **model.input_spreads(),
    }
    memory = MemoryAgent(CHROMA_PATH, scales=scales, max_distance=settings.similarity_max_distance)
    feature_explainer = FeatureExplainer(model)
    retriever = RetrievalAgent.from_settings(settings, CHROMA_PATH)
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


if __name__ == "__main__":
    patient = {
        "age": 45,
        "height_cm": 170,
        "weight_kg": 82.4,
        "bp": 130,
    }
    result = build_agent().run(patient)
    print(json.dumps(result, indent=2))
