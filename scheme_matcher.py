from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pprint import pprint
from typing import Any

from distress_scorer import DistressAssessment, run_batch_scoring


RISK_RANK = {"Low": 1, "Moderate": 2, "Severe": 3}

# Pure Python knowledge base of relief schemes (no external JSON file needed)
MAHARASHTRA_SCHEMES: list[dict[str, Any]] = [
    {
        "scheme_id": "PMFBY-MH",
        "name": "Pradhan Mantri Fasal Bima Yojana (PMFBY)",
        "level": "Central + Maharashtra State",
        "focus_drivers": ["Crop Loss", "Weather Anomaly"],
        "min_risk_level": "Moderate",
        "eligibility_summary": (
            "Farmers growing notified Kharif/Rabi crops in Maharashtra facing yield loss "
            "due to drought, dry spells, excess rain, hailstorm, or localized calamities."
        ),
        "benefit_summary": (
            "Comprehensive crop insurance payout covering post-harvest and mid-season "
            "adverse weather losses after crop-cutting experiments or localized loss intimation within 72 hours."
        ),
        "required_documents": [
            "Synthetic Farmer ID / Application Reference",
            "Land Holding Extract Placeholder ([7/12_RECORD_PLACEHOLDER])",
            "Crop Sowing Self-Declaration / E-Pik Pahani Reference",
            "Bank Passbook / IFSC Placeholder ([BANK_ACCOUNT_PLACEHOLDER])",
            "ID Verification Placeholder ([ID_VERIFICATION_PLACEHOLDER])",
        ],
        "action_window": "Report localized calamity within 72 hours via Krishi Rakshak Portal / Helpline 14447 or bank branch.",
        "official_portal": "https://pmfby.gov.in/",
    },
    {
        "scheme_id": "KCC-RESTRUCTURE",
        "name": "Kisan Credit Card (KCC) Short-Term Crop Loan Restructuring",
        "level": "Central (RBI / NABARD Guidelines)",
        "focus_drivers": ["Debt Pressure", "Crop Loss", "Weather Anomaly"],
        "min_risk_level": "Moderate",
        "eligibility_summary": (
            "KCC borrowers in areas affected by natural calamities (>=33% crop loss) "
            "facing repayment distress on short-term crop loans."
        ),
        "benefit_summary": (
            "Conversion/restructuring of short-term crop loans into medium-term loans (3 to 5 years) "
            "with moratorium period and continuation of interest subvention benefits."
        ),
        "required_documents": [
            "Existing KCC Account Reference ([KCC_ACCOUNT_PLACEHOLDER])",
            "Taluka Drought / Crop Loss Notification Reference",
            "Land Holding Extract Placeholder ([7/12_RECORD_PLACEHOLDER])",
            "Written Restructuring Request Letter (Draft)",
        ],
        "action_window": "Submit restructuring application to issuing Bank / PACS branch before crop loan due date.",
        "official_portal": "https://www.nabard.org/",
    },
    {
        "scheme_id": "MH-DROUGHT-RELIEF",
        "name": "Maharashtra State Agricultural Input Subsidy (SDRF / NDRF Relief)",
        "level": "Government of Maharashtra (Revenue & Agriculture Dept.)",
        "focus_drivers": ["Weather Anomaly", "Crop Loss"],
        "min_risk_level": "Severe",
        "eligibility_summary": (
            "Small and marginal farmers in drought-declared or heavy-rain-affected "
            "Maharashtra talukas suffering >=33% crop damage."
        ),
        "benefit_summary": (
            "Direct Benefit Transfer (DBT) input subsidy per hectare (up to 2 hectares) "
            "for rainfed, irrigated, or perennial horticultural crops."
        ),
        "required_documents": [
            "e-KYC & Farmer Registry Reference ([ID_VERIFICATION_PLACEHOLDER])",
            "Land Record Placeholder ([7/12_RECORD_PLACEHOLDER])",
            "Panchnama / Talathi Crop Damage Assessment Reference",
            "DBT-Linked Bank Account Placeholder ([BANK_ACCOUNT_PLACEHOLDER])",
        ],
        "action_window": "Verify name in village Talathi / Krishi Sevak beneficiary list during taluka relief window.",
        "official_portal": "https://mahadbt.maharashtra.gov.in/",
    },
    {
        "scheme_id": "PM-KISAN",
        "name": "Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)",
        "level": "Central Sector Scheme",
        "focus_drivers": ["Mandi Price Drop", "Debt Pressure", "Crop Loss"],
        "min_risk_level": "Low",
        "eligibility_summary": (
            "All landholding farmer families across Maharashtra needing supplemental "
            "income support for agricultural inputs and household liquidity."
        ),
        "benefit_summary": (
            "Rs. 6,000 per year income support in three equal installments of Rs. 2,000 "
            "every four months directly to DBT-enabled bank accounts."
        ),
        "required_documents": [
            "Land Ownership Record Placeholder ([7/12_RECORD_PLACEHOLDER])",
            "e-KYC Verification Placeholder ([ID_VERIFICATION_PLACEHOLDER])",
            "DBT-Enabled Bank Account Placeholder ([BANK_ACCOUNT_PLACEHOLDER])",
        ],
        "action_window": "Check installment status or complete pending e-KYC at nearest CSC / PM-KISAN portal.",
        "official_portal": "https://pmkisan.gov.in/",
    },
]


