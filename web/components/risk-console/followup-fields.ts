import type { AskableField, PredictionResult } from "@/types/healthcare";

export const FOLLOWUP_FIELDS: { field: AskableField; feature: string; group: string; label: string }[] = [
  { field: "high_chol", feature: "HighChol", group: "Tiền sử bệnh", label: "Từng được bác sĩ cho biết cholesterol cao" },
  { field: "stroke", feature: "Stroke", group: "Tiền sử bệnh", label: "Từng bị đột quỵ" },
  { field: "heart_disease_or_attack", feature: "HeartDiseaseorAttack", group: "Tiền sử bệnh", label: "Từng được chẩn đoán bệnh mạch vành hoặc nhồi máu cơ tim" },
  { field: "diff_walk", feature: "DiffWalk", group: "Tiền sử bệnh", label: "Gặp khó khăn nghiêm trọng khi đi bộ hoặc leo cầu thang" },
  { field: "smoker", feature: "Smoker", group: "Thói quen", label: "Đã hút ít nhất 100 điếu thuốc trong đời" },
  { field: "phys_activity", feature: "PhysActivity", group: "Thói quen", label: "Có hoạt động thể chất ngoài công việc trong 30 ngày qua" },
  { field: "fruits", feature: "Fruits", group: "Thói quen", label: "Ăn trái cây ít nhất một lần mỗi ngày" },
  { field: "veggies", feature: "Veggies", group: "Thói quen", label: "Ăn rau ít nhất một lần mỗi ngày" },
  { field: "heavy_alcohol_consump", feature: "HvyAlcoholConsump", group: "Thói quen", label: "Uống nhiều rượu bia (nam trên 14, nữ trên 7 ly mỗi tuần)" },
];

export function missingFollowupFields(result: PredictionResult) {
  const missing = new Set(result.safety.defaulted_fields ?? []);
  return FOLLOWUP_FIELDS.filter(({ feature }) => missing.has(feature));
}
