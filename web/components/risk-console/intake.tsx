import { Activity, Droplet, HeartPulse, Loader2, Minus, Plus, Ruler, Salad, Sparkles, Stethoscope } from "lucide-react";
import type { ReactNode } from "react";
import clsx from "clsx";

import type { PatientInput } from "@/types/healthcare";

import type { PatientFieldChange } from "./types";
import { SliderField, Toggle, TriToggle } from "./form-controls";

type Props = {
  form: PatientInput;
  calculatedBmi: number;
  isPending: boolean;
  error: Error | null;
  hasResult: boolean;
  onSubmit: () => void;
  onFieldChange: PatientFieldChange;
  onCancel: () => void;
};

const GLUCOSE_CONTEXT: Array<{ label: string; value: NonNullable<PatientInput["glucose_context"]> }> = [
  { label: "Lúc đói", value: "fasting" },
  { label: "Sau ăn", value: "after_meal" },
  { label: "Bất kỳ", value: "random" },
  { label: "Không nhớ", value: "unknown" },
];

const GENERAL_HEALTH = ["Rất tốt", "Tốt", "Khá", "Trung bình", "Kém"];

function bmiTone(bmi: number) {
  if (bmi < 18.5) return { label: "Thấp cân", color: "#9a5b07" };
  if (bmi < 23) return { label: "Bình thường", color: "#1b7a4b" };
  if (bmi < 25) return { label: "Thừa cân nhẹ", color: "#9a5b07" };
  return { label: "Thừa cân", color: "#b0372b" };
}

