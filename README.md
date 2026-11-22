# kisan-kavach-agent
Early Agrarian Distress Detection &amp; Automated Relief Agent

# Kisan Kavach — Early Agrarian Distress Detection & Automated Relief Agent

An AI-powered early distress triage and government scheme relief routing agent that detects agrarian financial and crop-loss stress early, generates pre-filled scheme checklists, and triggers immediate human-in-the-loop helpline escalation.

## Hackathon Track & Problem Statement
* **Event:** Homingo Hack Days (Edition 01)
* **Track:** Agents — Statement A3 (*A personal staff for everyone*) / A2 (*The full-stack AI firm*)
* **Domain:** Agriculture & Civic Impact

## 3-Step Agent Pipeline
1. **Distress Risk Scoring Engine:** Evaluates crop loss, weather anomalies, market price drops, and debt pressure (modeled on ICAR-CRIDA's Farmers Distress Index) to classify risk as **Low**, **Moderate**, or **Severe**.
2. **Automated Relief & Scheme Action (RAG + Tool Calling):** Matches eligible government schemes (PMFBY crop insurance, KCC loan restructuring, PM-KISAN, state drought relief) and generates a pre-filled draft claim checklist.
3. **Human Escalation & Multilingual Helpline Routing:** Detects emotional or severe crisis signals in English/Marathi/Hindi and immediately routes to verified human helplines (**Tele-MANAS: 14416**, **Kisan Call Center: 1800-180-1551**) alongside a simulated local *Krishi Sevak* alert.

## AI Tools, Models & Libraries Used
* **Language & Runtime:** Python 3.13, VS Code
* **LLM & Agent Framework:** Google Gemini API (`google-genai`), Function Calling
* **Frontend & Data:** Streamlit, Pandas, JSON/CSV Knowledge Base
* **AI Coding Assistants:** Gemini

## Ethical Guardrails & Legal Compliance (DPDP-Safe)
* **100% Synthetic Data:** Uses only fictional farmer test profiles; no real personal data, Aadhaar numbers, or live land records are collected or stored.
* **No Medical Diagnosis:** Never acts as a medical or psychiatric counselor; all severe distress cases trigger immediate human-in-the-loop handoff to official helplines.
* **Draft-Only Automation:** Generates pre-filled scheme drafts and document checklists for human review rather than auto-submitting to live government portals.
* **Simulated Escalations:** Outbound counselor/officer alerts are simulated in-app for safe hackathon testing.
