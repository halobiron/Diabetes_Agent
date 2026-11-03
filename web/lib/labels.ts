export const FEATURE_LABELS: Record<string, string> = {
  HighBP: "Tăng huyết áp",
  HighChol: "Cholesterol cao",
  CholCheck: "Đã kiểm tra cholesterol",
  BMI: "BMI",
  Smoker: "Hút thuốc",
  Stroke: "Tiền sử đột quỵ",
  HeartDiseaseorAttack: "Tiền sử bệnh tim",
  PhysActivity: "Vận động thể chất",
  Fruits: "Ăn trái cây",
  Veggies: "Ăn rau",
  HvyAlcoholConsump: "Uống nhiều rượu bia",
  AnyHealthcare: "Tiếp cận dịch vụ y tế",
  NoDocbcCost: "Rào cản chi phí",
  GenHlth: "Sức khỏe tổng quát",
  MentHlth: "Số ngày tinh thần kém",
  PhysHlth: "Số ngày thể chất kém",
  DiffWalk: "Khó khăn khi đi lại",
  Sex: "Giới tính",
  Age: "Nhóm tuổi",
  Education: "Trình độ học vấn",
  Income: "Mức thu nhập",
  age: "Tuổi",
  bmi: "BMI",
  bp: "Huyết áp",
  glucose: "Đường huyết",
};

export const BINARY_FEATURES = new Set([
  "HighBP",
  "HighChol",
  "CholCheck",
  "Smoker",
  "Stroke",
  "HeartDiseaseorAttack",
  "PhysActivity",
  "Fruits",
  "Veggies",
  "HvyAlcoholConsump",
  "AnyHealthcare",
  "NoDocbcCost",
  "DiffWalk",
]);

export const ESCALATION_LABELS: Record<string, string> = {
  routine_followup: "Theo dõi định kỳ",
  prompt_clinician_followup: "Sớm khám bác sĩ",
  urgent_clinician_review: "Khám bác sĩ khẩn cấp",
};

export const RISK_COLORS: Record<string, string> = {
  Low: "#2f9b6a",
  Medium: "#d49a35",
  High: "#d05245",
};

export const RISK_LABELS: Record<string, string> = {
  Low: "Thấp", Medium: "Trung bình", High: "Cao", Unknown: "Chưa rõ",
};

export const METHOD_LABELS: Record<string, string> = {
  shap: "SHAP", sensitivity: "Phân tích độ nhạy", none: "Chưa có",
};

export const ESCALATION_COLORS: Record<string, string> = {
  routine_followup: "#2f9b6a",
  prompt_clinician_followup: "#d49a35",
  urgent_clinician_review: "#d05245",
};

const GENERAL_HEALTH_LABELS: Record<number, string> = {
  1: "Rất tốt",
  2: "Tốt",
  3: "Khá",
  4: "Trung bình",
  5: "Kém",
};

export function featureLabel(feature: string) {
  return FEATURE_LABELS[feature] ?? feature;
}

export function formatFeatureValue(feature: string, value: number) {
  if (BINARY_FEATURES.has(feature)) {
    return Math.round(value) === 1 ? "Có" : "Không";
  }
  if (feature === "Sex") {
    return Math.round(value) === 1 ? "Nam" : "Nữ";
  }
  if (feature === "GenHlth") {
    return GENERAL_HEALTH_LABELS[Math.round(value)] ?? String(value);
  }
  if (feature === "BMI") {
    return value.toFixed(1);
  }
  if (["Age", "Education", "Income", "MentHlth", "PhysHlth"].includes(feature)) {
    return String(Math.round(value));
  }
  return value.toFixed(2);
}

export function formatModelName(modelName?: string) {
  if (!modelName) return "Chưa rõ";
  return modelName
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
