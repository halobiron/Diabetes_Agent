import { Activity, Database } from "lucide-react";

import { RISK_LABELS } from "@/lib/labels";

import type { PredictionResult } from "@/types/healthcare";

import { CitationLink } from "./citation";
import { DataTable, PanelHeading } from "./shared-ui";

export function Evidence({ result }: { result: PredictionResult }) {
  const contexts = result.retrieved_context ?? [];

  return (
    <section className="grid min-w-0 grid-cols-1 gap-5 xl:grid-cols-[1fr_0.9fr]">
      <div className="console-panel min-w-0 rounded-lg p-5">
        <PanelHeading icon={<Database className="h-4 w-4" />} title="Bằng chứng y khoa truy xuất" />
        <div className="mt-4 space-y-3">
          {contexts.length > 0 ? (
            contexts.map((context) => (
              <div key={context.evidence_id} className="rounded-md border border-borderSoft bg-canvas/40 p-4">
                <div className="font-semibold text-ink">{context.title}</div>
                <p className="mt-2 text-sm leading-6 text-muted">{context.text}</p>
                <p className="mt-2 text-xs leading-5 text-muted">
                  <CitationLink citation={context} /> · độ liên quan {context.relevance.toFixed(2)} · {context.via === "graph+semantic" ? "đồ thị tri thức + ngữ nghĩa" : "ngữ nghĩa"}
                </p>
              </div>
            ))
          ) : (
            <p className="text-sm text-muted">Chưa truy xuất được bằng chứng phù hợp cho hồ sơ này.</p>
          )}
        </div>
      </div>
      <div className="console-panel min-w-0 rounded-lg p-5">
        <PanelHeading icon={<Activity className="h-4 w-4" />} title="Dự đoán trước đây tương tự" />
        <DataTable
          rows={result.similar_cases.map((item) => ({
            "Nguy cơ": RISK_LABELS[item.metadata.risk ?? ""] ?? "—",
            "Xác suất":
              typeof item.metadata.probability === "number"
                ? `${(item.metadata.probability * 100).toFixed(1)}%`
                : "—",
            "Tuổi": item.metadata.age ?? "—",
            BMI: item.metadata.bmi ?? "—",
            "Huyết áp": item.metadata.bp ?? "—",
            "Khoảng cách": item.distance.toFixed(3),
          }))}
        />
        <p className="mt-3 text-xs text-muted">
          Đây là các dự đoán trước đây của mô hình, chưa phải chẩn đoán hoặc kết quả bệnh được xác nhận.
        </p>
      </div>
    </section>
  );
}
