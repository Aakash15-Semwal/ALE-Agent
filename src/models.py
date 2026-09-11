import re
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class TeamMember(BaseModel):
    name: str = Field(..., description="Full name of the executive or key team member")
    role: str = Field(..., description="Role or title (e.g. CEO, Head of Product)")
    linkedin_url: Optional[str] = Field(default=None, description="LinkedIn profile URL")

    @field_validator("name", "role")
    @classmethod
    def clean_text_fields(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty")
        return cleaned

    @field_validator("linkedin_url")
    @classmethod
    def validate_linkedin_url(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        cleaned = v.strip().rstrip("/")
        if "linkedin.com/in/" not in cleaned and "linkedin.com/company/" not in cleaned:
            # Handle raw handle inputs
            if re.match(r"^[a-zA-Z0-9_-]+$", cleaned):
                return f"https://www.linkedin.com/in/{cleaned}"
        return cleaned


class ExtractionMetadata(BaseModel):
    pages_crawled: List[str] = Field(default_factory=list)
    llm_provider: str = Field(default="gemini")
    model_name: str = Field(default="gemini-3.6-flash")
    prompt_tokens: int = Field(default=0)
    completion_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)
    estimated_cost_usd: float = Field(default=0.0)
    search_fallback_triggered: bool = Field(default=False)


class CompanyIntelligence(BaseModel):
    domain: str
    company_name: str
    company_overview: str = Field(
        ...,
        description="Concise 2-sentence summary of what the company does"
    )
    target_audience_icp: str = Field(
        ...,
        description="Who their product is built for"
    )
    contact_points: List[str] = Field(
        default_factory=list,
        description="Generic or public contact emails (sales@, support@, etc.)"
    )
    key_leadership: List[TeamMember] = Field(
        default_factory=list,
        description="Founders, executives, or core leadership"
    )
    data_confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score from 0.0 to 1.0"
    )
    confidence_reasoning: str
    metadata: Optional[ExtractionMetadata] = None

    @field_validator("contact_points")
    @classmethod
    def clean_contact_emails(cls, emails: List[str]) -> List[str]:
        seen = set()
        cleaned_list = []
        for email in emails:
            e = email.strip().lower()
            if e and e not in seen:
                seen.add(e)
                cleaned_list.append(e)
        return cleaned_list

    @field_validator("company_overview")
    @classmethod
    def validate_overview(cls, v: str) -> str:
        cleaned = v.strip()
        return cleaned or "Company overview unavailable."
