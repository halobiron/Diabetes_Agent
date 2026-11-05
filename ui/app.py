import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main import build_agent
from models.risk_model import RiskModel
from tools.vietnamese import (
    ESCALATION_LABELS,
    METHOD_LABELS,
    RISK_LABELS,
)
from tools.vietnamese import (
    FEATURE_LABELS as VI_FEATURE_LABELS,
)

st.set_page_config(
    page_title="Đánh giá nguy cơ sức khỏe bằng AI",
    page_icon=":hospital:",
    layout="wide",
)


FEATURE_LABELS = {key: value[0].upper() + value[1:] for key, value in VI_FEATURE_LABELS.items()}

agent = build_agent()

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

GENHLTH_LABELS = {1: "Rất tốt", 2: "Tốt", 3: "Khá", 4: "Trung bình", 5: "Kém"}


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
        return "Có" if int(round(value)) == 1 else "Không"
    if feature_name == "Sex":
        return "Nam" if int(round(value)) == 1 else "Nữ"
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

st.title("Đánh giá nguy cơ sức khỏe bằng AI")
st.caption(
    "Nguyên mẫu phục vụ học tập — không thay thế tư vấn y tế. "
    "Luôn tham khảo bác sĩ đủ chuyên môn khi quyết định chẩn đoán và điều trị."
)

with st.sidebar:
    st.header("Thông tin bệnh nhân")

    with st.expander("Chỉ số cơ thể", expanded=True):
        age = st.number_input("Tuổi", min_value=0, max_value=120, value=45)
        sex = st.selectbox(
            "Giới tính",
            ["female", "male"],
            index=0,
            format_func=lambda value: {"female": "Nữ", "male": "Nam"}[value],
        )
        c1, c2 = st.columns(2)
        height_cm = c1.number_input(
            "Chiều cao (cm)", min_value=50.0, max_value=250.0, value=170.0, step=0.5
        )
        weight_kg = c2.number_input(
            "Cân nặng (kg)", min_value=2.0, max_value=300.0, value=82.4, step=0.1
        )
        bp = st.number_input("Huyết áp tâm thu", min_value=0, max_value=260, value=130)
        has_glucose = st.checkbox("Có kết quả đường huyết", value=True)
        glucose = (
            st.number_input("Đường huyết (mg/dL)", min_value=0, max_value=500, value=180)
            if has_glucose
            else None
        )

    with st.expander("Tiền sử và sức khỏe", expanded=False):
        c1, c2 = st.columns(2)
        high_chol = c1.checkbox("Cholesterol cao", value=False)
        chol_check = c2.checkbox("Đã kiểm tra cholesterol (5 năm)", value=True)
        smoker = c1.checkbox("Hút thuốc", value=False)
        stroke = c2.checkbox("Tiền sử đột quỵ", value=False)
        heart_disease_or_attack = c1.checkbox("Tiền sử bệnh tim", value=False)
        diff_walk = c2.checkbox("Khó khăn khi đi lại", value=False)
        general_health = st.slider("Sức khỏe tổng quát (1=rất tốt, 5=kém)", 1, 5, 3)
        mental_health_days = st.slider("Số ngày sức khỏe tinh thần kém (30 ngày qua)", 0, 30, 2)
        physical_health_days = st.slider("Số ngày sức khỏe thể chất kém (30 ngày qua)", 0, 30, 2)

    with st.expander("Lối sống và tiếp cận y tế", expanded=False):
        c1, c2 = st.columns(2)
        phys_activity = c1.checkbox("Vận động thể chất", value=True)
        heavy_alcohol_consump = c2.checkbox("Uống nhiều rượu bia", value=False)
        fruits = c1.checkbox("Ăn trái cây hầu hết các ngày", value=True)
        veggies = c2.checkbox("Ăn rau hầu hết các ngày", value=True)
        any_healthcare = c1.checkbox("Tiếp cận dịch vụ y tế", value=True)
        no_doc_bc_cost = c2.checkbox("Bỏ khám vì chi phí", value=False)
        education = st.slider("Trình độ học vấn (1–6)", 1, 6, 5)
        income = st.slider("Mức thu nhập (1–8)", 1, 8, 5)

    analyze = st.button("Phân tích hồ sơ", type="primary", use_container_width=True)

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
    st.info("Nhập thông tin bệnh nhân ở bảng bên trái và chọn **Phân tích hồ sơ**.")
    st.stop()

