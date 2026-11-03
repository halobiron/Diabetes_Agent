import type { FeatureImpact, PatientInput } from "@/types/healthcare";

export type TabKey = "assessment";

export type ChartFeature = FeatureImpact & {
  label: string;
  valueLabel: string;
  directionLabel: string;
};

export type PatientFieldChange = <K extends keyof PatientInput>(
  key: K,
  value: PatientInput[K],
) => void;
