from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator


class BaseProvider(ABC):
    """Base class for AI providers (Ollama, Claude, OpenAI, Gemini, etc.)"""

    # Provider metadata
    provider_name: str = "base"
    supports_streaming: bool = True

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        messages: list[dict] | None = None,
    ) -> str:
        """Generate a response from the model."""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        messages: list[dict] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response from the model."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is available and working."""
        pass

    async def close(self) -> None:
        """Clean up resources. Override if needed."""
        pass

    def get_info(self) -> dict:
        """Return provider info for debugging."""
        return {
            "provider": self.provider_name,
            "supports_streaming": self.supports_streaming,
        }
