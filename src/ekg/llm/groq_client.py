from typing import Any, cast

from ekg.extract.prompts import PROMPT_VERSION
from ekg.llm.base import LLMClient
from ekg.llm.cache import ResponseCache
from ekg.llm.limiter import RateLimiter


class GroqClient(LLMClient):
    def __init__(self, api_key: str, model: str, cache: ResponseCache, limiter: RateLimiter, timeout_seconds: float, max_output_tokens: int) -> None:
        from groq import APIError, Groq
        self.api_error = APIError
        self.client: Any = Groq(api_key=api_key)
        self.model, self.cache, self.limiter, self.timeout_seconds, self.max_output_tokens = model, cache, limiter, timeout_seconds, max_output_tokens
        self.last_finish_reason: str | None = None
        self.last_truncated = False

    def complete(self, system: str, user: str) -> str:
        key = self.cache.key("groq", self.model, PROMPT_VERSION, system, user)
        cached = self.cache.get(key)
        if cached is not None:
            return cached if cached.strip() else "[]"
        self.limiter.acquire(len(user.split()) + 256)
        try:
            response = self.client.chat.completions.create(model=self.model, temperature=0, max_tokens=self.max_output_tokens, timeout=self.timeout_seconds, messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
        except self.api_error as exc:
            raise RuntimeError("Groq request failed") from exc
        self.last_finish_reason = str(response.choices[0].finish_reason) if response.choices[0].finish_reason is not None else None
        self.last_truncated = self.last_finish_reason == "length"
        value = cast(str, response.choices[0].message.content or "[]").strip()
        self.cache.put(key, value)
        return value

    def invalidate(self, system: str, user: str) -> None:
        key = self.cache.key("groq", self.model, PROMPT_VERSION, system, user)
        self.cache.delete(key)
