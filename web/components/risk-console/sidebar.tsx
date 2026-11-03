import {
  Activity,
  ClipboardList,
  HeartPulse,
  Loader2,
  Sparkles,
  Stethoscope,
} from "lucide-react";

import type { PatientInput } from "@/types/healthcare";

import type { PatientFieldChange } from "./types";
import {
  GlucoseField,
  InputSection,
  NumberField,
  SelectField,
  SliderField,
  Toggle,
  TriToggle,
  ToggleGrid,
} from "./form-controls";
import { MiniStat, Pill } from "./shared-ui";

export function PatientSidebar({
  form,
  calculatedBmi,
  isPending,
  error,
  onSubmit,
  onFieldChange,
}: {
  form: PatientInput;
  calculatedBmi: number;
  isPending: boolean;
  error: Error | null;
  onSubmit: () => void;
  onFieldChange: PatientFieldChange;
}) {
  return (
    <aside className="border-b border-borderSoft bg-panelMuted/80 px-5 py-6 xl:h-screen xl:overflow-y-auto xl:border-b-0 xl:border-r">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold text-info">
            <Stethoscope className="h-4 w-4" />
            Thông tin bệnh nhân
          </div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight">Đánh giá nguy cơ sức khỏe bằng AI</h1>
        </div>
        <Pill tone="neutral">Cục bộ</Pill>
      </div>

      <InputSection title="Chỉ số cơ thể" icon={<HeartPulse className="h-4 w-4" />}>
        <NumberField
          label="Tuổi"
          min={0}
          max={120}
          value={form.age}
          onChange={(value) => onFieldChange("age", value)}
        />
        <SelectField
          label="Giới tính"
          value={form.sex}
          options={[
            { value: "female", label: "Nữ" },
            { value: "male", label: "Nam" },
          ]}
          onChange={(value) => onFieldChange("sex", value as PatientInput["sex"])}
        />
        <div className="grid grid-cols-2 gap-3">
          <NumberField
            label="Chiều cao"
            suffix="cm"
            min={50}
            max={250}
            step={0.5}
            value={form.height_cm}
            onChange={(value) => onFieldChange("height_cm", value)}
          />
          <NumberField
            label="Cân nặng"
            suffix="kg"
            min={2}
            max={300}
            step={0.1}
            value={form.weight_kg}
            onChange={(value) => onFieldChange("weight_kg", value)}
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <NumberField
            label="Huyết áp tâm thu"
            min={0}
            max={260}
            value={form.bp}
            onChange={(value) => onFieldChange("bp", value)}
          />
          <GlucoseField value={form.glucose} onChange={(value) => {
            onFieldChange("glucose", value);
            onFieldChange("glucose_unavailable", false);
            if (value === null) onFieldChange("glucose_context", "unspecified");
          }} />
        </div>
        {form.glucose !== null ? (
          <SelectField
            label="Bối cảnh đo đường huyết"
            value={form.glucose_context ?? "unspecified"}
            options={[
              { value: "unspecified", label: "Chưa chọn bối cảnh đo" },
              { value: "fasting", label: "Lúc đói (nhịn ăn ít nhất 8 giờ)" },
              { value: "random", label: "Ngẫu nhiên" },
              { value: "after_meal", label: "Sau ăn thông thường" },
              { value: "unknown", label: "Không nhớ / không rõ" },
            ]}
            onChange={(value) => onFieldChange("glucose_context", value as PatientInput["glucose_context"])}
          />
        ) : null}
        {form.glucose !== null && (form.glucose_context ?? "unspecified") === "unspecified" ? (
          <p className="-mt-2 text-xs leading-5 text-muted">Chọn bối cảnh để hiện thang tham khảo phù hợp; nếu không nhớ, chọn &quot;Không nhớ / không rõ&quot; và thang sẽ giữ trung tính.</p>
        ) : null}
        <MiniStat label="BMI tính từ chiều cao và cân nặng" value={calculatedBmi.toFixed(1)} />
      </InputSection>

      <InputSection title="Tiền sử và sức khỏe" icon={<ClipboardList className="h-4 w-4" />} defaultOpen={false}>
        <ToggleGrid>
          <TriToggle
            label="Cholesterol cao"
            value={form.high_chol}
            onChange={(value) => onFieldChange("high_chol", value)}
          />
          <Toggle
            label="Đã kiểm tra cholesterol"
            checked={form.chol_check}
            onChange={(value) => onFieldChange("chol_check", value)}
          />
          <TriToggle label="Hút thuốc" value={form.smoker} onChange={(value) => onFieldChange("smoker", value)} />
          <TriToggle
            label="Tiền sử đột quỵ"
            value={form.stroke}
            onChange={(value) => onFieldChange("stroke", value)}
          />
          <TriToggle
            label="Tiền sử bệnh tim"
            value={form.heart_disease_or_attack}
            onChange={(value) => onFieldChange("heart_disease_or_attack", value)}
          />
          <TriToggle
            label="Khó khăn khi đi lại"
            value={form.diff_walk}
            onChange={(value) => onFieldChange("diff_walk", value)}
          />
        </ToggleGrid>
        <SliderField
          label="Sức khỏe tổng quát"
          min={1}
          max={5}
          value={form.general_health}
          onChange={(value) => onFieldChange("general_health", value)}
        />
        <SliderField
          label="Số ngày tinh thần kém"
          min={0}
          max={30}
          value={form.mental_health_days}
          onChange={(value) => onFieldChange("mental_health_days", value)}
        />
        <SliderField
          label="Số ngày thể chất kém"
          min={0}
          max={30}
          value={form.physical_health_days}
          onChange={(value) => onFieldChange("physical_health_days", value)}
        />
      </InputSection>

      <InputSection title="Lối sống và tiếp cận y tế" icon={<Activity className="h-4 w-4" />} defaultOpen={false}>
        <ToggleGrid>
          <TriToggle
            label="Vận động thể chất"
            value={form.phys_activity}
            onChange={(value) => onFieldChange("phys_activity", value)}
          />
          <TriToggle
            label="Ăn trái cây"
            value={form.fruits}
            onChange={(value) => onFieldChange("fruits", value)}
          />
          <TriToggle
            label="Ăn rau"
            value={form.veggies}
            onChange={(value) => onFieldChange("veggies", value)}
          />
          <TriToggle
            label="Uống nhiều rượu bia"
            value={form.heavy_alcohol_consump}
            onChange={(value) => onFieldChange("heavy_alcohol_consump", value)}
          />
          <Toggle
            label="Tiếp cận dịch vụ y tế"
            checked={form.any_healthcare}
            onChange={(value) => onFieldChange("any_healthcare", value)}
          />
          <Toggle
            label="Rào cản chi phí"
            checked={form.no_doc_bc_cost}
            onChange={(value) => onFieldChange("no_doc_bc_cost", value)}
          />
        </ToggleGrid>
        <SliderField
          label="Trình độ học vấn"
          min={1}
          max={6}
          value={form.education}
          onChange={(value) => onFieldChange("education", value)}
        />
        <SliderField
          label="Mức thu nhập"
          min={1}
          max={8}
          value={form.income}
          onChange={(value) => onFieldChange("income", value)}
        />
      </InputSection>

      <button
        type="button"
        onClick={onSubmit}
        disabled={isPending}
        className="mt-4 flex h-12 w-full items-center justify-center gap-2 rounded-md bg-info px-4 text-sm font-bold text-canvas transition hover:bg-[#7bbce9] disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
        Phân tích hồ sơ
      </button>

      {error ? (
        <div className="mt-4 rounded-md border border-danger/40 bg-danger/10 p-3 text-sm text-[#ffb4ad]">
          {error.message}
        </div>
      ) : null}
    </aside>
  );
}
