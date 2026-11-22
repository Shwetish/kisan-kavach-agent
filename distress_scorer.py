from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_WEIGHTS: dict[str, float] = {
    "crop_loss": 0.30,
    "weather_anomaly": 0.25,
    "mandi_price_drop": 0.20,
    "debt_pressure": 0.25,
}

# Thresholds on a 0-100 distress index
LOW_MAX_SCORE = 39.9
MODERATE_MAX_SCORE = 69.9


@dataclass
class DistressAssessment:
    farmer_id: str
    synthetic_label: str
    district: str
    taluka: str
    primary_crop: str
    land_acres: float
    distress_score: float
    risk_level: str  # "Low" | "Moderate" | "Severe"
    primary_drivers: list[str]
    triggers_scheme_workflow: bool
    triggers_crisis_escalation: bool
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clamp_0_100(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def _normalize_mandi_drop_to_100(mandi_price_drop_pct: float) -> float:
    """
    Maps mandi price drop percentage to a 0-100 stress component.
    A 50%+ price drop saturates at 100 stress points.
    """
    return _clamp_0_100((mandi_price_drop_pct / 50.0) * 100.0)


def classify_risk_level(score: float) -> str:
    if score <= LOW_MAX_SCORE:
        return "Low"
    if score <= MODERATE_MAX_SCORE:
        return "Moderate"
    return "Severe"


def score_farmer_record(
    record: dict[str, Any],
    weights: dict[str, float] | None = None,
) -> DistressAssessment:
    """
    Scores a single synthetic farmer record using ICAR-CRIDA Farmers Distress Index
    inspired dimensions: crop loss, weather anomalies, mandi price drops, and debt pressure.
    """
    w = weights or DEFAULT_WEIGHTS
    total_weight = sum(w.values())
    if total_weight <= 0:
        raise ValueError("Component weights must sum to a positive value.")

    crop_loss_component = _clamp_0_100(float(record["crop_loss_pct"]))
    weather_component = _clamp_0_100(float(record["weather_anomaly_score"]))
    mandi_component = _normalize_mandi_drop_to_100(float(record["mandi_price_drop_pct"]))
    debt_component = _clamp_0_100(float(record["debt_pressure_index"]))

    weighted_sum = (
        crop_loss_component * w["crop_loss"]
        + weather_component * w["weather_anomaly"]
        + mandi_component * w["mandi_price_drop"]
        + debt_component * w["debt_pressure"]
    )
    distress_score = round(weighted_sum / total_weight, 2)
    risk_level = classify_risk_level(distress_score)

    component_scores = {
        "Crop Loss": crop_loss_component,
        "Weather Anomaly": weather_component,
        "Mandi Price Drop": mandi_component,
        "Debt Pressure": debt_component,
    }
    # Identify top contributing drivers (scores >= 50, or top 2 highest)
    elevated = [name for name, val in component_scores.items() if val >= 50.0]
    if not elevated:
        sorted_dims = sorted(component_scores.items(), key=lambda x: x[1], reverse=True)
        elevated = [sorted_dims[0][0], sorted_dims[1][0]]

    emotional_flag = int(record.get("emotional_distress_flag", 0)) == 1
    triggers_scheme_workflow = risk_level in {"Moderate", "Severe"}
    triggers_crisis_escalation = risk_level == "Severe" or emotional_flag

    rationale = (
        f"{risk_level} risk ({distress_score}/100) in {record['taluka']}, {record['district']} "
        f"for {record['primary_crop']} ({record['land_acres']} acres). "
        f"Key drivers: {', '.join(elevated)}."
    )

    return DistressAssessment(
        farmer_id=str(record["farmer_id"]),
        synthetic_label=str(record["synthetic_label"]),
        district=str(record["district"]),
        taluka=str(record["taluka"]),
        primary_crop=str(record["primary_crop"]),
        land_acres=float(record["land_acres"]),
        distress_score=distress_score,
        risk_level=risk_level,
        primary_drivers=elevated,
        triggers_scheme_workflow=triggers_scheme_workflow,
        triggers_crisis_escalation=triggers_crisis_escalation,
        rationale=rationale,
    )


def score_farmers_dataframe(
    df: pd.DataFrame,
    weights: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Runs distress scoring across a DataFrame of synthetic farmer records."""
    required_cols = {
        "farmer_id",
        "synthetic_label",
        "district",
        "taluka",
        "primary_crop",
        "land_acres",
        "crop_loss_pct",
        "weather_anomaly_score",
        "mandi_price_drop_pct",
        "debt_pressure_index",
    }
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    assessments = [
        score_farmer_record(row.to_dict(), weights=weights).to_dict()
        for _, row in df.iterrows()
    ]
    result_df = pd.DataFrame(assessments)
    return result_df


def run_batch_scoring(csv_path: str | Path = "data/sample_farmers.csv") -> pd.DataFrame:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found at: {path}")
    df = pd.read_csv(path)
    return score_farmers_dataframe(df)


if __name__ == "__main__":
    scored_df = run_batch_scoring("data/sample_farmers.csv")

    print("=== Kisan Kavach — Step 1 Distress Risk Scoring Summary ===")
    print(scored_df["risk_level"].value_counts().to_dict())
    print("\n=== Detailed Assessments ===")
    for item in scored_df.to_dict(orient="records"):
        print(
            f"[{item['farmer_id']}] {item['risk_level']:8s} | Score: {item['distress_score']:5.2f} | "
            f"SchemeRAG: {str(item['triggers_scheme_workflow']):5s} | "
            f"Escalation: {str(item['triggers_crisis_escalation']):5s} | "
            f"{item['rationale']}"
        )

    print("\n=== Sample JSON Payload for Downstream Agent (FK-015) ===")
    sample_severe = scored_df[scored_df["farmer_id"] == "FK-015"].iloc[0].to_dict()
    print(json.dumps(sample_severe, indent=2))
