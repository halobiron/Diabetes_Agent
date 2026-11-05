import { useEffect, useState } from "react";

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
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <span className="field-label">{label}</span>
        {suffix ? <span className="text-sm text-muted">{suffix}</span> : null}
      </div>
      <input
        className="field-input tabular-nums"
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
    <div className="rounded-lg border border-borderSoft bg-panel p-4">
      <label className="flex items-center justify-between gap-3 text-base text-ink">
        <span className="font-semibold">Tôi có kết quả đường huyết</span>
        <input
          type="checkbox"
          checked={hasGlucose}
          onChange={(event) => {
            setHasGlucose(event.target.checked);
            onChange(null);
          }}
          className="h-5 w-5 accent-info"
        />
      </label>
      <label className="mt-4 block">
        <div className="mb-1.5 flex items-center justify-between gap-2">
          <span className="field-label">Đường huyết</span>
          <span className="text-sm text-muted">mg/dL</span>
        </div>
        <input
          className="field-input tabular-nums"
          type="number"
          min={0}
          max={500}
          value={value ?? ""}
          placeholder={hasGlucose ? "Nhập số đo" : "Chưa có số đo"}
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
      <span className="field-label mb-1.5 block">{label}</span>
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
  valueLabel,
  lowLabel,
  highLabel,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  valueLabel?: string;
  lowLabel?: string;
  highLabel?: string;
}) {
  const fillPercent = max > min ? ((value - min) / (max - min)) * 100 : 0;

  return (
    <label className="block rounded-lg border border-borderSoft bg-panel p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <span className="field-label">{label}</span>
        <span className="rounded-md bg-infoSoft px-2 py-0.5 text-sm font-semibold tabular-nums text-info">{valueLabel ?? value}</span>
      </div>
      <input
        className="range-input w-full"
        type="range"
        min={min}
        max={max}
        value={value}
        style={{
          background: `linear-gradient(to right, #4b3fa8 0%, #4b3fa8 ${fillPercent}%, rgba(40,30,110,0.16) ${fillPercent}%, rgba(40,30,110,0.16) 100%)`,
        }}
        onChange={(event) => onChange(Number(event.target.value))}
      />
      <div className="mt-2 flex justify-between text-xs text-muted">
        <span>{lowLabel ?? min}</span>
        <span>{highLabel ?? max}</span>
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
    <label className="toggle-row cursor-pointer justify-between">
      <span>{label}</span>
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="h-5 w-5 accent-info"
      />
    </label>
  );
}

const TRI_OPTIONS = [
  { label: "Chưa rõ", value: null },
  { label: "Không", value: false },
  { label: "Có", value: true },
] as const;

/** Yes / no / unknown: "Chưa rõ" sends nothing, so the agent may ask about it later. */
export function TriToggle({
  label,
  value,
  onChange,
}: {
  label: string;
  value: boolean | null;
  onChange: (value: boolean | null) => void;
}) {
  return (
    <fieldset className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
      <legend className="sr-only">{label}</legend>
      <span aria-hidden="true" className="text-base">{label}</span>
      <div className="grid w-full grid-cols-3 gap-1 rounded-lg bg-panelMuted p-1 text-sm sm:w-56 sm:shrink-0">
        {TRI_OPTIONS.map((option) => {
          const active = value === option.value;
          const tone = option.value === true ? "text-danger" : option.value === false ? "text-success" : "text-ink";
          return (
            <button
              key={option.label}
              type="button"
              aria-pressed={active}
              onClick={() => onChange(option.value)}
              className={`min-h-9 whitespace-nowrap rounded-md px-1 transition ${active ? `bg-panel font-semibold shadow-console ${tone}` : "text-muted hover:text-ink"}`}
            >
              {option.label}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}
