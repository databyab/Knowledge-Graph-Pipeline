from typing import Protocol


class LLMClient(Protocol):
    def complete(self, system: str, user: str) -> str: ...

    def invalidate(self, system: str, user: str) -> None: ...
