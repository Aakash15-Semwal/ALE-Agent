from bs4 import BeautifulSoup, Comment
from src.utils.logger import logger

STRIP_TAGS = {
    "script", "style", "svg", "canvas", "noscript", "iframe",
    "header", "footer", "nav", "form", "button", "input",
    "textarea", "select", "option", "picture", "source", "video", "audio"
}

NOISE_PATTERNS = [
    "cookie", "banner", "privacy-popup", "consent", "modal", "advertisement",
    "social-share", "newsletter-signup", "tracking", "promo-bar"
]

ALLOWED_ATTRS = {"href", "title", "alt"}


def prune_dom(raw_html: str) -> str:
    """Strips non-content tags, styles, scripts, and noise elements from raw HTML."""
    if not raw_html or not raw_html.strip():
        return ""

    soup = BeautifulSoup(raw_html, "html.parser")

    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    for tag_name in STRIP_TAGS:
        for element in soup.find_all(tag_name):
            try:
                element.decompose()
            except Exception:
                pass

    # Drop cookie banners, ads, and popups
    for element in soup.find_all(attrs={"class": True}):
        if not element or getattr(element, "attrs", None) is None:
            continue
        try:
            classes = " ".join(element.get("class", [])).lower()
            if any(noise in classes for noise in NOISE_PATTERNS):
                element.decompose()
        except Exception:
            pass

    for element in soup.find_all(attrs={"id": True}):
        if not element or getattr(element, "attrs", None) is None:
            continue
        try:
            elem_id = str(element.get("id", "")).lower()
            if any(noise in elem_id for noise in NOISE_PATTERNS):
                element.decompose()
        except Exception:
            pass

    for element in soup.find_all(attrs={"aria-hidden": "true"}):
        try:
            element.decompose()
        except Exception:
            pass

    for element in soup.find_all(style=True):
        if not element or getattr(element, "attrs", None) is None:
            continue
        try:
            style = str(element.get("style", "")).lower().replace(" ", "")
            if "display:none" in style or "visibility:hidden" in style:
                element.decompose()
        except Exception:
            pass

    # Keep only semantic attributes (href, alt, title) to save tokens
    for tag in soup.find_all():
        if not tag or getattr(tag, "attrs", None) is None:
            continue
        try:
            tag_attrs = list(tag.attrs.keys())
            for attr in tag_attrs:
                if attr not in ALLOWED_ATTRS:
                    del tag.attrs[attr]
        except Exception:
            pass

    cleaned_html = str(soup)
    logger.debug(f"DOM pruned: Raw length {len(raw_html)} -> Cleaned length {len(cleaned_html)}")
    return cleaned_html
