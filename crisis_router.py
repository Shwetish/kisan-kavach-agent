from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pprint import pprint
from typing import Any

from distress_scorer import DistressAssessment, run_batch_scoring


# Verified national & state support helplines (hardcoded for 100% accuracy)
VERIFIED_HELPLINES: list[dict[str, str]] = [
    {
        "service_name": "Tele-MANAS (National Tele Mental Health Programme)",
        "number": "14416",
        "toll_free_alt": "1800-891-4416",
        "languages": "Marathi, Hindi, English (24x7 Free & Confidential)",
        "purpose": "Immediate emotional support, crisis counseling, and stress relief.",
    },
    {
        "service_name": "Kisan Call Center (Ministry of Agriculture & Farmers Welfare)",
        "number": "1800-180-1551",
        "toll_free_alt": "1551",
        "languages": "Marathi, Hindi, English (6:00 AM – 10:00 PM)",
        "purpose": "Urgent crop damage advice, PMFBY claim guidance, and local agri-extension support.",
    },
]

# Deterministic multilingual crisis & distress keywords (English, Marathi, Hindi)
CRISIS_KEYWORDS: dict[str, list[str]] = {
    "English": [
        "hopeless", "give up", "can't go on", "cannot survive", "end my life",
        "no way out", "ruined", "debt trap", "bank recovery", "suicidal", "panic",
    ],
    "Marathi": [
        "जगणे नको", "आत्महत्या", "संपले सगळे", "काहीच उरले नाही", "कर्जबाजारी",
        "खूप तणाव", "निराश", "वाचण्याचा मार्ग नाही", "पीक पूर्ण गेले", "मदत करा",
    ],
    "Hindi": [
        "जीने का मन नहीं", "आत्महत्या", "सब खत्म", "कोई रास्ता नहीं", "कर्ज से परेशान",
        "बहुत तनाव", "निराश", "मर जाऊंगा", "बर्बाद हो गया", "मदद चाहिए",
    ],
}


@dataclass
class CrisisRoutingResult:
    farmer_id: str
    synthetic_label: str
    district: str
    taluka: str
    detected_language: str
    crisis_detected: bool
    escalation_priority: str  # "ROUTINE" | "PRIORITY_FIELD_VISIT" | "IMMEDIATE_CRISIS_ESCALATION"
    matched_cues: list[str]
    verified_helplines: list[dict[str, str]]
    simulated_krishi_sevak_alert: dict[str, Any]
    supportive_farmer_message: str
    safety_guardrail_note: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def detect_language_and_cues(farmer_note: str) -> tuple[str, list[str]]:
    """
    Scans English, Marathi, and Hindi text for distress/crisis indicators
    and identifies the primary language script/cues.
    """
    text_lower = farmer_note.lower()
    matched_cues: list[str] = []
    detected_lang = "English"

    for lang, keywords in CRISIS_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                matched_cues.append(f"{kw} ({lang})")
                if lang in {"Marathi", "Hindi"}:
                    detected_lang = lang

    # Basic Devanagari script heuristic if no keyword matched
    if detected_lang == "English" and any("\u0900" <= ch <= "\u097F" for ch in farmer_note):
        if any(word in farmer_note for word in ["आहे", "नाही", "शेतकरी", "पीक", "कर्ज"]):
            detected_lang = "Marathi"
        else:
            detected_lang = "Hindi"

    return detected_lang, matched_cues


def build_simulated_krishi_sevak_alert(
    assessment: dict[str, Any],
    priority: str,
    matched_cues: list[str],
) -> dict[str, Any]:
    """
    Tool Action: Simulates an outbound alert to the block-level Krishi Sevak /
    Taluka Agriculture Officer. Never dispatches real SMS/calls.
    """
    return {
        "dispatch_mode": "SIMULATED_SANDBOX_ALERT_ONLY",
        "real_sms_sent": False,
        "recipient_role": f"Taluka Krishi Sevak ({assessment['taluka']}, {assessment['district']})",
        "priority": priority,
        "synthetic_farmer_id": assessment["farmer_id"],
        "crop_and_area": f"{assessment['primary_crop']} ({assessment['land_acres']} acres)",
        "distress_score": assessment["distress_score"],
        "primary_drivers": assessment["primary_drivers"],
        "detected_signals": matched_cues if matched_cues else ["High quantitative distress index"],
        "recommended_field_action": (
            "Conduct immediate compassionate in-person wellness & crop-loss verification visit; "
            "assist with PMFBY / SDRF draft paperwork."
            if priority == "IMMEDIATE_CRISIS_ESCALATION"
            else "Schedule routine taluka advisory follow-up."
        ),
    }


