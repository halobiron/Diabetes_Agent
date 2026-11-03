import type { RiskLevel } from "@/types/healthcare";

export function calculateBmi(heightCm: number, weightKg: number) {
  const heightM = heightCm / 100;
  if (heightM <= 0) return 0;
  return weightKg / (heightM * heightM);
}

export function formatMemoryTimestamp(value: string | undefined, fallback: string) {
  if (!value) return fallback;

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return fallback;

  return new Intl.DateTimeFormat("vi-VN", {
    timeZone: "Asia/Ho_Chi_Minh",
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

export function riskDistribution(rows: Array<{ risk: string }>) {
  const counts: Record<RiskLevel, number> = { Low: 0, Medium: 0, High: 0 };
  rows.forEach((row) => {
    if (row.risk === "Low" || row.risk === "Medium" || row.risk === "High") {
      counts[row.risk] += 1;
    }
  });
  return Object.entries(counts).map(([risk, count]) => ({ risk: risk as RiskLevel, count }));
}
