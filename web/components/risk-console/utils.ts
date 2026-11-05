export function calculateBmi(heightCm: number, weightKg: number) {
  const heightM = heightCm / 100;
  if (heightM <= 0) return 0;
  return weightKg / (heightM * heightM);
}

