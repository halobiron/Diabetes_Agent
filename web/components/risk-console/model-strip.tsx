import { formatModelName } from "@/lib/labels";
import type { PredictionResult } from "@/types/healthcare";

import { Avatar, CAST } from "./agents";

/** Thẻ nhân viên của Ông Mô: ghi lại mô hình ông đang dùng. */
export function ModelStrip({ result }: { result: PredictionResult }) {
  const model = result.model;
  const selectedModel = model?.selected_model;
  const metrics = selectedModel ? model?.metrics?.[selectedModel]?.test : undefined;
  const rows: Array<[string, string]> = [
    ["Mô hình", formatModelName(selectedModel)],
    ["Số mẫu dữ liệu", typeof model?.rows_total === "number" ? model.rows_total.toLocaleString("vi-VN") : "—"],
    ["ROC AUC", typeof metrics?.roc_auc === "number" ? metrics.roc_auc.toFixed(3) : "—"],
    ["Hiệu chuẩn", model?.calibration ?? "—"],
  ];

  return (
    <section aria-label="Thẻ nhân viên của Ông Mô" className="paper flex flex-col gap-5 rounded-2xl border-2 border-dashed p-5 sm:flex-row sm:items-center" style={{ borderColor: `${CAST.mo.ink}66` }}>
      <div className="flex shrink-0 items-center gap-3 sm:flex-col sm:text-center">
        <Avatar id="mo" size={72} mood="happy" />
        <div>
          <div className="font-bold" style={{ color: CAST.mo.ink }}>{CAST.mo.name}</div>
          <div className="text-xs text-muted">{CAST.mo.role}</div>
        </div>
      </div>
      <dl className="grid flex-1 grid-cols-2 gap-x-6 gap-y-3 md:grid-cols-4">
        {rows.map(([label, value]) => (
          <div key={label} className="min-w-0">
            <dt className="text-xs font-semibold text-muted">{label}</dt>
            <dd className="mt-0.5 truncate text-base font-bold" title={value}>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
