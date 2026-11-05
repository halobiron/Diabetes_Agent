"""Typed messages between the components when their conclusions disagree.

This is a small, deterministic subset of FIPA-ACL: a message has a sender, a receiver,
a performative (`challenge`, `accept`, `propose`, `inform`) and a short content. A
component challenges another when a rule shows that the other's conclusion cannot stand
alone; the receiver answers through its own responder function below. Nothing here calls
an LLM.

Only one kind of message changes the outcome: a `propose` that carries an `action`. The
Orchestrator carries that action out (today: a wider evidence search proposed by the
retriever) and then reports the result back as an `inform`. Every other message records
why the rules prevailed. Nothing in the dialogue can lower an escalation level: the rules
still take precedence (see `Orchestrator._choose_next_step`).
"""

from dataclasses import asdict, dataclass
from typing import Optional

CHALLENGE = "challenge"
ACCEPT = "accept"
PROPOSE = "propose"
INFORM = "inform"

RETRIEVE_MORE = "retrieve_more_evidence"


@dataclass(frozen=True)
class Message:
    sender: str
    receiver: str
    performative: str
    content: str
    rule: Optional[str] = None  # rule code that caused the message, if any
    action: Optional[str] = None  # work the Orchestrator carries out for a `propose`

    def as_dict(self):
        return asdict(self)


def _risk_model_responds(challenge):
    """The statistical model concedes where a measurement beats it; it holds where it does not."""
    if challenge.rule == "CF-PRED-LOW-MEASURED-HIGH":
        return Message(
            "risk_model",
            challenge.sender,
            ACCEPT,
            "Tôi chỉ thấy các yếu tố lối sống nên không thấy số đo nguy hiểm này; "
            "chấp nhận nâng nguy cơ hiệu lực lên Cao theo số đo.",
            challenge.rule,
        )
    if challenge.rule == "CF-PRED-HIGH-GLUCOSE-NORMAL":
        return Message(
            "risk_model",
            challenge.sender,
            PROPOSE,
            "Glucose không phải đặc trưng của tôi nên một lần đo bình thường không bác được dự đoán; "
            "giữ mức Cao và đề nghị xét nghiệm A1C để xác nhận.",
            challenge.rule,
        )
    return Message(
        "risk_model",
        challenge.sender,
        ACCEPT,
        "Dữ liệu đầu vào chất lượng thấp; chấp nhận đánh dấu dự đoán là tạm thời.",
        challenge.rule,
    )


def _retriever_responds(challenge):
    """The retriever offers a wider search; the Orchestrator carries it out."""
    return Message(
        "retriever",
        challenge.sender,
        PROPOSE,
        "Đề nghị tìm mở rộng bằng chứng; mức chuyển tuyến không hạ trong lúc chờ.",
        challenge.rule,
        action=RETRIEVE_MORE,
    )


def _policy_responds(challenge):
    return Message(
        "support_policy",
        challenge.sender,
        ACCEPT,
        "Chấp nhận bị ghi đè: bước tiếp theo là chuyển bác sĩ vì luật đã yêu cầu mức cao hơn "
        "bước tôi chọn.",
        challenge.rule,
    )


RESPONDERS = {
    "risk_model": _risk_model_responds,
    "retriever": _retriever_responds,
    "support_policy": _policy_responds,
}

# Which component a conflict rule calls into question.
CONFLICT_TARGETS = {
    "CF-PRED-LOW-MEASURED-HIGH": "risk_model",
    "CF-PRED-HIGH-GLUCOSE-NORMAL": "risk_model",
    "CF-PRED-HIGH-LOW-QUALITY": "risk_model",
    "CF-ESCALATION-NO-EVIDENCE": "retriever",
}


def _exchange(target, rule, content):
    challenge = Message("safety_guard", target, CHALLENGE, content, rule)
    return [challenge, RESPONDERS[target](challenge)]


def conflict_exchanges(safety, retriever_available=True):
    """Challenge and reply for each fired conflict rule, as message dicts.

    The retriever is only challenged when there is a retriever to ask.
    """
    messages = []
    for conflict in safety.get("conflicts", []):
        target = CONFLICT_TARGETS.get(conflict["code"])
        if target is None or (target == "retriever" and not retriever_available):
            continue
        messages.extend(_exchange(target, conflict["code"], conflict["message"]))
    return [message.as_dict() for message in messages]


def override_exchange(policy):
    """The safety guard challenges the policy when the rules overrode its chosen step."""
    if not (policy and policy.get("overridden_by_rules")):
        return []
    messages = _exchange(
        "support_policy", None, "Luật yêu cầu mức chuyển tuyến cao hơn bước policy đã chọn."
    )
    return [message.as_dict() for message in messages]


def requested_actions(messages):
    """Actions that components proposed and the Orchestrator should carry out."""
    return [m["action"] for m in messages if m["performative"] == PROPOSE and m.get("action")]


def retrieval_outcome(count, status_label, rule=None, failed=False):
    """The retriever reports what the wider search found, or that it failed."""
    content = (
        f"Tìm mở rộng gặp lỗi; giữ {count} đoạn bằng chứng trước đó ({status_label}); "
        "mức chuyển tuyến giữ nguyên."
        if failed
        else f"Đã tìm mở rộng: {count} đoạn bằng chứng ({status_label}); "
        "mức chuyển tuyến giữ nguyên."
    )
    return Message("retriever", "safety_guard", INFORM, content, rule).as_dict()


def build_dialogue(safety, policy=None, retriever_available=True):
    """Messages for a finished run, in order; empty when the components agree."""
    return conflict_exchanges(safety, retriever_available) + override_exchange(policy)
