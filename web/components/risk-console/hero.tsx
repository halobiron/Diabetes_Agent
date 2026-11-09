import { AlertTriangle, BookOpenCheck, Check, ClipboardCheck } from "lucide-react";
import type { ReactNode } from "react";

import { ESCALATION_COLORS, ESCALATION_LABELS, RISK_COLORS, RISK_LABELS } from "@/lib/labels";
import type { PredictionResult } from "@/types/healthcare";

import { Avatar, Bubble, CAST, Seal, type Mood } from "./agents";
import { RiskGauge } from "./gauge";

function speech(result: PredictionResult, raised: boolean, alerts: number) {
  if (alerts > 0) return "Có số đo cần chú ý trước tiên, xem ngay bên dưới.";
  if (raised) return "Số đo thực tế đã nâng mức so với dự đoán của mô hình.";
  if (result.risk === "High") return "Nhiều yếu tố làm tăng nguy cơ, nhưng có việc làm được ngay.";
  if (result.risk === "Low") return "Mọi thứ khá ổn, cứ giữ thói quen tốt nhé!";
  return "Có vài yếu tố đáng để ý, xem tab Vì sao.";
}

function Stat({ icon, value, label, tone }: { icon: ReactNode; value: string; label: string; tone?: string }) {
  return (
    <li className="flex items-center gap-3 rounded-xl border border-borderSoft bg-panel/80 px-3 py-2.5">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg" style={{ background: `${tone ?? "#4b3fa8"}1a`, color: tone ?? "#4b3fa8" }}>{icon}</span>
      <span className="min-w-0">
        <span className="block text-base font-bold leading-5 tabular-nums">{value}</span>
        <span className="block truncate text-xs text-muted">{label}</span>
      </span>
    </li>
  );
}

export function Hero({ result }: { result: PredictionResult }) {
  const color = RISK_COLORS[result.risk];
  const probability = result.probability * 100;
  const lowMax = (result.model?.risk_bands?.low_max ?? 0.4) * 100;
  const highMin = (result.model?.risk_bands?.high_min ?? 0.7) * 100;
  const formatCutoff = (value: number) => value.toLocaleString("vi-VN", { maximumFractionDigits: 0 });
  const bands = [
    { risk: "Low", label: "Thấp", range: `< ${formatCutoff(lowMax)}%` },
    { risk: "Medium", label: "Trung bình", range: `${formatCutoff(lowMax)}–${formatCutoff(highMin)}%` },
    { risk: "High", label: "Cao", range: `≥ ${formatCutoff(highMin)}%` },
  ] as const;
  const escalation = result.safety.escalation;
  const riskLabel = RISK_LABELS[result.risk] ?? result.risk;
  const raised = Boolean(result.trace?.disagreement);
  const alertCount = result.safety.alerts.length;
  const mood: Mood = raised || alertCount > 0 ? "think" : result.risk === "High" ? "worried" : result.risk === "Low" ? "happy" : "think";
  const escColor = ESCALATION_COLORS[escalation];

  return (
    <header
      className="rise overflow-hidden rounded-2xl border border-borderSoft bg-panel p-5 shadow-console md:p-6"
      style={{ backgroundImage: `linear-gradient(135deg, ${color}1f 0%, transparent 55%)` }}
    >
      <div className="grid gap-6 lg:grid-cols-[16rem_minmax(0,1fr)] lg:gap-8">
        <div className="min-w-0">
          <h1 className="text-center text-sm font-semibold text-muted">Nguy cơ tiểu đường của bạn</h1>
          <div className="mt-2">
            <RiskGauge probability={probability} lowMax={lowMax} highMin={highMin} label={riskLabel.toLocaleLowerCase("vi-VN")} color={color} />
          </div>
          <ul aria-hidden="true" className="mt-3 flex justify-center gap-x-3 text-xs tabular-nums">
            {bands.map((band) => (
              <li key={band.risk} className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full" style={{ background: RISK_COLORS[band.risk] }} />
                <span className="text-muted">{band.range}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="flex min-w-0 flex-col gap-4">
          <div className="flex items-start gap-3">
            <Avatar id="mo" size={52} mood={mood} />
            <div className="min-w-0">
              <div className="mb-1 flex flex-wrap items-center gap-2">
                <span className="text-sm font-semibold" style={{ color: CAST.mo.ink }}>Ông Mô</span>
                <span className="stamp-in inline-block" style={{ ["--tilt" as string]: "0deg", ["--delay" as string]: "0.5s" }}>
                  <Seal id="mo" tilt={-3} className="!px-2 !py-0 !text-xs">Đã chấm</Seal>
                </span>
                {raised ? (
                  <span className="stamp-in inline-block" style={{ ["--tilt" as string]: "0deg", ["--delay" as string]: "0.8s" }}>
                    <Seal id="luat" tilt={3} className="!px-2 !py-0 !text-xs">Chú Luật nâng mức</Seal>
                  </span>
                ) : null}
              </div>
              <Bubble id="mo" className="text-sm leading-6">{speech(result, raised, alertCount)}</Bubble>
            </div>
          </div>

          <section aria-labelledby="hero-guidance" className="rounded-xl border-2 bg-panel px-4 py-3" style={{ borderColor: `${escColor}55` }}>
            <h2 id="hero-guidance" className="text-xs font-semibold uppercase tracking-wide text-muted">Hướng xử trí</h2>
            <p className="mt-0.5 text-2xl font-bold leading-snug" style={{ color: escColor }}>{ESCALATION_LABELS[escalation] ?? escalation}</p>
            {raised ? (
              <p className="mt-1 text-sm leading-6 text-muted">
                Sau kiểm tra an toàn: <strong className="text-ink">mức {RISK_LABELS[result.safety.effective_risk]}</strong>
              </p>
            ) : null}
          </section>

          <ul className="grid gap-2 sm:grid-cols-3">
            <Stat
              icon={alertCount > 0 ? <AlertTriangle aria-hidden="true" className="h-4 w-4" /> : <Check aria-hidden="true" className="h-4 w-4" />}
              value={alertCount > 0 ? `${alertCount} cảnh báo` : "Ổn"}
              label="Luật an toàn"
              tone={alertCount > 0 ? "#b0372b" : "#1b7a4b"}
            />
            <Stat
              icon={<BookOpenCheck aria-hidden="true" className="h-4 w-4" />}
              value={`${result.retrieved_context.length} đoạn`}
              label="Bằng chứng"
              tone="#1b6b4d"
            />
            <Stat
              icon={<ClipboardCheck aria-hidden="true" className="h-4 w-4" />}
              value={`${Math.round(result.safety.confidence_score * 100)}/100`}
              label="Điểm đầu vào"
              tone="#0b6b86"
            />
          </ul>
        </div>
      </div>

      <p className="mt-4 border-t border-borderSoft pt-3 text-xs text-muted">Ước tính thống kê, chưa phải chẩn đoán.</p>
    </header>
  );
}
