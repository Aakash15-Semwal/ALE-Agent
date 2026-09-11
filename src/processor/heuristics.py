import re
from dataclasses import dataclass, field
from typing import List, Set
from bs4 import BeautifulSoup
from src.utils.logger import logger

EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")

LINKEDIN_PROFILE_REGEX = re.compile(
    r"https?://(?:www\.)?linkedin\.com/in/([a-zA-Z0-9_-]+)/?",
    re.IGNORECASE
)

LINKEDIN_COMPANY_REGEX = re.compile(
    r"https?://(?:www\.)?linkedin\.com/company/([a-zA-Z0-9_-]+)/?",
    re.IGNORECASE
)

# Common false positive domains & placeholder image artifacts
DISALLOWED_EMAIL_DOMAINS = {
    "example.com", "yourdomain.com", "domain.com", "test.com",
    "sentry.io", "wixpress.com", "schema.org"
}

DISALLOWED_EMAIL_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".css", ".js"
}


@dataclass
class ExtractedHeuristics:
    emails: List[str] = field(default_factory=list)
    linkedin_profiles: List[str] = field(default_factory=list)
    linkedin_company_urls: List[str] = field(default_factory=list)


def extract_heuristics(raw_html: str, domain: str = "") -> ExtractedHeuristics:
    """Extracts candidate emails and LinkedIn URLs from HTML markup and text nodes."""
    if not raw_html:
        return ExtractedHeuristics()

    soup = BeautifulSoup(raw_html, "html.parser")
    found_emails: Set[str] = set()
    found_profiles: Set[str] = set()
    found_companies: Set[str] = set()

    # Direct mailto links and explicit anchor hrefs
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.lower().startswith("mailto:"):
            raw_email = href.split(":", 1)[1].split("?")[0].strip()
            if EMAIL_REGEX.match(raw_email):
                found_emails.add(raw_email.lower())

        if "linkedin.com" in href:
            clean_href = href.split("?")[0].rstrip("/")
            if "/in/" in clean_href:
                found_profiles.add(clean_href)
            elif "/company/" in clean_href:
                found_companies.add(clean_href)

    # General text node regex scan
    full_text = soup.get_text(" ")
    for match in EMAIL_REGEX.findall(full_text):
        match_lower = match.lower()
        parts = match_lower.split("@")
        if len(parts) == 2:
            username, email_domain = parts
            # Filter image assets that look like emails (e.g. icon@2x.png)
            if any(email_domain.endswith(ext) for ext in DISALLOWED_EMAIL_EXTENSIONS):
                continue
            if email_domain in DISALLOWED_EMAIL_DOMAINS:
                continue
            if username in ("name", "user", "email", "someone", "john.doe"):
                continue
            found_emails.add(match_lower)

    # Catch LinkedIn URLs referenced in data attributes or script payloads
    for profile_match in LINKEDIN_PROFILE_REGEX.findall(raw_html):
        clean_url = f"https://www.linkedin.com/in/{profile_match}".rstrip("/")
        found_profiles.add(clean_url)

    for company_match in LINKEDIN_COMPANY_REGEX.findall(raw_html):
        clean_url = f"https://www.linkedin.com/company/{company_match}".rstrip("/")
        found_companies.add(clean_url)

    logger.debug(
        f"Heuristic extraction complete: {len(found_emails)} emails, "
        f"{len(found_profiles)} LinkedIn profiles found."
    )

    return ExtractedHeuristics(
        emails=sorted(list(found_emails)),
        linkedin_profiles=sorted(list(found_profiles)),
        linkedin_company_urls=sorted(list(found_companies))
    )
