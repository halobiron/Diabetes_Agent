export const ASKABLE_FIELDS = [
  "high_chol",
  "smoker",
  "stroke",
  "heart_disease_or_attack",
  "phys_activity",
  "fruits",
  "veggies",
  "heavy_alcohol_consump",
  "diff_walk",
] as const;
export type AskableField = (typeof ASKABLE_FIELDS)[number];

export type RiskLevel = "Low" | "Medium" | "High";

export type PatientInput = {
  age: number;
  height_cm: number;
  weight_kg: number;
  bp: number;
  glucose: number | null;
  glucose_context?: "unspecified" | "fasting" | "random" | "after_meal" | "unknown";
  glucose_unavailable?: boolean;
  high_chol: boolean | null;
  chol_check: boolean;
  smoker: boolean | null;
  stroke: boolean | null;
  heart_disease_or_attack: boolean | null;
  phys_activity: boolean | null;
  fruits: boolean | null;
  veggies: boolean | null;
  heavy_alcohol_consump: boolean | null;
  any_healthcare: boolean;
  no_doc_bc_cost: boolean;
  general_health: number;
  mental_health_days: number;
  physical_health_days: number;
  diff_walk: boolean | null;
  sex: "female" | "male";
  education: number;
  income: number;
  skipped_fields?: string[];
};

export type PreparedPatient = {
  age: number;
  height_cm: number | null;
  weight_kg: number | null;
  bmi: number;
  bp: number;
  glucose: number;
  glucose_measured: boolean;
  glucose_context?: PatientInput["glucose_context"];
  glucose_unavailable?: boolean;
  high_bp?: number;
  age_bucket?: number;
  sex?: number;
};

export type FeatureImpact = {
  feature: string;
  value: number;
  impact: number;
  direction: string;
  magnitude: number;
  defaulted?: boolean;
};

export type FeatureExplanation = {
  method: string;
  method_note?: string;
  features: FeatureImpact[];
  inputs_not_in_model?: string[];
};

export type RuleResult = {
  code: string;
  name: string;
  category: "measurement" | "prediction" | "data_quality" | "conflict";
  priority: number;
  escalation: SafetyResult["escalation"] | null;
  message: string;
  basis: string;
  resolution?: string;
};

export type SupportPolicyResult = {
  next_step:
    | "request_glucose"
    | "retrieve_more_evidence"
    | "recommend_routine"
    | "recommend_followup"
    | "escalate_to_clinician";
  overridden_by_rules: boolean;
  steps: { action: string; state: number[]; source: string; evidence_status_after?: string }[];
  q_values: Record<string, number> | null;
  version: string | null;
  feedback: string;
};

export type SafetyResult = {
  alerts: string[];
  rules: RuleResult[];
  conflicts: RuleResult[];
  effective_risk: "Low" | "Medium" | "High";
  escalation: "routine_followup" | "prompt_clinician_followup" | "urgent_clinician_review";
  confidence_score: number;
  confidence_label: "Low" | "Medium" | "High";
  confidence_note?: string;
  defaulted_fields?: string[];
  disclaimers: string[];
};

export type Citation = {
  evidence_id: string;
  text: string;
  source_title: string;
  publisher?: string | null;
  year?: number | null;
  url?: string | null;
};

export type RetrievedContext = Citation & {
  title: string;
  relevance: number;
  via: "semantic" | "graph+semantic";
  supports: string[];
  factors: string[];
};

export type EvidenceTrailItem = {
  feature: string;
  value: number | null;
  impact: number;
  evidence: (Citation & { relevance: number; supports: string[] })[];
};

export type TraceStep = {
  component: string;
  status: "ok" | "degraded";
  ms: number;
  detail: string;
};

export type AgentTrace = {
  steps: TraceStep[];
  total_ms: number;
  evidence_count: number;
  evidence_status: "none" | "limited" | "sufficient";
  disagreement: {
    model_risk: RiskLevel;
    effective_risk: RiskLevel;
    rules: { code: string; message: string }[];
    conflicts: string[];
  } | null;
};

export type WhatIfScenario = {
  key: string;
  label: string;
  probability_after: number;
  change: number;
  risk_after: RiskLevel;
  evidence: Citation[];
};

export type WhatIfResult = {
  probability_before: number;
  scenarios: WhatIfScenario[];
  combined: WhatIfScenario | null;
};

export type SimilarCase = {
  metadata: {
    timestamp?: string;
    risk?: RiskLevel;
    probability?: number;
    age?: number;
    bmi?: number;
    bp?: number;
    glucose?: number;
    outcome_confirmed?: boolean;
  };
  distance: number;
};

export type EvalMetrics = {
  roc_auc?: number;
  average_precision?: number;
  brier_score?: number;
  f1?: number;
  selected_threshold?: number;
  [key: string]: unknown;
};

export type ModelMetrics = {
  cv?: { roc_auc_mean?: number; roc_auc_std?: number };
  tuning?: { best_params?: Record<string, unknown>; cv_roc_auc?: number };
  validation?: EvalMetrics;
  test?: EvalMetrics;
};

export type ModelMetadata = {
  selected_model?: string;
  rows_total?: number;
  calibration?: string;
  dataset_slug?: string;
  selection_method?: string;
  metrics?: Record<string, ModelMetrics>;
};

export type PredictionResult = {
  request_id?: string;
  probability: number;
  risk: RiskLevel;
  patient: PreparedPatient;
  feature_explanation: FeatureExplanation;
  retrieved_context: RetrievedContext[];
  similar_cases: SimilarCase[];
  safety: SafetyResult;
  policy?: SupportPolicyResult | null;
  evidence_trail?: EvidenceTrailItem[];
  what_if?: WhatIfResult | null;
  trace?: AgentTrace;
  degraded?: { component: string; error: string }[];
  explanation: string;
  recommendation: string;
  model?: ModelMetadata;
  measurement_scales?: MeasurementScale[];
  followup?: FollowupQuestion | null;
};

export type MeasurementBand = {
  min: number | null;
  max: number | null;
  label: string;
  tone: "neutral" | "success" | "warning" | "danger";
};

export type MeasurementScale = {
  key: string;
  title: string;
  unit: string;
  value: number | null;
  display_min: number;
  display_max: number;
  bands: MeasurementBand[];
  status: string;
  tone: MeasurementBand["tone"];
  note: string;
  sources: { title: string; url: string }[];
};

export type FollowupQuestion = {
  id: string;
  kind: "glucose" | "risk_factor";
  source: "policy" | "data_quality" | "model_sensitivity";
  /** Request field a risk_factor question fills in. */
  field?: AskableField;
  question: string;
  reason: string;
  model_note: string;
};
