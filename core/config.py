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
    request_timeout_seconds: int
    log_dir: Path
    model_artifact_path: Path
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    neo4j_database: str
    kb_path: Path


def get_settings():
    project_root = Path(__file__).resolve().parents[1]
    return Settings(
        api_token=os.getenv("API_TOKEN", ""),
        require_api_token=_as_bool(os.getenv("REQUIRE_API_TOKEN"), default=False),
        request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "25")),
        log_dir=Path(os.getenv("LOG_DIR", str(project_root / "logs"))),
        model_artifact_path=Path(
            os.getenv("MODEL_ARTIFACT_PATH", str(project_root / "artifacts" / "risk_model.joblib"))
        ),
        neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", ""),
        neo4j_database=os.getenv("NEO4J_DATABASE", "neo4j"),
        kb_path=Path(os.getenv("KB_PATH", str(project_root / "data" / "kb" / "diabetes_kb.json"))),
    )
