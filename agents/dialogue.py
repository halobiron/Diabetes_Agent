"""Rule-driven messages explaining conflicts between components; no LLM calls.

Only a proposal carrying RETRIEVE_MORE triggers work in the Orchestrator. Other
messages record why the safety rules prevailed; none can lower an escalation.
"""

RETRIEVE_MORE = "retrieve_more_evidence"


# rule -> (component challenged, reply performative, reply content).
CONFLICT_REPLIES = {
    "CF-PRED-LOW-MEASURED-HIGH": (
        "risk_model",
        "accept",
        "Tôi chỉ thấy các yếu tố lối sống nên không thấy số đo nguy hiểm này; "
        "chấp nhận nâng nguy cơ hiệu lực lên Cao theo số đo.",
    ),
    "CF-PRED-HIGH-LOW-QUALITY": (
        "risk_model",
        "accept",
        "Dữ liệu đầu vào chất lượng thấp; chấp nhận đánh dấu dự đoán là tạm thời.",
    ),
    "CF-ESCALATION-NO-EVIDENCE": (
        "retriever",
        "propose",
        "Đề nghị tìm mở rộng bằng chứng; mức chuyển tuyến không hạ trong lúc chờ.",
    ),
}


def _message(sender, receiver, performative, content, rule=None, action=None):
    return {
        "sender": sender,
        "receiver": receiver,
        "performative": performative,
        "content": content,
        "rule": rule,
        "action": action,
    }


def conflict_exchanges(safety, retriever_available=True):
    """Create a challenge and its fixed reply for each recognised conflict rule."""
    messages = []
    for conflict in safety.get("conflicts", []):
        rule = conflict["code"]
        reply = CONFLICT_REPLIES.get(rule)
        if reply is None:
            continue
        target, performative, content = reply
        if target == "retriever" and not retriever_available:
            continue
        action = RETRIEVE_MORE if target == "retriever" else None
        messages.extend(
            [
                _message("safety_guard", target, "challenge", conflict["message"], rule),
                _message(target, "safety_guard", performative, content, rule, action),
            ]
        )
    return messages


def override_exchange(policy):
    """The safety guard challenges the policy when the rules overrode its chosen step."""
    if not (policy and policy.get("overridden_by_rules")):
        return []
    return [
        _message(
            "safety_guard",
            "support_policy",
            "challenge",
            "Luật yêu cầu mức chuyển tuyến cao hơn bước policy đã chọn.",
        ),
        _message(
            "support_policy",
            "safety_guard",
            "accept",
            "Chấp nhận bị ghi đè: bước tiếp theo là chuyển bác sĩ vì luật đã yêu cầu mức cao hơn "
            "bước tôi chọn.",
        ),
    ]


def requested_actions(messages):
    """Actions that components proposed and the Orchestrator should carry out."""
    return [m["action"] for m in messages if m["performative"] == "propose" and m.get("action")]


def retrieval_outcome(count, status_label, rule=None, failed=False):
    """The retriever reports what the wider search found, or that it failed."""
    content = (
        f"Tìm mở rộng gặp lỗi; giữ {count} đoạn bằng chứng trước đó ({status_label}); "
        "mức chuyển tuyến giữ nguyên."
        if failed
        else f"Đã tìm mở rộng: {count} đoạn bằng chứng ({status_label}); "
        "mức chuyển tuyến giữ nguyên."
    )
    return _message("retriever", "safety_guard", "inform", content, rule)
