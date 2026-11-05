import { AlertTriangle, Check, ShieldCheck } from "lucide-react";

import { ESCALATION_COLORS, ESCALATION_LABELS, RISK_COLORS, RISK_LABELS } from "@/lib/labels";
import type { PredictionResult } from "@/types/healthcare";

import { Avatar, Seal, type Mood } from "./agents";

export function Hero({ result }: { result: PredictionResult }) {
  const color = RISK_COLORS[result.risk];
  const probability = result.probability * 100;
  const lowMax = (result.model?.risk_bands?.low_max ?? 0.4) * 100;
  const highMin = (result.model?.risk_bands?.high_min ?? 0.7) * 100;
  const formatCutoff = (value: number) => value.toLocaleString("vi-VN", { maximumFractionDigits: 2 });
  const bands = [
    { risk: "Low", label: "Thấp", range: `Dưới ${formatCutoff(lowMax)}%` },
    { risk: "Medium", label: "Trung bình", range: `${formatCutoff(lowMax)}–<${formatCutoff(highMin)}%` },
    { risk: "High", label: "Cao", range: `Từ ${formatCutoff(highMin)}%` },
  ] as const;
  const escalation = result.safety.escalation;
  const riskLabel = RISK_LABELS[result.risk] ?? result.risk;
  const raised = Boolean(result.trace?.disagreement);
  const hasAlerts = result.safety.alerts.length > 0;
  const mood: Mood = raised || hasAlerts ? "think" : result.risk === "High" ? "worried" : result.risk === "Low" ? "happy" : "think";
  const line = "Đây là ước tính thống kê từ dữ liệu khảo sát, chưa phải chẩn đoán. Mời bạn xem giải thích và khuyến nghị bên dưới.";

  return (
    <header className="rise paper relative overflow-hidden rounded-2xl border-2 border-borderSoft p-6 shadow-console md:p-10">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-x-6 gap-y-5">
        <h1 className="text-base font-semibold text-ink sm:text-lg">Nguy cơ tiểu đường của bạn</h1>
        <div className="ml-auto flex flex-wrap justify-end gap-x-4 gap-y-3 py-1">
          <span className="stamp-in inline-block" style={{ ["--tilt" as string]: "0deg", ["--delay" as string]: "0.3s" }}>
            <Seal id="mo" tilt={-3}>Ông Mô đã chấm</Seal>
          </span>
          {raised ? (
            <span className="stamp-in inline-block" style={{ ["--tilt" as string]: "0deg", ["--delay" as string]: "0.7s" }}>
              <Seal id="luat" tilt={-3}>Chú Luật nâng mức</Seal>
            </span>
          ) : null}
        </div>
      </div>
      <div className="grid gap-6 lg:grid-cols-5 lg:gap-8">
        <div className="min-w-0 lg:col-span-3">
          <div className="flex items-center justify-between gap-4 sm:gap-8">
            <p className="min-w-0 text-3xl font-extrabold tracking-tight min-[375px]:text-4xl sm:text-6xl" style={{ color }}>
              {riskLabel}
            </p>
            <p className="max-w-28 shrink-0 border-l border-borderSoft pl-4 text-right sm:max-w-none sm:pl-8">
              <span className="block text-3xl font-bold tabular-nums tracking-tight text-ink sm:text-4xl">{probability.toFixed(0)}%</span>
              <span className="mt-1 block text-xs text-muted sm:text-sm">xác suất theo mô hình</span>
            </p>
          </div>

          <div className="mt-6">
            <div
              className="relative"
              role="img"
              aria-label={`Xác suất mô hình ${probability.toFixed(1)}%. Thấp: dưới ${formatCutoff(lowMax)}%; Trung bình: từ ${formatCutoff(lowMax)}% đến dưới ${formatCutoff(highMin)}%; Cao: từ ${formatCutoff(highMin)}%.`}
            >
              <div className="flex h-3 overflow-hidden rounded-full" aria-hidden="true">
                <div style={{ width: `${lowMax}%`, backgroundColor: RISK_COLORS.Low }} />
                <div className="border-x-2 border-canvas" style={{ width: `${highMin - lowMax}%`, backgroundColor: RISK_COLORS.Medium }} />
                <div style={{ width: `${100 - highMin}%`, backgroundColor: RISK_COLORS.High }} />
              </div>
              <span aria-hidden="true" className="absolute -top-1 h-5 w-1 -translate-x-1/2 rounded-full bg-ink ring-2 ring-canvas" style={{ left: `${Math.min(99.5, Math.max(0.5, probability))}%` }} />
            </div>
            <ul aria-label="Các mức nguy cơ theo mô hình" className="mt-3 grid grid-cols-3 gap-2 sm:gap-4">
              {bands.map((band) => (
                <li key={band.risk} className="min-w-0 py-1">
                  <p className={`flex items-center gap-1 text-xs font-semibold sm:text-sm ${result.risk === band.risk ? "underline decoration-2 underline-offset-4 sm:no-underline" : ""}`} style={{ color: RISK_COLORS[band.risk] }}>
                    {band.label}
                    {result.risk === band.risk ? <><Check aria-hidden="true" className="hidden h-3 w-3 shrink-0 sm:block" strokeWidth={3} /><span className="sr-only"> (Mức của bạn)</span></> : null}
                  </p>
                  <p className="mt-1 text-xs tabular-nums text-muted sm:text-sm">{band.range}</p>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <section aria-labelledby="hero-guidance" className="min-w-0 border-t border-borderSoft pt-6 lg:col-span-2 lg:border-l lg:border-t-0 lg:pl-8 lg:pt-0">
          <h2 id="hero-guidance" className="flex items-center gap-2 text-base font-semibold text-ink sm:text-lg">
            <ShieldCheck aria-hidden="true" className="h-5 w-5 shrink-0" /> Hướng xử trí
          </h2>
          <p className="mt-3 text-2xl font-bold leading-snug" style={{ color: ESCALATION_COLORS[escalation] }}>
            {ESCALATION_LABELS[escalation] ?? escalation}
          </p>
          {raised ? (
            <p className="mt-3 text-sm leading-relaxed text-muted">
              Sau kiểm tra an toàn: <strong className="text-ink">mức {RISK_LABELS[result.safety.effective_risk]}</strong>.
              {" "}Cảnh báo từ số đo được ưu tiên khi đưa ra hướng xử trí.
            </p>
          ) : null}
          <div className="mt-4">
            <p className="flex items-center gap-2 text-sm font-semibold text-ink">
              {hasAlerts ? <AlertTriangle aria-hidden="true" className="h-4 w-4 shrink-0" /> : <Check aria-hidden="true" className="h-4 w-4 shrink-0" />}
              {hasAlerts ? `${result.safety.alerts.length} cảnh báo cần xem` : "Không có cảnh báo từ luật an toàn"}
            </p>
            {hasAlerts ? (
              <ul aria-label="Các cảnh báo an toàn" className="mt-2 list-disc space-y-2 pl-5 text-sm leading-relaxed text-muted [overflow-wrap:anywhere]">
                {result.safety.alerts.map((alert, index) => (
                  <li key={`${index}-${alert}`}>{alert}</li>
                ))}
              </ul>
            ) : null}
          </div>
        </section>
      </div>

      <div className="mt-5 flex items-start gap-3 border-t border-borderSoft pt-5">
        <Avatar id="mo" size={40} mood={mood} />
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-3 py-1">
            <p className="text-sm font-semibold text-info">Ông Mô</p>
          </div>
          <p className="mt-2 max-w-prose text-sm leading-relaxed text-muted">{line}</p>
        </div>
      </div>
    </header>
  );
}
