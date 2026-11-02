import os

from openai import OpenAI

from agents.retriever import evidence_status


class RecommendationAgent:
    def __init__(self, model_name="gpt-4o-mini"):
        self.model_name = model_name
        self.client = OpenAI() if os.getenv("OPENAI_API_KEY") else None

    def recommend(
        self,
        patient_data,
        risk,
        retrieved_context=None,
        similar_cases=None,
        safety=None,
        feature_explanation=None,
    ):
        if self.client is None:
            return self._fallback_recommendation(
                patient_data, risk, retrieved_context, similar_cases, safety, feature_explanation
            )

        prompt = f"""
        Patient data: {patient_data}
        Risk level: {risk}
        Numbered guideline evidence:
        {self._evidence_block(retrieved_context)}
        Similar prior cases (earlier model predictions, not confirmed outcomes): {similar_cases}
        Safety assessment: {safety}
        Main model risk drivers: {self._drivers(feature_explanation)}

        Suggest actionable health recommendations. Support each guideline-based
        recommendation with its evidence number in square brackets, e.g. [1]. Use only
        the numbered evidence above for guideline claims; if it does not cover something,
        say there is no supporting evidence instead of inventing a source.
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model_name, messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content + self._sources_note(retrieved_context)
        except Exception as exc:
            fallback = self._fallback_recommendation(
                patient_data, risk, retrieved_context, similar_cases, safety, feature_explanation
            )
            return f"{fallback} LLM recommendation unavailable: {exc}"

    def _fallback_recommendation(
        self,
        patient_data,
        risk,
        retrieved_context=None,
        similar_cases=None,
        safety=None,
        feature_explanation=None,
    ):
        glucose_note = ""
        if not patient_data.get("glucose_measured", True):
            glucose_note = " Because glucose was not measured, get an A1C or fasting blood glucose test before making clinical decisions."

        if risk == "High":
            recommendation = "Recommend prompt clinician review, repeat vitals/labs, and a care plan focused on blood pressure, glucose, nutrition, activity, and medication adherence."
        elif risk == "Medium":
            recommendation = "Recommend follow-up monitoring, lifestyle coaching, and reviewing blood pressure and glucose trends with a clinician."
        else:
            recommendation = "Recommend routine preventive care, healthy activity, balanced nutrition, and periodic monitoring."

        context_note = self._context_note(retrieved_context)
        memory_note = ""
        if similar_cases:
            memory_note = (
                " Similar stored cases are earlier model predictions without confirmed outcomes;"
                " do not treat them as evidence of what happens to this patient."
            )
        safety_note = self._safety_note(safety)
        drivers = self._drivers(feature_explanation)
        driver_note = f" Focus on the main model risk drivers: {drivers}." if drivers else ""

        return (
            recommendation
            + driver_note
            + glucose_note
            + context_note
            + memory_note
            + safety_note
            + self._sources_note(retrieved_context)
        )

    def _drivers(self, feature_explanation, limit=3):
        """Names of the features that raise risk the most, e.g. 'BMI, HighBP'."""
        features = (feature_explanation or {}).get("features", [])
        raising = [item["feature"] for item in features if item["impact"] > 0]
        return ", ".join(raising[:limit])

    def _context_note(self, retrieved_context):
        status = evidence_status(retrieved_context)
        if status == "none":
            return (
                " No sufficiently relevant guideline evidence was retrieved, so this advice is"
                " general and should be confirmed by a clinician."
            )

        points = " ".join(
            f"{item['text']} [{number}]" for number, item in enumerate(retrieved_context, 1)
        )
        note = f" Guideline evidence: {points}"
        if status == "limited":
            note += " Supporting evidence is limited; confirm with a clinician."
        return note

    def _evidence_block(self, retrieved_context):
        if not retrieved_context:
            return "(none retrieved)"
        return "\n".join(
            f"[{number}] {item['text']} ({item['source_title']}, {item.get('year')})"
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
        return "\n\nSources:\n" + "\n".join(lines)

    def _safety_note(self, safety):
        if not safety:
            return ""
        alerts = safety.get("alerts", [])
        escalation = safety.get("escalation", "routine_followup")
        if not alerts and escalation == "routine_followup":
            return ""
        alert_text = " ".join(alerts[:2])
        resolutions = "; ".join(c["resolution"] for c in safety.get("conflicts", []))
        conflict_text = f" Rule conflicts resolved: {resolutions}." if resolutions else ""
        return f" Safety escalation: {escalation}. {alert_text}{conflict_text}"
