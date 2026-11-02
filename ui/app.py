import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main import agent
from models.risk_model import RiskModel

st.set_page_config(
    page_title="Healthcare AI Risk Console",
    page_icon=":hospital:",
    layout="wide",
)


FEATURE_LABELS = {
    "HighBP": "High blood pressure",
    "HighChol": "High cholesterol",
    "CholCheck": "Cholesterol checked (5y)",
    "BMI": "BMI",
    "Smoker": "Smoker",
    "Stroke": "Stroke history",
    "HeartDiseaseorAttack": "Heart disease history",
    "PhysActivity": "Physical activity",
    "Fruits": "Eats fruit",
    "Veggies": "Eats vegetables",
    "HvyAlcoholConsump": "Heavy alcohol consumption",
    "AnyHealthcare": "Has healthcare coverage",
    "NoDocbcCost": "Skipped doctor (cost)",
    "GenHlth": "General health",
    "MentHlth": "Mental health days",
    "PhysHlth": "Physical health days",
    "DiffWalk": "Difficulty walking",
    "Sex": "Sex",
    "Age": "Age band",
    "Education": "Education level",
    "Income": "Income level",
    "age": "Age",
    "bmi": "BMI",
    "bp": "Blood pressure",
    "glucose": "Glucose",
}

BINARY_FEATURES = {
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
}

GENHLTH_LABELS = {1: "Excellent", 2: "Very good", 3: "Good", 4: "Fair", 5: "Poor"}

ESCALATION_LABELS = {
    "routine_followup": "Routine follow-up",
    "prompt_clinician_followup": "Prompt clinician follow-up",
    "urgent_clinician_review": "Urgent clinician review",
}

ESCALATION_COLORS = {
    "routine_followup": "#3b8c5a",
    "prompt_clinician_followup": "#c98f1f",
    "urgent_clinician_review": "#c4423a",
}

RISK_COLORS = {"Low": "#3b8c5a", "Medium": "#c98f1f", "High": "#c4423a"}


def label_for(feature_name):
    return FEATURE_LABELS.get(feature_name, feature_name)


def format_feature_value(feature_name, value):
    if feature_name in BINARY_FEATURES:
        return "Yes" if int(round(value)) == 1 else "No"
    if feature_name == "Sex":
        return "Male" if int(round(value)) == 1 else "Female"
    if feature_name == "GenHlth":
        return GENHLTH_LABELS.get(int(round(value)), str(value))
    if feature_name == "BMI":
        return f"{value:.1f}"
    if feature_name in {"Age", "Education", "Income", "MentHlth", "PhysHlth"}:
        return str(int(round(value)))
    return f"{value:.2f}"


