# 🌾 Kisan Kavach — Proactive Farmer Distress Detection & Automated Relief Agent

**Homingo Hack Days Submission** | **Track:** Agents — Statement A3 (*"A personal staff for everyone"*)  
**Domain:** Agriculture & Civic Impact | **Author:** Shweta Katneshwarkar (Solo Participant)

---

## 🎯 Problem & Motivation
Smallholder farmers in Maharashtra frequently face overlapping shocks—erratic monsoons, localized crop damage, sharp mandi price drops, and recurring credit pressure. Navigating relief schemes (like PMFBY or KCC restructuring) requires complex paperwork at the exact moment a household is under acute financial and emotional stress.

**Kisan Kavach** acts as an ethical, human-in-the-loop "chief of staff" for agricultural extension officers (*Krishi Sevaks*) and farmers—detecting distress early, preparing draft relief checklists, and immediately routing acute crisis signals to verified human helplines.

---

## ⚙️ 3-Step Agent Architecture

1. **Step 1: Distress Risk Scoring Engine (`distress_scorer.py`)**
   - Evaluates **Crop Loss (30%)**, **Weather Anomalies (25%)**, **Debt Pressure (25%)**, and **Mandi Price Drops (20%)** on a transparent `0–100` index inspired by **ICAR-CRIDA's Farmers Distress Index**.
   - Classifies scenarios into **Low** (`0–39.9`), **Moderate** (`40.0–69.9`), or **Severe** (`70.0–100`), identifies root-cause stress drivers, and sets routing triggers.

2. **Step 2: Automated Relief & Scheme Action (`scheme_matcher.py`)**
   - Matches Moderate and Severe cases against a structured Maharashtra & Central scheme knowledge base (**PMFBY**, **KCC Short-Term Loan Restructuring**, **Maharashtra State SDRF/NDRF Drought Relief**, and **PM-KISAN**).
   - Generates a **draft-only** consolidated document checklist (`auto_submit_enabled = False`) and uses `google-genai` (`gemini-2.5-flash`) with deterministic offline fallback to summarize grounded next steps.

3. **Step 3: Human Escalation & Multilingual Helpline Routing (`crisis_router.py`)**
   - Scans farmer notes and messages across **English, Marathi, and Hindi** for emotional distress or financial panic cues.
   - Immediately routes crisis cases to verified human support (**Tele-MANAS: `14416`** and **Kisan Call Center: `1800-180-1551`**) alongside a simulated block-level **Krishi Sevak** alert.

---

## 🛡️ Strict Ethical & DPDP Compliance Guardrails
- **100% Synthetic Data Only:** `data/sample_farmers.csv` contains 20 purely synthetic Maharashtra farmer scenarios (`FK-001` to `FK-020`). Zero real farmer PII, Aadhaar numbers, or 7/12 land records are stored or processed.
- **Zero Medical/Psychiatric Diagnosis:** The agent never attempts clinical diagnosis; any severe or emotional distress cue triggers immediate human helpline routing.
- **Human-in-the-Loop Drafts Only:** Scheme outputs are strictly labeled `DRAFT_ONLY_DO_NOT_AUTO_SUBMIT` and outbound Krishi Sevak alerts run in sandbox simulation mode.

---

## 🗂️ Repository Structure
```text
kisan-kavach-agent/
├── data/
│   └── sample_farmers.csv    # 20 DPDP-safe synthetic Maharashtra farmer scenarios
├── distress_scorer.py        # Step 1: ICAR-CRIDA inspired distress scoring & classification
├── scheme_matcher.py         # Step 2: Grounded scheme retrieval & draft checklist generator
├── crisis_router.py          # Step 3: Multilingual (EN/MR/HI) crisis & helpline router
├── app.py                    # Interactive Streamlit dashboard orchestrating Steps 1–3
├── requirements.txt          # Python dependencies
└── README.md                 # Project documentation & guardrails
