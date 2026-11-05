import { ArrowRight, Check } from "lucide-react";

import { featureLabel } from "@/lib/labels";
import type { PredictionResult } from "@/types/healthcare";

const GROUPS = [
  { step: "body", label: "số đo cơ thể và giới tính", fields: ["Sex"] },
  { step: "history", label: "tiền sử bệnh", fields: ["HighChol", "CholCheck", "Stroke", "HeartDiseaseorAttack", "DiffWalk"] },
  { step: "habits", label: "thói quen", fields: ["Smoker", "HvyAlcoholConsump", "PhysActivity", "Fruits", "Veggies"] },
  { step: "feel", label: "cảm nhận chung và thông tin bổ sung", fields: ["GenHlth", "MentHlth", "PhysHlth", "AnyHealthcare", "NoDocbcCost", "Education", "Income"] },
];

export function InputReview({ result, confirmed, onConfirm, onEdit, coveredFields = [] }: {
  result: PredictionResult;
  confirmed: string[];
  onConfirm: (signature: string) => void;
  onEdit: (step: string) => void;
  coveredFields?: string[];
}) {
  const reasons = (result.safety.confidence_reasons ?? []).map((reason) => reason.code === "defaulted_inputs"
    ? { ...reason, fields: reason.fields.filter((field) => !coveredFields.includes(field)) }
    : reason).filter((reason) => reason.code !== "defaulted_inputs" || reason.fields.length > 0);
  if (!reasons.length) return null;

  const format = (value: number) => value.toLocaleString("vi-VN", { maximumFractionDigits: 2 });
  const editAction = "inline-flex min-h-11 shrink-0 items-center justify-center gap-1.5 rounded-lg px-3 text-sm font-semibold text-info transition-colors hover:bg-infoSoft focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-info";

  return (
    <section aria-labelledby="input-review-title" className="rounded-2xl border border-borderSoft bg-panel px-4 py-4 sm:px-5">
      <h2 id="input-review-title" className="text-base font-bold leading-6">Thông tin còn thiếu hoặc cần xác nhận</h2>
      <div className="mt-3 divide-y divide-borderSoft">
        {reasons.map((reason) => {
          const missing = reason.code === "defaulted_inputs";
          const bp = reason.code === "bp_outside_check_range";
          // Bind confirmation to the actual measurements, including height and weight.
          const signature = JSON.stringify(bp
            ? [reason.code, result.patient.bp]
            : [reason.code, result.patient.bmi, result.patient.height_cm, result.patient.weight_kg]);
          const isConfirmed = !missing && confirmed.includes(signature);
          return (
            <div key={reason.code} className="py-3 first:pt-0 last:pb-0">
              {missing ? (
                <>
                <p className="max-w-prose text-sm leading-relaxed text-muted">{reason.message}</p>
                <ul className="mt-2 divide-y divide-borderSoft">
                  {GROUPS.map((group) => {
                    const fields = reason.fields.filter((field) => group.fields.includes(field));
                    if (!fields.length) return null;
                    return (
                      <li key={group.step} className="flex items-start justify-between gap-3 py-2 sm:items-center">
                        <div className="min-w-0 py-1">
                          <h3 className="text-sm font-semibold text-ink">{group.label.charAt(0).toLocaleUpperCase("vi-VN") + group.label.slice(1)}</h3>
                          <p className="mt-0.5 text-sm leading-relaxed text-muted">{fields.map(featureLabel).join(", ")}</p>
                        </div>
                        <button type="button" onClick={() => onEdit(group.step)} className={editAction} aria-label={`Bổ sung ${group.label}`}>
                          Bổ sung <ArrowRight aria-hidden="true" className="h-3.5 w-3.5" />
                        </button>
                      </li>
                    );
                  })}
                </ul>
                </>
              ) : (
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between sm:gap-5">
                  <div className="min-w-0 flex-1">
                    <h3 className="text-sm font-semibold">{isConfirmed ? (bp ? "Huyết áp đã được bạn xác nhận" : "Chiều cao và cân nặng đã được bạn xác nhận") : bp ? "Xác nhận số đo huyết áp" : "Xác nhận chiều cao và cân nặng"}</h3>
                    <p className="mt-1 text-sm tabular-nums text-ink">
                      {bp ? `${format(result.patient.bp)} mmHg` : `BMI ${format(result.patient.bmi)}`}
                      {!bp && result.patient.height_cm != null && result.patient.weight_kg != null ? (
                        <span className="text-muted"> · {format(result.patient.height_cm)} cm, {format(result.patient.weight_kg)} kg</span>
                      ) : null}
                    </p>
                    {isConfirmed ? (
                      <p role="status" className="mt-1 flex items-start gap-1.5 text-sm leading-relaxed text-muted"><Check aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0 text-success" />Đã xác nhận trong phiên này; các cảnh báo an toàn vẫn được giữ nguyên.</p>
                    ) : (
                      <p className="mt-1 text-sm text-muted">Số đo nằm ngoài khoảng kiểm tra đầu vào của hệ thống.</p>
                    )}
                    <details className="mt-1 text-sm text-muted">
                      <summary className="w-fit cursor-pointer py-1 underline-offset-4 hover:underline">Vì sao cần xác nhận?</summary>
                      <p className="mt-1 max-w-prose leading-relaxed">{reason.message}</p>
                    </details>
                  </div>
                  <div className="flex flex-wrap items-center gap-1 sm:justify-end">
                    {!isConfirmed ? (
                      <button type="button" className="inline-flex min-h-11 items-center justify-center rounded-lg bg-infoSoft px-3 text-sm font-semibold text-info transition-colors hover:bg-info/15 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-info" onClick={() => onConfirm(signature)}>Đúng số đo của tôi</button>
                    ) : null}
                    <button type="button" className={editAction} onClick={() => onEdit("body")} aria-label={`Sửa ${bp ? "huyết áp" : "chiều cao, cân nặng"}`}>Sửa</button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
      {!coveredFields.length ? <InputScoreDetails result={result} /> : null}
    </section>
  );
}

export function InputScoreDetails({ result }: { result: PredictionResult }) {
  const reasons = result.safety.confidence_reasons ?? [];
  if (!reasons.length) return null;
  const format = (value: number) => value.toLocaleString("vi-VN", { maximumFractionDigits: 2 });
  return (
      <details className="mt-3 border-t border-borderSoft pt-1 text-sm text-muted">
        <summary className="w-fit cursor-pointer py-3 font-medium underline-offset-4 hover:text-ink hover:underline">Cách hệ thống tính điểm đầu vào</summary>
        <p className="mt-3">Điểm quy ước hiện tại: {format(result.safety.confidence_score * 100)}/100. Bắt đầu từ 100 điểm, sau đó trừ:</p>
        <ul className="mt-2 list-disc space-y-1 pl-5">
          {reasons.map((reason) => (
            <li key={reason.code}>{reason.code === "defaulted_inputs" ? "Các mục dùng giá trị mặc định" : reason.code === "bp_outside_check_range" ? "Huyết áp ngoài khoảng kiểm tra đầu vào" : "BMI ngoài khoảng kiểm tra đầu vào"}: {format(reason.penalty * 100)} điểm.</li>
          ))}
        </ul>
        <p className="mt-3">Đây là quy tắc kiểm tra đầu vào, không phải tỷ lệ dự đoán đúng. Xác nhận số đo chỉ ghi nhận câu trả lời của bạn, không tự tăng điểm hay bỏ cảnh báo.</p>
      </details>
  );
}
