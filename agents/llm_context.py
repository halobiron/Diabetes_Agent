"""What an LLM prompt may present as the patient's own answers.

Optional model inputs the patient did not give are filled with training defaults so the
model can score them (`defaulted_fields`). Those values are not facts about the patient:
an LLM shown `phys_activity: 1` writes "the patient exercises regularly". Prompts therefore
get the supplied inputs only, plus an explicit list of what is unknown.
"""

from models.risk_model import RiskModel
from tools.vietnamese import feature_label

# Model feature -> key of the same input in the prepared patient dict.
PATIENT_KEY = {**RiskModel.FEATURE_KEYS, "Sex": "sex"}
# Bookkeeping keys that describe the request rather than the patient.
INTERNAL_KEYS = (
    "defaulted_fields",
    "skipped_fields",
    "optional_field_count",
    "patient_id",
    "unanswered_fields",
    "screening_mode",
)


def supplied_inputs(patient):
    """The patient dict without auto-filled values and bookkeeping keys."""
    hidden = {PATIENT_KEY.get(feature, feature) for feature in patient.get("defaulted_fields", [])}
    return {
        key: value
        for key, value in patient.items()
        if key not in hidden and key not in INTERNAL_KEYS
    }


def unknown_inputs(patient):
    """Vietnamese labels of the inputs the patient did not give."""
    missing = dict.fromkeys(
        [*patient.get("defaulted_fields", []), *patient.get("unanswered_fields", [])]
    )
    return [feature_label(feature) for feature in missing]


def supplied_features(feature_explanation):
    """The feature explanation without the auto-filled inputs."""
    explanation = dict(feature_explanation or {})
    explanation["features"] = [f for f in explanation.get("features", []) if not f.get("defaulted")]
    return explanation


def unknown_inputs_instruction(patient):
    """Prompt text that forbids stating anything about the inputs the patient did not give."""
    unknown = unknown_inputs(patient)
    if not unknown:
        return "Người dùng đã trả lời đủ các mục tùy chọn."
    if patient.get("screening_mode") == "symptoms":
        return (
            "Người dùng CHƯA trả lời các mục sau, không được suy diễn có hoặc không có: "
            + ", ".join(unknown)
            + ". Các mục này không được dùng để chấm mô hình triệu chứng."
        )
    return (
        "Người dùng CHƯA trả lời các mục sau; mô hình chỉ tạm dùng giá trị mặc định để tính: "
        + ", ".join(unknown)
        + ". Không được nói bệnh nhân có hay không có các mục này, cũng không được khen hay"
        " nhắc thói quen của họ về các mục này; nếu cần, chỉ gợi ý người dùng bổ sung thông tin."
    )
