import os

from openai import OpenAI

from agents.llm_context import supplied_features, supplied_inputs, unknown_inputs_instruction
from agents.retriever import evidence_status, excerpt
from memory.context import describe_memory
from tools.vietnamese import ESCALATION_LABELS, feature_label


class RecommendationAgent:
    def __init__(self, model_name="gpt-4o-mini"):
        self.model_name = model_name
        self.client = OpenAI() if os.getenv("OPENAI_API_KEY") else None

    def recommend(
        self,
        patient_data,
        risk,
        retrieved_context=None,
        memory_context=None,
        safety=None,
        feature_explanation=None,
    ):
        if self.client is None:
            return self._fallback_recommendation(
                patient_data, risk, retrieved_context, memory_context, safety, feature_explanation
            )

        prompt = f"""
        Patient data (only what the patient supplied): {supplied_inputs(patient_data)}
        Inputs the patient did not supply: {unknown_inputs_instruction(patient_data)}
        Risk level: {risk}
        Numbered guideline evidence:
        {self._evidence_block(retrieved_context)}
        Same-patient assessment history: {describe_memory(memory_context)}
        Safety assessment: {safety}
        Main model risk drivers: {self._drivers(supplied_features(feature_explanation))}

        Suggest actionable health recommendations. Support each guideline-based
        recommendation with its evidence number in square brackets, e.g. [1]. Use only
        the numbered evidence above for guideline claims; if it does not cover something,
        say there is no supporting evidence instead of inventing a source.
        Use history to describe supplied measurement changes, not to establish diagnoses
        or treatment effectiveness, and never relax current safety rules based on history.
        Never compare probabilities across model versions.
        Put all history observations in a final separate section titled
        "Lịch sử đánh giá:"; do not present past measurements as action items.
        Viết hoàn toàn bằng tiếng Việt. Giữ nguyên số trích dẫn và tên tài liệu gốc.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model_name, messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content + self._sources_note(retrieved_context)
        except Exception:
            fallback = self._fallback_recommendation(
                patient_data, risk, retrieved_context, memory_context, safety, feature_explanation
            )
            return f"{fallback} Không thể tạo khuyến nghị bằng LLM; đang dùng nội dung dự phòng."

    def _fallback_recommendation(
        self,
        patient_data,
        risk,
        retrieved_context=None,
        memory_context=None,
        safety=None,
        feature_explanation=None,
    ):
        if risk == "High":
            recommendation = "Nên sớm khám bác sĩ, đo lại các chỉ số và xét nghiệm; lập kế hoạch chăm sóc tập trung vào huyết áp, đường huyết, dinh dưỡng, vận động và tuân thủ dùng thuốc."
        elif risk == "Medium":
            recommendation = "Nên tiếp tục theo dõi, được hướng dẫn điều chỉnh lối sống và trao đổi với bác sĩ về diễn biến huyết áp, đường huyết."
        else:
            recommendation = "Nên chăm sóc dự phòng định kỳ, vận động phù hợp, ăn uống cân bằng và theo dõi sức khỏe thường xuyên."

        context_note = self._context_note(retrieved_context)
        memory_note = (
            f"\n\nLịch sử đánh giá: {describe_memory(memory_context)}" if memory_context else ""
        )
        safety_note = self._safety_note(safety)
        drivers = self._drivers(feature_explanation)
        driver_note = (
            f" Chú ý các yếu tố chính làm tăng nguy cơ theo mô hình: {drivers}." if drivers else ""
        )

        return (
            recommendation
            + driver_note
            + context_note
            + safety_note
            + memory_note
            + self._sources_note(retrieved_context)
        )

    def _drivers(self, feature_explanation, limit=3):
        """Names of the features that raise risk the most, e.g. 'BMI, HighBP'."""
        features = (feature_explanation or {}).get("features", [])
        raising = [item["feature"] for item in features if item["impact"] > 0]
        return ", ".join(map(feature_label, raising[:limit]))

    def _context_note(self, retrieved_context):
        status = evidence_status(retrieved_context)
        if status == "none":
            return (
                " Chưa truy xuất được bằng chứng hướng dẫn đủ phù hợp; khuyến nghị này mang tính"
                " tổng quát và cần được bác sĩ xác nhận."
            )

        points = " ".join(
            f"{excerpt(item['text'], 260)} [{number}]"
            for number, item in enumerate(retrieved_context, 1)
        )
        note = f" Bằng chứng hướng dẫn: {points}"
        if status == "limited":
            note += " Bằng chứng hỗ trợ còn hạn chế; cần xác nhận với bác sĩ."
        return note

    def _evidence_block(self, retrieved_context):
        if not retrieved_context:
            return "(chưa truy xuất được bằng chứng)"
        return "\n".join(
            f"[{number}] {excerpt(item['text'], 700)} ({item['source_title']}, {item.get('year')})"
            for number, item in enumerate(retrieved_context, 1)
        )

    def _sources_note(self, retrieved_context):
        if not retrieved_context:
            return ""
        lines = [
            f"[{number}] {item['source_title']}"
            + (f", {item['publisher']}" if item.get("publisher") else "")
            + (f" ({item['year']})" if item.get("year") else "")
            + (f" - {item['url']}" if item.get("url") else "")
            for number, item in enumerate(retrieved_context, 1)
        ]
        return "\n\nNguồn tham khảo:\n" + "\n".join(lines)

    def _safety_note(self, safety):
        if not safety:
            return ""
        alerts = safety.get("alerts", [])
        escalation = safety.get("escalation", "routine_followup")
        if not alerts and escalation == "routine_followup":
            return ""
        alert_text = " ".join(alerts[:2])
        resolutions = "; ".join(c["message"] for c in safety.get("conflicts", []))
        conflict_text = f" Xử lý xung đột luật: {resolutions}." if resolutions else ""
        return f" Hướng xử trí theo luật an toàn: {ESCALATION_LABELS.get(escalation, escalation)}. {alert_text}{conflict_text}"