export function Intake({ form, calculatedBmi, isPending, error, hasResult, onSubmit, onFieldChange, onCancel }: Props) {
  const bmi = bmiTone(calculatedBmi);
  const glucoseState = form.glucose !== null ? "yes" : form.glucose_unavailable ? "no" : "unset";
  const glucoseNeedsContext = form.glucose !== null && (form.glucose_context ?? "unspecified") === "unspecified";

  return (
    <div className="mx-auto w-full max-w-6xl px-5 pb-32 pt-8">
      <div className="rise max-w-2xl">
        <h1 className="text-balance text-3xl font-bold tracking-tight md:text-4xl">Hồ sơ sức khỏe của bạn</h1>
        <p className="mt-3 text-base leading-7 text-muted">
          Điền một lần, bấm một nút. Mục nào chưa biết cứ để &quot;Chưa rõ&quot;, bạn vẫn nhận được kết quả.
        </p>
      </div>

      <div className="rise mt-8 grid gap-5 lg:grid-cols-12">
        {/* Số đo: khối chính, nhập nhanh bằng bước tăng giảm */}
        <Card className="lg:col-span-7" icon={<Ruler className="h-5 w-5" />} title="Số đo cơ thể">
          <div className="grid gap-5 sm:grid-cols-2">
            <Stepper label="Tuổi" unit="tuổi" value={form.age} min={0} max={120} step={1} onChange={(v) => onFieldChange("age", v)} />
            <div>
              <div className="field-label mb-1.5">Giới tính</div>
              <Segmented
                value={form.sex}
                options={[{ label: "Nữ", value: "female" }, { label: "Nam", value: "male" }]}
                onChange={(v) => onFieldChange("sex", v as PatientInput["sex"])}
              />
            </div>
            <Stepper label="Chiều cao" unit="cm" value={form.height_cm} min={50} max={250} step={1} onChange={(v) => onFieldChange("height_cm", v)} />
            <Stepper label="Cân nặng" unit="kg" value={form.weight_kg} min={2} max={300} step={0.5} onChange={(v) => onFieldChange("weight_kg", v)} />
          </div>
          <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-xl bg-canvas px-4 py-3">
            <span className="text-sm text-muted">Chỉ số BMI tự tính</span>
            <span className="flex items-baseline gap-2">
              <strong className="text-2xl tabular-nums">{calculatedBmi.toFixed(1)}</strong>
              <span className="text-sm font-semibold" style={{ color: bmi.color }}>{bmi.label}</span>
            </span>
          </div>
          <div className="mt-5">
            <Stepper label="Huyết áp tâm thu" unit="mmHg" value={form.bp} min={0} max={260} step={5} onChange={(v) => onFieldChange("bp", v)} />
          </div>
        </Card>

        {/* Đường huyết: tùy chọn, mở rộng khi cần */}
        <Card className="lg:col-span-5" icon={<Droplet className="h-5 w-5" />} title="Đường huyết" note="Không bắt buộc">
          <Segmented
            value={glucoseState}
            options={[{ label: "Có kết quả", value: "yes" }, { label: "Chưa có", value: "no" }]}
            onChange={(v) => {
              if (v === "yes") {
                onFieldChange("glucose_unavailable", false);
                if (form.glucose === null) onFieldChange("glucose", 100);
              } else {
                onFieldChange("glucose", null);
                onFieldChange("glucose_unavailable", true);
                onFieldChange("glucose_context", "unspecified");
              }
            }}
          />
          {form.glucose !== null ? (
            <div className="mt-5 space-y-5">
              <Stepper label="Kết quả" unit="mg/dL" value={form.glucose} min={0} max={500} step={5} onChange={(v) => onFieldChange("glucose", v)} />
              <div>
                <div className="field-label mb-2">Đo trong hoàn cảnh nào?</div>
                <div className="flex flex-wrap gap-2">
                  {GLUCOSE_CONTEXT.map((item) => (
                    <Chip key={item.value} active={form.glucose_context === item.value} onClick={() => onFieldChange("glucose_context", item.value)}>
                      {item.label}
                    </Chip>
                  ))}
                </div>
                {glucoseNeedsContext ? <p className="mt-2 text-sm text-muted">Chọn hoàn cảnh đo để thang tham khảo chính xác hơn (có thể bỏ qua).</p> : null}
              </div>
            </div>
          ) : (
            <p className="mt-5 text-sm leading-6 text-muted">
              {glucoseState === "no"
                ? "Đã ghi nhận. Kết quả vẫn có, nhưng độ tin cậy sẽ thấp hơn."
                : "Có kết quả xét nghiệm gần đây sẽ giúp đánh giá chính xác hơn."}
            </p>
          )}
        </Card>

        <Card className="lg:col-span-6" icon={<HeartPulse className="h-5 w-5" />} title="Tiền sử bệnh">
          <div className="divide-y divide-borderSoft">
            <TriToggle label="Cholesterol cao" value={form.high_chol} onChange={(v) => { onFieldChange("high_chol", v); if (v !== null) onFieldChange("chol_check", true); }} />
            <TriToggle label="Từng bị đột quỵ" value={form.stroke} onChange={(v) => onFieldChange("stroke", v)} />
            <TriToggle label="Bệnh tim / nhồi máu" value={form.heart_disease_or_attack} onChange={(v) => onFieldChange("heart_disease_or_attack", v)} />
            <TriToggle label="Khó đi lại, leo cầu thang" value={form.diff_walk} onChange={(v) => onFieldChange("diff_walk", v)} />
          </div>
        </Card>

        <Card className="lg:col-span-6" icon={<Salad className="h-5 w-5" />} title="Thói quen hằng ngày">
          <div className="divide-y divide-borderSoft">
            <TriToggle label="Hút thuốc" value={form.smoker} onChange={(v) => onFieldChange("smoker", v)} />
            <TriToggle label="Uống nhiều rượu bia" value={form.heavy_alcohol_consump} onChange={(v) => onFieldChange("heavy_alcohol_consump", v)} />
            <TriToggle label="Vận động thể chất" value={form.phys_activity} onChange={(v) => onFieldChange("phys_activity", v)} />
            <TriToggle label="Ăn trái cây" value={form.fruits} onChange={(v) => onFieldChange("fruits", v)} />
            <TriToggle label="Ăn rau" value={form.veggies} onChange={(v) => onFieldChange("veggies", v)} />
          </div>
        </Card>

        <Card className="lg:col-span-12" icon={<Activity className="h-5 w-5" />} title="Cảm nhận chung">
          <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr_1fr]">
            <div>
              <div className="field-label mb-2">Bạn thấy sức khỏe mình thế nào?</div>
              <div className="grid grid-cols-5 gap-2">
                {GENERAL_HEALTH.map((label, i) => (
                  <button
                    key={label}
                    type="button"
                    aria-pressed={form.general_health === i + 1}
                    onClick={() => onFieldChange("general_health", i + 1)}
                    className={clsx(
                      "flex min-h-14 flex-col items-center justify-center rounded-xl border-2 px-1 text-center text-xs font-semibold transition sm:text-sm",
                      form.general_health === i + 1 ? "border-info bg-infoSoft" : "border-borderSoft bg-panel text-muted hover:border-info/50",
                    )}
                  >
                    <span className="text-lg font-bold tabular-nums text-ink">{i + 1}</span>
                    {label}
                  </button>
                ))}
              </div>
            </div>
            <SliderField label="Ngày tinh thần kém" min={0} max={30} value={form.mental_health_days} valueLabel={`${form.mental_health_days}/30 ngày`} onChange={(v) => onFieldChange("mental_health_days", v)} />
            <SliderField label="Ngày thể chất kém" min={0} max={30} value={form.physical_health_days} valueLabel={`${form.physical_health_days}/30 ngày`} onChange={(v) => onFieldChange("physical_health_days", v)} />
          </div>
          <details className="group mt-6 rounded-xl border border-borderSoft">
            <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-3 text-base font-semibold [&::-webkit-details-marker]:hidden">
              Hoàn cảnh xã hội và tiếp cận y tế
              <Plus aria-hidden="true" className="h-4 w-4 text-muted group-open:hidden" />
              <Minus aria-hidden="true" className="hidden h-4 w-4 text-muted group-open:block" />
            </summary>
            <div className="grid gap-4 border-t border-borderSoft p-4 md:grid-cols-2">
              <Toggle label="Dễ đến được cơ sở y tế" checked={form.any_healthcare} onChange={(v) => onFieldChange("any_healthcare", v)} />
              <Toggle label="Từng ngại đi khám vì chi phí" checked={form.no_doc_bc_cost} onChange={(v) => onFieldChange("no_doc_bc_cost", v)} />
              <SliderField label="Trình độ học vấn" min={1} max={6} value={form.education} valueLabel={`Mức ${form.education}/6`} lowLabel="Thấp" highLabel="Cao" onChange={(v) => onFieldChange("education", v)} />
              <SliderField label="Mức thu nhập" min={1} max={8} value={form.income} valueLabel={`Mức ${form.income}/8`} lowLabel="Thấp" highLabel="Cao" onChange={(v) => onFieldChange("income", v)} />
            </div>
          </details>
        </Card>
      </div>

      {error ? (
        <div role="alert" className="mt-5 rounded-xl border border-danger/40 bg-danger/10 p-4 text-sm text-danger">{error.message}</div>
      ) : null}

      <div className="fixed inset-x-0 bottom-0 z-10 border-t border-borderSoft bg-panel/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-3">
          <p className="hidden items-center gap-2 text-sm text-muted sm:flex">
            <Stethoscope aria-hidden="true" className="h-4 w-4" /> Dữ liệu chỉ dùng để tính kết quả cho hồ sơ này.
          </p>
          <div className="flex w-full items-center justify-end gap-3 sm:w-auto">
            {hasResult ? <button type="button" className="btn-secondary" onClick={onCancel}>Xem lại kết quả</button> : null}
            <button type="button" className="btn-primary" onClick={onSubmit} disabled={isPending}>
              {isPending ? <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" /> : <Sparkles aria-hidden="true" className="h-4 w-4" />}
              Phân tích hồ sơ
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Card({ title, icon, note, className, children }: { title: string; icon: ReactNode; note?: string; className?: string; children: ReactNode }) {
  return (
    <section className={clsx("console-panel rounded-2xl p-5 md:p-6", className)}>
      <h2 className="mb-5 flex items-center gap-2 text-lg font-bold">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-infoSoft text-info">{icon}</span>
        {title}
        {note ? <span className="ml-auto text-sm font-normal text-muted">{note}</span> : null}
      </h2>
      {children}
    </section>
  );
}

function Segmented({ value, options, onChange }: { value: string; options: Array<{ label: string; value: string }>; onChange: (v: string) => void }) {
  return (
    <div role="group" className="flex rounded-xl bg-panelMuted p-1">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          aria-pressed={value === o.value}
          onClick={() => onChange(o.value)}
          className={clsx(
            "min-h-10 flex-1 rounded-lg px-3 text-base font-semibold transition",
            value === o.value ? "bg-panel text-info shadow-console" : "text-muted hover:text-ink",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={clsx(
        "min-h-10 rounded-full border-2 px-4 text-sm font-semibold transition",
        active ? "border-info bg-infoSoft text-ink" : "border-borderSoft bg-panel text-muted hover:border-info/50",
      )}
    >
      {children}
    </button>
  );
}

function Stepper({ label, unit, value, min, max, step, onChange }: { label: string; unit: string; value: number; min: number; max: number; step: number; onChange: (v: number) => void }) {
  const clamp = (v: number) => Math.min(max, Math.max(min, Math.round(v * 10) / 10));
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between">
        <span className="field-label">{label}</span>
        <span className="text-sm text-muted">{unit}</span>
      </div>
      <div className="flex h-12 items-stretch overflow-hidden rounded-xl border border-borderSoft bg-panel focus-within:border-info focus-within:ring-2 focus-within:ring-info/25">
        <button type="button" aria-label={`Giảm ${label}`} onClick={() => onChange(clamp(value - step))} className="w-12 text-muted transition hover:bg-panelMuted hover:text-ink">
          <Minus aria-hidden="true" className="mx-auto h-4 w-4" />
        </button>
        <input
          aria-label={label}
          type="number"
          inputMode="decimal"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="min-w-0 flex-1 bg-transparent text-center text-lg font-semibold tabular-nums outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none"
        />
        <button type="button" aria-label={`Tăng ${label}`} onClick={() => onChange(clamp(value + step))} className="w-12 text-muted transition hover:bg-panelMuted hover:text-ink">
          <Plus aria-hidden="true" className="mx-auto h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
