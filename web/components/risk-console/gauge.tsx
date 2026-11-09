"use client";

import { useEffect, useState } from "react";

import { RISK_COLORS } from "@/lib/labels";

const CX = 100;
const CY = 100;
const R = 80;

function point(percent: number) {
  const angle = (Math.PI * percent) / 100;
  return { x: CX - R * Math.cos(angle), y: CY - R * Math.sin(angle) };
}

function arc(from: number, to: number) {
  const a = point(from);
  const b = point(to);
  return `M ${a.x.toFixed(2)} ${a.y.toFixed(2)} A ${R} ${R} 0 0 1 ${b.x.toFixed(2)} ${b.y.toFixed(2)}`;
}

function prefersReducedMotion() {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** Đếm từ 0 lên `target` trong ~0,9 giây; tôn trọng prefers-reduced-motion. */
export function useCountUp(target: number, ms = 900) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (prefersReducedMotion()) {
      setValue(target);
      return;
    }
    let frame = 0;
    const started = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - started) / ms);
      setValue(target * (1 - Math.pow(1 - t, 3)));
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, ms]);
  return value;
}

/** Đồng hồ nửa vòng: ba vùng nguy cơ, kim quay tới vị trí xác suất, số đếm lên. */
export function RiskGauge({ probability, lowMax, highMin, label, color }: { probability: number; lowMax: number; highMin: number; label: string; color: string }) {
  const percent = Math.min(100, Math.max(0, probability));
  const [armed, setArmed] = useState(false);
  useEffect(() => {
    const frame = requestAnimationFrame(() => setArmed(true));
    return () => cancelAnimationFrame(frame);
  }, []);
  const shown = useCountUp(percent);
  const angle = armed ? -90 + 1.8 * percent : -90;
  const gap = 0.8;

  return (
    <div
      className="mx-auto w-full max-w-[15rem]"
      role="img"
      aria-label={`Xác suất mô hình ${percent.toFixed(1)}%. Thấp: dưới ${lowMax}%; Trung bình: từ ${lowMax}% đến dưới ${highMin}%; Cao: từ ${highMin}%.`}
    >
      <svg viewBox="0 0 200 112" className="w-full overflow-visible" aria-hidden="true">
        <path d={arc(0, 100)} fill="none" stroke="rgba(40,30,110,0.08)" strokeWidth="18" strokeLinecap="round" />
        <path d={arc(gap, lowMax - gap)} fill="none" stroke={RISK_COLORS.Low} strokeWidth="14" />
        <path d={arc(lowMax + gap, highMin - gap)} fill="none" stroke={RISK_COLORS.Medium} strokeWidth="14" />
        <path d={arc(highMin + gap, 100 - gap)} fill="none" stroke={RISK_COLORS.High} strokeWidth="14" />
        <g
          style={{
            transformOrigin: `${CX}px ${CY}px`,
            transformBox: "view-box",
            transform: `rotate(${angle}deg)`,
            transition: "transform 1.1s cubic-bezier(0.34, 1.4, 0.64, 1)",
          }}
        >
          <path d={`M ${CX - 3.5} ${CY} L ${CX} ${CY - 70} L ${CX + 3.5} ${CY} Z`} fill="#1c1a3a" />
        </g>
        <circle cx={CX} cy={CY} r="8" fill="#1c1a3a" />
        <circle cx={CX} cy={CY} r="3" fill="#fff" />
      </svg>
      <div className="mt-2 flex items-center justify-center gap-3">
        <span className="text-4xl font-extrabold tabular-nums leading-none text-ink">{Math.round(shown)}%</span>
        <span className="border-l border-borderSoft pl-3 leading-tight">
          <span className="block text-lg font-bold" style={{ color }}>Mức {label}</span>
          <span className="block text-xs text-muted">theo mô hình</span>
        </span>
      </div>
    </div>
  );
}
