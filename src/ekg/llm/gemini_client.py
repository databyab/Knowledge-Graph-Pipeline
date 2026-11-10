from typing import Any, cast

from ekg.extract.prompts import PROMPT_VERSION
from ekg.llm.base import LLMClient
from ekg.llm.cache import ResponseCache
from ekg.llm.limiter import RateLimiter


class GeminiClient(LLMClient):
    def __init__(self, api_key: str, model: str, cache: ResponseCache, limiter: RateLimiter, max_output_tokens: int) -> None:
        from google import genai
        self.client: Any = genai.Client(api_key=api_key)
        self.model, self.cache, self.limiter, self.max_output_tokens = model, cache, limiter, max_output_tokens
        self.last_finish_reason: str | None = None
        self.last_truncated = False

    def complete(self, system: str, user: str) -> str:
        key = self.cache.key("gemini", self.model, PROMPT_VERSION, system, user)
        cached = self.cache.get(key)
        if cached is not None:
            return cached if cached.strip() else "[]"
        self.limiter.acquire(len(user.split()) + 256)
        response = self.client.models.generate_content(model=self.model, contents=f"{system}\n{user}", config={"temperature": 0, "max_output_tokens": self.max_output_tokens})
        candidate = response.candidates[0] if response.candidates else None
        self.last_finish_reason = str(candidate.finish_reason) if candidate and candidate.finish_reason is not None else None
        self.last_truncated = self.last_finish_reason in {"MAX_TOKENS", "FinishReason.MAX_TOKENS"}
        value = cast(str, response.text or "[]").strip()
        self.cache.put(key, value)
        return value