@dataclass
class SchemeMatchResult:
    farmer_id: str
    synthetic_label: str
    district: str
    taluka: str
    primary_crop: str
    risk_level: str
    distress_score: float
    matched_schemes: list[dict[str, Any]]
    draft_claim_checklist: dict[str, Any]
    ai_guidance_note: str
    guardrail_notice: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def retrieve_eligible_schemes(
    assessment: dict[str, Any],
    schemes_kb: list[dict[str, Any]] = MAHARASHTRA_SCHEMES,
) -> list[dict[str, Any]]:
    """
    Retrieves and ranks eligible schemes from the Python knowledge base
    based on distress risk tier and primary distress drivers.
    """
    farmer_risk_rank = RISK_RANK.get(assessment["risk_level"], 1)
    drivers = set(assessment.get("primary_drivers", []))

    scored_matches: list[tuple[int, dict[str, Any]]] = []
    for scheme in schemes_kb:
        min_rank = RISK_RANK.get(scheme.get("min_risk_level", "Low"), 1)
        if farmer_risk_rank < min_rank:
            continue

        focus_drivers = set(scheme.get("focus_drivers", []))
        overlap = drivers.intersection(focus_drivers)
        relevance_score = len(overlap) * 10 + min_rank

        if overlap or assessment["risk_level"] == "Low":
            enriched = dict(scheme)
            enriched["matched_drivers"] = (
                sorted(overlap) if overlap else ["General Income Support"]
            )
            enriched["relevance_score"] = relevance_score
            scored_matches.append((relevance_score, enriched))

    scored_matches.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in scored_matches]


