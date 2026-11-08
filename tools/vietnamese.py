"""Vietnamese display labels; API field names, rule codes and model inputs stay stable."""

FEATURE_LABELS = {
    "HighBP": "tăng huyết áp",
    "HighChol": "cholesterol cao",
    "CholCheck": "kiểm tra cholesterol",
    "BMI": "BMI",
    "Smoker": "hút thuốc",
    "Stroke": "tiền sử đột quỵ",
    "HeartDiseaseorAttack": "tiền sử bệnh tim",
    "PhysActivity": "vận động thể chất",
    "Fruits": "ăn trái cây",
    "Veggies": "ăn rau",
    "HvyAlcoholConsump": "uống nhiều rượu bia",
    "AnyHealthcare": "tiếp cận dịch vụ y tế",
    "NoDocbcCost": "rào cản chi phí khám bệnh",
    "GenHlth": "sức khỏe tổng quát",
    "MentHlth": "số ngày sức khỏe tinh thần kém",
    "PhysHlth": "số ngày sức khỏe thể chất kém",
    "DiffWalk": "khó khăn khi đi lại",
    "Sex": "giới tính",
    "Age": "nhóm tuổi",
    "Education": "trình độ học vấn",
    "Income": "mức thu nhập",
    "age": "tuổi",
    "bmi": "BMI",
    "bp": "huyết áp",
    "glucose": "đường huyết",
}
RISK_LABELS = {"Low": "Thấp", "Medium": "Trung bình", "High": "Cao"}
ESCALATION_LABELS = {
    "routine_followup": "Theo dõi định kỳ",
    "prompt_clinician_followup": "Sớm khám bác sĩ",
    "urgent_clinician_review": "Khám bác sĩ khẩn cấp",
}
METHOD_LABELS = {"shap": "SHAP", "sensitivity": "phân tích độ nhạy", "none": "chưa có"}
EVIDENCE_LABELS = {"none": "không có", "limited": "hạn chế", "sufficient": "đầy đủ"}


def feature_label(name):
    return FEATURE_LABELS.get(name, name)
