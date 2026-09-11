import re
from bs4 import BeautifulSoup
import trafilatura
from src.utils.logger import logger


def html_to_markdown_fallback(soup: BeautifulSoup) -> str:
    lines = []

    for elem in soup.find_all(["h1", "h2", "h3", "h4", "p", "li", "a", "tr"]):
        tag = elem.name
        text = elem.get_text(" ", strip=True)

        if not text or len(text) < 2:
            continue

        if tag == "h1":
            lines.append(f"\n# {text}\n")
        elif tag == "h2":
            lines.append(f"\n## {text}\n")
        elif tag in ("h3", "h4"):
            lines.append(f"\n### {text}\n")
        elif tag == "li":
            lines.append(f"- {text}")
        elif tag == "a":
            href = elem.get("href", "")
            if href and not href.startswith("#"):
                lines.append(f"[{text}]({href})")
            else:
                lines.append(text)
        else:
            lines.append(f"{text}\n")

    markdown_text = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", markdown_text).strip()


def convert_html_to_clean_markdown(
    cleaned_html: str,
    max_chars: int = 12000
) -> str:
    """Converts HTML to compact Markdown, truncating if over character budget."""
    if not cleaned_html:
        return ""

    # Try trafilatura first for clean article/prose extraction
    extracted = trafilatura.extract(
        cleaned_html,
        output_format="markdown",
        include_links=True,
        include_images=False,
        include_tables=True,
        no_fallback=False
    )

    if extracted and len(extracted.strip()) > 150:
        content = extracted.strip()
    else:
        # If trafilatura skips marketing grids, fall back to custom DOM traversal
        soup = BeautifulSoup(cleaned_html, "html.parser")
        content = html_to_markdown_fallback(soup)

    content = re.sub(r"[ \t]+", " ", content)
    content = re.sub(r"\n\s*\n", "\n\n", content).strip()

    if len(content) > max_chars:
        logger.debug(f"Content truncated from {len(content)} to {max_chars} chars.")
        content = content[:max_chars] + "\n\n...[Truncated]..."

    return content
