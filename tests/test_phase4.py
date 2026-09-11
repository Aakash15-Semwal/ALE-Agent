import json
from pathlib import Path
from src.bonus.cost_tracker import calculate_cost, TokenCostTracker
from src.bonus.search_fallback import extract_linkedin_profile_url
from src.utils.exporter import export_to_json, export_to_csv
from src.models import CompanyIntelligence, TeamMember, ExtractionMetadata


def test_cost_calculation():
    cost_gemini = calculate_cost(
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
        model_name="gemini-1.5-flash"
    )
    assert cost_gemini == 0.375

    cost_small = calculate_cost(
        prompt_tokens=2_000,
        completion_tokens=500,
        model_name="gemini-1.5-flash"
    )
    assert cost_small == 0.0003


def test_token_cost_tracker():
    tracker = TokenCostTracker()
    cost = tracker.record_usage("postman.com", "gemini-1.5-flash", 2000, 500)
    assert cost == 0.0003
    assert tracker.total_prompt_tokens == 2000
    assert tracker.total_completion_tokens == 500
    assert tracker.total_tokens == 2500

    table = tracker.create_summary_table()
    assert table is not None
    assert table.title == "LLM Token & Cost Accounting Summary"


def test_extract_linkedin_profile_url():
    raw_text = "Check out our CEO at https://www.linkedin.com/in/abhinavasthana/ and connect."
    url = extract_linkedin_profile_url(raw_text)
    assert url == "https://www.linkedin.com/in/abhinavasthana"

    assert extract_linkedin_profile_url("https://linkedin.com/company/postman") is None
    assert extract_linkedin_profile_url("https://linkedin.com/feed") is None


def test_exporters(tmp_path: Path):
    sample_records = [
        CompanyIntelligence(
            domain="example.com",
            company_name="Example Corp",
            company_overview="Example Corp provides testing tools. It enables fast validation.",
            target_audience_icp="Developers",
            contact_points=["hello@example.com"],
            key_leadership=[TeamMember(name="Alice", role="CEO", linkedin_url="https://linkedin.com/in/alice")],
            data_confidence_score=0.9,
            confidence_reasoning="Complete data.",
            metadata=ExtractionMetadata(
                pages_crawled=["https://example.com"],
                prompt_tokens=1500,
                completion_tokens=300,
                total_tokens=1800,
                estimated_cost_usd=0.0002
            )
        )
    ]

    json_file = tmp_path / "test_out.json"
    csv_file = tmp_path / "test_out.csv"

    export_to_json(sample_records, json_file)
    export_to_csv(sample_records, csv_file)

    assert json_file.exists()
    assert csv_file.exists()

    with open(json_file, "r", encoding="utf-8") as f:
        loaded_json = json.load(f)
        assert len(loaded_json) == 1
        assert loaded_json[0]["domain"] == "example.com"
        assert loaded_json[0]["company_name"] == "Example Corp"

    with open(csv_file, "r", encoding="utf-8") as f:
        content = f.read()
        assert "example.com" in content
        assert "Example Corp" in content
        assert "hello@example.com" in content
        assert "Alice (CEO) [https://linkedin.com/in/alice]" in content
