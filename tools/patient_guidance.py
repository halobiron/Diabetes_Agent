"""Source-backed reference displays and one actionable follow-up question.

Reference bands explain measurements, not model probability or diagnoses. Fasting
glucose references apply to non-pregnant adults; unknown context stays neutral.
"""

BMI_SOURCE = {
    "title": "CDC — Adult BMI",
    "url": "https://www.cdc.gov/bmi/adult-calculator/index.html",
}
BP_SOURCE = {
    "title": "AHA — Blood pressure readings",
    "url": "https://www.heart.org/en/health-topics/high-blood-pressure/understanding-blood-pressure-readings",
}
GLU_SOURCE = {
    "title": "NIDDK — Diabetes tests",
    "url": "https://www.niddk.nih.gov/health-information/diabetes/overview/tests-diagnosis",
}
LOW_GLU_SOURCE = {
    "title": "CDC — Low blood sugar",
    "url": "https://www.cdc.gov/diabetes/about/low-blood-sugar-hypoglycemia.html",
}


def _band(start, end, label, tone):
    return {"min": start, "max": end, "label": label, "tone": tone}


def _scale(key, title, unit, value, bounds, bands, note, sources):
    active = next(
        (
            b
            for b in bands
            if value is not None
            and (b["min"] is None or value >= b["min"])
            and (b["max"] is None or value < b["max"])
        ),
        None,
    )
    return {
        "key": key,
        "title": title,
        "unit": unit,
        "value": value,
        "display_min": bounds[0],
        "display_max": bounds[1],
        "bands": bands,
        "status": active["label"]
        if active
        else ("Chưa có số đo" if value is None else "Chưa phân vùng"),
        "tone": active["tone"] if active else "neutral",
        "note": note,
        "sources": sources,
    }


def measurement_scales(patient):
    age = patient.get("age") or 0
    bmi_bands = (
        [
            _band(None, 18.5, "Thiếu cân", "warning"),
            _band(18.5, 25, "Khoảng cân nặng khỏe mạnh", "success"),
            _band(25, 30, "Thừa cân", "warning"),
            _band(30, None, "Béo phì", "danger"),
        ]
        if age >= 20
        else []
    )
    bmi = _scale(
        "bmi",
        "Chỉ số BMI",
        "kg/m²",
        patient.get("bmi"),
        (10, 45),
        bmi_bands,
        "Phân nhóm CDC cho người từ 20 tuổi; BMI là chỉ số sàng lọc, không phải mục tiêu cân nặng cá nhân."
        if age >= 20
        else "Không áp dụng thang BMI người lớn cho người dưới 20 tuổi; cần đánh giá theo tuổi và giới.",
        [BMI_SOURCE],
    )
    bp_bands = (
        [
            _band(None, 120, "Tâm thu dưới 120", "neutral"),
            _band(120, 130, "Tâm thu 120–129", "warning"),
            _band(130, 140, "Tâm thu 130–139", "warning"),
            _band(140, 180, "Tâm thu 140–179", "danger"),
            _band(180, None, "Tâm thu từ 180", "danger"),
        ]
        if age >= 18
        else []
    )
    bp = _scale(
        "bp",
        "Huyết áp tâm thu",
        "mmHg",
        patient.get("bp"),
        (60, 220),
        bp_bands,
        "Chỉ có số tâm thu: chưa đủ phân loại huyết áp, cần cả số tâm trương. Mốc ≥180 là ngưỡng cảnh báo của dự án; AHA nêu mức nghiêm trọng >180."
        if age >= 18
        else "Không áp dụng mốc huyết áp người lớn cho người dưới 18 tuổi.",
        [BP_SOURCE],
    )
    measured = patient.get("glucose_measured", True)
    context = patient.get("glucose_context", "unspecified")
    glucose_bands = []
    note = "Chưa đo: không hiển thị giá trị tự điền như số đo thật."
    if measured:
        note = "Chưa biết bối cảnh đo; không gán vùng bình thường hay ngưỡng chẩn đoán."
        if context == "fasting" and age >= 18:
            glucose_bands = [
                _band(None, 70, "Dưới 70: đường huyết thấp", "danger"),
                _band(70, 100, "70 đến dưới 100", "success"),
                _band(100, 126, "100 đến dưới 126", "warning"),
                _band(126, None, "Từ 126: cần xác nhận", "danger"),
            ]
            note = "Mốc tham khảo lúc đói ≥8 giờ cho người lớn không mang thai. Kết quả máy đo tại nhà không dùng để chẩn đoán; bác sĩ thường cần xét nghiệm xác nhận."
        elif context == "random":
            note = "Đo ngẫu nhiên không có vùng bình thường chung trên thang này. Ngưỡng xét nghiệm ≥200 cần đặt trong bối cảnh triệu chứng và đánh giá của bác sĩ."
        elif context == "after_meal":
            note = "Đo sau ăn thông thường không tương đương nghiệm pháp dung nạp glucose; không áp dụng mốc OGTT."
        elif context == "fasting":
            note = "Không áp dụng thang tham khảo người lớn cho người dưới 18 tuổi."
    glucose = _scale(
        "glucose",
        "Đường huyết",
        "mg/dL",
        patient["glucose"] if measured else None,
        (40, 300),
        glucose_bands,
        note,
        [GLU_SOURCE, LOW_GLU_SOURCE],
    )
    return [bmi, bp, glucose]


