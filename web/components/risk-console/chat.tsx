"use client";

import { useMutation } from "@tanstack/react-query";
import { ChevronDown, Loader2, Send } from "lucide-react";
import { useState, type FormEvent } from "react";

import { askQuestion } from "@/lib/api";
import type { ChatReply } from "@/types/healthcare";

import { Avatar, CAST } from "./agents";
import { CitationLink } from "./citation";

const EXAMPLES = [
  "Chẩn đoán đái tháo đường bằng xét nghiệm nào?",
  "Béo phì ảnh hưởng đến nguy cơ tiểu đường thế nào?",
  "Chế độ ăn nào phù hợp cho người tiền đái tháo đường?",
];

export function ChatPanel({ className = "" }: { className?: string }) {
  const [question, setQuestion] = useState("");
  const mutation = useMutation({ mutationFn: askQuestion });

  function ask(text: string) {
    const trimmed = text.trim();
    if (trimmed.length < 2 || mutation.isPending) return;
    setQuestion(trimmed);
    mutation.mutate(trimmed);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    ask(question);
  }

  return (
    <details className={`group rounded-2xl border-2 border-borderSoft bg-panel ${className}`}>
      <summary className="flex cursor-pointer list-none items-center gap-4 p-4 md:px-6 [&::-webkit-details-marker]:hidden">
        <Avatar id="chung" size={44} />
        <span className="min-w-0 flex-1">
          <span className="block text-lg font-bold" style={{ color: CAST.chung.ink }}>Hỏi đáp về đái tháo đường</span>
          <span className="block text-sm text-muted">Trả lời từ cơ sở tri thức y khoa, có trích dẫn nguồn</span>
        </span>
        <ChevronDown aria-hidden="true" className="h-5 w-5 shrink-0 text-muted transition group-open:rotate-180" />
      </summary>
      <div className="space-y-4 p-4 pt-0 md:px-6 md:pb-6">
        <form onSubmit={submit} className="flex gap-2">
          <label htmlFor="chat-question" className="sr-only">Câu hỏi</label>
          <input
            id="chat-question"
            value={question}
            maxLength={500}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ví dụ: Chẩn đoán đái tháo đường bằng xét nghiệm nào?"
            className="min-h-11 min-w-0 flex-1 rounded-lg border-2 border-borderSoft bg-canvas px-3 text-base focus-visible:outline focus-visible:outline-2 focus-visible:outline-info"
          />
          <button
            type="submit"
            disabled={mutation.isPending || question.trim().length < 2}
            className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-info px-4 text-sm font-bold text-onAccent disabled:opacity-50"
          >
            {mutation.isPending ? <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" /> : <Send aria-hidden="true" className="h-4 w-4" />}
            Hỏi
          </button>
        </form>

        {!mutation.data && !mutation.isPending ? (
          <div className="flex flex-wrap gap-2">
            {EXAMPLES.map((example) => (
              <button
                key={example}
                type="button"
                onClick={() => ask(example)}
                className="min-h-11 rounded-full border border-borderSoft bg-canvas px-3 py-1.5 text-left text-sm text-muted hover:text-ink"
              >
                {example}
              </button>
            ))}
          </div>
        ) : null}

        {mutation.isPending ? <p role="status" className="text-sm font-semibold text-info">Đang tìm trong cơ sở tri thức…</p> : null}
        {mutation.error ? <p role="alert" className="text-sm font-semibold text-red-700">{mutation.error.message}</p> : null}
        {mutation.data ? <Answer reply={mutation.data} /> : null}
      </div>
    </details>
  );
}

function Answer({ reply }: { reply: ChatReply }) {
  const { trace } = reply;
  return (
    <div className="space-y-4" aria-live="polite">
      <div className="whitespace-pre-line text-base leading-relaxed">{reply.answer}</div>

      {reply.citations.length > 0 ? (
        <ol className="space-y-2">
          {reply.citations.map((item, index) => (
            <li key={item.evidence_id} className="rounded-lg border border-borderSoft bg-canvas p-3">
              <details>
                <summary className="cursor-pointer text-sm font-semibold">
                  [{index + 1}] {item.title} <span className="font-normal text-muted">· điểm {item.final_score.toFixed(2)}</span>
                </summary>
                <p className="mt-2 text-sm leading-relaxed">{item.text}</p>
                <p className="mt-2 text-xs text-muted">
                  <CitationLink citation={item} /> · cách tìm: {item.via === "graph+semantic" ? "ngữ nghĩa + đồ thị" : "ngữ nghĩa"}
                </p>
              </details>
            </li>
          ))}
        </ol>
      ) : null}

      <details className="rounded-lg border border-borderSoft bg-canvas p-3">
        <summary className="cursor-pointer text-sm font-semibold">Cách hệ thống truy xuất (vết RAG)</summary>
        <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm leading-relaxed">
          <li>Nhúng câu hỏi bằng <code>{trace.embedding_model}</code>.</li>
          <li>
            So khớp cosine với {trace.passages_in_index} đoạn trong chỉ mục (điểm cao nhất {(trace.best_score ?? 0).toFixed(2)});
            chỉ giữ đoạn từ {trace.min_relevance}, còn {trace.passages_above_floor ?? 0} đoạn.
          </li>
          <li>
            Đồ thị tri thức ({trace.kb_source}): yếu tố nguy cơ nhận ra trong câu hỏi: {trace.graph_factors.join(", ") || "không có"};
            {" "}{trace.graph_linked ?? 0} đoạn được cộng {trace.graph_boost} điểm.
          </li>
          <li>Xếp theo điểm cuối và ghép thành câu trả lời kèm trích dẫn.</li>
        </ol>
      </details>
    </div>
  );
}
