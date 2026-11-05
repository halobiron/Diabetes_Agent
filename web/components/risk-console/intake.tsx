"use client";

import clsx from "clsx";
import { ArrowLeft, ArrowRight, Loader2, Pencil, Sparkles } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";

import type { PatientInput } from "@/types/healthcare";

import { Avatar, CAST, Say, type CastId, type Mood } from "./agents";
import { ChipGroup, HABITS, HISTORY, type GroupItem } from "./grouped-choices";
import { SliderField, Toggle } from "./form-controls";
import { Choice, Stepper } from "./inputs";
import type { PatientFieldChange } from "./types";

type Props = {
  initialStep?: string | null;
  form: PatientInput;
  calculatedBmi: number;
  isPending: boolean;
  error: Error | null;
  hasResult: boolean;
  onSubmit: () => void;
  onFieldChange: PatientFieldChange;
  onCancel: () => void;
};

type Reaction = { mood: Mood; text: string };
type Ctx = { form: PatientInput; set: PatientFieldChange; bmi: number; answer: (reaction?: Reaction | null) => void };

type Step = {
  id: string;
  cast: CastId;
  ask: string;
  body: (c: Ctx) => ReactNode;
  summary: (f: PatientInput) => string;
  label: string;
};

const GENERAL_HEALTH = ["Rất tốt", "Tốt", "Khá", "Trung bình", "Kém"];

function groupSummary(f: PatientInput, items: GroupItem[], none: string) {
  if (items.every((i) => f[i.key] === null)) return "Chưa rõ";
  const on = items.filter((i) => f[i.key] === true).map((i) => i.label);
  return on.length ? on.join(", ") : none;
}

function bmiReaction(bmi: number): Reaction {
  if (bmi < 18.5) return { mood: "think", text: `BMI của bạn khoảng ${bmi.toFixed(1)}, hơi thấp cân.` };
  if (bmi < 23) return { mood: "happy", text: `BMI ${bmi.toFixed(1)}, đẹp lắm, đang ở mức bình thường!` };
  if (bmi < 25) return { mood: "think", text: `BMI ${bmi.toFixed(1)}, hơi thừa cân một chút.` };
  return { mood: "worried", text: `BMI ${bmi.toFixed(1)}, ở mức thừa cân. Mình sẽ lưu ý điều này.` };
}

