DEFAULT_LOW_MAX = 0.4
DEFAULT_HIGH_MIN = 0.7


def classify_risk(prob, bands=None):
    """Map a probability to Low/Medium/High.

    bands comes from the trained artifact (risk_bands: low_max is the binary
    threshold chosen on validation); without it the legacy 0.4/0.7 cut points apply.
    """
    bands = bands or {}
    low_max = bands.get("low_max") or DEFAULT_LOW_MAX
    high_min = bands.get("high_min") or DEFAULT_HIGH_MIN
    if prob >= high_min:
        return "High"
    if prob >= low_max:
        return "Medium"
    return "Low"
