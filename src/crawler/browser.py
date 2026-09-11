from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Playwright
from src.config import settings
from src.utils.logger import logger


STEALTH_JS = """
// Mask webdriver detection flag
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});

// Emulate regular desktop languages and plugin list
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en']
});

Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5]
});
"""

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class BrowserManager:
    """Manages the shared Playwright browser instance."""

    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

    async def start(self) -> None:
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=settings.browser_headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--no-first-run",
                    "--no-zygote",
                    "--disable-gpu",
                ]
            )

    async def create_stealth_context(self) -> BrowserContext:
        if not self._browser:
            await self.start()

        assert self._browser is not None

        context = await self._browser.new_context(
            user_agent=DEFAULT_USER_AGENT,
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True,
            bypass_csp=True,
            java_script_enabled=True,
            locale="en-US",
            timezone_id="America/New_York",
        )

        await context.add_init_script(STEALTH_JS)
        return context

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None


browser_manager = BrowserManager()