patient = result["patient"]
safety = result.get("safety", {})
escalation_key = safety.get("escalation", "routine_followup")
escalation_label = ESCALATION_LABELS.get(escalation_key, escalation_key.replace("_", " ").title())
escalation_color = ESCALATION_COLORS.get(escalation_key, "#666")
risk_color = RISK_COLORS.get(result["risk"], "#666")
confidence = RISK_LABELS.get(safety.get("confidence_label"), "Chưa rõ")
confidence_score = safety.get("confidence_score")

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(
        f"""
        <div class="hc-card">
          <div class="hc-label">Nguy cơ</div>
          <div style="display:flex;align-items:center;gap:10px;">
            <span class="hc-pill" style="background:{risk_color};color:#fff;">
              {RISK_LABELS.get(result["risk"], result["risk"])}
            </span>
            <span class="hc-value">{result["probability"]:.1%}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
m2.metric("Xác suất", f"{result['probability']:.1%}")
m3.metric("BMI", f"{patient['bmi']:.1f}")
confidence_display = (
    f"{confidence} ({confidence_score:.0%})" if confidence_score is not None else confidence
)
m4.metric("Chất lượng dữ liệu", confidence_display)

st.markdown(
    f"""
    <div class="hc-card" style="display:flex;align-items:center;gap:14px;">
      <span class="hc-label" style="margin:0;">Hướng xử trí</span>
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
    calibration = {"isotonic_cv3": "Đẳng điệu, kiểm định chéo 3 phần"}.get(calibration, calibration)
    items = [
        (
            "Mô hình được chọn",
            {
                "mlp": "Mạng nơ-ron MLP",
                "logistic_regression": "Hồi quy logistic",
                "hist_gradient_boosting": "Tăng cường gradient theo histogram",
            }.get(selected_name, selected_name.replace("_", " ")),
        ),
        ("Số mẫu dữ liệu", f"{rows_total:,}" if isinstance(rows_total, int) else "—"),
        (
            "ROC AUC trên tập kiểm tra",
            f"{roc_auc:.3f}" if isinstance(roc_auc, (int, float)) else "—",
        ),
        ("Hiệu chuẩn", calibration),
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

assessment_tab, evidence_tab, history_tab = st.tabs(["Đánh giá", "Bằng chứng", "Lịch sử"])

with assessment_tab:
    left, right = st.columns([1, 1])

    with left:
        st.subheader("Giải thích")
        st.write(result["explanation"])

        st.subheader("Khuyến nghị")
        st.write(result["recommendation"])

    with right:
        st.subheader("Đặc trưng tác động mạnh nhất")
        features = result["feature_explanation"]["features"]
        if features:
            chart_df = pd.DataFrame(features).copy()
            chart_df["label"] = chart_df["feature"].map(label_for)
            chart_df["direction_clean"] = chart_df["impact"].apply(
                lambda v: "Tăng nguy cơ" if v > 0 else "Giảm nguy cơ" if v < 0 else "Không tác động"
            )
            chart_df["value_display"] = chart_df.apply(
                lambda row: format_feature_value(row["feature"], row["value"]), axis=1
            )
            top = chart_df.sort_values("magnitude", ascending=False).head(8)

            bar = (
                alt.Chart(top)
                .mark_bar()
                .encode(
                    x=alt.X("impact:Q", title="Tác động lên xác suất nguy cơ"),
                    y=alt.Y("label:N", sort="-x", title=None),
                    color=alt.Color(
                        "direction_clean:N",
                        scale=alt.Scale(
                            domain=["Tăng nguy cơ", "Giảm nguy cơ"],
                            range=["#c4423a", "#3b8c5a"],
                        ),
                        legend=alt.Legend(title=None, orient="bottom"),
                    ),
                    tooltip=[
                        alt.Tooltip("label:N", title="Đặc trưng"),
                        alt.Tooltip("value_display:N", title="Giá trị"),
                        alt.Tooltip("impact:Q", title="Mức tác động", format=".3f"),
                        alt.Tooltip("direction_clean:N", title="Chiều tác động"),
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
                    "label": "Đặc trưng",
                    "value_display": "Giá trị",
                    "direction_clean": "Chiều tác động",
                    "impact": "Mức tác động",
                }
            )
            st.dataframe(
                table_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Mức tác động": st.column_config.NumberColumn(format="%.3f"),
                },
            )
            st.caption(
                f"Phương pháp: {METHOD_LABELS.get(result['feature_explanation'].get('method'), '—')}"
            )
        else:
            st.write("Chưa có giải thích đặc trưng.")

with evidence_tab:
    st.subheader("Bằng chứng y khoa truy xuất")
    contexts = result.get("retrieved_context") or []
    if contexts:
        for item in contexts:
            with st.expander(
                f"{item['title']} (độ liên quan {item['relevance']:.2f})", expanded=False
            ):
                st.write(item["text"])
                if item.get("supports"):
                    st.caption("Liên kết trong đồ thị tới: " + ", ".join(item["supports"]))
                if item.get("url"):
                    st.markdown(f"[{item['source_title']}]({item['url']})")
        if result.get("evidence_status") == "limited":
            st.warning("Bằng chứng hỗ trợ cho hồ sơ này còn hạn chế.")
    else:
        st.warning("Chưa truy xuất được bằng chứng hướng dẫn đủ phù hợp cho hồ sơ này.")

    st.subheader("Dự đoán trước đây tương tự")
    similar_cases = result.get("similar_cases") or []
    if similar_cases:
        similar_df = pd.DataFrame(
            [
                {
                    "Nguy cơ": RISK_LABELS.get(item["metadata"].get("risk"), "Chưa rõ"),
                    "Xác suất": item["metadata"].get("probability"),
                    "Tuổi": item["metadata"].get("age"),
                    "BMI": item["metadata"].get("bmi"),
                    "Huyết áp": item["metadata"].get("bp"),
                    "Đường huyết": item["metadata"].get("glucose"),
                    "Khoảng cách": item["distance"],
                }
                for item in similar_cases
            ]
        )
        st.dataframe(
            similar_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Xác suất": st.column_config.NumberColumn(format="%.2f"),
                "Khoảng cách": st.column_config.NumberColumn(format="%.3f"),
            },
        )
    else:
        st.write("Chưa có hồ sơ trước đây phù hợp.")

with history_tab:
    history = agent.memory.get_all()
    if not history:
        st.write("Chưa có lịch sử hồ sơ.")
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
        history_df["timestamp"] = pd.to_datetime(
            history_df["timestamp"], errors="coerce", utc=True
        ).dt.tz_convert("Asia/Ho_Chi_Minh")
        history_df["risk"] = history_df["risk"].map(RISK_LABELS)
        history_df = history_df.sort_values("timestamp")

        trend_col, dist_col = st.columns(2)

        with trend_col:
            st.subheader("Xu hướng nguy cơ")
            trend_df = history_df.dropna(subset=["timestamp", "probability"]).set_index("timestamp")
            if not trend_df.empty:
                st.line_chart(
                    trend_df[["probability"]]
                    .rename(columns={"probability": "Xác suất"})
                    .rename_axis("Thời gian"),
                    use_container_width=True,
                )
            else:
                st.write("Chưa đủ hồ sơ có thời gian ghi nhận.")

        with dist_col:
            st.subheader("Phân bố mức nguy cơ")
            risk_counts = (
                history_df["risk"].value_counts().rename_axis("risk").reset_index(name="count")
            )
            st.bar_chart(
                risk_counts.set_index("risk")
                .rename(columns={"count": "Số hồ sơ"})
                .rename_axis("Nguy cơ"),
                use_container_width=True,
            )

        st.subheader("Các lần đánh giá gần đây")
        display_df = history_df.copy()
        display_df["timestamp"] = display_df["timestamp"].dt.strftime("%d/%m/%Y %H:%M:%S")
        display_df = display_df.rename(
            columns={
                "timestamp": "Thời gian",
                "risk": "Nguy cơ",
                "probability": "Xác suất",
                "age": "Tuổi",
                "bmi": "BMI",
                "bp": "Huyết áp",
                "glucose": "Đường huyết",
            }
        )
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Xác suất": st.column_config.NumberColumn(format="%.2f"),
            },
        )