st.markdown(
    """
    <style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    div[data-testid="stMetric"] { background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.06); border-radius: 10px;
        padding: 14px 16px; }
    div[data-testid="stMetricValue"] { font-size: 1.45rem; }
    .hc-card { background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.06); border-radius: 10px;
        padding: 14px 18px; margin-bottom: 8px; }
    .hc-pill { display: inline-block; padding: 6px 12px; border-radius: 999px;
        font-weight: 600; font-size: 0.85rem; letter-spacing: 0.02em; }
    .hc-label { font-size: 0.78rem; text-transform: uppercase;
        letter-spacing: 0.06em; opacity: 0.7; margin-bottom: 4px; }
    .hc-value { font-size: 1.05rem; font-weight: 600; }
    .hc-disclaimer { font-size: 0.78rem; opacity: 0.7; }
    .hc-model-row { display: flex; gap: 18px; flex-wrap: wrap; }
    .hc-model-item { min-width: 120px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Healthcare AI Risk Console")
st.caption(
    "Educational prototype only — not medical advice. "
    "Always consult a qualified clinician for diagnosis and treatment decisions."
)

with st.sidebar:
    st.header("Patient input")

    with st.expander("Vitals", expanded=True):
        age = st.number_input("Age", min_value=0, max_value=120, value=45)
        sex = st.selectbox("Sex", ["female", "male"], index=0)
        c1, c2 = st.columns(2)
        height_cm = c1.number_input(
            "Height (cm)", min_value=50.0, max_value=250.0, value=170.0, step=0.5
        )
        weight_kg = c2.number_input(
            "Weight (kg)", min_value=2.0, max_value=300.0, value=82.4, step=0.1
        )
        bp = st.number_input("Blood pressure (systolic)", min_value=0, max_value=260, value=130)
        has_glucose = st.checkbox("Glucose value available", value=True)
        glucose = (
            st.number_input("Glucose (mg/dL)", min_value=0, max_value=500, value=180)
            if has_glucose
            else None
        )

    with st.expander("Health profile", expanded=False):
        c1, c2 = st.columns(2)
        high_chol = c1.checkbox("High cholesterol", value=False)
        chol_check = c2.checkbox("Cholesterol checked (5y)", value=True)
        smoker = c1.checkbox("Smoker", value=False)
        stroke = c2.checkbox("Stroke history", value=False)
        heart_disease_or_attack = c1.checkbox("Heart disease history", value=False)
        diff_walk = c2.checkbox("Difficulty walking", value=False)
        general_health = st.slider("General health (1=excellent, 5=poor)", 1, 5, 3)
        mental_health_days = st.slider("Poor mental-health days (last 30)", 0, 30, 2)
        physical_health_days = st.slider("Poor physical-health days (last 30)", 0, 30, 2)

    with st.expander("Lifestyle and access", expanded=False):
        c1, c2 = st.columns(2)
        phys_activity = c1.checkbox("Physical activity", value=True)
        heavy_alcohol_consump = c2.checkbox("Heavy alcohol use", value=False)
        fruits = c1.checkbox("Fruit most days", value=True)
        veggies = c2.checkbox("Vegetables most days", value=True)
        any_healthcare = c1.checkbox("Healthcare coverage", value=True)
        no_doc_bc_cost = c2.checkbox("Skipped doctor (cost)", value=False)
        education = st.slider("Education level (1–6)", 1, 6, 5)
        income = st.slider("Income level (1–8)", 1, 8, 5)

    analyze = st.button("Analyze patient", type="primary", use_container_width=True)

if analyze:
    calculated_bmi = RiskModel.calculate_bmi(height_cm, weight_kg)
    patient_input = {
        "age": age,
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "bmi": round(calculated_bmi, 1),
        "bp": bp,
        "glucose": glucose,
        "high_chol": high_chol,
        "chol_check": chol_check,
        "smoker": smoker,
        "stroke": stroke,
        "heart_disease_or_attack": heart_disease_or_attack,
        "phys_activity": phys_activity,
        "fruits": fruits,
        "veggies": veggies,
        "heavy_alcohol_consump": heavy_alcohol_consump,
        "any_healthcare": any_healthcare,
        "no_doc_bc_cost": no_doc_bc_cost,
        "general_health": general_health,
        "mental_health_days": mental_health_days,
        "physical_health_days": physical_health_days,
        "diff_walk": diff_walk,
        "sex": sex,
        "education": education,
        "income": income,
    }
    st.session_state["last_result"] = agent.run(patient_input)

result = st.session_state.get("last_result")

if not result:
    st.info("Enter patient values in the sidebar and click **Analyze patient**.")
    st.stop()

patient = result["patient"]
safety = result.get("safety", {})
escalation_key = safety.get("escalation", "routine_followup")
escalation_label = ESCALATION_LABELS.get(escalation_key, escalation_key.replace("_", " ").title())
escalation_color = ESCALATION_COLORS.get(escalation_key, "#666")
risk_color = RISK_COLORS.get(result["risk"], "#666")
confidence = safety.get("confidence_label", "Unknown")
confidence_score = safety.get("confidence_score")

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(
        f"""
        <div class="hc-card">
          <div class="hc-label">Risk</div>
          <div style="display:flex;align-items:center;gap:10px;">
            <span class="hc-pill" style="background:{risk_color};color:#fff;">
              {result["risk"]}
            </span>
            <span class="hc-value">{result["probability"]:.1%}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
m2.metric("Probability", f"{result['probability']:.1%}")
m3.metric("BMI", f"{patient['bmi']:.1f}")
confidence_display = (
    f"{confidence} ({confidence_score:.0%})" if confidence_score is not None else confidence
)
m4.metric("Confidence", confidence_display)

st.markdown(
    f"""
    <div class="hc-card" style="display:flex;align-items:center;gap:14px;">
      <span class="hc-label" style="margin:0;">Escalation</span>
      <span class="hc-pill" style="background:{escalation_color};color:#fff;">
        {escalation_label}
      </span>
    </div>
    """,
    unsafe_allow_html=True,
)

if safety.get("alerts"):
    for alert in safety["alerts"]:
        st.warning(alert)

model_meta = result.get("model") or {}
if model_meta:
    selected_name = model_meta.get("selected_model", "—")
    metrics_block = (model_meta.get("metrics") or {}).get(selected_name, {})
    roc_auc = (metrics_block.get("test") or {}).get("roc_auc")
    rows_total = model_meta.get("rows_total")
    calibration = model_meta.get("calibration") or "—"
    dataset_slug = model_meta.get("dataset_slug") or "—"
    items = [
        ("Selected model", selected_name.replace("_", " ")),
        ("Dataset rows", f"{rows_total:,}" if isinstance(rows_total, int) else "—"),
        ("Holdout ROC AUC", f"{roc_auc:.3f}" if isinstance(roc_auc, (int, float)) else "—"),
        ("Calibration", calibration),
        ("Dataset", dataset_slug),
    ]
    item_html = "".join(
        f'<div class="hc-model-item"><div class="hc-label">{label}</div>'
        f'<div class="hc-value">{value}</div></div>'
        for label, value in items
    )
    st.markdown(
        f'<div class="hc-card"><div class="hc-model-row">{item_html}</div></div>',
        unsafe_allow_html=True,
    )

for disclaimer in safety.get("disclaimers", []):
    st.markdown(f'<div class="hc-disclaimer">{disclaimer}</div>', unsafe_allow_html=True)

assessment_tab, evidence_tab, history_tab = st.tabs(["Assessment", "Evidence", "History"])

with assessment_tab:
    left, right = st.columns([1, 1])

    with left:
        st.subheader("Explanation")
        st.write(result["explanation"])

        st.subheader("Recommendation")
        st.write(result["recommendation"])

    with right:
        st.subheader("Top feature impacts")
        features = result["feature_explanation"]["features"]
        if features:
            chart_df = pd.DataFrame(features).copy()
            chart_df["label"] = chart_df["feature"].map(label_for)
            chart_df["direction_clean"] = chart_df["impact"].apply(
                lambda v: "Raises risk" if v > 0 else "Lowers risk"
            )
            chart_df["value_display"] = chart_df.apply(
                lambda row: format_feature_value(row["feature"], row["value"]), axis=1
            )
            top = chart_df.sort_values("magnitude", ascending=False).head(8)

            bar = (
                alt.Chart(top)
                .mark_bar()
                .encode(
                    x=alt.X("impact:Q", title="Impact on risk probability"),
                    y=alt.Y("label:N", sort="-x", title=None),
                    color=alt.Color(
                        "direction_clean:N",
                        scale=alt.Scale(
                            domain=["Raises risk", "Lowers risk"],
                            range=["#c4423a", "#3b8c5a"],
                        ),
                        legend=alt.Legend(title=None, orient="bottom"),
                    ),
                    tooltip=[
                        alt.Tooltip("label:N", title="Feature"),
                        alt.Tooltip("value_display:N", title="Value"),
                        alt.Tooltip("impact:Q", title="Impact", format=".3f"),
                        alt.Tooltip("direction_clean:N", title="Direction"),
                    ],
                )
                .properties(height=320)
                .configure(background="transparent")
                .configure_axis(
                    labelColor="#9aa4b2",
                    titleColor="#9aa4b2",
                    gridColor="rgba(255,255,255,0.08)",
                    domainColor="rgba(255,255,255,0.18)",
                    tickColor="rgba(255,255,255,0.18)",
                )
                .configure_legend(labelColor="#9aa4b2", titleColor="#9aa4b2")
                .configure_view(strokeOpacity=0)
            )
            st.altair_chart(bar, use_container_width=True)

            table_df = top[["label", "value_display", "direction_clean", "impact"]].rename(
                columns={
                    "label": "Feature",
                    "value_display": "Value",
                    "direction_clean": "Direction",
                    "impact": "Impact",
                }
            )
            st.dataframe(
                table_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Impact": st.column_config.NumberColumn(format="%.3f"),
                },
            )
            st.caption(f"Method: {result['feature_explanation'].get('method', '—')}")
        else:
            st.write("No feature explanation available.")

