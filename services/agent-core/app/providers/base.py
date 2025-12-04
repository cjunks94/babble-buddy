from abc import ABC, abstractmethod
from typing import AsyncGenerator


class BaseProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        pass

    @abstractmethod
    async def generate_stream(
        self, prompt: str, system_prompt: str | None = None
    ) -> AsyncGenerator[str, None]:
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        pass
