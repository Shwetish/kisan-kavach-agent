from __future__ import annotations

import os
import pandas as pd
import streamlit as st

from distress_scorer import run_batch_scoring, score_farmer_record
from scheme_matcher import run_step2_scheme_action
from crisis_router import run_step3_crisis_router


st.set_page_config(
    page_title="Kisan Kavach — Agricultural Distress & Relief Agent",
    page_icon="🌾",
    layout="wide",
)

# Sidebar: Guardrails & Optional Gemini API Key
with st.sidebar:
    st.header("🛡️ Ethical & DPDP Guardrails")
    st.info(
        "**100% Synthetic Data Only**\n\n"
        "- No real farmer PII, Aadhaar, or 7/12 records.\n"
        "- **No Medical Diagnosis:** Immediate human helpline routing only.\n"
        "- **Human-in-the-Loop:** Draft-only scheme checklists (no auto-submission) & simulated alerts."
    )

    st.divider()
    st.subheader("🔑 Optional Gemini API Key")
    user_api_key = st.text_input(
        "GEMINI_API_KEY (Optional)",
        type="password",
        help="Leave blank to run with deterministic offline RAG & multilingual templates.",
    )
    if user_api_key:
        os.environ["GEMINI_API_KEY"] = user_api_key
        st.success("Gemini API enabled for live synthesis.")
    else:
        st.caption("Running in deterministic offline-safe mode.")

    st.divider()
    st.markdown(
        "**Verified Emergency Helplines**\n"
        "- **Tele-MANAS:** `14416` (24x7 Mental Health)\n"
        "- **Kisan Call Center:** `1800-180-1551`"
    )

# Main Header
st.title("🌾 Kisan Kavach — Proactive Farmer Distress & Relief Agent")
st.caption(
    "Homingo Hack Days | Track: Agents (Statement A3: A personal staff for everyone) | "
    "Modeled on ICAR-CRIDA's Farmers Distress Index"
)

# Load & Score Dataset (Step 1 Batch Overview)
scored_df = run_batch_scoring("data/sample_farmers.csv")
raw_df = pd.read_csv("data/sample_farmers.csv")

# Top KPI Summary Metrics
counts = scored_df["risk_level"].value_counts().to_dict()
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Synthetic Profiles", len(scored_df))
col2.metric("Severe Distress Cases", counts.get("Severe", 0))
col3.metric("Moderate Distress Cases", counts.get("Moderate", 0))
col4.metric("Low Risk Cases", counts.get("Low", 0))

st.divider()

tab1, tab2 = st.tabs(["📋 Evaluate Synthetic Cohort (20 Farmers)", "🧪 Custom Scenario Simulator"])

