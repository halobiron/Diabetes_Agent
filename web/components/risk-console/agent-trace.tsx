"use client";

import { Fragment } from "react";

import { EVIDENCE_LABELS, RISK_LABELS } from "@/lib/labels";
import type { AgentMessage, PredictionResult } from "@/types/healthcare";

import { Avatar, Bubble, CAST, COMPONENT_CAST, Say, Seal, useInView, type Mood } from "./agents";

const PERFORMATIVES: Record<string, string> = { challenge: "phản biện", accept: "chấp nhận", propose: "đề xuất", inform: "thông báo" };
const ACTIONS: Record<string, string> = { retrieve_more_evidence: "tìm mở rộng bằng chứng, rồi tính lại luật và khuyến nghị" };
const MOOD: Record<string, Mood> = { challenge: "worried", accept: "happy", propose: "think", inform: "neutral" };

/** Nhân vật phụ trách một thành phần phía API (null nếu không có). */
function castOf(component: string) {
  const meta = COMPONENT_CAST[component];
  return meta ? CAST[meta.cast] : null;
}

/** Cuộc trao đổi giữa các agent, xen vào dòng thời gian ngay sau bước sinh ra nó. */
function DialogueChat({ messages }: { messages: AgentMessage[] }) {
  return (
    <li className="relative">
      <ol className="ml-[60px] space-y-3 rounded-2xl border-2 border-dashed border-borderSoft bg-panelMuted p-4">
        {messages.map((message, index) => {
          const sender = castOf(message.sender);
          const receiver = castOf(message.receiver);
          const senderId = COMPONENT_CAST[message.sender]?.cast ?? "luat";
          return (
            <li key={`${message.sender}-${index}`} className="flex gap-3">
              {sender ? <Avatar id={sender.id} size={40} mood={MOOD[message.performative] ?? "neutral"} /> : null}
              <div className="min-w-0 flex-1 space-y-1.5">
                <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1 text-sm">
                  <span className="font-bold" style={{ color: sender?.ink }}>{sender?.name ?? message.sender}</span>
                  <span className="text-muted">gửi tới {receiver?.name ?? message.receiver}</span>
                  <Seal id={senderId} tilt={-2} className="!px-2 !py-0 !text-xs">{PERFORMATIVES[message.performative] ?? message.performative}</Seal>
                </div>
                <Bubble id={senderId} className="text-sm">
                  {message.content}
                  {message.rule ? <span className="mt-1 block text-xs text-muted">Căn cứ: {message.rule}</span> : null}
                  {message.action ? <span className="mt-1 block text-xs font-bold" style={{ color: sender?.ink }}>Đã thực hiện: {ACTIONS[message.action] ?? message.action}</span> : null}
                </Bubble>
              </div>
            </li>
          );
        })}
      </ol>
    </li>
  );
}