def build_draft_claim_checklist(
    assessment: dict[str, Any],
    matched_schemes: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Generates a DPDP-safe, draft-only claim preparation checklist as a Python dictionary.
    Never auto-submits to any government portal.
    """
    consolidated_docs: list[str] = []
    for scheme in matched_schemes:
        for doc in scheme.get("required_documents", []):
            if doc not in consolidated_docs:
                consolidated_docs.append(doc)

    return {
        "document_status": "DRAFT_ONLY_DO_NOT_AUTO_SUBMIT",
        "auto_submit_enabled": False,
        "applicant_profile": {
            "synthetic_farmer_id": assessment["farmer_id"],
            "synthetic_label": assessment["synthetic_label"],
            "district": assessment["district"],
            "taluka": assessment["taluka"],
            "notified_crop": assessment["primary_crop"],
            "land_area_acres": assessment["land_acres"],
            "pii_status": "SYNTHETIC_ONLY_NO_REAL_PII_OR_7_12",
        },
        "assessed_distress_context": {
            "distress_score": assessment["distress_score"],
            "risk_level": assessment["risk_level"],
            "primary_drivers": assessment["primary_drivers"],
        },
        "recommended_schemes": [
            {
                "scheme_id": s["scheme_id"],
                "scheme_name": s["name"],
                "matched_drivers": s["matched_drivers"],
                "action_window": s["action_window"],
                "official_portal": s["official_portal"],
            }
            for s in matched_schemes
        ],
        "consolidated_document_checklist": consolidated_docs,
        "next_human_verification_step": (
            "Review this draft checklist with your local Krishi Sevak, Talathi, "
            "or CSC operator before submitting on an official government portal."
        ),
    }


def generate_gemini_grounded_note(
    assessment: dict[str, Any],
    matched_schemes: list[dict[str, Any]],
) -> str:
    """
    Uses google-genai (if GEMINI_API_KEY is available) to produce a concise,
    grounded action summary strictly from retrieved schemes. Falls back cleanly
    to a deterministic Python summary when offline or without an API key.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    scheme_names = [s["name"] for s in matched_schemes]

    if not api_key:
        return (
            f"[Offline RAG Summary] Based on {assessment['risk_level']} distress "
            f"({assessment['distress_score']}/100) for {assessment['primary_crop']} in "
            f"{assessment['taluka']}, {assessment['district']}, prioritized schemes are: "
            f"{', '.join(scheme_names) if scheme_names else 'PM-KISAN'}. "
            "All checklists are draft-only for human review."
        )

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        prompt = (
            "You are Kisan Kavach, an ethical agricultural relief assistant for Maharashtra.\n"
            "Using ONLY the retrieved scheme facts below, write a clear 3-bullet action note "
            "for a field officer helping this synthetic farmer profile. Do NOT invent scheme "
            "amounts, do NOT ask for real personal IDs/PII, and state clearly that this is a draft "
            "checklist requiring human verification.\n\n"
            f"Farmer Assessment: {assessment}\n"
            f"Retrieved Schemes: {matched_schemes}"
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as exc:
        return (
            f"[Fallback RAG Summary - Gemini API unavailable: {exc}] "
            f"Prioritized schemes: {', '.join(scheme_names)}."
        )


def run_step2_scheme_action(
    assessment: dict[str, Any] | DistressAssessment,
) -> SchemeMatchResult:
    assessment_dict = (
        assessment.to_dict() if isinstance(assessment, DistressAssessment) else dict(assessment)
    )
    matched = retrieve_eligible_schemes(assessment_dict, MAHARASHTRA_SCHEMES)
    draft_checklist = build_draft_claim_checklist(assessment_dict, matched)
    guidance_note = generate_gemini_grounded_note(assessment_dict, matched)

    return SchemeMatchResult(
        farmer_id=assessment_dict["farmer_id"],
        synthetic_label=assessment_dict["synthetic_label"],
        district=assessment_dict["district"],
        taluka=assessment_dict["taluka"],
        primary_crop=assessment_dict["primary_crop"],
        risk_level=assessment_dict["risk_level"],
        distress_score=assessment_dict["distress_score"],
        matched_schemes=matched,
        draft_claim_checklist=draft_checklist,
        ai_guidance_note=guidance_note,
        guardrail_notice=(
            "DPDP-Safe & Human-in-the-Loop: Synthetic profile only; no auto-submission "
            "to government portals."
        ),
    )


if __name__ == "__main__":
    scored_df = run_batch_scoring("data/sample_farmers.csv")

    for sample_id in ["FK-001", "FK-008", "FK-015"]:
        row = scored_df[scored_df["farmer_id"] == sample_id].iloc[0].to_dict()
        result = run_step2_scheme_action(row)
        print(f"\n=== Step 2 Scheme Action for {sample_id} ({result.risk_level}) ===")
        print("Matched Schemes:", [s["scheme_id"] for s in result.matched_schemes])
        print("Guidance:", result.ai_guidance_note)
        print("Draft Checklist:")
        pprint(result.draft_claim_checklist)
