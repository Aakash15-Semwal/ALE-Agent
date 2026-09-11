from typing import List, Set, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from src.utils.logger import logger

PRIORITY_KEYWORDS = {
    # Team & Leadership
    "about": 10,
    "about-us": 10,
    "team": 12,
    "leadership": 12,
    "company": 8,
    "founders": 12,
    "people": 8,
    "our-team": 12,
    # Contact
    "contact": 10,
    "contact-us": 10,
    "reach-us": 9,
    "support": 6,
    # Pricing & Product
    "pricing": 9,
    "product": 7,
    "platform": 7,
    "features": 6,
}

IGNORE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
    ".pdf", ".zip", ".tar", ".gz", ".mp4", ".mp3", ".wav",
    ".css", ".js", ".json", ".xml", ".txt"
}


def normalize_url(base_url: str, link_href: str) -> str:
    absolute = urljoin(base_url, link_href.strip())
    parsed = urlparse(absolute)
    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    return clean_url.rstrip("/") if clean_url.endswith("/") and len(parsed.path) > 1 else clean_url


def is_valid_internal_url(base_domain: str, candidate_url: str) -> bool:
    base_netloc = urlparse(base_domain if base_domain.startswith("http") else f"https://{base_domain}").netloc.lower()
    candidate_parsed = urlparse(candidate_url)
    candidate_netloc = candidate_parsed.netloc.lower()

    if candidate_netloc != base_netloc and not candidate_netloc.endswith(f".{base_netloc}"):
        return False

    path = candidate_parsed.path.lower()
    if any(path.endswith(ext) for ext in IGNORE_EXTENSIONS):
        return False

    if candidate_parsed.scheme not in ("http", "https"):
        return False

    return True


def score_link(url: str, anchor_text: str) -> int:
    score = 0
    url_lower = url.lower()
    text_lower = anchor_text.lower()

    for keyword, weight in PRIORITY_KEYWORDS.items():
        if keyword in url_lower:
            score += weight
        if keyword in text_lower:
            score += weight

    return score


def discover_priority_subpages(
    html_content: str,
    base_url: str,
    max_pages: int = 3
) -> List[str]:
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, "html.parser")
    seen_urls: Set[str] = set()
    scored_links: List[Tuple[int, str]] = []

    base_clean = base_url.rstrip("/")

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        text = a_tag.get_text(strip=True)

        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue

        full_url = normalize_url(base_url, href)

        if full_url == base_clean or full_url == f"{base_clean}/":
            continue

        if full_url in seen_urls:
            continue

        if is_valid_internal_url(base_url, full_url):
            score = score_link(full_url, text)
            if score > 0:
                seen_urls.add(full_url)
                scored_links.append((score, full_url))

    scored_links.sort(key=lambda x: x[0], reverse=True)
    selected_urls = [url for _, url in scored_links[:max_pages]]
    logger.debug(f"Discovered {len(selected_urls)} priority subpages for {base_url}: {selected_urls}")
    return selected_urls
