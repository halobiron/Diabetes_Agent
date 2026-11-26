import type { PatientInput } from "@/types/healthcare";

export const SYMPTOM_QUESTIONS = [
  ["polyuria", "Đi tiểu nhiều"],
  ["polydipsia", "Khát nước nhiều"],
  ["sudden_weight_loss", "Sụt cân đột ngột"],
  ["weakness", "Mệt hoặc yếu sức"],
  ["polyphagia", "Ăn nhiều hoặc hay đói"],
  ["genital_thrush", "Nấm sinh dục (nếu bạn biết)"],
  ["visual_blurring", "Nhìn mờ"],
  ["itching", "Ngứa"],
  ["irritability", "Dễ cáu gắt"],
  ["delayed_healing", "Vết thương lâu lành"],
  ["partial_paresis", "Yếu hoặc liệt một phần cơ thể"],
  ["muscle_stiffness", "Cứng cơ"],
  ["alopecia", "Rụng tóc"],
  ["obesity", "Béo phì (theo thông tin bạn biết)"],
] as const;

export type SymptomKey = typeof SYMPTOM_QUESTIONS[number][0];
export type SymptomInput = Record<SymptomKey, boolean | null>;
export const EMPTY_SYMPTOMS = Object.fromEntries(SYMPTOM_QUESTIONS.map(([key]) => [key, null])) as SymptomInput;

export function symptomInputError(form: PatientInput): string | null {
  if (form.screening_mode !== "symptoms") return null;
  if (form.age < 16 || form.age > 90) return "Mô hình triệu chứng chỉ được khảo sát với tuổi 16–90. Bạn có thể chọn hồ sơ lối sống.";
  if (!form.sex) return "Cần chọn giới tính ở phần Số đo cơ thể để dùng mô hình triệu chứng.";
  const remaining = SYMPTOM_QUESTIONS.filter(([key]) => typeof form.symptoms?.[key] !== "boolean").length;
  return remaining ? `Còn ${remaining}/14 mục triệu chứng chưa có câu trả lời Có/Không. Bạn có thể bổ sung hoặc chọn hồ sơ lối sống.` : null;
}
