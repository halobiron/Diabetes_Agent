import { AlertTriangle, Database, GitCompareArrows, Timer, Workflow } from "lucide-react";

import { EVIDENCE_LABELS, RISK_LABELS } from "@/lib/labels";
import type { PredictionResult } from "@/types/healthcare";

import { MetricTile, PanelHeading } from "./shared-ui";

const COMPONENT_LABELS: Record<string, string> = {
  risk_model: "Mô hình dự đoán",
  feature_explainer: "Giải thích đặc trưng",
  memory_search: "Bộ nhớ: hồ sơ tương tự",
  retriever: "Truy xuất bằng chứng (KB + RAG)",
  safety_guard: "Luật an toàn",
  recommender: "Khuyến nghị",
  support_policy: "Policy học tăng cường",
  what_if: "Mô phỏng nếu thay đổi",
  explainer: "Giải thích bằng lời",
  memory_store: "Bộ nhớ: lưu hồ sơ",
};

export function AgentTrace({ result }: { result: PredictionResult }) {
  const trace = result.trace;
  if (!trace) return <p className="text-sm text-muted">Phiên bản API này chưa trả về vết xử lý của các agent.</p>;

  const slowest = Math.max(...trace.steps.map((step) => step.ms), 1);
  const errors = new Map((result.degraded ?? []).map((item) => [item.component, item.error]));
  const failed = trace.steps.filter((step) => step.status === "degraded").length;

  return (
    <section className="min-w-0 space-y-5">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <MetricTile label="Tổng thời gian xử lý" value={`${trace.total_ms.toFixed(0)} ms`} icon={<Timer className="h-4 w-4" />} />
        <MetricTile label="Bằng chứng tìm được" value={`${trace.evidence_count} đoạn (${EVIDENCE_LABELS[trace.evidence_status] ?? trace.evidence_status})`} icon={<Database className="h-4 w-4" />} />
        <MetricTile label="Bước dùng cơ chế dự phòng" value={`${failed} / ${trace.steps.length}`} icon={<AlertTriangle className="h-4 w-4" />} />
      </div>

      {trace.disagreement ? (
        <div role="status" className="rounded-lg border border-info/40 bg-info/10 p-4 text-sm">
          <div className="flex items-center gap-2 font-semibold text-ink"><GitCompareArrows aria-hidden="true" className="h-4 w-4 text-info" />Mô hình và luật không thống nhất</div>
          <p className="mt-2 leading-6 text-muted">Mô hình xếp nguy cơ <strong className="text-ink">{RISK_LABELS[trace.disagreement.model_risk]}</strong>, nhưng các luật trên số đo thực tế nâng lên <strong className="text-ink">{RISK_LABELS[trace.disagreement.effective_risk]}</strong>. Luật được ưu tiên vì số đo thực tế đáng tin hơn một ước tính thống kê.</p>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-muted">
            {trace.disagreement.rules.map((rule) => <li key={rule.code}><span className="font-mono text-xs text-ink">{rule.code}</span> {rule.message}</li>)}
            {trace.disagreement.conflicts.map((message) => <li key={message}>{message}</li>)}
          </ul>
        </div>
      ) : null}

      <div className="console-panel min-w-0 rounded-lg p-5">
        <PanelHeading icon={<Workflow className="h-4 w-4" />} title="Các agent đã chạy theo thứ tự" />
        <ol className="mt-4 space-y-2">
          {trace.steps.map((step, index) => (
            <li key={`${step.component}-${index}`} className={`rounded-md border p-3 ${step.status === "degraded" ? "border-danger/40 bg-danger/10" : "border-borderSoft bg-canvas/40"}`}>
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="font-semibold text-ink"><span className="mr-2 tabular-nums text-muted">{index + 1}.</span>{COMPONENT_LABELS[step.component] ?? step.component}</span>
                <span className="text-xs tabular-nums text-muted">{step.ms.toFixed(1)} ms</span>
              </div>
              <div className="mt-2 h-1 overflow-hidden rounded-full bg-borderSoft" aria-hidden="true">
                <div className={`h-full rounded-full ${step.status === "degraded" ? "bg-danger" : "bg-info"}`} style={{ width: `${Math.max(2, (step.ms / slowest) * 100)}%` }} />
              </div>
              <p className="mt-2 text-sm leading-6 text-muted">
                {step.status === "degraded" ? <><strong className="text-ink">Lỗi, dùng dự phòng:</strong> {step.detail}{errors.get(step.component) ? ` (${errors.get(step.component)})` : ""}</> : step.detail}
              </p>
            </li>
          ))}
        </ol>
        <p className="mt-3 text-xs leading-5 text-muted">Một thành phần có thể xuất hiện nhiều lần khi policy yêu cầu truy xuất thêm bằng chứng và tính lại khuyến nghị.</p>
      </div>
    </section>
  );
}
