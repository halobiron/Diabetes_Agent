import { formatModelName } from "@/lib/labels";
import type { PredictionResult } from "@/types/healthcare";

import { ModelItem } from "./shared-ui";

export function ModelStrip({ result }: { result: PredictionResult }) {
  const model = result.model;
  const selectedModel = model?.selected_model;
  const metrics = selectedModel ? model?.metrics?.[selectedModel]?.test : undefined;

  return (
    <section className="console-panel grid gap-3 rounded-lg p-4 md:grid-cols-5">
      <ModelItem label="Model" value={formatModelName(selectedModel)} />
      <ModelItem
        label="Rows"
        value={typeof model?.rows_total === "number" ? model.rows_total.toLocaleString() : "—"}
      />
      <ModelItem
        label="ROC AUC"
        value={typeof metrics?.roc_auc === "number" ? metrics.roc_auc.toFixed(3) : "—"}
      />
      <ModelItem label="Calibration" value={model?.calibration ?? "—"} />
      <ModelItem label="Source" value={model?.dataset_slug ?? "Kaggle artifact"} />
    </section>
  );
}
