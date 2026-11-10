import os
from dataclasses import dataclass
from pathlib import Path


def _as_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    api_token: str
    require_api_token: bool
    log_dir: Path
    model_artifact_path: Path
    support_policy_path: Path
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    neo4j_database: str
    similarity_max_distance: float
    similarity_bp_scale: float
    data_quality_max_penalty: float


def get_settings():
    project_root = Path(__file__).resolve().parents[1]
    return Settings(
        api_token=os.getenv("API_TOKEN", ""),
        require_api_token=_as_bool(os.getenv("REQUIRE_API_TOKEN"), default=False),
        log_dir=Path(os.getenv("LOG_DIR", str(project_root / "logs"))),
        model_artifact_path=Path(
            os.getenv("MODEL_ARTIFACT_PATH", str(project_root / "artifacts" / "risk_model.joblib"))
        ),
        support_policy_path=Path(
            os.getenv(
                "SUPPORT_POLICY_PATH", str(project_root / "artifacts" / "support_policy.json")
            )
        ),
        neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", ""),
        neo4j_database=os.getenv("NEO4J_DATABASE", "neo4j"),
        # Similar cases: farther than this many spreads (RMS) are not "similar". Age and BMI
        # spreads come from the training data; systolic blood pressure has none there.
        similarity_max_distance=float(os.getenv("SIMILARITY_MAX_DISTANCE", "1.0")),
        similarity_bp_scale=float(os.getenv("SIMILARITY_BP_SCALE", "25")),
        # Largest data-quality deduction when every optional model input was auto-filled.
        data_quality_max_penalty=float(os.getenv("DATA_QUALITY_MAX_PENALTY", "0.2")),
    )
