import logging
import sys
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from typing import Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import get_settings
from main import build_agent
from tools.audit_logger import AuditLogger
from tools.what_if import ASKABLE_FIELDS

app = FastAPI(title="API hỗ trợ đánh giá nguy cơ sức khỏe")
settings = get_settings()
audit_logger = AuditLogger(settings.log_dir)
logger = logging.getLogger(__name__)
_agent_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="agent-init")
_agent_future: Future | None = None
_agent_lock = Lock()


def _start_agent_initialization():
    """Initialize the model and retrieval index outside the server startup path."""
    global _agent_future
    with _agent_lock:
        if _agent_future is None:
            _agent_future = _agent_executor.submit(build_agent)
            _agent_future.add_done_callback(_log_agent_initialization_failure)
        return _agent_future


def _log_agent_initialization_failure(future):
    try:
        future.result()
    except Exception:
        logger.exception("Agent initialization failed")


@app.on_event("startup")
def initialize_agent_in_background():
    # Let Uvicorn bind Render's port immediately. Model download/index creation can
    # take a while on a fresh, ephemeral free instance.
    _start_agent_initialization()


def _get_agent():
    future = _start_agent_initialization()
    try:
        return future.result()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Dịch vụ phân tích chưa khởi tạo được: {exc}",
        ) from exc


class PatientRequest(BaseModel):
    age: int = Field(..., ge=0, le=120)
    height_cm: Optional[float] = Field(None, ge=50, le=250)
    weight_kg: Optional[float] = Field(None, ge=2, le=300)
    bmi: Optional[float] = Field(None, gt=0, le=80)
    bp: int = Field(..., ge=0, le=260)
    high_chol: Optional[bool] = None
    chol_check: Optional[bool] = None
    smoker: Optional[bool] = None
    stroke: Optional[bool] = None
    heart_disease_or_attack: Optional[bool] = None
    phys_activity: Optional[bool] = None
    fruits: Optional[bool] = None
    veggies: Optional[bool] = None
    heavy_alcohol_consump: Optional[bool] = None
    any_healthcare: Optional[bool] = None
    no_doc_bc_cost: Optional[bool] = None
    general_health: Optional[int] = Field(None, ge=1, le=5)
    mental_health_days: Optional[int] = Field(None, ge=0, le=30)
    physical_health_days: Optional[int] = Field(None, ge=0, le=30)
    diff_walk: Optional[bool] = None
    sex: Optional[str] = Field(None, pattern="^(female|male|0|1|F|M|f|m)$")
    education: Optional[int] = Field(None, ge=1, le=6)
    income: Optional[int] = Field(None, ge=1, le=8)
    # Optional yes/no inputs the patient declined to answer; the agent will not ask again.
    skipped_fields: list[str] = Field(default_factory=list, max_length=len(ASKABLE_FIELDS))

    @field_validator("skipped_fields")
    @classmethod
    def known_skipped_fields(cls, fields):
        unknown = sorted(set(fields) - set(ASKABLE_FIELDS))
        if unknown:
            raise ValueError(f"Trường không thể bỏ qua: {', '.join(unknown)}.")
        return fields

    @model_validator(mode="after")
    def require_body_measurements(self):
        if self.bmi is None and (self.height_cm is None or self.weight_kg is None):
            raise ValueError("Cần cung cấp BMI hoặc cả chiều cao và cân nặng.")
        return self


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=500)
    n_results: int = Field(5, ge=1, le=10)


def _authorize(authorization: Optional[str] = Header(default=None)):
    if not settings.require_api_token:
        return
    if not settings.api_token:
        raise HTTPException(
            status_code=500, detail="Hệ thống yêu cầu mã truy cập API nhưng chưa được cấu hình."
        )
    expected = f"Bearer {settings.api_token}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Không có quyền truy cập.")


@app.get("/health")
def health():
    return {"status": "ok"}


def _assess(patient):
    request_id = str(uuid4())
    result = _get_agent().run(patient.model_dump(), request_id=request_id)
    audit_logger.log_decision(request_id, result["patient"], result)
    return request_id, result


def _summary(result):
    safety = result.get("safety", {})
    return {
        "risk": result["risk"],
        "probability": result["probability"],
        "confidence": safety.get("confidence_label"),
        "confidence_score": safety.get("confidence_score"),
        "escalation": safety.get("escalation"),
        "alerts": safety.get("alerts", []),
    }


@app.post("/predict")
def predict(patient: PatientRequest, _auth=Depends(_authorize)):
    return _assess(patient)[1]


@app.post("/predict/summary")
def predict_summary(patient: PatientRequest, _auth=Depends(_authorize)):
    return _summary(_assess(patient)[1])


@app.get("/history")
def history(limit: int = 25, _auth=Depends(_authorize)):
    return {"records": _get_agent().memory.get_all(limit=limit)}


@app.get("/v1/health")
def health_v1():
    return {
        "status": "ok",
        "version": "v1",
        "auth_required": settings.require_api_token,
    }


@app.post("/v1/predict")
def predict_v1(patient: PatientRequest, _auth=Depends(_authorize)):
    request_id, result = _assess(patient)
    return {**result, "request_id": request_id}


@app.post("/v1/predict/summary")
def predict_summary_v1(patient: PatientRequest, _auth=Depends(_authorize)):
    request_id, result = _assess(patient)
    return {"request_id": request_id, **_summary(result)}


@app.post("/v1/chat")
def chat_v1(request: ChatRequest, _auth=Depends(_authorize)):
    """Answer a free-text question from the diabetes KB; returns citations and the retrieval trace."""
    retriever = _get_agent().retriever
    if retriever is None:
        raise HTTPException(status_code=503, detail="Chưa có cơ sở tri thức để trả lời.")
    return retriever.ask(request.question, n_results=request.n_results)


@app.get("/v1/kb")
def kb_overview(_auth=Depends(_authorize)):
    """The knowledge graph behind the RAG: entities, relations, corpus sizes and which store serves it."""
    retriever = _get_agent().retriever
    if retriever is None:
        raise HTTPException(status_code=503, detail="Chưa có cơ sở tri thức.")
    try:
        graph = retriever.kb.graph()
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"Không đọc được cơ sở tri thức: {exc}"
        ) from exc
    return {
        "source": "neo4j",
        "neo4j_configured": bool(settings.neo4j_password),
        **graph,
    }


@app.get("/v1/kb/entities/{entity_id}")
def kb_entity(entity_id: str, _auth=Depends(_authorize)):
    """Relations touching one entity, each with the evidence passages and sources that support it."""
    retriever = _get_agent().retriever
    if retriever is None:
        raise HTTPException(status_code=503, detail="Chưa có cơ sở tri thức.")
    try:
        relations = retriever.kb.relations_with_evidence(entity_id, limit=60)
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"Không đọc được cơ sở tri thức: {exc}"
        ) from exc
    return {"entity_id": entity_id, "relations": relations}
