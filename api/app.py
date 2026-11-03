import sys
from pathlib import Path
from typing import Literal, Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field, model_validator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import get_settings
from main import agent
from tools.audit_logger import AuditLogger

app = FastAPI(title="API hỗ trợ đánh giá nguy cơ sức khỏe")
settings = get_settings()
audit_logger = AuditLogger(settings.log_dir)


class PatientRequest(BaseModel):
    age: int = Field(..., ge=0, le=120)
    height_cm: Optional[float] = Field(None, ge=50, le=250)
    weight_kg: Optional[float] = Field(None, ge=2, le=300)
    bmi: Optional[float] = Field(None, gt=0, le=80)
    bp: int = Field(..., ge=0, le=260)
    glucose: Optional[float] = Field(None, ge=0, le=500)
    glucose_context: Literal["unspecified", "fasting", "random", "after_meal", "unknown"] = (
        "unspecified"
    )
    glucose_unavailable: bool = False
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

    @model_validator(mode="after")
    def require_body_measurements(self):
        if self.bmi is None and (self.height_cm is None or self.weight_kg is None):
            raise ValueError("Cần cung cấp BMI hoặc cả chiều cao và cân nặng.")
        return self


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


@app.post("/predict")
def predict(patient: PatientRequest, _auth=Depends(_authorize)):
    result = agent.run(patient.model_dump())
    audit_logger.log_decision(str(uuid4()), result["patient"], result)
    return result


@app.post("/predict/summary")
def predict_summary(patient: PatientRequest, _auth=Depends(_authorize)):
    result = agent.run(patient.model_dump())
    audit_logger.log_decision(str(uuid4()), result["patient"], result)
    return {
        "risk": result["risk"],
        "probability": result["probability"],
        "confidence": result.get("safety", {}).get("confidence_label"),
        "confidence_score": result.get("safety", {}).get("confidence_score"),
        "escalation": result.get("safety", {}).get("escalation"),
        "alerts": result.get("safety", {}).get("alerts", []),
    }


@app.get("/history")
def history(limit: int = 25, _auth=Depends(_authorize)):
    return {"records": agent.memory.get_all(limit=limit)}


@app.get("/v1/health")
def health_v1():
    return {
        "status": "ok",
        "version": "v1",
        "auth_required": settings.require_api_token,
    }


@app.post("/v1/predict")
def predict_v1(patient: PatientRequest, _auth=Depends(_authorize)):
    result = agent.run(patient.model_dump())
    request_id = str(uuid4())
    audit_logger.log_decision(request_id, result["patient"], result)
    result["request_id"] = request_id
    return result


@app.post("/v1/predict/summary")
def predict_summary_v1(patient: PatientRequest, _auth=Depends(_authorize)):
    result = agent.run(patient.model_dump())
    request_id = str(uuid4())
    audit_logger.log_decision(request_id, result["patient"], result)
    return {
        "request_id": request_id,
        "risk": result["risk"],
        "probability": result["probability"],
        "confidence": result.get("safety", {}).get("confidence_label"),
        "confidence_score": result.get("safety", {}).get("confidence_score"),
        "escalation": result.get("safety", {}).get("escalation"),
        "alerts": result.get("safety", {}).get("alerts", []),
    }
