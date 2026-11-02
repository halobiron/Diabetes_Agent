import { Activity, Database } from "lucide-react";

import type { PredictionResult } from "@/types/healthcare";

import { DataTable, PanelHeading } from "./shared-ui";

export function Evidence({ result }: { result: PredictionResult }) {
  const contexts = result.retrieved_context ?? [];

  return (
    <section className="grid gap-5 xl:grid-cols-[1fr_0.9fr]">
      <div className="console-panel rounded-lg p-5">
        <PanelHeading icon={<Database className="h-4 w-4" />} title="Retrieved Medical Context" />
        <div className="mt-4 space-y-3">
          {contexts.length > 0 ? (
            contexts.map((context) => (
              <div key={context.title} className="rounded-md border border-borderSoft bg-canvas/40 p-4">
                <div className="font-semibold text-ink">{context.title}</div>
                <p className="mt-2 text-sm leading-6 text-muted">{context.text}</p>
              </div>
            ))
          ) : (
            <p className="text-sm text-muted">No medical context retrieved for this case.</p>
          )}
        </div>
      </div>
      <div className="console-panel rounded-lg p-5">
        <PanelHeading icon={<Activity className="h-4 w-4" />} title="Similar Prior Predictions" />
        <DataTable
          rows={result.similar_cases.map((item) => ({
            Risk: item.metadata.risk ?? "—",
            Probability:
              typeof item.metadata.probability === "number"
                ? `${(item.metadata.probability * 100).toFixed(1)}%`
                : "—",
            Age: item.metadata.age ?? "—",
            BMI: item.metadata.bmi ?? "—",
            BP: item.metadata.bp ?? "—",
            Distance: item.distance.toFixed(3),
          }))}
        />
        <p className="mt-3 text-xs text-muted">
          Earlier model predictions, not confirmed diagnoses or outcomes.
        </p>
      </div>
    </section>
  );
}
