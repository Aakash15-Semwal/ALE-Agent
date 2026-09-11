SYSTEM_PROMPT = """You are an AI assistant extracting structured company intelligence from scraped website content.

Guidelines:
1. Rely strictly on the provided content. Do not invent leadership names, emails, or LinkedIn URLs.
2. Company Overview: Exactly 2 concise sentences explaining what the company builds or solves.
3. Target Audience / ICP: Clear description of who the product is designed for.
4. Contact Points: Public contact emails found on the site (support@, sales@, info@, etc.).
5. Key Leadership: Executive names, roles, and LinkedIn URLs if present in the text or detected heuristics.
6. Data Confidence Score: Float between 0.0 and 1.0 reflecting completeness:
   - 0.9 - 1.0: Full overview, explicit ICP, verified contacts, and leadership with LinkedIn links.
   - 0.7 - 0.8: Good overview and ICP, contacts found, partial leadership.
   - 0.4 - 0.6: Overview found, but missing contacts or leadership.
   - 0.0 - 0.3: Very sparse, blocked, or ambiguous content.
7. Return only a valid JSON object matching the requested schema.
"""

EXTRACTION_USER_PROMPT_TEMPLATE = """Extract structured company intelligence for domain: '{domain}'

### Detected DOM Heuristics:
- Emails: {heuristic_emails}
- LinkedIn URLs: {heuristic_linkedin}

### Cleaned Website Content:
{context_markdown}

### Expected JSON Format:
{{
  "domain": "{domain}",
  "company_name": "Company Name",
  "company_overview": "Two-sentence summary.",
  "target_audience_icp": "Target audience description.",
  "contact_points": ["contact@domain.com"],
  "key_leadership": [
    {{
      "name": "Full Name",
      "role": "Role / Title",
      "linkedin_url": "https://www.linkedin.com/in/username or null"
    }}
  ],
  "data_confidence_score": 0.85,
  "confidence_reasoning": "Reasoning for score."
}}
"""


def build_extraction_prompt(
    domain: str,
    context_markdown: str,
    heuristic_emails: list,
    heuristic_linkedin: list
) -> str:
    emails_str = ", ".join(heuristic_emails) if heuristic_emails else "None detected"
    linkedin_str = ", ".join(heuristic_linkedin) if heuristic_linkedin else "None detected"

    return EXTRACTION_USER_PROMPT_TEMPLATE.format(
        domain=domain,
        heuristic_emails=emails_str,
        heuristic_linkedin=linkedin_str,
        context_markdown=context_markdown
    )
