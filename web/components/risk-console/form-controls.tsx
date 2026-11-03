import { ChevronDown } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";

export function InputSection({
  title,
  icon,
  children,
  defaultOpen = true,
}: {
  title: string;
  icon: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  return (
    <details open={defaultOpen} className="group mb-4 rounded-lg border border-borderSoft bg-panel p-4">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-sm font-semibold text-ink [&::-webkit-details-marker]:hidden">
        <span className="flex items-center gap-2">
          <span className="text-info">{icon}</span>
          {title}
        </span>
        <ChevronDown className="h-4 w-4 text-muted transition group-open:rotate-180" />
      </summary>
      <div className="mt-4 space-y-3">{children}</div>
    </details>
  );
}

export function NumberField({
  label,
  value,
  onChange,
  min,
  max,
  step = 1,
  suffix,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  step?: number;
  suffix?: string;
}) {
  return (
    <label className="block">
      <div className="mb-1 flex items-center justify-between gap-2">
        <span className="field-label">{label}</span>
        {suffix ? <span className="text-xs text-muted">{suffix}</span> : null}
      </div>
      <input
        className="field-input"
        type="number"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}

export function GlucoseField({
  value,
  onChange,
}: {
  value: number | null;
  onChange: (value: number | null) => void;
}) {
  const [hasGlucose, setHasGlucose] = useState(value !== null);
  useEffect(() => {
    if (value !== null) setHasGlucose(true);
  }, [value]);

  return (
    <div className="rounded-md border border-borderSoft bg-canvas/50 p-3">
      <label className="flex items-center justify-between gap-3 text-sm text-ink">
        <span className="font-semibold">Có kết quả đường huyết</span>
        <input
          type="checkbox"
          checked={hasGlucose}
          onChange={(event) => {
            setHasGlucose(event.target.checked);
            onChange(null);
          }}
          className="h-4 w-4 accent-info"
        />
      </label>
      <label className="mt-3 block">
        <div className="mb-1 flex items-center justify-between gap-2">
          <span className="field-label">Đường huyết</span>
          <span className="text-xs text-muted">mg/dL</span>
        </div>
        <input
          className="field-input disabled:cursor-not-allowed disabled:opacity-50"
          type="number"
          min={0}
          max={500}
          value={value ?? ""}
          placeholder="Chưa có số đo"
          disabled={!hasGlucose}
          onChange={(event) => onChange(event.target.value === "" ? null : Number(event.target.value))}
        />
      </label>
    </div>
  );
}

export function SelectField({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: Array<{ value: string; label: string }>;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="field-label mb-1 block">{label}</span>
      <select className="field-input" value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export function SliderField({
  label,
  value,
  onChange,
  min,
  max,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
}) {
  const fillPercent = max > min ? ((value - min) / (max - min)) * 100 : 0;

  return (
    <label className="block rounded-md border border-borderSoft bg-canvas/50 p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="field-label">{label}</span>
        <span className="text-sm font-semibold text-info">{value}</span>
      </div>
      <input
        className="range-input w-full"
        type="range"
        min={min}
        max={max}
        value={value}
        style={{
          background: `linear-gradient(to right, #5aa3d9 0%, #5aa3d9 ${fillPercent}%, rgba(255,255,255,0.14) ${fillPercent}%, rgba(255,255,255,0.14) 100%)`,
        }}
        onChange={(event) => onChange(Number(event.target.value))}
      />
      <div className="mt-1 flex justify-between text-[11px] text-muted">
        <span>{min}</span>
        <span>{max}</span>
      </div>
    </label>
  );
}

export function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="toggle-row">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="h-4 w-4 accent-info"
      />
      <span>{label}</span>
    </label>
  );
}

export function ToggleGrid({ children }: { children: ReactNode }) {
  return <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">{children}</div>;
}