RISK_FACTOR_QUESTIONS = {
    "PhysActivity": "Trong 30 ngày qua, bạn có vận động thể chất ngoài công việc (đi bộ, chạy, thể thao) không?",
    "Smoker": "Bạn đã từng hút ít nhất 100 điếu thuốc (khoảng 5 bao) trong đời chưa?",
    "HighChol": "Bác sĩ đã từng cho biết bạn bị cholesterol cao chưa?",
    "HeartDiseaseorAttack": "Bạn đã từng được chẩn đoán bệnh mạch vành hoặc nhồi máu cơ tim chưa?",
    "Stroke": "Bạn đã từng bị đột quỵ chưa?",
    "DiffWalk": "Bạn có gặp khó khăn nghiêm trọng khi đi bộ hoặc leo cầu thang không?",
    "HvyAlcoholConsump": "Bạn có uống nhiều rượu bia không (nam trên 14 ly, nữ trên 7 ly mỗi tuần)?",
    "Fruits": "Bạn có ăn trái cây ít nhất một lần mỗi ngày không?",
    "Veggies": "Bạn có ăn rau ít nhất một lần mỗi ngày không?",
}


def _risk_factor_question(unknown):
    low, high = sorted((unknown["probability_if_no"], unknown["probability_if_yes"]))
    return {
        "id": unknown["field"],
        "kind": "risk_factor",
        "source": "model_sensitivity",
        "field": unknown["field"],
        "question": RISK_FACTOR_QUESTIONS[unknown["feature"]],
        "reason": (
            f"Mục này chưa được cung cấp nên mô hình đang dùng giá trị mặc định. Tùy câu trả lời, xác suất ước tính"
            f" nằm trong khoảng {low:.1%} đến {high:.1%}; đây là mục còn thiếu có ảnh hưởng lớn nhất."
            " Bạn có thể bỏ qua; hệ thống sẽ không hỏi lại mục này trong hồ sơ."
        ),
        "model_note": "Câu trả lời được đưa vào mô hình và có thể đổi xác suất, cảnh báo và khuyến nghị.",
    }


def build_followup(patient, safety, policy=None, unknown=None):
    """One next question: glucose first (it drives the safety rules), then the missing model
    input whose answer could move the estimate most (`unknown`).

    The glucose measurement context is not asked here: the form collects it next to the value.
    """
    # Never put a data-entry task ahead of a clinician escalation or a failed safety check.
    if safety["escalation"] != "routine_followup":
        return None
    measured = patient.get("glucose_measured", True)
    if not measured and not patient.get("glucose_unavailable"):
        source = "policy" if policy and policy["next_step"] == "request_glucose" else "data_quality"
        return {
            "id": "glucose",
            "kind": "glucose",
            "source": source,
            "question": "Bạn có kết quả đo đường huyết để bổ sung không?",
            "reason": "Số đo này giúp bộ luật kiểm tra cảnh báo và truy xuất bằng chứng phù hợp hơn. Bạn có thể chọn chưa có kết quả; hệ thống sẽ không hỏi lặp trong hồ sơ này.",
            "model_note": "Glucose không tham gia MLP BRFSS hiện tại; bổ sung số đo không trực tiếp đổi xác suất của mô hình.",
        }
    return _risk_factor_question(unknown) if unknown else None
