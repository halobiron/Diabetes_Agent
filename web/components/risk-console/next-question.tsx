"use client";

import { Loader2 } from "lucide-react";

import { ESCALATION_LABELS } from "@/lib/labels";
import type { AskableField, FollowupQuestion, PatientInput, PredictionResult } from "@/types/healthcare";

import { Bubble, Say, Seal } from "./agents";
import { Choice } from "./inputs";

/** Bạn Gợi hỏi thêm một câu để đánh giá chính xác hơn. */
export function NextQuestion({ question, pending, error, onAnswer }: {
  question: FollowupQuestion;
  pending: boolean;
  error: Error | null;
  onAnswer: (answer: Partial<PatientInput>) => void;
}) {
  return (
    <section aria-labelledby="next-question-title" className="rise rounded-3xl border-2 border-dashed bg-panel p-5 md:p-7" style={{ borderColor: "#0b6b8688" }}>
      <h2 id="next-question-title" className="sr-only">Bạn Gợi hỏi thêm</h2>
      <Say id="goi" size={80} mood={pending ? "think" : "talk"} text={`Khoan đã, cho mình hỏi thêm một câu nhé. ${question.question}`} />
      <div className="mt-4 md:pl-[92px]">
        <Bubble id="goi" className="text-sm text-muted">{question.reason}</Bubble>
        {pending ? (
          <p role="status" className="mt-4 flex items-center gap-2 text-base font-semibold text-info">
            <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" /> Mình đang nhờ cả đội tính lại…
          </p>
        ) : null}
        <YesNoAnswer field={question.field} pending={pending} onAnswer={onAnswer} />
        <p className="mt-4 text-xs leading-5 text-muted">{question.model_note} Cập nhật áp dụng cho hồ sơ vừa đánh giá.</p>
        {error ? <p role="alert" className="mt-3 text-sm text-danger">{error.message} Bạn có thể thử cập nhật lại.</p> : null}
      </div>
    </section>
  );
}

function YesNoAnswer({ field, pending, onAnswer }: { field: AskableField; pending: boolean; onAnswer: (answer: Partial<PatientInput>) => void }) {
  return (
    <div className={`mt-4 grid grid-cols-3 gap-3 ${pending ? "pointer-events-none opacity-60" : ""}`}>
      <Choice active={false} onClick={() => onAnswer({ [field]: true })}>Có</Choice>
      <Choice active={false} onClick={() => onAnswer({ [field]: false })}>Không</Choice>
      <Choice active={false} onClick={() => onAnswer({ skipped_fields: [field] })}>Bỏ qua</Choice>
    </div>
  );
}

export function FollowupChange({ before, after }: { before: PredictionResult; after: PredictionResult }) {
  const delta = (after.probability - before.probability) * 100;
  const mood = delta < -0.05 ? "happy" : delta > 0.05 ? "worried" : "think";
  const line =
    delta < -0.05
      ? `Cảm ơn bạn! Nhờ thông tin này, xác suất giảm từ ${(before.probability * 100).toFixed(1)}% xuống ${(after.probability * 100).toFixed(1)}%.`
      : delta > 0.05
        ? `Cảm ơn bạn! Xác suất nhích lên từ ${(before.probability * 100).toFixed(1)}% thành ${(after.probability * 100).toFixed(1)}%. Cả đội đã tính lại mọi thứ bên dưới.`
        : `Cảm ơn bạn! Xác suất của mô hình vẫn quanh ${(after.probability * 100).toFixed(1)}%, nhưng cảnh báo và khuyến nghị bên dưới đã được tính lại.`;
  return (
    <section role="status" className="rise rounded-3xl border-2 border-borderSoft bg-panelMuted p-5 md:p-6">
      <Say id="mo" size={72} mood={mood} text={line} />
      <div className="mt-4 flex flex-wrap gap-x-3 gap-y-2 md:pl-[84px]">
        <Seal id="mo" tilt={-2}>Cảnh báo {before.safety.alerts.length} → {after.safety.alerts.length}</Seal>
        <Seal id="chung" tilt={2}>Bằng chứng {before.retrieved_context.length} → {after.retrieved_context.length}</Seal>
        <Seal id="luat" tilt={-1}>{ESCALATION_LABELS[after.safety.escalation]}</Seal>
      </div>
    </section>
  );
}
