"""One shared description of patient history for both advice agents."""

from datetime import datetime, timedelta, timezone

LABELS = {
    "age": "Tuổi",
    "bmi": "BMI",
    "bp": "Huyết áp tâm thu",
    "height_cm": "Chiều cao",
    "weight_kg": "Cân nặng",
}


def describe_memory(context):
    if not context:
        return ""
    if context["status"] == "unavailable":
        return "Chưa đọc được lịch sử đánh giá; không thể kết luận đây là lần đánh giá đầu tiên."
    if context["status"] == "first_assessment":
        return "Chưa có lần đánh giá trước cho mã hồ sơ này; đây là lần đầu được ghi nhận."
    previous = context["previous"]["metadata"]
    timestamp = datetime.fromisoformat(previous["timestamp"]).astimezone(
        timezone(timedelta(hours=7))
    )
    parts = [
        f"Có {context['assessment_count']} lần đánh giá trước của cùng mã hồ sơ. So sánh với lần gần nhất lúc {timestamp:%H:%M:%S ngày %d/%m/%Y} (UTC+7)."
    ]
    for change in context["changes"]:
        if change["field"] == "age":
            continue
        label = change.get("label") or LABELS.get(change["field"], change["field"])
        delta = change.get("delta")
        unit = f" {change['unit']}" if change.get("unit") else ""
        if delta is None:  # An answer such as a habit: no arithmetic difference to report.
            parts.append(f"{label} từ {change['previous']} thành {change['current']}.")
            continue
        difference = f"{'tăng' if delta > 0 else 'giảm'} {abs(delta):g}{unit}"
        parts.append(f"{label} từ {change['previous']:g} thành {change['current']:g}{unit} ({difference}).")
    comparison = context.get("prediction_comparison")
    if comparison:
        delta = comparison["probability_delta"]
        if delta is not None:
            parts.append(f"Xác suất mô hình thay đổi {delta * 100:+.2f} điểm phần trăm.")
        parts.append(comparison["note"])
    parts.append(
        "Các kết quả lưu là dự đoán, chưa phải kết quả bệnh được xác nhận; lịch sử không thay thế bằng chứng hướng dẫn hay luật an toàn."
    )
    return " ".join(parts)
