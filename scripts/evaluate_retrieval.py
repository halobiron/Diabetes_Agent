"""Evaluate RAG retrieval quality and pick the relevance threshold.

Relevance labels come from `data/eval/rag_retrieval_questions.json`: a passage is relevant to a
question when its text matches that question's `relevant_if` pattern. Every in-scope question
must have at least one relevant passage in the KB (checked here), so each label is grounded in
the corpus text. Labels are a keyword proxy for relevance: a passage that answers the question
without the key term counts as irrelevant, so precision is a lower bound.

Usage: python scripts/evaluate_retrieval.py [--output logs/retrieval-eval.json]
"""

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.retriever import ANSWER_PASSAGES, RetrievalAgent, is_dosing_text  # noqa: E402
from core.config import get_settings  # noqa: E402
from tools.neo4j_kb import KnowledgeGraph, create_driver  # noqa: E402
from tools.semantic_embeddings import SemanticEmbeddingModel  # noqa: E402

DATASET = PROJECT_ROOT / "data/eval/rag_retrieval_questions.json"
# Independent held-out chat questions labelled with the risk factor they mention.
HELDOUT = PROJECT_ROOT / "data/eval/chat_heldout_questions.json"
THRESHOLDS = [0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65]
TOP_K = ANSWER_PASSAGES


def build_retriever(knowledge_graph):
    # min_relevance=0 so one search yields every score; thresholds are applied afterwards.
    return RetrievalAgent(knowledge_graph, SemanticEmbeddingModel(), min_relevance=0.0)


def ranked(retriever, question):
    """Citations the way `ask` ranks them (final score), before any threshold is applied."""
    return retriever.ask(question, n_results=len(retriever.evidence))["citations"]


def best(citations):
    return round(max((c["relevance"] for c in citations), default=0.0), 3)


def evaluate(retriever, data):
    shown = {i: e for i, e in retriever.evidence.items() if i not in retriever.withheld}
    labelled = []
    for item in data["in_scope"]:
        pattern = re.compile(item["relevant_if"], re.IGNORECASE | re.DOTALL)
        sources = set(item.get("relevant_source", []))
        relevant = {
            i for i, e in shown.items() if pattern.search(e["text"]) or e["source_id"] in sources
        }
        if not relevant:
            raise SystemExit(f"{item['id']}: no passage in the KB matches the label pattern")
        labelled.append((item, relevant, ranked(retriever, item["question"])))
    out_of_scope = [(q, ranked(retriever, q)) for q in data["out_of_scope"]]

    rows = []
    for threshold in THRESHOLDS:
        hits = precisions = recalls = mrr = answered = 0.0
        for _item, relevant, citations in labelled:
            top = [c for c in citations if c["relevance"] >= threshold][:TOP_K]
            found = [c["evidence_id"] in relevant for c in top]
            answered += bool(top)
            hits += any(found)
            precisions += (sum(found) / len(top)) if top else 0.0
            recalls += sum(found) / min(TOP_K, len(relevant))
            first = next((n for n, ok in enumerate(found, 1) if ok), None)
            mrr += 1 / first if first else 0.0
        n = len(labelled)
        accepted = sum(1 for _q, cs in out_of_scope if any(c["relevance"] >= threshold for c in cs))
        rows.append(
            {
                "threshold": threshold,
                f"hit@{TOP_K}": round(hits / n, 3),
                f"precision@{TOP_K}": round(precisions / n, 3),
                f"recall@{TOP_K}": round(recalls / n, 3),
                "mrr": round(mrr / n, 3),
                "answered_in_scope": round(answered / n, 3),
                "wrongly_answered_out_of_scope": round(accepted / len(out_of_scope), 3),
            }
        )
    dosing_leaks = [
        {"question": question, "evidence_id": c["evidence_id"]}
        for question in data["dosing"]
        for c in ranked(retriever, question)
        if is_dosing_text(c["text"])
    ]
    return {
        "factor_detection": factor_detection(retriever),
        "kb_source": retriever.kb_source,
        "embedding_model": retriever.embedding_model.name,
        "passages": len(retriever.evidence),
        "passages_withheld_dosing": len(retriever.withheld),
        "in_scope_questions": len(labelled),
        "out_of_scope_questions": len(out_of_scope),
        "relevant_passages_per_question": {i["id"]: len(r) for i, r, _c in labelled},
        "by_threshold": rows,
        "best_score_out_of_scope": {q: best(cs) for q, cs in out_of_scope},
        "best_score_in_scope": {i["id"]: best(cs) for i, _r, cs in labelled},
        "dosing_questions": len(data["dosing"]),
        "dosing_passages_returned": dosing_leaks,
        "top_k": TOP_K,
    }


def factor_detection(retriever):
    """How well chat finds the risk factor a held-out question mentions (KB names + aliases)."""
    questions = json.loads(HELDOUT.read_text(encoding="utf-8"))["questions"]
    found = exact = extra = 0
    mismatches = []
    for item in questions:
        detected = set(retriever._question_factors(item["question"]))
        gold = {item["factor"]} if item["factor"] else set()
        found += bool(gold & detected)
        exact += detected == gold
        extra += bool(detected - gold)
        if detected != gold:
            mismatches.append(
                {"id": item["id"], "gold": item["factor"], "detected": sorted(detected)}
            )
    with_factor = sum(1 for item in questions if item["factor"])
    return {
        "questions": len(questions),
        "gold_factor_found": f"{found}/{with_factor}",
        "exact_match": f"{exact}/{len(questions)}",
        "questions_with_an_extra_factor": f"{extra}/{len(questions)}",
        "mismatches": mismatches,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "logs/retrieval-eval.json")
    args = parser.parse_args()
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    settings = get_settings()
    with create_driver(settings) as driver:
        graph = KnowledgeGraph(driver, settings.neo4j_database)
        graph.export_kb()  # Fail clearly if the required database has not been populated.
        result = evaluate(build_retriever(graph), data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
