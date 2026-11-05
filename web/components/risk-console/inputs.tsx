import clsx from "clsx";
import { Minus, Plus } from "lucide-react";
import type { ReactNode } from "react";

export function Stepper({ label, unit, value, min, max, step, onChange }: { label: string; unit: string; value: number; min: number; max: number; step: number; onChange: (v: number) => void }) {
  const clamp = (v: number) => Math.min(max, Math.max(min, Math.round(v * 10) / 10));
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between">
        <span className="field-label">{label}</span>
        <span className="text-sm text-muted">{unit}</span>
      </div>
      <div className="flex h-16 items-stretch overflow-hidden rounded-2xl border-2 border-borderSoft bg-panel focus-within:border-info focus-within:ring-2 focus-within:ring-info/25">
        <button type="button" aria-label={`Giảm ${label}`} onClick={() => onChange(clamp(value - step))} className="choice w-16 text-muted hover:bg-panelMuted hover:text-ink">
          <Minus aria-hidden="true" className="mx-auto h-5 w-5" />
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
          className="min-w-0 flex-1 bg-transparent text-center text-3xl font-bold tabular-nums outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none"
        />
        <button type="button" aria-label={`Tăng ${label}`} onClick={() => onChange(clamp(value + step))} className="choice w-16 text-muted hover:bg-panelMuted hover:text-ink">
          <Plus aria-hidden="true" className="mx-auto h-5 w-5" />
        </button>
      </div>
    </div>
  );
}

/** Nút lựa chọn to, dễ bấm; dùng cho câu hỏi một chạm. */
export function Choice({ active, onClick, children, tone }: { active: boolean; onClick: () => void; children: ReactNode; tone?: "good" | "bad" | "neutral" }) {
  const activeStyle =
    tone === "good" ? "border-success bg-success/10 text-success" : tone === "bad" ? "border-danger bg-danger/10 text-danger" : "border-info bg-infoSoft text-info";
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={clsx(
        "choice min-h-16 rounded-2xl border-2 px-4 text-lg font-bold",
        active ? activeStyle : "border-borderSoft bg-panel text-ink hover:border-info/50",
      )}
    >
      {children}
    </button>
  );
}

export function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={clsx(
        "choice min-h-11 rounded-full border-2 px-4 text-base font-semibold",
        active ? "border-info bg-infoSoft text-ink" : "border-borderSoft bg-panel text-muted hover:border-info/50",
      )}
    >
      {children}
    </button>
  );
}
