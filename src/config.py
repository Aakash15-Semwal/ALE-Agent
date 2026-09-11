import os
from pathlib import Path
from typing import Literal, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH if ENV_PATH.exists() else None)


class Settings(BaseModel):
    default_llm_provider: Literal["gemini", "openai", "groq"] = "gemini"

    gemini_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY"))
    openai_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    groq_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("GROQ_API_KEY"))

    llm_model_name: Optional[str] = Field(default_factory=lambda: os.getenv("LLM_MODEL_NAME") or None)

    browser_headless: bool = Field(
        default_factory=lambda: os.getenv("BROWSER_HEADLESS", "true").lower() in ("true", "1", "yes")
    )
    page_load_timeout_ms: int = Field(default_factory=lambda: int(os.getenv("PAGE_LOAD_TIMEOUT_MS", "20000")))
    max_subpages_per_domain: int = Field(default_factory=lambda: int(os.getenv("MAX_SUBPAGES_PER_DOMAIN", "3")))
    max_concurrent_pages: int = Field(default_factory=lambda: int(os.getenv("MAX_CONCURRENT_PAGES", "2")))

    enable_search_fallback: bool = Field(
        default_factory=lambda: os.getenv("ENABLE_SEARCH_FALLBACK", "true").lower() in ("true", "1", "yes")
    )
    enable_cost_tracking: bool = Field(
        default_factory=lambda: os.getenv("ENABLE_COST_TRACKING", "true").lower() in ("true", "1", "yes")
    )

    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper())

    project_root: Path = BASE_DIR
    output_json_path: Path = BASE_DIR / "output.json"
    output_csv_path: Path = BASE_DIR / "output.csv"

    def get_active_model_name(self) -> str:
        if self.llm_model_name:
            return self.llm_model_name

        defaults = {
            "gemini": "gemini-3.6-flash",
            "openai": "gpt-4o-mini",
            "groq": "llama-3.3-70b-versatile",
        }
        return defaults.get(self.default_llm_provider, "gemini-3.6-flash")

    def validate_active_provider_key(self) -> None:
        key_map = {
            "gemini": (self.gemini_api_key, "GEMINI_API_KEY"),
            "openai": (self.openai_api_key, "OPENAI_API_KEY"),
            "groq": (self.groq_api_key, "GROQ_API_KEY"),
        }
        val, name = key_map.get(self.default_llm_provider, (None, ""))
        if not val:
            raise ValueError(f"{name} is missing. Add it to .env or pass --provider with a configured model.")


settings = Settings(
    default_llm_provider=os.getenv("DEFAULT_LLM_PROVIDER", "gemini").lower()  # type: ignore
)