with evidence_tab:
    st.subheader("Retrieved medical context")
    contexts = result.get("retrieved_context") or []
    if contexts:
        for item in contexts:
            with st.expander(
                f"{item['title']} (relevance {item['relevance']:.2f})", expanded=False
            ):
                st.write(item["text"])
                if item.get("supports"):
                    st.caption("Linked in graph to: " + ", ".join(item["supports"]))
                if item.get("url"):
                    st.markdown(f"[{item['source_title']}]({item['url']})")
        if result.get("evidence_status") == "limited":
            st.warning("Supporting evidence is limited for this case.")
    else:
        st.warning("No sufficiently relevant guideline evidence was retrieved for this case.")

    st.subheader("Similar prior cases")
    similar_cases = result.get("similar_cases") or []
    if similar_cases:
        similar_df = pd.DataFrame(
            [
                {
                    "Risk": item["metadata"].get("risk"),
                    "Probability": item["metadata"].get("probability"),
                    "Age": item["metadata"].get("age"),
                    "BMI": item["metadata"].get("bmi"),
                    "BP": item["metadata"].get("bp"),
                    "Glucose": item["metadata"].get("glucose"),
                    "Distance": item["distance"],
                }
                for item in similar_cases
            ]
        )
        st.dataframe(
            similar_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Probability": st.column_config.NumberColumn(format="%.2f"),
                "Distance": st.column_config.NumberColumn(format="%.3f"),
            },
        )
    else:
        st.write("No prior cases stored yet.")

