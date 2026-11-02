export type RiskLevel = "Low" | "Medium" | "High";

export type PatientInput = {
  age: number;
  height_cm: number;
  weight_kg: number;
  bp: number;
  glucose: number | null;
  high_chol: boolean;
  chol_check: boolean;
  smoker: boolean;
  stroke: boolean;
  heart_disease_or_attack: boolean;
  phys_activity: boolean;
  fruits: boolean;
  veggies: boolean;
  heavy_alcohol_consump: boolean;
  any_healthcare: boolean;
  no_doc_bc_cost: boolean;
  general_health: number;
  mental_health_days: number;
  physical_health_days: number;
  diff_walk: boolean;
  sex: "female" | "male";
  education: number;
  income: number;
};

export type PreparedPatient = {
  age: number;
  height_cm: number | null;
  weight_kg: number | null;
  bmi: number;
  bp: number;
  glucose: number;
  glucose_measured: boolean;
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

export type RetrievedContext = {
  title: string;
  text: string;
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

export type MemoryRecord = {
  id: string;
  summary: string;
  metadata: SimilarCase["metadata"];
};

export type HistoryResponse = {
  records: MemoryRecord[];
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
  explanation: string;
  recommendation: string;
  model?: ModelMetadata;
};
