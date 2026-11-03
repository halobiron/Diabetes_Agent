import { formatModelName } from "@/lib/labels";
import type { PredictionResult } from "@/types/healthcare";

import { ModelItem } from "./shared-ui";

export function ModelStrip({ result }: { result: PredictionResult }) {
  const model = result.model;
  const selectedModel = model?.selected_model;
  const metrics = selectedModel ? model?.metrics?.[selectedModel]?.test : undefined;

  return (
    <section className="console-panel grid gap-3 rounded-lg p-4 md:grid-cols-4">
      <ModelItem label="Mô hình" value={formatModelName(selectedModel)} />
      <ModelItem
        label="Số mẫu dữ liệu"
        value={typeof model?.rows_total === "number" ? model.rows_total.toLocaleString("vi-VN") : "—"}
      />
      <ModelItem
        label="ROC AUC"
        value={typeof metrics?.roc_auc === "number" ? metrics.roc_auc.toFixed(3) : "—"}
      />
      <ModelItem label="Hiệu chuẩn" value={model?.calibration ?? "—"} />
    </section>
  );
}
