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

# Translations of the checked-in KB passages. Retrieval embeds and scores the original
# English corpus; only the returned display text changes.
EVIDENCE_TEXTS = {
    "ev-ada-dx-a1c": "Đái tháo đường được chẩn đoán khi A1C từ 6,5% trở lên; tiền đái tháo đường tương ứng A1C từ 5,7% đến 6,4%.",
    "ev-ada-dx-fpg": "Đái tháo đường được chẩn đoán khi glucose huyết tương lúc đói từ 126 mg/dL trở lên; tiền đái tháo đường tương ứng từ 100 đến 125 mg/dL.",
    "ev-ada-dx-ogtt": "Đái tháo đường được chẩn đoán khi glucose huyết tương sau 2 giờ từ 200 mg/dL trở lên trong nghiệm pháp dung nạp 75 g glucose đường uống; tiền đái tháo đường tương ứng từ 140 đến 199 mg/dL.",
    "ev-ada-confirm": "Khi không có tình trạng tăng đường huyết rõ ràng, chẩn đoán cần hai kết quả bất thường từ cùng một mẫu hoặc từ hai mẫu riêng biệt.",
    "ev-ada-screen-age": "Sàng lọc tiền đái tháo đường và đái tháo đường típ 2 nên bắt đầu từ 35 tuổi ở mọi người trưởng thành, và sớm hơn ở người thừa cân hoặc béo phì có thêm ít nhất một yếu tố nguy cơ.",
    "ev-ada-screen-factors": "Các yếu tố nguy cơ cần xét nghiệm gồm thừa cân hoặc béo phì, có người thân bậc một mắc đái tháo đường, ít vận động và tăng huyết áp (từ 130/80 mmHg trở lên hoặc đang điều trị).",
    "ev-ada-bmi-asian": "Ở người Mỹ gốc Á, xét nghiệm được cân nhắc với ngưỡng BMI thấp hơn, từ 23 kg/m².",
    "ev-ada-prediabetes-progress": "Người tiền đái tháo đường có nguy cơ cao hơn tiến triển thành đái tháo đường típ 2 và nên được giới thiệu đến chương trình thay đổi lối sống chuyên sâu.",
    "ev-dpp-lifestyle": "Can thiệp lối sống chuyên sâu làm giảm 58% tỷ lệ mắc đái tháo đường típ 2 so với giả dược ở người trưởng thành bị rối loạn dung nạp glucose.",
    "ev-dpp-metformin": "Metformin làm giảm 31% tỷ lệ mắc đái tháo đường típ 2 so với giả dược và có hiệu quả thấp hơn can thiệp lối sống.",
    "ev-dpp-weight": "Mục tiêu thay đổi lối sống là giảm ít nhất 7% cân nặng và vận động thể chất ít nhất 150 phút mỗi tuần.",
    "ev-ada-activity": "Người trưởng thành nên vận động aerobic cường độ vừa đến mạnh ít nhất 150 phút mỗi tuần, phân bố trong ít nhất 3 ngày mỗi tuần.",
    "ev-ada-weight": "Giảm từ 5% trọng lượng cơ thể trở lên có thể cải thiện đường huyết và các yếu tố nguy cơ tim mạch, chuyển hóa.",
    "ev-ada-bp-target": "Cần đo huyết áp ở mỗi lần khám định kỳ, xác nhận số đo tăng vào một ngày khác; mục tiêu điều trị là dưới 130/80 mmHg.",
    "ev-ada-cvd": "Bệnh tim mạch do xơ vữa là nguyên nhân hàng đầu gây bệnh tật và tử vong ở người đái tháo đường; tăng huyết áp là yếu tố nguy cơ góp phần quan trọng.",
    "ev-ada-smoking": "Mọi người nên được khuyên không sử dụng thuốc lá điếu hoặc các sản phẩm thuốc lá khác; tư vấn cai thuốc cần là một phần của chăm sóc.",
    "ev-cdc-risk": "Tiền đái tháo đường, thừa cân, từ 45 tuổi trở lên, có cha mẹ hoặc anh chị em ruột mắc đái tháo đường típ 2 và vận động dưới ba lần mỗi tuần làm tăng nguy cơ đái tháo đường típ 2.",
    "ev-cdc-smoking": "Người hút thuốc có khả năng mắc đái tháo đường típ 2 cao hơn người không hút thuốc.",
    "ev-who-risk": "Thừa cân, béo phì và ít vận động là các yếu tố chính có thể thay đổi của đái tháo đường típ 2; ăn uống lành mạnh, vận động đều đặn và tránh thuốc lá giúp phòng ngừa hoặc trì hoãn bệnh.",
    "ev-who-bp": "Đái tháo đường làm tăng nguy cơ nhồi máu cơ tim và đột quỵ; người đái tháo đường cũng thường bị tăng huyết áp.",
    "ev-niddk-clinician": "Nhân viên y tế chẩn đoán tiền đái tháo đường và đái tháo đường bằng xét nghiệm máu; một số đo đường huyết tại nhà không phải là chẩn đoán.",
}


def feature_label(name):
    return FEATURE_LABELS.get(name, name)
