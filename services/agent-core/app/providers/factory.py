from typing import Literal

from app.providers.anthropic import AnthropicProvider
from app.providers.base import BaseProvider
from app.providers.gemini import GeminiProvider
from app.providers.ollama import OllamaProvider
from app.providers.openai import OpenAIProvider

ProviderType = Literal["ollama", "anthropic", "openai", "gemini"]


class ProviderFactory:
    """Factory for creating AI provider instances."""

    PROVIDERS = {
        "ollama": OllamaProvider,
        "anthropic": AnthropicProvider,
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
    }

    @classmethod
    def create(
        cls,
        provider_type: ProviderType,
        **kwargs,
    ) -> BaseProvider:
        """
        Create a provider instance.

        Args:
            provider_type: The type of provider to create
            **kwargs: Provider-specific configuration

        Returns:
            A configured provider instance

        Raises:
            ValueError: If provider_type is not supported

        Examples:
            # Create Ollama provider
            provider = ProviderFactory.create(
                "ollama",
                host="http://localhost:11434",
                model="llama3.2"
            )

            # Create Claude provider
            provider = ProviderFactory.create(
                "anthropic",
                api_key="sk-ant-...",
                model="claude-3-5-sonnet-20241022"
            )

            # Create OpenAI provider
            provider = ProviderFactory.create(
                "openai",
                api_key="sk-...",
                model="gpt-4o"
            )

            # Create Gemini provider
            provider = ProviderFactory.create(
                "gemini",
                api_key="...",
                model="gemini-1.5-pro"
            )
        """
        if provider_type not in cls.PROVIDERS:
            raise ValueError(
                f"Unknown provider type: {provider_type}. Supported: {list(cls.PROVIDERS.keys())}"
            )

        provider_class = cls.PROVIDERS[provider_type]
        return provider_class(**kwargs)

    @classmethod
    def get_supported_providers(cls) -> list[str]:
        """Return list of supported provider types."""
        return list(cls.PROVIDERS.keys())

    @classmethod
    def get_provider_info(cls, provider_type: ProviderType) -> dict:
        """Get info about a provider type."""
        if provider_type not in cls.PROVIDERS:
            raise ValueError(f"Unknown provider type: {provider_type}")

        provider_class = cls.PROVIDERS[provider_type]
        return {
            "type": provider_type,
            "name": provider_class.provider_name,
            "supports_streaming": provider_class.supports_streaming,
        }


def create_provider(provider_type: ProviderType, **kwargs) -> BaseProvider:
    """Convenience function for creating providers."""
    return ProviderFactory.create(provider_type, **kwargs)
