import re
from typing import List, Optional, Tuple

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

from src.config import settings
from src.utils.logger import logger
from src.models import TeamMember

LINKEDIN_PROFILE_REGEX = re.compile(
    r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/in/([a-zA-Z0-9_-]+)/?",
    re.IGNORECASE
)


def extract_linkedin_profile_url(text: str) -> Optional[str]:
    match = LINKEDIN_PROFILE_REGEX.search(text)
    if match:
        handle = match.group(1)
        if handle.lower() not in ("company", "feed", "posts", "pulse", "jobs"):
            return f"https://www.linkedin.com/in/{handle}"
    return None


def parse_name_and_role_from_title(title: str, default_company: str) -> Tuple[str, str]:
    # Parse standard search snippet formats like "Name - Role at Company | LinkedIn"
    clean_title = title.replace("| LinkedIn", "").replace("- LinkedIn", "").strip()
    parts = [p.strip() for p in clean_title.split("-") if p.strip()]

    if len(parts) >= 2:
        return parts[0], parts[1]
    elif len(parts) == 1:
        return parts[0], "Founder / Executive"
    return f"{default_company} Founder/CEO", "Founder / Executive"


def search_founder_linkedin(
    company_name: str,
    leader_name: Optional[str] = None
) -> Optional[Tuple[str, Optional[str], Optional[str]]]:
    if not settings.enable_search_fallback:
        return None

    query = (
        f"{leader_name} {company_name} linkedin"
        if leader_name
        else f"{company_name} founder CEO linkedin"
    )

    logger.debug(f"Search fallback query: {query}")

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))

        for result in results:
            url = result.get("href", "")
            title = result.get("title", "")
            body = result.get("body", "")

            candidate_url = extract_linkedin_profile_url(url) or extract_linkedin_profile_url(body)
            if candidate_url:
                parsed_name, parsed_role = parse_name_and_role_from_title(title, company_name)
                logger.info(
                    f"External search discovered profile for {leader_name or company_name}: "
                    f"{candidate_url} ({parsed_name})"
                )
                return candidate_url, parsed_name, parsed_role

    except Exception as e:
        logger.warning(f"Search fallback failed for {query}: {type(e).__name__} - {str(e)}")

    return None


def enrich_leadership_with_search(
    company_name: str,
    leadership: List[TeamMember]
) -> List[TeamMember]:
    enriched: List[TeamMember] = []

    for member in leadership:
        if not member.linkedin_url:
            res = search_founder_linkedin(company_name=company_name, leader_name=member.name)
            if res:
                found_url, _, _ = res
                member.linkedin_url = found_url
        enriched.append(member)

    # If leadership section was empty on site, search for company founder
    if not enriched:
        res = search_founder_linkedin(company_name=company_name, leader_name=None)
        if res:
            found_url, parsed_name, parsed_role = res
            enriched.append(TeamMember(
                name=parsed_name or f"{company_name} Founder",
                role=parsed_role or "Founder / Executive",
                linkedin_url=found_url
            ))

    return enriched
