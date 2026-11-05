"use client";

import { ArrowRight, Loader2 } from "lucide-react";
import { useState, type FormEvent } from "react";

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
        {question.kind === "risk_factor" && question.field ? <YesNoAnswer field={question.field} pending={pending} onAnswer={onAnswer} /> : <GlucoseAnswer pending={pending} onAnswer={onAnswer} />}
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

function GlucoseAnswer({ pending, onAnswer }: { pending: boolean; onAnswer: (answer: Partial<PatientInput>) => void }) {
  const [glucose, setGlucose] = useState("");
  const [context, setContext] = useState<NonNullable<PatientInput["glucose_context"]>>("unspecified");

  function answer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onAnswer({ glucose: Number(glucose), glucose_unavailable: false, glucose_context: context });
  }

  return (
    <form onSubmit={answer} className="mt-4">
      <fieldset disabled={pending} className="flex min-w-0 flex-col gap-3 disabled:opacity-60 sm:flex-row sm:flex-wrap sm:items-end">
        <label className="block sm:w-44">
          <span className="mb-1 block text-sm">Kết quả đường huyết (mg/dL)</span>
          <input autoComplete="off" required type="number" min="0" max="500" step="any" value={glucose} onChange={(event) => setGlucose(event.target.value)} className="field-input tabular-nums" placeholder="Nhập số đo thực tế" />
        </label>
        <label className="block min-w-0 sm:max-w-sm sm:flex-1">
          <span className="mb-1 block text-sm">Bối cảnh đo</span>
          <select required className="field-input" value={context} onChange={(event) => setContext(event.target.value as typeof context)}>
            <option value="unspecified" disabled>Chọn bối cảnh đo</option>
            <option value="fasting">Lúc đói (nhịn ăn ít nhất 8 giờ)</option>
            <option value="random">Ngẫu nhiên</option>
            <option value="after_meal">Sau ăn thông thường</option>
            <option value="unknown">Không nhớ / không rõ</option>
          </select>
        </label>
        <button type="submit" disabled={pending || context === "unspecified"} className="btn-primary">
          {pending ? <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" /> : <ArrowRight aria-hidden="true" className="h-4 w-4" />}Cập nhật đánh giá
        </button>
        <button type="button" disabled={pending} onClick={() => onAnswer({ glucose: null, glucose_context: "unspecified", glucose_unavailable: true })} className="btn-secondary">
          Chưa có kết quả đo
        </button>
      </fieldset>
    </form>
  );
}

/** Ông Mô báo kết quả vừa đổi thế nào sau khi bạn trả lời. */
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
      <p className="mt-3 text-xs leading-5 text-muted md:pl-[84px]">Glucose không trực tiếp thay đổi xác suất MLP BRFSS.</p>
    </section>
  );
}
