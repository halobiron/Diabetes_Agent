import { Brain, Gauge, ShieldCheck } from "lucide-react";

import { ESCALATION_COLORS, ESCALATION_LABELS, RISK_COLORS, RISK_LABELS } from "@/lib/labels";
import type { PredictionResult } from "@/types/healthcare";

import { MetricTile, ProbabilityGauge, RiskBadge } from "./shared-ui";

export function Hero({ result }: { result: PredictionResult | null | undefined }) {
  const risk = result?.risk ?? "Low";
  const riskColor = RISK_COLORS[risk];
  const confidenceLabel = RISK_LABELS[result?.safety?.confidence_label ?? ""] ?? "Chờ đánh giá";
  const confidenceScore = result?.safety?.confidence_score;
  const confidence =
    confidenceScore !== undefined
      ? `${confidenceLabel} (${(confidenceScore * 100).toFixed(0)}%)`
      : confidenceLabel;
  const escalation = result?.safety?.escalation ?? "routine_followup";
  const escalationLabel = ESCALATION_LABELS[escalation] ?? escalation;
  const probability = result ? result.probability * 100 : 0;

  return (
    <header className="grid gap-4 lg:grid-cols-[0.85fr_1.15fr]">
      <div>
        <div className="flex items-center gap-2 text-sm font-semibold text-info">
          <Brain className="h-4 w-4" />
          Hỗ trợ quyết định bằng AI
        </div>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-muted">
          Mô hình học máy kết hợp giải thích đặc trưng, truy xuất bằng chứng và luật an toàn.
          Nguyên mẫu phục vụ học tập; không thay thế tư vấn y tế.
        </p>
      </div>

      <div className="console-panel rounded-lg p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <RiskBadge risk={result ? result.risk : "Low"} muted={!result} />
            <div>
              <div className="field-label">Nguy cơ dự đoán</div>
              <div className="mt-1 text-sm text-muted">
                {result ? `${probability.toFixed(1)}% xác suất` : "Chờ đánh giá"}
              </div>
            </div>
          </div>
          <Gauge className="h-5 w-5" style={{ color: result ? riskColor : "#9aa4b2" }} />
        </div>

        <ProbabilityGauge value={probability} color={result ? riskColor : "#5aa3d9"} muted={!result} />

        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <MetricTile label="BMI" value={result ? result.patient.bmi.toFixed(1) : "—"} />
          <MetricTile label="Chất lượng dữ liệu" value={confidence} icon={<ShieldCheck className="h-4 w-4" />} />
          <div className="rounded-md border border-borderSoft bg-canvas/50 p-3">
            <div className="field-label">Hướng xử trí</div>
            <div className="mt-2 flex min-h-7 items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: ESCALATION_COLORS[escalation] }} />
              <span className="text-sm font-semibold text-ink">{result ? escalationLabel : "Chưa xác định"}</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
