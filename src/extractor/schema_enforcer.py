import json
from typing import Any, Dict, Optional
from pydantic import ValidationError
from src.models import CompanyIntelligence, ExtractionMetadata
from src.utils.logger import logger


def calculate_rubric_confidence(
    overview: str,
    icp: str,
    contact_points: list,
    leadership: list
) -> float:
    """Computes a baseline confidence score based on field completeness."""
    score = 0.0

    if overview and len(overview.strip()) > 20 and overview != "Company overview unavailable.":
        score += 0.25

    if icp and len(icp.strip()) > 10:
        score += 0.25

    if contact_points:
        score += 0.20

    if leadership:
        score += 0.20
        if any(getattr(m, "linkedin_url", None) for m in leadership):
            score += 0.10

    return min(1.0, round(score, 2))


def clean_json_string(raw_str: str) -> str:
    """Strips markdown code fences and extraneous leading/trailing whitespace."""
    cleaned = raw_str.strip()

    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1]
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1]

    if "```" in cleaned:
        cleaned = cleaned.rsplit("```", 1)[0]

    return cleaned.strip()


def parse_and_validate_extraction(
    raw_json_str: str,
    target_domain: str,
    metadata: Optional[ExtractionMetadata] = None
) -> CompanyIntelligence:
    cleaned_str = clean_json_string(raw_json_str)

    try:
        data: Dict[str, Any] = json.loads(cleaned_str)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON for {target_domain}: {e}")
        data = {
            "domain": target_domain,
            "company_name": target_domain.split(".")[0].capitalize(),
            "company_overview": "Overview extraction failed due to response format error.",
            "target_audience_icp": "Unknown ICP.",
            "contact_points": [],
            "key_leadership": [],
            "data_confidence_score": 0.1,
            "confidence_reasoning": "JSON parse error on LLM response."
        }

    data["domain"] = target_domain

    try:
        intelligence = CompanyIntelligence(**data)
    except ValidationError as ve:
        logger.warning(f"Pydantic validation error for {target_domain}: {ve}")
        intelligence = CompanyIntelligence(
            domain=target_domain,
            company_name=str(data.get("company_name", target_domain.split(".")[0].capitalize())),
            company_overview=str(data.get("company_overview", "Overview unavailable.")),
            target_audience_icp=str(data.get("target_audience_icp", "Unknown target audience.")),
            contact_points=[str(e) for e in data.get("contact_points", []) if isinstance(e, str)],
            key_leadership=[],
            data_confidence_score=0.2,
            confidence_reasoning=f"Partial validation failure: {str(ve)}"
        )

    # Blend model self-assessment with objective presence score
    objective_score = calculate_rubric_confidence(
        intelligence.company_overview,
        intelligence.target_audience_icp,
        intelligence.contact_points,
        intelligence.key_leadership
    )

    blended_score = round((intelligence.data_confidence_score + objective_score) / 2.0, 2)
    intelligence.data_confidence_score = max(0.0, min(1.0, blended_score))

    if metadata:
        intelligence.metadata = metadata

    return intelligence


def create_empty_fallback(domain: str, error_message: str) -> CompanyIntelligence:
    return CompanyIntelligence(
        domain=domain,
        company_name=domain.split(".")[0].capitalize(),
        company_overview=f"Failed to extract intelligence for {domain}: {error_message}",
        target_audience_icp="N/A",
        contact_points=[],
        key_leadership=[],
        data_confidence_score=0.0,
        confidence_reasoning=f"Domain crawl or extraction failed: {error_message}",
        metadata=ExtractionMetadata(
            pages_crawled=[],
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            estimated_cost_usd=0.0
        )
    )
