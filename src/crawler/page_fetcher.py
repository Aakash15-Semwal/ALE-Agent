from dataclasses import dataclass
from typing import Optional
from playwright.async_api import BrowserContext, TimeoutError as PlaywrightTimeoutError
from src.config import settings
from src.utils.logger import logger


@dataclass
class FetchedPage:
    url: str
    final_url: str
    status_code: int
    html: str
    success: bool
    error_message: Optional[str] = None


async def fetch_page(
    context: BrowserContext,
    url: str,
    timeout_ms: Optional[int] = None
) -> FetchedPage:
    timeout = timeout_ms or settings.page_load_timeout_ms
    page = await context.new_page()

    target_url = url if url.startswith(("http://", "https://")) else f"https://{url}"

    try:
        logger.debug(f"Fetching URL: {target_url} (Timeout: {timeout}ms)")

        response = await page.goto(
            target_url,
            wait_until="domcontentloaded",
            timeout=timeout
        )

        # Give client-side frameworks a moment to hydrate
        try:
            await page.wait_for_load_state("networkidle", timeout=min(5000, timeout // 2))
        except PlaywrightTimeoutError:
            logger.debug(f"Networkidle reached timeout for {target_url}; proceeding with current DOM.")

        status_code = response.status if response else 200
        final_url = page.url
        html_content = await page.content()

        # Check for challenge or captcha pages
        page_title = (await page.title()).lower()
        if any(term in page_title for term in ("just a moment...", "cloudflare", "ddos-guard", "attention required")):
            logger.warning(f"Possible anti-bot challenge encountered on {target_url}")

        logger.debug(f"Retrieved {target_url} (Status: {status_code}, length: {len(html_content)})")
        return FetchedPage(
            url=target_url,
            final_url=final_url,
            status_code=status_code,
            html=html_content,
            success=True
        )

    except PlaywrightTimeoutError as e:
        logger.warning(f"Timeout while loading {target_url}: {str(e)}")
        # Check if partial DOM was rendered before timing out
        try:
            partial_html = await page.content()
            if partial_html and len(partial_html) > 500:
                return FetchedPage(
                    url=target_url,
                    final_url=page.url or target_url,
                    status_code=408,
                    html=partial_html,
                    success=True,
                    error_message="Partial content retrieved after timeout"
                )
        except Exception:
            pass

        return FetchedPage(
            url=target_url,
            final_url=target_url,
            status_code=408,
            html="",
            success=False,
            error_message=f"Navigation timed out after {timeout}ms"
        )

    except Exception as e:
        logger.warning(f"Failed to fetch {target_url}: {type(e).__name__} - {str(e)}")
        return FetchedPage(
            url=target_url,
            final_url=target_url,
            status_code=500,
            html="",
            success=False,
            error_message=str(e)
        )

    finally:
        await page.close()
