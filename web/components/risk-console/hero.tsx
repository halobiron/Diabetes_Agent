import { Pencil } from "lucide-react";

import { ESCALATION_COLORS, ESCALATION_LABELS, RISK_COLORS, RISK_LABELS } from "@/lib/labels";
import type { PredictionResult } from "@/types/healthcare";

const ARC = Math.PI * 80;

export function Hero({ result, onEdit }: { result: PredictionResult; onEdit: () => void }) {
  const color = RISK_COLORS[result.risk];
  const probability = result.probability * 100;
  const escalation = result.safety.escalation;
  const confidence = Math.round(result.safety.confidence_score * 100);
  const riskLabel = (RISK_LABELS[result.risk] ?? result.risk).toLowerCase();

  return (
    <header className="rise console-panel overflow-hidden rounded-3xl">
      <div className="grid lg:grid-cols-[minmax(0,420px)_1fr]">
        <div className="flex flex-col items-center justify-center px-6 pb-4 pt-8" style={{ background: `${color}14` }}>
          <svg viewBox="0 0 200 112" className="w-full max-w-[340px]" role="img" aria-label={`Xác suất nguy cơ ${probability.toFixed(1)}%`}>
            <path d="M20 100 A80 80 0 0 1 180 100" fill="none" stroke="#ffffff" strokeWidth="16" strokeLinecap="round" />
            <path
              d="M20 100 A80 80 0 0 1 180 100"
              fill="none"
              stroke={color}
              strokeWidth="16"
              strokeLinecap="round"
              strokeDasharray={`${Math.max(1, (ARC * probability) / 100)} ${ARC}`}
              style={{ transition: "stroke-dasharray 0.8s cubic-bezier(0.16,1,0.3,1)" }}
            />
            <text x="100" y="88" textAnchor="middle" fontSize="34" fontWeight="700" fill="#112f2c" className="tabular-nums">
              {probability.toFixed(0)}%
            </text>
            <text x="100" y="106" textAnchor="middle" fontSize="9.5" fill="#4c6260">xác suất theo mô hình</text>
          </svg>
          <p className="mt-1 text-center text-2xl font-bold md:text-3xl">
            Nguy cơ <span style={{ color }}>{riskLabel}</span>
          </p>
        </div>

        <div className="flex flex-col justify-between gap-6 p-6 md:p-8">
          <div>
            <p className="text-sm font-semibold text-muted">Hướng xử trí đề xuất</p>
            <p className="mt-1 flex items-center gap-3 text-2xl font-bold md:text-3xl">
              <span aria-hidden="true" className="h-4 w-4 shrink-0 rounded-full" style={{ backgroundColor: ESCALATION_COLORS[escalation] }} />
              {ESCALATION_LABELS[escalation] ?? escalation}
            </p>
            <p className="mt-3 max-w-prose text-base leading-7 text-muted">
              Đây là ước tính thống kê từ dữ liệu khảo sát, không phải chẩn đoán. Hãy xem phần &quot;Bạn nên làm gì&quot; bên dưới.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <Stat label="BMI" value={result.patient.bmi.toFixed(1)} />
            <Stat label="Độ tin cậy dữ liệu" value={`${confidence}%`} sub={RISK_LABELS[result.safety.confidence_label]} />
            <Stat label="Cảnh báo" value={String(result.safety.alerts.length)} sub={result.safety.alerts.length ? "cần xem" : "không có"} />
          </div>

          <button type="button" onClick={onEdit} className="btn-secondary self-start">
            <Pencil aria-hidden="true" className="h-4 w-4" /> Chỉnh sửa hồ sơ
          </button>
        </div>
      </div>
    </header>
  );
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl bg-canvas px-4 py-3">
      <div className="text-xs font-semibold text-muted">{label}</div>
      <div className="mt-1 text-xl font-bold tabular-nums">{value}</div>
      {sub ? <div className="text-xs text-muted">{sub}</div> : null}
    </div>
  );
}
