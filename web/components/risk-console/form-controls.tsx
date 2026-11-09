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
