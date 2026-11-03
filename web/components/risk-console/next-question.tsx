import { ArrowRight, CheckCircle2, Loader2, MessageCircleQuestion } from "lucide-react";
import { useState, type FormEvent } from "react";

import type { FollowupQuestion, PatientInput, PredictionResult } from "@/types/healthcare";
import { ESCALATION_LABELS } from "@/lib/labels";

export function NextQuestion({ question, pending, error, onAnswer }: {
  question: FollowupQuestion;
  pending: boolean;
  error: Error | null;
  onAnswer: (answer: Partial<PatientInput>) => void;
}) {
  const [glucose, setGlucose] = useState("");
  const [context, setContext] = useState<NonNullable<PatientInput["glucose_context"]>>("unspecified");

  function answer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onAnswer({ ...(question.kind === "glucose" ? { glucose: Number(glucose), glucose_unavailable: false } : {}), glucose_context: context });
  }

  return (
    <section aria-labelledby="next-question-title" className="console-panel rounded-lg p-5">
      <h2 id="next-question-title" className="flex items-start gap-2 text-base font-semibold"><MessageCircleQuestion aria-hidden="true" className="mt-0.5 h-5 w-5 shrink-0 text-info" />{question.question}</h2>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">{question.reason}</p>
      <form onSubmit={answer} className="mt-4">
        <fieldset disabled={pending} className="flex min-w-0 flex-col gap-3 disabled:opacity-60 sm:flex-row sm:flex-wrap sm:items-end">
          {question.kind === "glucose" ? <label className="block sm:w-44"><span className="mb-1 block text-sm">Kết quả đường huyết (mg/dL)</span><input autoComplete="off" required type="number" min="0" max="500" step="any" value={glucose} onChange={(event) => setGlucose(event.target.value)} className="field-input" placeholder="Nhập số đo thực tế" /></label> : null}
          <label className="block min-w-0 sm:max-w-sm sm:flex-1"><span className="mb-1 block text-sm">Bối cảnh đo</span><select required className="field-input" value={context} onChange={(event) => setContext(event.target.value as typeof context)}>
            <option value="unspecified" disabled>Chọn bối cảnh đo</option>
            <option value="fasting">Lúc đói (nhịn ăn ít nhất 8 giờ)</option>
            <option value="random">Ngẫu nhiên</option>
            <option value="after_meal">Sau ăn thông thường</option>
            <option value="unknown">Không nhớ / không rõ</option>
          </select></label>
          <button type="submit" disabled={pending || context === "unspecified"} className="flex min-h-11 items-center justify-center gap-2 rounded-md bg-info px-4 text-sm font-semibold text-canvas transition hover:bg-[#7bbce9] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-info disabled:cursor-not-allowed disabled:opacity-60">{pending ? <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" /> : <ArrowRight aria-hidden="true" className="h-4 w-4" />}Cập nhật đánh giá</button>
          {question.kind === "glucose" ? <button type="button" disabled={pending} onClick={() => onAnswer({ glucose: null, glucose_context: "unspecified", glucose_unavailable: true })} className="min-h-11 rounded-md border border-borderSoft px-4 text-sm text-ink hover:bg-panelMuted focus-visible:outline focus-visible:outline-2 focus-visible:outline-info">Chưa có kết quả đo</button> : null}
        </fieldset>
      </form>
      <p className="mt-3 text-xs leading-5 text-muted">{question.model_note} Cập nhật áp dụng cho hồ sơ vừa đánh giá.</p>
      {error ? <p role="alert" className="mt-3 text-sm text-[#ffb4ad]">{error.message} Bạn có thể thử cập nhật lại.</p> : null}
    </section>
  );
}

export function FollowupChange({ before, after }: { before: PredictionResult; after: PredictionResult }) {
  return (
    <section role="status" className="rounded-lg border border-borderSoft bg-panelMuted p-4 text-sm">
      <h2 className="flex items-center gap-2 font-semibold"><CheckCircle2 aria-hidden="true" className="h-4 w-4 text-info" />Đã cập nhật hồ sơ</h2>
      <dl className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div><dt className="text-xs text-muted">Xác suất mô hình</dt><dd className="mt-1 tabular-nums">{(before.probability * 100).toFixed(1)}% → {(after.probability * 100).toFixed(1)}%</dd></div>
        <div><dt className="text-xs text-muted">Số cảnh báo</dt><dd className="mt-1 tabular-nums">{before.safety.alerts.length} → {after.safety.alerts.length}</dd></div>
        <div><dt className="text-xs text-muted">Số đoạn bằng chứng</dt><dd className="mt-1 tabular-nums">{before.retrieved_context.length} → {after.retrieved_context.length}</dd></div>
        <div><dt className="text-xs text-muted">Hướng xử trí hiện tại</dt><dd className="mt-1">{ESCALATION_LABELS[after.safety.escalation]}</dd></div>
      </dl>
      <p className="mt-3 text-xs leading-5 text-muted">Thang đo, cảnh báo, bằng chứng và khuyến nghị bên dưới đã được tính lại. Glucose không trực tiếp thay đổi xác suất MLP BRFSS.</p>
    </section>
  );
}