def generate_multilingual_support_message(
    assessment: dict[str, Any],
    language: str,
    crisis_detected: bool,
) -> str:
    """
    Produces a warm, non-clinical support message in English, Marathi, or Hindi
    with verified helpline numbers. Uses google-genai if GEMINI_API_KEY is present,
    with guaranteed deterministic multilingual fallbacks.
    """
    if not crisis_detected:
        return (
            f"Routine status for {assessment['synthetic_label']} ({assessment['taluka']}): "
            "No acute crisis cues detected. Standard Kisan Call Center (1800-180-1551) "
            "available for crop advisory."
        )

    fallback_messages = {
        "Marathi": (
            f"नमस्कार, {assessment['taluka']} येथील पीक व आर्थिक ताणामुळे तुम्ही एकटे नाहीत. "
            "कृपया त्वरित मोफत व गोपनीय मदतीसाठी Tele-MANAS (14416) किंवा किसान कॉल सेंटर "
            "(1800-180-1551) यांच्याशी संपर्क साधा. तुमच्या तालुक्यातील कृषी सेवकांना मदतीसाठी "
            "सूचित केले आहे."
        ),
        "Hindi": (
            f"नमस्ते, {assessment['taluka']} में फसल और आर्थिक तनाव की इस स्थिति में आप अकेले नहीं हैं। "
            "कृपया तुरंत निःशुल्क और गोपनीय सहायता के लिए Tele-MANAS (14416) या किसान कॉल सेंटर "
            "(1800-180-1551) पर बात करें। आपके तालुका के कृषि सेवक को सहायता हेतु सूचित किया गया है।"
        ),
        "English": (
            f"You are not alone during this difficult crop and financial period in {assessment['taluka']}. "
            "Please reach out right away for free, confidential human support at Tele-MANAS (14416) "
            "or the Kisan Call Center (1800-180-1551). A simulated alert has also been logged for "
            "your local Krishi Sevak to assist with relief steps."
        ),
    }

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return fallback_messages.get(language, fallback_messages["English"])

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        prompt = (
            f"Write a short, deeply empathetic 3-sentence support message in {language} for a farmer "
            f"in {assessment['taluka']}, Maharashtra experiencing severe agricultural distress.\n"
            "STRICT RULES:\n"
            "1. Do NOT give any medical, psychological, or psychiatric diagnosis.\n"
            "2. Explicitly include both verified helplines: Tele-MANAS (14416) and Kisan Call Center (1800-180-1551).\n"
            "3. Mention that a local Krishi Sevak has been alerted to help with relief schemes.\n"
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text.strip()
    except Exception:
        return fallback_messages.get(language, fallback_messages["English"])


def run_step3_crisis_router(
    assessment: dict[str, Any] | DistressAssessment,
    farmer_message_or_note: str = "",
) -> CrisisRoutingResult:
    assessment_dict = (
        assessment.to_dict() if isinstance(assessment, DistressAssessment) else dict(assessment)
    )

    detected_lang, matched_cues = detect_language_and_cues(farmer_message_or_note)
    quantitative_trigger = bool(assessment_dict.get("triggers_crisis_escalation", False))
    crisis_detected = quantitative_trigger or len(matched_cues) > 0

    if crisis_detected:
        priority = "IMMEDIATE_CRISIS_ESCALATION"
    elif assessment_dict.get("risk_level") == "Moderate":
        priority = "PRIORITY_FIELD_VISIT"
    else:
        priority = "ROUTINE"

    alert_payload = build_simulated_krishi_sevak_alert(
        assessment=assessment_dict,
        priority=priority,
        matched_cues=matched_cues,
    )
    support_msg = generate_multilingual_support_message(
        assessment=assessment_dict,
        language=detected_lang,
        crisis_detected=crisis_detected,
    )

    return CrisisRoutingResult(
        farmer_id=assessment_dict["farmer_id"],
        synthetic_label=assessment_dict["synthetic_label"],
        district=assessment_dict["district"],
        taluka=assessment_dict["taluka"],
        detected_language=detected_lang,
        crisis_detected=crisis_detected,
        escalation_priority=priority,
        matched_cues=matched_cues,
        verified_helplines=VERIFIED_HELPLINES,
        simulated_krishi_sevak_alert=alert_payload,
        supportive_farmer_message=support_msg,
        safety_guardrail_note=(
            "STRICT GUARDRAIL: No medical/psychiatric diagnosis performed. "
            "Immediate routing to verified human helplines (14416 / 1800-180-1551) "
            "and simulated Krishi Sevak sandbox alert only."
        ),
    )


if __name__ == "__main__":
    scored_df = run_batch_scoring("data/sample_farmers.csv")

    # Test 1: Routine Low-Risk Case (FK-001)
    low_case = scored_df[scored_df["farmer_id"] == "FK-001"].iloc[0].to_dict()
    res_low = run_step3_crisis_router(low_case, "Normal harvest, checking mandi rates.")
    print("=== Test 1: FK-001 (Low Risk) ===")
    print("Priority:", res_low.escalation_priority, "| Crisis:", res_low.crisis_detected)

    # Test 2: Severe Risk with Marathi Distress Note (FK-015)
    severe_case = scored_df[scored_df["farmer_id"] == "FK-015"].iloc[0].to_dict()
    res_severe_mr = run_step3_crisis_router(
        severe_case,
        "दुष्काळामुळे पीक पूर्ण गेले आहे, खूप तणाव आहे, काहीच उरले नाही.",
    )
    print("\n=== Test 2: FK-015 (Severe + Marathi Crisis Cues) ===")
    pprint(res_severe_mr.to_dict())
