import logging
import time

from agents.retriever import evidence_status
from rl.environment import TERMINAL_ACTIONS, encode_state
from tools.explainability import evidence_trail
from tools.patient_guidance import build_followup, measurement_scales
from tools.risk_classifier import classify_risk
from tools.vietnamese import ESCALATION_LABELS, EVIDENCE_LABELS, METHOD_LABELS, RISK_LABELS

logger = logging.getLogger(__name__)

MAX_POLICY_STEPS = 3


class RunLog:
    """One request's record of each agent step: how long it took, how it ended, what it did.

    `degraded` keeps the failures (and is returned as such); `steps` is the full trace.
    """

    def __init__(self):
        self.degraded = []
        self.steps = []
        self._started = time.perf_counter()

    def record(self, component, started, status, detail):
        self.steps.append(
            {
                "component": component,
                "status": status,
                "ms": round((time.perf_counter() - started) * 1000, 1),
                "detail": detail,
            }
        )

    def guard(self, component, call, fallback, detail=lambda value: "", on_failure=""):
        """Run an optional step; on failure note it, trace `on_failure`, and return `fallback`."""
        started = time.perf_counter()
        try:
            value = call()
        except Exception as exc:
            logger.warning("%s failed: %s", component, exc)
            self.degraded.append({"component": component, "error": f"{type(exc).__name__}: {exc}"})
            self.record(component, started, "degraded", on_failure)
            return fallback
        self.record(component, started, "ok", detail(value))
        return value

    def trace(self, risk, safety, retrieved_context, evidence_status):
        rules = [rule for rule in safety["rules"] if rule.get("escalation")]
        disagrees = safety["effective_risk"] != risk or bool(safety["conflicts"])
        return {
            "steps": self.steps,
            "total_ms": round((time.perf_counter() - self._started) * 1000, 1),
            "evidence_count": len(retrieved_context),
            "evidence_status": evidence_status,
            "disagreement": {
                "model_risk": risk,
                "effective_risk": safety["effective_risk"],
                "rules": [{"code": rule["code"], "message": rule["message"]} for rule in rules],
                "conflicts": [conflict["message"] for conflict in safety["conflicts"]],
            }
            if disagrees
            else None,
        }