const STEPS: Step[] = [
  {
    id: "body",
    cast: "tiep",
    label: "Số đo cơ thể",
    ask: "Chào bạn, mình là Bé Tiếp! Cho mình xin vài số đo cơ bản của bạn nhé. Mình sẽ tự tính BMI giúp bạn.",
    summary: (f) => `${f.age} tuổi, ${f.sex === "male" ? "nam" : "nữ"}, ${f.height_cm} cm, ${f.weight_kg} kg, huyết áp ${f.bp}`,
    body: ({ form, set, bmi }) => (
      <div className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <Stepper label="Tuổi" unit="tuổi" value={form.age} min={0} max={120} step={1} onChange={(v) => set("age", v)} />
          <div>
            <div className="field-label mb-1.5">Giới tính</div>
            <div className="grid h-16 grid-cols-2 gap-2">
              <Choice active={form.sex === "female"} onClick={() => set("sex", "female")}>Nữ</Choice>
              <Choice active={form.sex === "male"} onClick={() => set("sex", "male")}>Nam</Choice>
            </div>
          </div>
          <Stepper label="Chiều cao" unit="cm" value={form.height_cm} min={50} max={250} step={1} onChange={(v) => set("height_cm", v)} />
          <Stepper label="Cân nặng" unit="kg" value={form.weight_kg} min={2} max={300} step={0.5} onChange={(v) => set("weight_kg", v)} />
        </div>
        <Stepper label="Huyết áp tâm thu (số trên)" unit="mmHg" value={form.bp} min={0} max={260} step={5} onChange={(v) => set("bp", v)} />
        <div className="flex items-baseline justify-between rounded-2xl bg-canvas px-5 py-3">
          <span className="text-sm text-muted">BMI tự tính</span>
          <strong className="text-3xl tabular-nums">{bmi.toFixed(1)}</strong>
        </div>
      </div>
    ),
  },
  {
    id: "history",
    cast: "luat",
    label: "Tiền sử bệnh",
    ask: "Mình là Chú Luật, phụ trách an toàn. Bạn có điều nào sau đây không? Chọn hết những điều đúng với bạn.",
    summary: (f) => groupSummary(f, HISTORY, "Không có điều nào"),
    body: ({ form, set, answer }) => (
      <ChipGroup
        items={HISTORY}
        form={form}
        set={set}
        noneLabel="Không có điều nào"
        onChange={(next) => {
          const any = HISTORY.some((i) => next[i.key] === true);
          const none = HISTORY.every((i) => next[i.key] === false);
          const unknown = HISTORY.every((i) => next[i.key] === null);
          answer(
            any
              ? { mood: "worried", text: "Cảm ơn bạn đã chia sẻ, mình ghi lại cẩn thận." }
              : none
                ? { mood: "happy", text: "Tốt quá, mình ghi nhận rồi!" }
                : unknown
                  ? { mood: "think", text: "Chưa rõ cũng không sao, mình sẽ hỏi lại nếu cần." }
                  : null,
          );
        }}
      />
    ),
  },
  {
    id: "habits",
    cast: "goi",
    label: "Thói quen",
    ask: "Mình là Bạn Gợi! Còn thói quen hằng ngày thì sao? Chọn những điều đúng với bạn.",
    summary: (f) => groupSummary(f, HABITS, "Không có điều nào"),
    body: ({ form, set, answer }) => (
      <ChipGroup
        items={HABITS}
        form={form}
        set={set}
        noneLabel="Không có điều nào"
        onChange={(next) => {
          const bad = HABITS.filter((i) => !i.good && next[i.key] === true).length;
          const good = HABITS.filter((i) => i.good && next[i.key] === true).length;
          const unknown = HABITS.every((i) => next[i.key] === null);
          answer(
            unknown
              ? { mood: "think", text: "Chưa rõ cũng không sao, mình sẽ hỏi lại nếu cần." }
              : bad > 0
                ? { mood: "think", text: "Mình ghi lại rồi, ta cùng cải thiện dần nhé." }
                : good >= 2
                  ? { mood: "happy", text: "Tuyệt vời, thói quen tốt đó!" }
                  : { mood: "think", text: "Mình ghi nhận rồi nhé." },
          );
        }}
      />
    ),
  },
  {
    id: "feel",
    cast: "chung",
    label: "Cảm nhận chung",
    ask: "Mình là Cô Chứng. Nhìn chung bạn thấy sức khỏe mình thế nào? Phần còn lại không bắt buộc.",
    summary: (f) => `${GENERAL_HEALTH[f.general_health - 1] ?? f.general_health}, tinh thần kém ${f.mental_health_days} ngày, thể chất kém ${f.physical_health_days} ngày`,
    body: ({ form, set, answer }) => (
      <div className="space-y-5">
        <div className="grid grid-cols-5 gap-2">
          {GENERAL_HEALTH.map((label, i) => (
            <button
              key={label}
              type="button"
              aria-pressed={form.general_health === i + 1}
              onClick={() => {
                set("general_health", i + 1);
                answer(i <= 1 ? { mood: "happy", text: "Nghe vui quá!" } : i === 2 ? null : { mood: "worried", text: "Mình hiểu rồi, cảm ơn bạn đã nói thật." });
              }}
              className={clsx(
                "choice flex min-h-20 flex-col items-center justify-center rounded-2xl border-2 px-1 text-center text-xs font-bold sm:text-base",
                form.general_health === i + 1 ? "border-info bg-infoSoft text-info" : "border-borderSoft bg-panel text-ink hover:border-info/50",
              )}
            >
              <span className="text-2xl tabular-nums">{i + 1}</span>
              {label}
            </button>
          ))}
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <SliderField label="Ngày tinh thần kém (30 ngày qua)" min={0} max={30} value={form.mental_health_days} valueLabel={`${form.mental_health_days}/30`} onChange={(v) => set("mental_health_days", v)} />
          <SliderField label="Ngày thể chất kém (30 ngày qua)" min={0} max={30} value={form.physical_health_days} valueLabel={`${form.physical_health_days}/30`} onChange={(v) => set("physical_health_days", v)} />
        </div>
        <details className="group rounded-2xl border-2 border-borderSoft">
          <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between px-4 text-base font-semibold [&::-webkit-details-marker]:hidden">
            Hoàn cảnh xã hội và tiếp cận y tế (không bắt buộc)
            <span aria-hidden="true" className="text-muted group-open:hidden">+</span>
            <span aria-hidden="true" className="hidden text-muted group-open:inline">−</span>
          </summary>
          <div className="grid gap-4 border-t border-borderSoft p-4">
            <Toggle label="Dễ đến được cơ sở y tế" checked={form.any_healthcare} onChange={(v) => set("any_healthcare", v)} />
            <Toggle label="Từng ngại đi khám vì chi phí" checked={form.no_doc_bc_cost} onChange={(v) => set("no_doc_bc_cost", v)} />
            <SliderField label="Trình độ học vấn" min={1} max={6} value={form.education} valueLabel={`Mức ${form.education}/6`} lowLabel="Thấp" highLabel="Cao" onChange={(v) => set("education", v)} />
            <SliderField label="Mức thu nhập" min={1} max={8} value={form.income} valueLabel={`Mức ${form.income}/8`} lowLabel="Thấp" highLabel="Cao" onChange={(v) => set("income", v)} />
          </div>
        </details>
      </div>
    ),
  },
];

