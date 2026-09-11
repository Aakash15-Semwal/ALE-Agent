import pytest
from src.crawler.browser import browser_manager
from src.crawler.page_fetcher import fetch_page


@pytest.mark.asyncio
async def test_playwright_fetch_live():
    try:
        await browser_manager.start()
        context = await browser_manager.create_stealth_context()

        page_res = await fetch_page(context, "https://example.com", timeout_ms=15000)

        assert page_res.success is True
        assert page_res.status_code == 200
        assert "Example Domain" in page_res.html
        assert page_res.final_url.startswith("https://example.com")

        await context.close()
    finally:
        await browser_manager.close()
