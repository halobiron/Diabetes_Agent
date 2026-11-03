from pathlib import Path

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression

# BRFSS HighBP is a self-reported diagnosis, not a reading. A systolic value
# >= 130 mmHg (ACC/AHA stage 1) is used as a proxy when only bp is given.
HIGH_BP_SYSTOLIC_CUTOFF = 130


class RiskModel:
    LEGACY_FEATURE_NAMES = ["age", "bmi", "bp", "glucose"]
    BRFSS_FEATURE_NAMES = [
        "HighBP",
        "HighChol",
        "CholCheck",
        "BMI",
        "Smoker",
        "Stroke",
        "HeartDiseaseorAttack",
        "PhysActivity",
        "Fruits",
        "Veggies",
        "HvyAlcoholConsump",
        "AnyHealthcare",
        "NoDocbcCost",
        "GenHlth",
        "MentHlth",
        "PhysHlth",
        "DiffWalk",
        "Sex",
        "Age",
        "Education",
        "Income",
    ]
    FEATURE_NAMES = LEGACY_FEATURE_NAMES
    INPUT_NAMES = ["age", "height_cm", "weight_kg", "bp", "glucose"]
    BINARY_FIELDS = {
        "high_chol": "HighChol",
        "chol_check": "CholCheck",
        "smoker": "Smoker",
        "stroke": "Stroke",
        "heart_disease_or_attack": "HeartDiseaseorAttack",
        "phys_activity": "PhysActivity",
        "fruits": "Fruits",
        "veggies": "Veggies",
        "heavy_alcohol_consump": "HvyAlcoholConsump",
        "any_healthcare": "AnyHealthcare",
        "no_doc_bc_cost": "NoDocbcCost",
        "diff_walk": "DiffWalk",
    }
    # Request input -> model feature(s) that consume it; (feature, years or units per step).
    INPUT_FEATURES = {
        "age": (("age", 1.0), ("Age", 5.0)),  # Age is a 5-year BRFSS bucket
        "bmi": (("bmi", 1.0), ("BMI", 1.0)),
        "bp": (("bp", 1.0), ("HighBP", None)),
        "glucose": (("glucose", 1.0),),
    }
    # Optional model inputs outside BINARY_FIELDS: feature name -> accepted request keys.
    OPTIONAL_FIELD_KEYS = {
        "GenHlth": ("gen_hlth", "general_health", "GenHlth"),
        "MentHlth": ("ment_hlth", "mental_health_days", "MentHlth"),
        "PhysHlth": ("phys_hlth", "physical_health_days", "PhysHlth"),
        "Education": ("education", "Education"),
        "Income": ("income", "Income"),
        "Sex": ("sex", "Sex"),
    }

    def __init__(self):
        self.model = LogisticRegression(max_iter=1000)
        self.feature_names = list(self.LEGACY_FEATURE_NAMES)
        self.is_trained = False
        self.default_glucose = None
        self.default_values = {}
        self.training_frame = None
        self.artifact_metadata = {}

    @staticmethod
    def calculate_bmi(height_cm, weight_kg):
        height_m = height_cm / 100
        if height_m <= 0:
            raise ValueError("Height must be greater than 0.")
        return weight_kg / (height_m**2)

    def train(self, df):
        df = df.copy()
        if "bmi" not in df.columns:
            df["bmi"] = df.apply(
                lambda row: self.calculate_bmi(row["height_cm"], row["weight_kg"]), axis=1
            )

        self.default_glucose = float(df["glucose"].median())
        self.feature_names = list(self.LEGACY_FEATURE_NAMES)
        X = df[self.feature_names]
        y = df["target"]
        self.model.fit(X, y)
        self.default_values = X.median(numeric_only=True).to_dict()
        self.training_frame = X.copy()
        self.is_trained = True

    def train_from_csv(self, path):
        df = pd.read_csv(path)
        self.train(df)

    def load_artifact(self, path):
        artifact_path = Path(path)
        artifact = joblib.load(artifact_path)

        self.model = artifact["model"]
        self.feature_names = list(artifact.get("feature_names", self.LEGACY_FEATURE_NAMES))
        self.default_values = {
            key: float(value) for key, value in artifact.get("default_values", {}).items()
        }
        self.default_glucose = artifact.get("default_glucose", self.default_values.get("glucose"))
        self.artifact_metadata = artifact.get("metadata", {})

        training_frame = artifact.get("training_frame")
        if training_frame is not None:
            self.training_frame = pd.DataFrame(training_frame)[self.feature_names].copy()
        else:
            self.training_frame = pd.DataFrame([self.default_values], columns=self.feature_names)

        self.is_trained = True
        return self

    def assess(self, patient_data):
        if not self.is_trained:
            raise RuntimeError("RiskModel must be trained before prediction.")

        patient = self.prepare_patient(patient_data)
        row = self.feature_frame(patient)

        prob = self.model.predict_proba(row)[0][1]
        return float(prob), patient

    @property
    def risk_bands(self):
        return self.artifact_metadata.get("risk_bands")

    @property
    def decision_threshold(self):
        return self.artifact_metadata.get("selected_threshold")

    @property
    def model_version(self):
        return self.artifact_metadata.get("model_version", "legacy-unversioned")

    def predict(self, patient_data):
        prob, _patient = self.assess(patient_data)
        return prob

    def prepare_patient(self, patient_data):
        if isinstance(patient_data, dict):
            patient = patient_data.copy()
        else:
            patient = dict(zip(self.INPUT_NAMES, patient_data))

        has_height_weight = (
            patient.get("height_cm") is not None and patient.get("weight_kg") is not None
        )
        has_bmi = patient.get("bmi") is not None
        required_fields = []
        if self._get(patient, "age", "Age") is None:
            required_fields.append("age")
        if self._uses_feature("bp") and self._get(patient, "bp", "blood_pressure") is None:
            required_fields.append("bp")
        if (
            self._uses_feature("HighBP")
            and self._get(patient, "bp", "blood_pressure", "HighBP", "high_bp") is None
        ):
            required_fields.append("bp or high_bp")
        missing = required_fields.copy()
        if not has_height_weight and not has_bmi:
            missing.append("height_cm and weight_kg or bmi")
        if missing:
            raise ValueError(f"Missing required patient fields: {', '.join(missing)}")

        glucose_measured = patient.get("glucose") is not None
        glucose = float(patient["glucose"]) if glucose_measured else self.default_glucose
        if glucose is None:
            glucose = 0.0
        bmi = (
            self.calculate_bmi(float(patient["height_cm"]), float(patient["weight_kg"]))
            if has_height_weight
            else float(patient["bmi"])
        )
        age = self._get(patient, "age")
        age_bucket = self._get(patient, "Age", "age_bucket")
        if age is None and age_bucket is not None:
            age = self._age_from_brfss_bucket(age_bucket)
        if age_bucket is None and age is not None:
            age_bucket = self._age_to_brfss_bucket(age)

        bp = self._get(patient, "bp", "blood_pressure")
        high_bp = self._get(patient, "high_bp", "HighBP")
        if high_bp is None and bp is not None:
            high_bp = 1 if float(bp) >= HIGH_BP_SYSTOLIC_CUTOFF else 0

        sex = self._coerce_sex(self._get(patient, "sex", "Sex"), self._default_for("Sex"))

        prepared = {
            "age": int(age),
            "height_cm": (
                float(patient["height_cm"]) if patient.get("height_cm") is not None else None
            ),
            "weight_kg": (
                float(patient["weight_kg"]) if patient.get("weight_kg") is not None else None
            ),
            "bmi": round(bmi, 1),
            "bp": int(bp) if bp is not None else int(self._default_for("bp", 0)),
            "glucose": glucose,
            "glucose_measured": glucose_measured,
            "glucose_context": patient.get("glucose_context", "unspecified")
            if glucose_measured
            else "unspecified",
            "glucose_unavailable": bool(patient.get("glucose_unavailable", False))
            and not glucose_measured,
            "high_bp": self._coerce_binary(high_bp, self._default_for("HighBP")),
            "age_bucket": int(age_bucket),
            "sex": sex,
        }
        prepared.update(self._prepare_brfss_fields(patient))
        prepared["defaulted_fields"] = self._defaulted_features(patient)
        prepared["optional_field_count"] = len(self._optional_features())
        return prepared

    def _optional_features(self):
        names = list(self.BINARY_FIELDS.values()) + list(self.OPTIONAL_FIELD_KEYS)
        return [name for name in names if self._uses_feature(name)]

    def inputs_not_in_model(self, patient):
        """Measured request inputs that no model feature consumes (glucose for the BRFSS model)."""
        unused = []
        for name, consumers in self.INPUT_FEATURES.items():
            measured = patient.get(f"{name}_measured", patient.get(name) is not None)
            if measured and not any(self._uses_feature(feature) for feature, _ in consumers):
                unused.append(name)
        return unused

    def input_spreads(self):
        """Standard deviation of age (years), BMI and other continuous inputs in the training data.

        Inputs the model was not trained on (e.g. blood pressure in mmHg, glucose) are absent.
        """
        spreads = {}
        if self.training_frame is None:
            return spreads
        for name, consumers in self.INPUT_FEATURES.items():
            for feature, step in consumers:
                if step is not None and feature in self.training_frame:
                    spread = float(self.training_frame[feature].std()) * step
                    if spread > 0:
                        spreads[name] = spread
                    break
        return spreads

    def _defaulted_features(self, patient):
        """Model inputs the caller left out, so the model saw a default instead of a real value."""
        accepted = {
            feature: (snake_name, feature) for snake_name, feature in self.BINARY_FIELDS.items()
        }
        accepted.update(self.OPTIONAL_FIELD_KEYS)
        return [
            feature
            for feature, keys in accepted.items()
            if self._uses_feature(feature) and self._get(patient, *keys) is None
        ]

    def feature_frame(self, patient):
        row = {feature: self._feature_value(feature, patient) for feature in self.feature_names}
        return pd.DataFrame([row], columns=self.feature_names)

    def _feature_value(self, feature, patient):
        if feature == "age":
            return patient["age"]
        if feature == "bmi":
            return patient["bmi"]
        if feature == "bp":
            return patient["bp"]
        if feature == "glucose":
            return patient["glucose"]
        if feature == "HighBP":
            return patient["high_bp"]
        if feature == "BMI":
            return patient["bmi"]
        if feature == "Age":
            return patient["age_bucket"]
        if feature == "Sex":
            return patient["sex"]

        snake_name = self._snake_case(feature)
        return patient.get(snake_name, self._default_for(feature))

    def _prepare_brfss_fields(self, patient):
        prepared = {}
        for snake_name, feature_name in self.BINARY_FIELDS.items():
            prepared[snake_name] = self._coerce_binary(
                self._get(patient, snake_name, feature_name),
                self._default_for(feature_name),
            )

        prepared["gen_hlth"] = int(
            self._bounded_number(
                self._get(patient, "gen_hlth", "general_health", "GenHlth"), "GenHlth", 1, 5
            )
        )
        prepared["ment_hlth"] = int(
            self._bounded_number(
                self._get(patient, "ment_hlth", "mental_health_days", "MentHlth"), "MentHlth", 0, 30
            )
        )
        prepared["phys_hlth"] = int(
            self._bounded_number(
                self._get(patient, "phys_hlth", "physical_health_days", "PhysHlth"),
                "PhysHlth",
                0,
                30,
            )
        )
        prepared["education"] = int(
            self._bounded_number(self._get(patient, "education", "Education"), "Education", 1, 6)
        )
        prepared["income"] = int(
            self._bounded_number(self._get(patient, "income", "Income"), "Income", 1, 8)
        )
        return prepared

    def _uses_feature(self, feature_name):
        return feature_name in self.feature_names

    def _default_for(self, feature_name, fallback=0):
        return self.default_values.get(feature_name, fallback)

    @staticmethod
    def _get(patient, *names):
        for name in names:
            if name in patient and patient[name] is not None:
                return patient[name]
        return None

    @staticmethod
    def _coerce_binary(value, default=0):
        if value is None:
            value = default
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "yes", "y", "1", "positive"}:
                return 1
            if normalized in {"false", "no", "n", "0", "negative"}:
                return 0
        return 1 if int(float(value)) == 1 else 0

    @staticmethod
    def _coerce_sex(value, default=0):
        if value is None:
            value = default
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"male", "m", "1"}:
                return 1
            if normalized in {"female", "f", "0"}:
                return 0
        return 1 if int(float(value)) == 1 else 0

    def _bounded_number(self, value, feature_name, minimum, maximum):
        if value is None:
            value = self._default_for(feature_name, minimum)
        return max(minimum, min(maximum, float(value)))

    @staticmethod
    def _age_to_brfss_bucket(age):
        age = int(age)
        if age < 25:
            return 1
        if age < 30:
            return 2
        if age < 35:
            return 3
        if age < 40:
            return 4
        if age < 45:
            return 5
        if age < 50:
            return 6
        if age < 55:
            return 7
        if age < 60:
            return 8
        if age < 65:
            return 9
        if age < 70:
            return 10
        if age < 75:
            return 11
        if age < 80:
            return 12
        return 13

    @staticmethod
    def _age_from_brfss_bucket(bucket):
        bucket_midpoints = {
            1: 21,
            2: 27,
            3: 32,
            4: 37,
            5: 42,
            6: 47,
            7: 52,
            8: 57,
            9: 62,
            10: 67,
            11: 72,
            12: 77,
            13: 82,
        }
        return bucket_midpoints.get(int(bucket), 45)

    @staticmethod
    def _snake_case(feature_name):
        mapping = {
            "HighChol": "high_chol",
            "CholCheck": "chol_check",
            "Smoker": "smoker",
            "Stroke": "stroke",
            "HeartDiseaseorAttack": "heart_disease_or_attack",
            "PhysActivity": "phys_activity",
            "Fruits": "fruits",
            "Veggies": "veggies",
            "HvyAlcoholConsump": "heavy_alcohol_consump",
            "AnyHealthcare": "any_healthcare",
            "NoDocbcCost": "no_doc_bc_cost",
            "GenHlth": "gen_hlth",
            "MentHlth": "ment_hlth",
            "PhysHlth": "phys_hlth",
            "DiffWalk": "diff_walk",
            "Education": "education",
            "Income": "income",
        }
        return mapping.get(feature_name, feature_name)