const SUMMARY_INDEX = STEPS.length;

export function Intake({ form, calculatedBmi, isPending, error, hasResult, onSubmit, onFieldChange, onCancel, initialStep }: Props) {
  const initialIndex = initialStep ? STEPS.findIndex((step) => step.id === initialStep) : -1;
  const [index, setIndex] = useState(initialIndex >= 0 ? initialIndex : hasResult ? SUMMARY_INDEX : 0);
  const [reaction, setReaction] = useState<Reaction | null>(null);
  const [fromSummary, setFromSummary] = useState(hasResult && initialIndex >= 0);
  const timer = useRef<number | null>(null);

  useEffect(() => () => { if (timer.current) window.clearTimeout(timer.current); }, []);

  function go(next: number) {
    if (timer.current) window.clearTimeout(timer.current);
    setReaction(null);
    setIndex(Math.max(0, Math.min(SUMMARY_INDEX, next)));
  }

  function advance() {
    go(fromSummary ? SUMMARY_INDEX : index + 1);
  }

  const onSummary = index === SUMMARY_INDEX;
  const step = onSummary ? null : STEPS[index];

  function answer(r?: Reaction | null) {
    if (!step) return;
    if (timer.current) window.clearTimeout(timer.current);
    setReaction(r ?? null);
  }

  const ctx: Ctx = { form, set: onFieldChange, bmi: calculatedBmi, answer };
  const progress = Math.round((Math.min(index, STEPS.length) / STEPS.length) * 100);
  const bmiNote = step?.id === "body" ? bmiReaction(calculatedBmi) : null;
  const shown = reaction ?? bmiNote;

  return (
    <div className="mx-auto w-full max-w-2xl px-5 pb-16 pt-8">
      <div className="mb-6" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress} aria-label="Tiến độ điền hồ sơ">
        <div className="mb-2 flex items-center justify-between text-sm font-semibold text-muted">
          <span>{onSummary ? "Xem lại hồ sơ" : `Câu ${index + 1} / ${STEPS.length}`}</span>
          <span className="tabular-nums">{progress}%</span>
        </div>
        <div className="h-3 overflow-hidden rounded-full bg-panelMuted">
          <div className="h-full rounded-full bg-info" style={{ width: `${progress}%`, transition: "width 0.5s cubic-bezier(0.16,1,0.3,1)" }} />
        </div>
      </div>

      {step ? (
        <section
          key={step.id}
          className="step-in"
          aria-live="polite"
          onKeyDown={(e) => {
            if (e.key === "Enter" && e.target instanceof HTMLInputElement && e.target.type === "number") {
              e.preventDefault();
              advance();
            }
          }}
        >
          <Say id={step.cast} text={step.ask} mood={index === 0 && !fromSummary ? "wave" : shown?.mood ?? "neutral"} size={96} />

          {shown ? (
            <div key={shown.text} className="bubble ml-[108px] mt-3 inline-block rounded-2xl rounded-tl-sm bg-infoSoft px-4 py-2 text-base font-semibold" style={{ color: CAST[step.cast].ink }}>
              {shown.text}
            </div>
          ) : null}

          <div className="mt-6 rounded-3xl border-2 border-borderSoft bg-panel p-5 shadow-console md:p-6">{step.body(ctx)}</div>

          <div className="mt-6 flex items-center justify-between gap-3">
            <button type="button" className="btn-secondary" onClick={() => go(index - 1)} disabled={index === 0}>
              <ArrowLeft aria-hidden="true" className="h-4 w-4" /> Quay lại
            </button>
            <button type="button" className="btn-primary" onClick={advance}>
              {fromSummary ? "Xong, về phần xem lại" : "Tiếp theo"} <ArrowRight aria-hidden="true" className="h-4 w-4" />
            </button>
          </div>
        </section>
      ) : (
        <section key="summary" className="step-in">
          <Say id="tiep" mood={isPending ? "think" : "happy"} size={96} text="Xong rồi! Bạn xem lại hồ sơ nhé. Cả đội sẵn sàng xem giúp bạn." />
          <ul className="mt-6 divide-y divide-borderSoft rounded-3xl border-2 border-borderSoft bg-panel px-5 shadow-console">
            {STEPS.map((s, i) => (
              <li key={s.id} className="flex items-center gap-3 py-3">
                <Avatar id={s.cast} size={32} />
                <div className="min-w-0 flex-1">
                  <div className="text-sm text-muted">{s.label}</div>
                  <div className="truncate text-base font-semibold">{s.summary(form)}</div>
                </div>
                <button
                  type="button"
                  className="inline-flex min-h-10 items-center gap-1 rounded-lg px-3 text-sm font-semibold text-info hover:bg-infoSoft"
                  aria-label={`Sửa: ${s.label}`}
                  onClick={() => { setFromSummary(true); go(i); }}
                >
                  <Pencil aria-hidden="true" className="h-3.5 w-3.5" /> Sửa
                </button>
              </li>
            ))}
          </ul>

          {error ? (
            <div role="alert" className="mt-5 rounded-xl border border-danger/40 bg-danger/10 p-4 text-sm text-danger">{error.message}</div>
          ) : null}

          <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
            <button type="button" className="btn-secondary" onClick={() => { setFromSummary(false); go(STEPS.length - 1); }}>
              <ArrowLeft aria-hidden="true" className="h-4 w-4" /> Quay lại
            </button>
            <div className="flex flex-wrap items-center gap-3">
              {hasResult ? <button type="button" className="btn-secondary" onClick={onCancel}>Xem lại kết quả</button> : null}
              <button type="button" className="btn-primary" onClick={onSubmit} disabled={isPending}>
                {isPending ? <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" /> : <Sparkles aria-hidden="true" className="h-4 w-4" />}
                Phân tích hồ sơ
              </button>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