with tab1:
    st.subheader("Select a Synthetic Maharashtra Farmer Profile")
    farmer_options = [
        f"{row['farmer_id']} — {row['synthetic_label']} ({row['taluka']}, {row['district']} | {row['primary_crop']} | {row['risk_level']})"
        for _, row in scored_df.iterrows()
    ]
    selected_option = st.selectbox("Choose profile to run 3-Step Agent Pipeline:", farmer_options)
    selected_id = selected_option.split(" — ")[0].strip()

    raw_row = raw_df[raw_df["farmer_id"] == selected_id].iloc[0].to_dict()
    assessment = score_farmer_record(raw_row).to_dict()

    farmer_note = st.text_area(
        "Farmer Field Note / Message (English, Marathi, or Hindi):",
        value=str(raw_row.get("notes", "")),
        height=80,
    )

    if st.button("🚀 Run 3-Step Kisan Kavach Agent", type="primary", key="run_cohort"):
        st.markdown("### Step 1: ICAR-CRIDA Distress Risk Scoring")
        s1_c1, s1_c2, s1_c3 = st.columns(3)
        s1_c1.metric("Distress Index Score", f"{assessment['distress_score']} / 100")
        s1_c2.metric("Risk Classification", assessment["risk_level"])
        s1_c3.metric("Crisis Escalation Flag", "YES" if assessment["triggers_crisis_escalation"] else "NO")
        st.write(f"**Rationale:** {assessment['rationale']}")
        st.write(f"**Primary Stress Drivers:** {', '.join(assessment['primary_drivers'])}")

        st.markdown("---")
        st.markdown("### Step 2: Automated Relief & Scheme Action (Draft-Only)")
        step2_res = run_step2_scheme_action(assessment)
        st.info(step2_res.ai_guidance_note)

        for scheme in step2_res.matched_schemes:
            with st.expander(f"✅ {scheme['name']} ({scheme['scheme_id']})", expanded=True):
                st.write(f"**Eligibility:** {scheme['eligibility_summary']}")
                st.write(f"**Benefit:** {scheme['benefit_summary']}")
                st.write(f"**Action Window:** {scheme['action_window']}")
                st.write(f"**Official Portal:** {scheme['official_portal']}")

        st.write("**DPDP-Safe Draft Claim Checklist (Requires Human Verification):**")
        st.json(step2_res.draft_claim_checklist)

        st.markdown("---")
        st.markdown("### Step 3: Human Escalation & Multilingual Helpline Routing")
        step3_res = run_step3_crisis_router(assessment, farmer_note)

        if step3_res.crisis_detected:
            st.error(
                f"🚨 **{step3_res.escalation_priority}** | Language Detected: **{step3_res.detected_language}**"
            )
            st.warning(step3_res.supportive_farmer_message)
        else:
            st.success(
                f"✅ **{step3_res.escalation_priority}** | Language Detected: **{step3_res.detected_language}**"
            )
            st.write(step3_res.supportive_farmer_message)

        h_col1, h_col2 = st.columns(2)
        with h_col1:
            st.write("**Verified Human Helplines:**")
            st.table(pd.DataFrame(step3_res.verified_helplines))
        with h_col2:
            st.write("**Simulated Krishi Sevak Alert (Sandbox Only):**")
            st.json(step3_res.simulated_krishi_sevak_alert)

    with st.expander("📊 View Full 20-Farmer Scored Dataset"):
        st.dataframe(scored_df, use_container_width=True)

with tab2:
    st.subheader("Simulate a Custom Synthetic Scenario")
    c1, c2, c3 = st.columns(3)
    sim_district = c1.text_input("District", value="Yavatmal")
    sim_taluka = c2.text_input("Taluka", value="Pusad")
    sim_crop = c3.text_input("Primary Crop", value="Cotton")

    s1, s2, s3, s4 = st.columns(4)
    crop_loss = s1.slider("Crop Loss (%)", 0, 100, 75)
    weather_anom = s2.slider("Weather Anomaly (0-100)", 0, 100, 82)
    mandi_drop = s3.slider("Mandi Price Drop (%)", 0, 60, 40)
    debt_press = s4.slider("Debt Pressure (0-100)", 0, 100, 80)

    custom_msg = st.text_area(
        "Farmer Message (Try English, Marathi, or Hindi):",
        value="दुष्काळामुळे पीक पूर्ण गेले आहे, खूप तणाव आहे, काहीच उरले नाही.",
    )

    if st.button("🧪 Evaluate Custom Scenario", type="primary", key="run_custom"):
        custom_record = {
            "farmer_id": "FK-SIM-999",
            "synthetic_label": "Custom Synthetic Farmer",
            "district": sim_district,
            "taluka": sim_taluka,
            "primary_crop": sim_crop,
            "land_acres": 3.5,
            "crop_loss_pct": crop_loss,
            "weather_anomaly_score": weather_anom,
            "mandi_price_drop_pct": mandi_drop,
            "debt_pressure_index": debt_press,
            "emotional_distress_flag": 0,
        }
        custom_assessment = score_farmer_record(custom_record).to_dict()
        s2_custom = run_step2_scheme_action(custom_assessment)
        s3_custom = run_step3_crisis_router(custom_assessment, custom_msg)

        st.metric("Computed Distress Score", f"{custom_assessment['distress_score']} / 100 ({custom_assessment['risk_level']})")
        st.info(s2_custom.ai_guidance_note)
        if s3_custom.crisis_detected:
            st.error(s3_custom.supportive_farmer_message)
        else:
            st.success(s3_custom.supportive_farmer_message)
        st.json(s3_custom.simulated_krishi_sevak_alert)
