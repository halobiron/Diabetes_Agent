"""Editable patient inputs, including migration of previously stored prepared profiles."""

from secrets import choice

ID_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def generate_patient_id():
    return "HS-" + "".join(choice(ID_ALPHABET) for _ in range(10))


BINARY_FIELDS = {
    "high_chol": "HighChol", "chol_check": "CholCheck", "smoker": "Smoker",
    "stroke": "Stroke", "heart_disease_or_attack": "HeartDiseaseorAttack",
    "phys_activity": "PhysActivity", "fruits": "Fruits", "veggies": "Veggies",
    "heavy_alcohol_consump": "HvyAlcoholConsump", "any_healthcare": "AnyHealthcare",
    "no_doc_bc_cost": "NoDocbcCost", "diff_walk": "DiffWalk",
}
OPTIONAL_FIELDS = {
    "general_health": ("GenHlth", "gen_hlth"),
    "mental_health_days": ("MentHlth", "ment_hlth"),
    "physical_health_days": ("PhysHlth", "phys_hlth"),
    "education": ("Education", "education"), "income": ("Income", "income"),
}


def editable_inputs(patient):
    """Return only request fields. Imputed model defaults must remain unknown in the form."""
    unknown = set(patient.get("defaulted_fields", []))
    result = {key: patient.get(key) for key in ("age", "height_cm", "weight_kg", "bmi", "bp")}
    for key, feature in BINARY_FIELDS.items():
        value = patient.get(key, patient.get(feature))
        result[key] = None if feature in unknown or value is None else value in (True, 1, "1", "true")
    for key, (feature, alias) in OPTIONAL_FIELDS.items():
        result[key] = None if feature in unknown else patient.get(key, patient.get(alias))
    sex = patient.get("sex", patient.get("Sex"))
    result["sex"] = (
        None if "Sex" in unknown or sex is None
        else "male" if sex in (1, "1", "male", "M", "m") else "female"
    )
    result["skipped_fields"] = list(patient.get("skipped_fields") or [])
    if patient.get("symptoms") is not None:
        result["symptoms"] = dict(patient["symptoms"])
        result["screening_mode"] = patient.get("screening_mode", "lifestyle")
    return result
