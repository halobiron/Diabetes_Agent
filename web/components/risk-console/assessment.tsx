import { AlertTriangle, BarChart3, Brain, CheckCircle2 } from "lucide-react";
import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { featureLabel, formatFeatureValue, METHOD_LABELS } from "@/lib/labels";
import type { PredictionResult } from "@/types/healthcare";

import { EvidenceTrail } from "./evidence-trail";
import { DataTable, NarrativePanel, PanelHeading } from "./shared-ui";
import type { ChartFeature } from "./types";
import { WhatIf } from "./what-if";

export function Assessment({ result }: { result: PredictionResult }) {
  const topFeatures = useMemo(() => {
    return result.feature_explanation.features
      .slice()
      .sort((a, b) => b.magnitude - a.magnitude)
      .slice(0, 8)
      .map((feature) => ({
        ...feature,
        label: featureLabel(feature.feature),
        valueLabel: formatFeatureValue(feature.feature, feature.value),
        directionLabel: feature.impact > 0 ? "Tăng nguy cơ" : feature.impact < 0 ? "Giảm nguy cơ" : "Không tác động",
      }));
  }, [result.feature_explanation.features]);

  return (
    <section className="grid min-w-0 grid-cols-1 gap-5 xl:grid-cols-[0.95fr_1.05fr]">
      <div className="min-w-0 space-y-5">
        <NarrativePanel title="Giải thích" icon={<Brain className="h-4 w-4" />} text={result.explanation} />
        <NarrativePanel
          title="Khuyến nghị"
          icon={<CheckCircle2 className="h-4 w-4" />}
          text={result.recommendation}
        />
        {result.what_if ? <WhatIf whatIf={result.what_if} /> : null}
        {result.safety.alerts.length > 0 ? (
          <div className="rounded-lg border border-danger/40 bg-danger/10 p-4 text-sm text-[#ffc1bc]">
            <div className="mb-2 flex items-center gap-2 font-semibold text-ink">
              <AlertTriangle className="h-4 w-4 text-danger" />
              Cảnh báo an toàn
            </div>
            <ul className="space-y-1">
              {result.safety.alerts.map((alert) => (
                <li key={alert}>{alert}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
      <div className="min-w-0 space-y-5">
        <FeatureImpactPanel features={topFeatures} method={result.feature_explanation.method} />
        <EvidenceTrail trail={result.evidence_trail ?? []} />
      </div>
    </section>
  );
}

function FeatureImpactPanel({ features, method }: { features: ChartFeature[]; method: string }) {
  return (
    <div className="console-panel min-w-0 rounded-lg p-5">
      <PanelHeading icon={<BarChart3 className="h-4 w-4" />} title="Tác động của đặc trưng" />
      <div className="mt-4 h-80">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={features} layout="vertical" margin={{ top: 8, right: 18, bottom: 8, left: 28 }}>
            <CartesianGrid stroke="rgba(255,255,255,0.08)" horizontal={false} />
            <XAxis type="number" stroke="#9aa4b2" tickLine={false} axisLine={false} />
            <YAxis
              type="category"
              dataKey="label"
              width={135}
              stroke="#9aa4b2"
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 12 }}
            />
            <Tooltip
              cursor={{ fill: "rgba(255,255,255,0.04)" }}
              formatter={(value) => [Number(value).toFixed(4), "Mức tác động"]}
              contentStyle={{
                background: "#101318",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 8,
              }}
            />
            <ReferenceLine x={0} stroke="rgba(244,246,248,0.45)" strokeDasharray="3 3" />
            <Bar dataKey="impact" radius={[0, 4, 4, 0]}>
              {features.map((feature) => (
                <Cell key={feature.feature} fill={feature.impact >= 0 ? "#d05245" : "#2f9b6a"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-xs text-muted">
        <span>Phương pháp: {METHOD_LABELS[method] ?? method}</span>
        <span>{features.length} đặc trưng có tác động lớn nhất</span>
      </div>
      <DataTable
        rows={features.map((feature) => ({
          "Đặc trưng": feature.label,
          "Giá trị": feature.valueLabel,
          "Chiều tác động": feature.directionLabel,
          "Mức tác động": feature.impact.toFixed(4),
        }))}
        compact
      />
    </div>
  );
}
