import os

from openai import OpenAI

from tools.vietnamese import ESCALATION_LABELS, EVIDENCE_LABELS, METHOD_LABELS, feature_label


class ExplanationAgent:
    def __init__(self, model_name="gpt-4o-mini"):
        self.model_name = model_name
        self.client = OpenAI() if os.getenv("OPENAI_API_KEY") else None

    def explain(
        self,
        patient_data,
        prob,
        feature_explanation=None,
        similar_cases=None,
        safety=None,
        evidence_status=None,
    ):
        if self.client is None:
            return self._fallback_explanation(
                patient_data, prob, feature_explanation, similar_cases, safety, evidence_status
            )

        prompt = f"""
        Patient data: {patient_data}
        Risk probability: {prob}
        Feature explanation: {feature_explanation}
        Similar prior cases (earlier model predictions, not confirmed outcomes): {similar_cases}
        Safety assessment (rules applied to the measurements): {safety}
        Guideline evidence status: {evidence_status}

        Explain in simple terms why this patient has this risk. If the safety assessment
        raised the risk or an escalation above the model estimate, say so and why.
        Viết hoàn toàn bằng tiếng Việt, dùng nhãn tiếng Việt cho các mã và đặc trưng.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model_name, messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception:
            fallback = self._fallback_explanation(
                patient_data, prob, feature_explanation, similar_cases, safety, evidence_status
            )
            return f"{fallback} Không thể tạo giải thích bằng LLM; đang dùng nội dung dự phòng."

    def _fallback_explanation(
        self,
        patient_data,
        prob,
        feature_explanation=None,
        similar_cases=None,
        safety=None,
        evidence_status=None,
    ):
        bmi = patient_data["bmi"]
        features = (feature_explanation or {}).get("features", [])
        if features:
            driver_text = self._driver_text(feature_explanation)
        else:
            driver_text = self._threshold_text(patient_data)
        memory_text = ""
        if similar_cases:
            memory_text = (
                f"Tìm thấy {len(similar_cases)} hồ sơ tương tự đã lưu; đây là các dự đoán"
                " trước đây của mô hình, chưa phải kết quả bệnh được xác nhận."
            )

        return (
            f"Mô hình ước tính nguy cơ {prob:.1%} với BMI tính được là {bmi:.1f}. "
            f"{driver_text}"
            f"{self._defaults_text(patient_data)}{memory_text}"
            f"{self._safety_text(safety)}{self._evidence_text(evidence_status)}"
        )

    def _driver_text(self, feature_explanation):
        """Describe only what the model used; auto-filled inputs are not claimed as patient facts."""
        method_key = feature_explanation.get("method", "model")
        method = METHOD_LABELS.get(method_key, method_key)
        features = [f for f in feature_explanation["features"] if not f.get("defaulted")]
        raising = [f["feature"] for f in features if f["direction"] == "raises risk"][:3]
        lowering = [f["feature"] for f in features if f["direction"] == "lowers risk"][:2]
        parts = []
        if raising:
            parts.append(f"tăng nguy cơ: {', '.join(map(feature_label, raising))}")
        if lowering:
            parts.append(f"giảm nguy cơ: {', '.join(map(feature_label, lowering))}")
        if not parts:
            return f"Giải thích bằng {method} không tìm thấy đầu vào có tác động đáng kể. "
        return f"Giải thích bằng {method} cho thấy {'; '.join(parts)}. "

    def _threshold_text(self, patient_data):
        """Used only when no model explanation is available: plain range checks, not model output."""
        notable = []
        if patient_data["age"] >= 55:
            notable.append("tuổi cao")
        if patient_data["bmi"] >= 30:
            notable.append("BMI cao")
        if patient_data["bp"] >= 140:
            notable.append("huyết áp cao")
        if not notable:
            return (
                "Chưa có giải thích từ mô hình; phần lớn số đo nằm trong khoảng nguy cơ thấp hơn. "
            )
        return f"Chưa có giải thích từ mô hình; các yếu tố đáng chú ý: {', '.join(notable)}. "

    def _defaults_text(self, patient_data):
        defaulted = patient_data.get("defaulted_fields", [])
        if not defaulted:
            return ""
        return f"Có {len(defaulted)} đầu vào tùy chọn chưa được cung cấp và đã được điền bằng giá trị mặc định. "

    def _safety_text(self, safety):
        if not safety or not safety.get("alerts"):
            return ""
        text = f" Luật an toàn: {' '.join(safety['alerts'][:2])}"
        if safety.get("escalation", "routine_followup") != "routine_followup":
            text += f" Hướng xử trí: {ESCALATION_LABELS.get(safety['escalation'], safety['escalation'])}."
        return text

    def _evidence_text(self, evidence_status):
        if evidence_status in ("none", "limited"):
            return f" Bằng chứng hướng dẫn cho hồ sơ này: {EVIDENCE_LABELS[evidence_status]}."
        return ""
