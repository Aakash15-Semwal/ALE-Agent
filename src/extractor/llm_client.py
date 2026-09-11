from dataclasses import dataclass
from tenacity import retry, stop_after_attempt, wait_exponential
from src.config import settings
from src.utils.logger import logger
from src.extractor.prompts import SYSTEM_PROMPT


@dataclass
class LLMResponse:
    raw_json: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    provider: str
    model_name: str


class LLMClient:
    def __init__(self):
        self.provider = settings.default_llm_provider
        self.model_name = settings.get_active_model_name()

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1.5, min=2, max=10)
    )
    def complete(self, user_prompt: str) -> LLMResponse:
        logger.debug(f"Invoking LLM provider: {self.provider} ({self.model_name})")

        if self.provider == "gemini":
            return self._call_gemini(user_prompt)
        elif self.provider == "openai":
            return self._call_openai(user_prompt)
        elif self.provider == "groq":
            return self._call_groq(user_prompt)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def _call_gemini(self, user_prompt: str) -> LLMResponse:
        from google import genai
        from google.genai import types

        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not set.")

        client = genai.Client(api_key=settings.gemini_api_key)

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.1
        )

        response = client.models.generate_content(
            model=self.model_name,
            contents=user_prompt,
            config=config
        )

        raw_text = response.text or "{}"

        prompt_tokens = 0
        completion_tokens = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
            completion_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0

        return LLMResponse(
            raw_json=raw_text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            provider="gemini",
            model_name=self.model_name
        )

    def _call_openai(self, user_prompt: str) -> LLMResponse:
        from openai import OpenAI

        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set.")

        client = OpenAI(api_key=settings.openai_api_key)

        response = client.chat.completions.create(
            model=self.model_name,
            response_format={"type": "json_object"},
            temperature=0.1,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
        )

        content = response.choices[0].message.content or "{}"
        usage = response.usage

        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0

        return LLMResponse(
            raw_json=content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            provider="openai",
            model_name=self.model_name
        )

    def _call_groq(self, user_prompt: str) -> LLMResponse:
        from groq import Groq

        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is not set.")

        client = Groq(api_key=settings.groq_api_key)

        response = client.chat.completions.create(
            model=self.model_name,
            response_format={"type": "json_object"},
            temperature=0.1,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
        )

        content = response.choices[0].message.content or "{}"
        usage = response.usage

        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0

        return LLMResponse(
            raw_json=content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            provider="groq",
            model_name=self.model_name
        )


llm_client = LLMClient()