with history_tab:
    history = agent.memory.get_all()
    if not history:
        st.write("No memory records yet.")
    else:
        history_df = pd.DataFrame(
            [
                {
                    "timestamp": item["metadata"].get("timestamp"),
                    "risk": item["metadata"].get("risk"),
                    "probability": item["metadata"].get("probability"),
                    "age": item["metadata"].get("age"),
                    "bmi": item["metadata"].get("bmi"),
                    "bp": item["metadata"].get("bp"),
                    "glucose": item["metadata"].get("glucose"),
                }
                for item in history
            ]
        )
        history_df["timestamp"] = pd.to_datetime(history_df["timestamp"], errors="coerce")
        history_df = history_df.sort_values("timestamp")

        trend_col, dist_col = st.columns(2)

        with trend_col:
            st.subheader("Risk trend")
            trend_df = history_df.dropna(subset=["timestamp", "probability"]).set_index("timestamp")
            if not trend_df.empty:
                st.line_chart(trend_df[["probability"]], use_container_width=True)
            else:
                st.write("Not enough timestamped records.")

        with dist_col:
            st.subheader("Risk level distribution")
            risk_counts = (
                history_df["risk"].value_counts().rename_axis("risk").reset_index(name="count")
            )
            st.bar_chart(risk_counts.set_index("risk"), use_container_width=True)

        st.subheader("Recent assessments")
        display_df = history_df.copy()
        display_df["timestamp"] = display_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
        display_df = display_df.rename(
            columns={
                "timestamp": "Timestamp",
                "risk": "Risk",
                "probability": "Probability",
                "age": "Age",
                "bmi": "BMI",
                "bp": "BP",
                "glucose": "Glucose",
            }
        )
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Probability": st.column_config.NumberColumn(format="%.2f"),
            },
        )
