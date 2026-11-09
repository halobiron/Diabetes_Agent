"""Demo trên terminal theo thứ tự: KB Neo4j -> chat RAG -> hệ đa agent.

    python scripts/demo.py            # cả ba phần
    python scripts/demo.py --part 2   # chỉ chat RAG

Đọc NEO4J_PASSWORD từ .env (Python không tự đọc .env). Không cần OPENAI_API_KEY.
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CHAT_QUESTIONS = [
    "Béo phì có làm tăng nguy cơ tiểu đường không?",
    "Chẩn đoán đái tháo đường bằng xét nghiệm nào?",
    "Hút thuốc lá ảnh hưởng thế nào đến bệnh tiểu đường?",
    "Cách nấu phở bò ngon",  # ngoài chủ đề: hệ thống phải từ chối
]

PATIENTS = {
    "Hồ sơ nguy cơ cao": dict(
        age=62, bmi=34, bp=150, glucose=135, high_chol=True, smoker=True, phys_activity=False,
        general_health=4, diff_walk=True, heart_disease_or_attack=True, fruits=False, veggies=False,
    ),
    "Hồ sơ nguy cơ thấp": dict(
        age=28, bmi=21, bp=112, glucose=88, high_chol=False, smoker=False, phys_activity=True,
        general_health=1, fruits=True, veggies=True,
    ),
}

AGENT_NAMES = {
    "diagnosis": "Agent chẩn đoán",
    "advisor": "Agent tư vấn",
    "orchestrator": "Agent điều phối",
}


def load_env():
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())
    os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
    os.environ["OPENAI_API_KEY"] = ""


def heading(text):
    print(f"\n{'=' * 78}\n{text}\n{'=' * 78}")


def show_kb(agent):
    heading("PHẦN 1 - Cơ sở tri thức trong Neo4j")
    kb = agent.retriever.kb
    print(f"Nguồn KB: {agent.retriever.kb_source}")
    if hasattr(kb, "stats"):
        print("Số nút / quan hệ:", kb.stats())
    print("\nYếu tố nguy cơ -> can thiệp/xét nghiệm -> đoạn bằng chứng:")
    seen = set()
    for row in kb.support_for_risk_factors(["BMI", "HighBP", "Smoker", "glucose"]):
        key = (row["factor_key"], row["support_name"])
        if key in seen:
            continue
        seen.add(key)
        print(f"  {row['factor_key']:<8} -> {row['support_name']:<40} ({row['evidence_id']})")
    print("\nTrên trình duyệt http://localhost:7474 chạy: MATCH (n)-[r]->(m) RETURN n,r,m LIMIT 100")


def show_chat(agent):
    heading("PHẦN 2 - Chat RAG trên KB")
    for question in CHAT_QUESTIONS:
        reply = agent.retriever.ask(question, n_results=3)
        trace = reply["trace"]
        print(f"\nHỏi: {question}")
        print(
            f"  Truy xuất: điểm cao nhất {trace.get('best_score', 0):.2f}, "
            f"{trace.get('passages_above_floor', 0)}/{trace['passages_in_index']} đoạn qua ngưỡng "
            f"{trace['min_relevance']}, yếu tố đồ thị: {trace['graph_factors'] or 'không'}"
        )
        print(f"  Trạng thái: {reply['status']}")
        for line in reply["answer"].splitlines():
            print("  " + (line if len(line) < 200 else line[:197] + "..."))
        for number, item in enumerate(reply["citations"], start=1):
            print(f"  [{number}] {item['title']} (điểm {item['final_score']:.2f}, {item['via']})")


def show_agents(agent):
    heading("PHẦN 3 - Hệ đa agent")
    for name, patient in PATIENTS.items():
        result = agent.run(patient)
        print(f"\n{name}: xác suất {result['probability']:.1%}, mức {result['risk']}, "
              f"hướng xử trí {result['safety']['escalation']}")
        print("  Vết theo agent:")
        for step in result["trace"]["steps"]:
            print(f"    {AGENT_NAMES[step['agent']]:<16} {step['component']:<18} {step['detail']}")
        if result["policy"]:
            print(f"  Bước tiếp theo (Q-learning): {result['policy']['next_step']}")
        print("  Bằng chứng trích dẫn:")
        for item in result["retrieved_context"]:
            print(f"    - {item['title']} (độ liên quan {item['relevance']})")
        print("  Khuyến nghị:")
        for line in str(result["recommendation"]).splitlines():
            print("    " + line)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--part", type=int, choices=(1, 2, 3), help="chỉ chạy một phần")
    args = parser.parse_args()

    load_env()
    import main as app

    app.CHROMA_PATH = Path(tempfile.mkdtemp(prefix="demo-chroma-"))
    agent = app.build_agent()
    parts = {1: show_kb, 2: show_chat, 3: show_agents}
    for number in [args.part] if args.part else parts:
        parts[number](agent)


if __name__ == "__main__":
    main()
