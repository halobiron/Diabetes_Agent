from tools.rules import RuleContext, RuleEngine


class SafetyGuard:
    def __init__(self, engine=None, max_defaulted_penalty=0.2):
        self.engine = engine or RuleEngine()
        self.max_defaulted_penalty = max_defaulted_penalty

    def assess(self, patient, probability, risk, evidence_status=None):
        confidence_reasons = self._confidence_reasons(patient)
        confidence_score, confidence_label = self._confidence(patient)
        outcome = self.engine.evaluate(
            RuleContext(
                patient=patient,
                probability=probability,
                risk=risk,
                evidence_status=evidence_status,
                confidence_label=confidence_label,
            )
        )
        disclaimers = [
            "Nguyên mẫu phục vụ học tập; không phải thiết bị chẩn đoán y tế.",
            "Quyết định lâm sàng cần đánh giá của bác sĩ cùng kết quả xét nghiệm và số đo thực tế.",
        ]

        return {
            **outcome,
            "confidence_score": confidence_score,
            "confidence_label": confidence_label,
            "confidence_reasons": confidence_reasons,
            "confidence_note": (
                "Điểm quy ước dựa trên thông tin còn thiếu hoặc số đo ngoài khoảng kiểm tra; đây không phải"
                " độ tin cậy thống kê của dự đoán."
            ),
            "defaulted_fields": list(patient.get("defaulted_fields", [])),
            "disclaimers": disclaimers,
        }

    def _confidence_reasons(self, patient):
        """Explain each deduction using the same rules that calculate the score."""
        reasons = []
        optional = patient.get("optional_field_count", 0)
        defaulted = list(patient.get("defaulted_fields", []))
        if optional and defaulted:
            reasons.append({
                "code": "defaulted_inputs",
                "fields": defaulted,
                "penalty": self.max_defaulted_penalty * min(1.0, len(defaulted) / optional),
                "message": "Các mục này chưa có câu trả lời nên mô hình đang dùng giá trị mặc định. Bạn có thể bổ sung nếu biết; nếu chưa rõ, có thể giữ nguyên.",
            })
        if patient["bp"] <= 70 or patient["bp"] >= 220:
            reasons.append({
                "code": "bp_outside_check_range",
                "fields": ["bp"],
                "penalty": 0.15,
                "message": f"Huyết áp đã nhập là {patient['bp']:g} mmHg. Quy tắc kiểm tra đầu vào đánh dấu số đo ≤ 70 hoặc ≥ 220 mmHg để xác nhận. Điều này không có nghĩa bạn đã nhập sai.",
            })
        if patient["bmi"] <= 14 or patient["bmi"] >= 50:
            reasons.append({
                "code": "bmi_outside_check_range",
                "fields": ["bmi"],
                "penalty": 0.1,
                "message": f"BMI được tính là {patient['bmi']:g}. Quy tắc kiểm tra đầu vào đánh dấu BMI ≤ 14 hoặc ≥ 50 để xác nhận chiều cao và cân nặng. Điều này không có nghĩa các số đo đã nhập sai.",
            })
        return reasons

    def _confidence(self, patient):
        score = 1.0
        for reason in self._confidence_reasons(patient):
            score -= reason["penalty"]
        score = max(0.0, min(1.0, score))

        if score >= 0.85:
            label = "High"
        elif score >= 0.65:
            label = "Medium"
        else:
            label = "Low"
        return round(score, 2), label
