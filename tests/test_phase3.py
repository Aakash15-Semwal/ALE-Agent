from src.models import CompanyIntelligence, TeamMember
from src.extractor.schema_enforcer import (
    parse_and_validate_extraction,
    calculate_rubric_confidence,
    create_empty_fallback
)


def test_team_member_normalization():
    member = TeamMember(name="  Jane Doe  ", role=" CTO ", linkedin_url="janedoe")
    assert member.name == "Jane Doe"
    assert member.role == "CTO"
    assert member.linkedin_url == "https://www.linkedin.com/in/janedoe"


def test_company_intelligence_validation():
    data = {
        "domain": "supabase.com",
        "company_name": "Supabase",
        "company_overview": "Supabase is an open source Firebase alternative. It provides PostgreSQL databases with real-time subscriptions.",
        "target_audience_icp": "Developers and engineers building web and mobile backend applications.",
        "contact_points": ["SUPPORT@SUPABASE.COM", "support@supabase.com", "sales@supabase.com"],
        "key_leadership": [
            {"name": "Paul Copplestone", "role": "CEO", "linkedin_url": "https://www.linkedin.com/in/paulcopplestone"}
        ],
        "data_confidence_score": 0.9,
        "confidence_reasoning": "Complete overview, leadership, and contacts found."
    }

    ci = CompanyIntelligence(**data)
    assert ci.domain == "supabase.com"
    assert len(ci.contact_points) == 2
    assert "support@supabase.com" in ci.contact_points
    assert ci.key_leadership[0].name == "Paul Copplestone"
    assert 0.0 <= ci.data_confidence_score <= 1.0


def test_schema_enforcer_json_markdown():
    raw_markdown_json = """
    ```json
    {
        "domain": "postman.com",
        "company_name": "Postman",
        "company_overview": "Postman is an API platform for building and using APIs. It simplifies each step of the API lifecycle.",
        "target_audience_icp": "Software engineers and API developers.",
        "contact_points": ["help@postman.com"],
        "key_leadership": [
            {"name": "Abhinav Asthana", "role": "CEO", "linkedin_url": "https://www.linkedin.com/in/abhinavasthana"}
        ],
        "data_confidence_score": 0.95,
        "confidence_reasoning": "High completeness."
    }
    ```
    """
    res = parse_and_validate_extraction(raw_markdown_json, target_domain="postman.com")
    assert res.company_name == "Postman"
    assert "help@postman.com" in res.contact_points
    assert res.data_confidence_score >= 0.8


def test_rubric_confidence_calculation():
    score_full = calculate_rubric_confidence(
        overview="Acme is a cloud platform for scaling software microservices easily.",
        icp="Backend engineers.",
        contact_points=["contact@acme.com"],
        leadership=[TeamMember(name="Alice", role="CEO", linkedin_url="https://linkedin.com/in/alice")]
    )
    assert score_full == 1.0

    score_partial = calculate_rubric_confidence(
        overview="Acme is a cloud platform for scaling software microservices easily.",
        icp="Backend engineers.",
        contact_points=[],
        leadership=[]
    )
    assert score_partial == 0.50


def test_fallback_creation():
    fallback = create_empty_fallback("unreachable.com", "Connection timed out")
    assert fallback.domain == "unreachable.com"
    assert fallback.data_confidence_score == 0.0
    assert "Connection timed out" in fallback.confidence_reasoning