/** Dòng thời gian chuyền hồ sơ: mỗi nhân vật nhận hồ sơ từ người trước, làm phần của mình rồi chuyền tiếp. */
export function AgentTrace({ result }: { result: PredictionResult }) {
  const trace = result.trace;
  const [ref, seen] = useInView<HTMLElement>();
  if (!trace) return <p className="text-sm text-muted">Phiên bản API này chưa trả về vết xử lý của các agent.</p>;

  const total = Math.max(trace.steps.reduce((sum, step) => sum + step.ms, 0), 1);
  const errors = new Map((result.degraded ?? []).map((item) => [item.component, item.error]));
  const failed = trace.steps.filter((step) => step.status === "degraded").length;
  const mood: Mood = failed > 0 ? "worried" : "happy";
  // Mỗi thông điệp nằm ngay sau bước đã sinh ra nó (after_step = số bước đã ghi lúc đó).
  const dialogue = trace.dialogue ?? [];
  const chatAt = (position: number) => {
    const messages = dialogue.filter((message) => Math.min(message.after_step ?? trace.steps.length, trace.steps.length) === position);
    return messages.length > 0 ? <DialogueChat key={`chat-${position}`} messages={messages} /> : null;
  };
  const summary = `Cả đội đã chuyền hồ sơ của bạn qua ${trace.steps.length} bước trong ${trace.total_ms.toFixed(0)} ms, tìm được ${trace.evidence_count} đoạn bằng chứng (${EVIDENCE_LABELS[trace.evidence_status] ?? trace.evidence_status}). ${failed > 0 ? `Có ${failed} bước phải dùng cách dự phòng.` : "Không bước nào phải dùng cách dự phòng."}`;

  return (
    <section ref={ref} aria-labelledby="trace-title" className="act-in min-w-0 space-y-6">
      <h2 id="trace-title" className="sr-only">Cả đội đã làm việc thế nào</h2>
      <Say id="tiep" size={72} mood={mood} text={summary} run={seen} />

      {trace.disagreement ? (
        <div role="status" className="space-y-3 rounded-3xl border-2 border-borderSoft bg-panelMuted p-5 md:p-6">
          <Say id="mo" size={56} mood="think" text={`Tôi xếp nguy cơ của bạn ở mức ${RISK_LABELS[trace.disagreement.model_risk]}.`} run={seen} />
          <Say id="luat" size={56} mood="worried" text={`Nhưng số đo thực tế nâng lên mức ${RISK_LABELS[trace.disagreement.effective_risk]}. Luật được ưu tiên vì số đo thực tế đáng tin hơn một ước tính thống kê.`} run={seen} />
          <ul className="space-y-1 text-sm text-muted md:pl-[68px]">
            {trace.disagreement.rules.map((rule) => <li key={rule.code}><Seal id="luat" tilt={-1} className="mr-2 !px-2 !py-0 !text-xs">{rule.code}</Seal>{rule.message}</li>)}
            {/* Khi có hội thoại, các xung đột đã hiện ở đó (đúng chỗ xảy ra); chỉ liệt kê lại nếu API cũ không trả hội thoại. */}
            {dialogue.length === 0 ? trace.disagreement.conflicts.map((message) => <li key={message}>{message}</li>) : null}
          </ul>
        </div>
      ) : null}

      <ol className="relative space-y-4">
        <span aria-hidden="true" className="absolute bottom-6 left-[27px] top-6 w-0.5 bg-borderSoft" />
        {chatAt(0)}
        {trace.steps.map((step, index) => {
          const start = trace.steps.slice(0, index).reduce((sum, item) => sum + item.ms, 0);
          const degraded = step.status === "degraded";
          const meta = COMPONENT_CAST[step.component];
          const member = meta ? CAST[meta.cast] : null;
          const ink = degraded ? "#b3261e" : member?.ink ?? "#4b3fa8";
          return (
            <Fragment key={`${step.component}-${index}`}>
            <li className="relative" style={seen ? { animation: `step-in 0.45s cubic-bezier(0.16,1,0.3,1) ${index * 0.12}s both` } : { opacity: 0 }}>
              <details className="group">
                <summary className="flex cursor-pointer list-none items-center gap-3 rounded-2xl py-1 pr-2 hover:bg-canvas [&::-webkit-details-marker]:hidden">
                  <span className="relative z-[1] rounded-full bg-canvas p-0.5">
                    {meta ? <Avatar id={meta.cast} size={48} mood={degraded ? "worried" : "neutral"} /> : <span className="block h-12 w-12 rounded-full bg-panelMuted" />}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex flex-wrap items-baseline justify-between gap-x-3">
                      <span className="text-base font-bold" style={{ color: ink }}>{member?.name ?? step.component}</span>
                      <span className="text-xs tabular-nums text-muted">{step.ms.toFixed(1)} ms</span>
                    </span>
                    <span className="block truncate text-sm text-muted">{meta?.label ?? step.component}</span>
                    <span className="relative mt-1.5 block h-2.5 overflow-hidden rounded-full bg-panelMuted" role="img" aria-label={`${step.ms.toFixed(1)} ms, bắt đầu sau ${start.toFixed(1)} ms`}>
                      <span
                        className="absolute inset-y-0 rounded-full"
                        style={{
                          left: `${(start / total) * 100}%`,
                          width: seen ? `${Math.max(1.5, (step.ms / total) * 100)}%` : "0%",
                          backgroundColor: ink,
                          transition: `width 0.8s cubic-bezier(0.16,1,0.3,1) ${0.2 + index * 0.12}s`,
                        }}
                      />
                    </span>
                  </span>
                  {degraded ? <Seal id="luat" tilt={-4} className="shrink-0 !px-2 !py-0 !text-xs">Dự phòng</Seal> : null}
                </summary>
                <div className="pb-1 pl-[60px] pt-2">
                  <Bubble id={meta?.cast ?? "mo"} className="text-sm text-muted">
                    {step.detail}
                    {degraded && errors.get(step.component) ? ` (${errors.get(step.component)})` : ""}
                  </Bubble>
                </div>
              </details>
            </li>
            {chatAt(index + 1)}
            </Fragment>
          );
        })}
      </ol>
      <p className="text-xs leading-5 text-muted">Bấm vào từng người để nghe họ kể đã làm gì. Khung hội thoại xen giữa các bước là lúc các agent phản biện nhau, đúng vào thời điểm chúng xảy ra. Một người có thể xuất hiện nhiều lần khi cần truy xuất thêm bằng chứng và tính lại khuyến nghị.</p>
    </section>
  );
}
