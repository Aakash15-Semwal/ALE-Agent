import csv
import json
from pathlib import Path
from typing import List, Union
from src.models import CompanyIntelligence
from src.utils.logger import logger


def export_to_json(
    records: List[CompanyIntelligence],
    output_path: Union[str, Path]
) -> Path:
    path = Path(output_path)
    data = [record.model_dump() for record in records]

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {len(records)} records to JSON: {path.resolve()}")
    return path


def export_to_csv(
    records: List[CompanyIntelligence],
    output_path: Union[str, Path]
) -> Path:
    path = Path(output_path)

    fieldnames = [
        "domain",
        "company_name",
        "company_overview",
        "target_audience_icp",
        "contact_points",
        "key_leadership",
        "data_confidence_score",
        "confidence_reasoning",
        "total_tokens",
        "estimated_cost_usd"
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for record in records:
            leadership_str = "; ".join(
                f"{m.name} ({m.role})" + (f" [{m.linkedin_url}]" if m.linkedin_url else "")
                for m in record.key_leadership
            )

            tokens = record.metadata.total_tokens if record.metadata else 0
            cost = record.metadata.estimated_cost_usd if record.metadata else 0.0

            writer.writerow({
                "domain": record.domain,
                "company_name": record.company_name,
                "company_overview": record.company_overview,
                "target_audience_icp": record.target_audience_icp,
                "contact_points": "; ".join(record.contact_points),
                "key_leadership": leadership_str,
                "data_confidence_score": record.data_confidence_score,
                "confidence_reasoning": record.confidence_reasoning,
                "total_tokens": tokens,
                "estimated_cost_usd": f"${cost:.6f}"
            })

    logger.info(f"Saved {len(records)} records to CSV: {path.resolve()}")
    return path