class Orchestrator:
    def __init__(
        self,
        model,
        explanation_agent,
        recommendation_agent,
        memory_agent,
        feature_explainer=None,
        retrieval_agent=None,
        safety_guard=None,
        support_policy=None,
        what_if=None,
    ):
        self.model = model
        self.explainer = explanation_agent
        self.recommender = recommendation_agent
        self.memory = memory_agent
        self.feature_explainer = feature_explainer
        self.retriever = retrieval_agent
        self.safety_guard = safety_guard
        self.support_policy = support_policy
        self.what_if = what_if

    def run(self, patient_data):
        log = RunLog()
        started = time.perf_counter()
        prob, patient = self.model.assess(patient_data)
        risk = classify_risk(prob, self.model.risk_bands)
        log.record(
            "risk_model", started, "ok", f"xác suất {prob:.1%}, nguy cơ {RISK_LABELS.get(risk, risk)}"
        )
        threshold = self.model.decision_threshold
        prediction = {
            "probability": prob,
            # 1 = flagged by the binary threshold chosen on validation; None when unknown.
            "label": int(prob >= threshold) if threshold is not None else None,
            "threshold": threshold,
            "risk_level": risk,
            "model": self.model.artifact_metadata.get("selected_model"),
            "model_version": self.model.model_version,
        }
        no_explanation = {"method": "none", "features": []}
        feature_explanation = log.guard(
            "feature_explainer",
            lambda: (
                self.feature_explainer.explain(patient)
                if self.feature_explainer is not None
                else no_explanation
            ),
            no_explanation,
            detail=lambda value: (
                f"{METHOD_LABELS.get(value['method'], value['method'])}, "
                f"{len(value['features'])} đặc trưng"
            ),
            on_failure="dùng ngưỡng đơn giản thay giải thích của mô hình",
        )
        similar_cases = log.guard(
            "memory_search",
            lambda: self.memory.find_similar(patient),
            [],
            detail=lambda value: f"{len(value)} hồ sơ tương tự",
            on_failure="không dùng hồ sơ tương tự",
        )
        retrieved_context = self._retrieve(patient, risk, feature_explanation, log)

        status, safety, recommendation = self._advise(
            patient, prob, risk, retrieved_context, similar_cases, feature_explanation, log
        )
        policy = None
        if self.support_policy is not None:
            retrieved_context, status, safety, recommendation, policy = log.guard(
                "support_policy",
                lambda: self._choose_next_step(
                    patient,
                    prob,
                    risk,
                    feature_explanation,
                    similar_cases,
                    (retrieved_context, status, safety, recommendation),
                    log,
                ),
                (retrieved_context, status, safety, recommendation, None),
                detail=lambda value: (
                    f"{len(value[4]['steps'])} bước, bước tiếp theo: {value[4]['next_step']}"
                    + (" (luật ghi đè)" if value[4]["overridden_by_rules"] else "")
                ),
                on_failure="giữ kết quả trước khi chạy policy",
            )

        what_if, unknown_input = log.guard(
            "what_if",
            lambda: self._counterfactuals(patient, safety),
            (None, None),
            detail=lambda value: (
                f"{len(value[0]['scenarios'])} kịch bản" if value[0] else "không áp dụng"
            ),
            on_failure="bỏ qua mô phỏng",
        )

        # Explained last so it sees the final evidence status and safety outcome.
        explanation = log.guard(
            "explainer",
            lambda: self.explainer.explain(
                patient,
                prob,
                feature_explanation=feature_explanation,
                similar_cases=similar_cases,
                safety=safety,
                evidence_status=status,
            ),
            "Không tạo được giải thích; xem phần tác động đặc trưng để biết các yếu tố ảnh hưởng đến mô hình.",
            detail=lambda value: "đã tạo giải thích",
            on_failure="dùng văn bản cố định",
        )
        log.guard(
            "memory_store",
            lambda: self.memory.store(patient, prob, risk),
            None,
            detail=lambda value: "đã lưu hồ sơ",
            on_failure="không lưu hồ sơ",
        )

        if log.degraded:
            safety = {
                **safety,
                "disclaimers": [
                    *safety["disclaimers"],
                    "Một số thành phần gặp lỗi ("
                    + ", ".join(item["component"] for item in log.degraded)
                    + "); kết quả này chưa đầy đủ.",
                ],
            }

        return {
            "probability": prob,
            "risk": risk,
            "prediction": prediction,
            "patient": patient,
            "feature_explanation": feature_explanation,
            "retrieved_context": retrieved_context,
            "evidence_status": status,
            "similar_cases": similar_cases,
            "safety": safety,
            "explanation": explanation,
            "recommendation": recommendation,
            "model": self.model.artifact_metadata,
            "policy": policy,
            "degraded": log.degraded,
            "trace": log.trace(risk, safety, retrieved_context, status),
            "measurement_scales": measurement_scales(patient),
            "evidence_trail": evidence_trail(feature_explanation, retrieved_context),
            "what_if": what_if,
            "followup": build_followup(patient, safety, policy, unknown_input),
        }

    def _counterfactuals(self, patient, safety):
        """What-if scenarios and the most informative missing input, only for routine cases.

        Lifestyle scenarios and extra questions must not distract from a clinician escalation.
        """
        if self.what_if is None or safety["escalation"] != "routine_followup":
            return None, None
        result = self.what_if.scenarios(patient)
        cite = self.retriever.citation if self.retriever is not None else lambda _id: None
        for entry in (*result["scenarios"], result["combined"]):
            if entry is not None:
                entry["evidence"] = list(filter(None, map(cite, entry.pop("evidence_ids"))))
        return result, self.what_if.most_informative_unknown(patient)

    def _retrieve(self, patient, risk, feature_explanation, log, broaden=False, previous=()):
        """Evidence search; if it fails, keep the `previous` passages instead of losing them."""
        if self.retriever is None:
            return list(previous)
        return log.guard(
            "retriever",
            lambda: self.retriever.retrieve(patient, risk, feature_explanation, broaden=broaden),
            list(previous),
            detail=lambda value: (
                f"{'tìm mở rộng, ' if broaden else ''}{len(value)} đoạn bằng chứng"
                f" ({EVIDENCE_LABELS[evidence_status(value)]})"
            ),
            on_failure="giữ các đoạn bằng chứng trước đó",
        )

    def _advise(
        self,
        patient,
        prob,
        risk,
        retrieved_context,
        similar_cases,
        feature_explanation,
        log,
    ):
        """Safety rules then recommendation for the current evidence (rules never see the policy)."""
        status = evidence_status(retrieved_context)
        if self.safety_guard is None:
            safety = {
                "alerts": [],
                "rules": [],
                "conflicts": [],
                "effective_risk": risk,
                "escalation": "routine_followup",
                "confidence_score": 1.0,
                "confidence_label": "High",
                "disclaimers": [],
            }
        else:
            # A failed rule check must not read as "all clear": fail toward clinician review.
            safety = log.guard(
                "safety_guard",
                lambda: self.safety_guard.assess(patient, prob, risk, evidence_status=status),
                {
                    "alerts": ["Không kiểm tra được các luật an toàn; cần được bác sĩ đánh giá."],
                    "rules": [],
                    "conflicts": [],
                    "effective_risk": risk,
                    "escalation": "prompt_clinician_followup",
                    "confidence_score": 0.0,
                    "confidence_label": "Low",
                    "disclaimers": [],
                },
                detail=lambda value: (
                    f"{len(value['rules'])} luật kích hoạt, hướng xử trí: "
                    f"{ESCALATION_LABELS[value['escalation']]}"
                ),
                on_failure="chuyển hướng sang bác sĩ đánh giá",
            )
        recommendation = log.guard(
            "recommender",
            lambda: self.recommender.recommend(
                patient,
                safety["effective_risk"],
                retrieved_context=retrieved_context,
                similar_cases=similar_cases,
                safety=safety,
                feature_explanation=feature_explanation,
            ),
            "Không tạo được khuyến nghị; hãy khám bác sĩ để được theo dõi.",
            detail=lambda value: "đã tạo khuyến nghị",
            on_failure="dùng văn bản cố định",
        )
        return status, safety, recommendation

    def _choose_next_step(
        self, patient, prob, risk, feature_explanation, similar_cases, current, log
    ):
        """Let the support policy pick the next step; only evidence retrieval is acted on here.

        Requesting glucose cannot be done inside one API call, so it is reported as the
        next step. The rules keep precedence: a policy answer below the rules' escalation
        is replaced by escalation.
        """
        retrieved_context, status, safety, recommendation = current
        retrieved_more = False
        steps = []
        for _ in range(MAX_POLICY_STEPS):
            glucose = "unmeasured"
            if patient.get("glucose_measured", True):
                codes = {rule["code"] for rule in safety["rules"]}
                glucose = "elevated" if codes & {"GLU-200", "GLU-300"} else "normal"
            state = encode_state(
                risk,
                glucose,
                status,
                asked_glucose=patient.get("glucose_unavailable", False),
                retrieved_more=retrieved_more,
            )
            decision = self.support_policy.decide(state)
            action = decision["action"]
            step = {"action": action, "state": list(state), "source": decision["source"]}
            steps.append(step)
            if action == "retrieve_more_evidence" and self.retriever is not None:
                retrieved_more = True
                retrieved_context = self._retrieve(
                    patient,
                    risk,
                    feature_explanation,
                    log,
                    broaden=True,
                    previous=retrieved_context,
                )
                status, safety, recommendation = self._advise(
                    patient,
                    prob,
                    risk,
                    retrieved_context,
                    similar_cases,
                    feature_explanation,
                    log,
                )
                step["evidence_status_after"] = status
                continue
            break

        next_step = steps[-1]["action"]
        if next_step == "retrieve_more_evidence":  # no retriever configured
            next_step = "recommend_followup"
        overridden = (
            next_step in TERMINAL_ACTIONS
            and next_step != "escalate_to_clinician"
            and safety["escalation"] != "routine_followup"
        )
        if overridden:
            next_step = "escalate_to_clinician"
        policy = {
            "next_step": next_step,
            "overridden_by_rules": overridden,
            "steps": steps,
            "q_values": decision["q_values"],
            "version": self.support_policy.metadata.get("version"),
            "feedback": self.support_policy.metadata.get("feedback", "simulated"),
        }
        return retrieved_context, status, safety, recommendation, policy
