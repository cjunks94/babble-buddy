"""Tests for AI providers."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.providers import (
    BaseProvider,
    OllamaProvider,
    AnthropicProvider,
    OpenAIProvider,
    GeminiProvider,
    ProviderFactory,
    create_provider,
)


class TestProviderFactory:
    """Test the provider factory."""

    def test_create_ollama_provider(self):
        """Should create Ollama provider."""
        provider = create_provider(
            "ollama",
            host="http://localhost:11434",
            model="llama3.2",
        )
        assert isinstance(provider, OllamaProvider)
        assert provider.provider_name == "ollama"

    def test_create_anthropic_provider(self):
        """Should create Anthropic provider."""
        provider = create_provider(
            "anthropic",
            api_key="test-key",
            model="claude-3-5-sonnet-20241022",
        )
        assert isinstance(provider, AnthropicProvider)
        assert provider.provider_name == "anthropic"

    def test_create_openai_provider(self):
        """Should create OpenAI provider."""
        provider = create_provider(
            "openai",
            api_key="test-key",
            model="gpt-4o",
        )
        assert isinstance(provider, OpenAIProvider)
        assert provider.provider_name == "openai"

    def test_create_gemini_provider(self):
        """Should create Gemini provider."""
        provider = create_provider(
            "gemini",
            api_key="test-key",
            model="gemini-1.5-flash",
        )
        assert isinstance(provider, GeminiProvider)
        assert provider.provider_name == "gemini"

    def test_raises_for_unknown_provider(self):
        """Should raise ValueError for unknown provider type."""
        with pytest.raises(ValueError) as exc_info:
            create_provider("unknown", api_key="test")
        assert "Unknown provider type" in str(exc_info.value)

    def test_get_supported_providers(self):
        """Should return list of supported providers."""
        providers = ProviderFactory.get_supported_providers()
        assert "ollama" in providers
        assert "anthropic" in providers
        assert "openai" in providers
        assert "gemini" in providers


class TestAnthropicProvider:
    """Test Anthropic (Claude) provider."""

    @pytest.fixture
    def provider(self):
        return AnthropicProvider(
            api_key="test-key",
            model="claude-3-5-sonnet-20241022",
            max_tokens=100,
        )

    def test_provider_metadata(self, provider):
        """Should have correct metadata."""
        assert provider.provider_name == "anthropic"
        assert provider.supports_streaming is True

    def test_format_messages_simple(self, provider):
        """Should format simple message correctly."""
        messages = provider._format_messages("Hello")
        assert messages == [{"role": "user", "content": "Hello"}]

    def test_format_messages_with_history(self, provider):
        """Should include message history."""
        history = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ]
        messages = provider._format_messages("How are you?", messages=history)
        assert len(messages) == 3
        assert messages[0]["content"] == "Hi"
        assert messages[1]["content"] == "Hello!"
        assert messages[2]["content"] == "How are you?"

    def test_format_messages_skips_system(self, provider):
        """Should skip system messages in history (handled separately)."""
        history = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hi"},
        ]
        messages = provider._format_messages("Hello", messages=history)
        assert len(messages) == 2
        assert messages[0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_generate_makes_correct_request(
        self, provider, mock_anthropic_response
    ):
        """Should make correct API request."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_anthropic_response
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            provider.client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = mock_response

            result = await provider.generate(
                "Hello", system_prompt="Be helpful"
            )

            assert result == "Hello from Claude!"
            mock_post.assert_called_once()

            # Check request payload
            call_kwargs = mock_post.call_args
            payload = call_kwargs.kwargs["json"]
            assert payload["model"] == "claude-3-5-sonnet-20241022"
            assert payload["system"] == "Be helpful"
            assert "x-api-key" in call_kwargs.kwargs["headers"]

    def test_get_info(self, provider):
        """Should return provider info."""
        info = provider.get_info()
        assert info["provider"] == "anthropic"
        assert info["model"] == "claude-3-5-sonnet-20241022"
        assert info["max_tokens"] == 100


class TestOpenAIProvider:
    """Test OpenAI (GPT) provider."""

    @pytest.fixture
    def provider(self):
        return OpenAIProvider(
            api_key="test-key",
            model="gpt-4o",
            max_tokens=100,
        )

    def test_provider_metadata(self, provider):
        """Should have correct metadata."""
        assert provider.provider_name == "openai"
        assert provider.supports_streaming is True

    def test_format_messages_with_system(self, provider):
        """Should include system prompt first."""
        messages = provider._format_messages(
            "Hello",
            system_prompt="Be helpful",
        )
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "Be helpful"
        assert messages[1]["role"] == "user"

    def test_custom_base_url(self):
        """Should support custom base URL for compatible APIs."""
        provider = OpenAIProvider(
            api_key="test-key",
            base_url="https://custom-api.example.com/v1/chat/completions",
        )
        assert "custom-api.example.com" in provider.base_url

    @pytest.mark.asyncio
    async def test_generate_makes_correct_request(
        self, provider, mock_openai_response
    ):
        """Should make correct API request."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_openai_response
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            provider.client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = mock_response

            result = await provider.generate("Hello")

            assert result == "Hello from GPT!"
            mock_post.assert_called_once()


class TestGeminiProvider:
    """Test Gemini provider."""

    @pytest.fixture
    def provider(self):
        return GeminiProvider(
            api_key="test-key",
            model="gemini-1.5-flash",
            max_tokens=100,
        )

    def test_provider_metadata(self, provider):
        """Should have correct metadata."""
        assert provider.provider_name == "gemini"
        assert provider.supports_streaming is True

    def test_format_contents_simple(self, provider):
        """Should format simple message correctly."""
        contents, system = provider._format_contents("Hello")
        assert len(contents) == 1
        assert contents[0]["role"] == "user"
        assert contents[0]["parts"][0]["text"] == "Hello"
        assert system is None

    def test_format_contents_with_system(self, provider):
        """Should handle system prompt separately."""
        contents, system = provider._format_contents(
            "Hello", system_prompt="Be helpful"
        )
        assert system is not None
        assert system["parts"][0]["text"] == "Be helpful"

    def test_format_contents_converts_roles(self, provider):
        """Should convert 'assistant' to 'model' for Gemini."""
        history = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ]
        contents, _ = provider._format_contents("How are you?", messages=history)
        assert contents[1]["role"] == "model"  # converted from assistant

    @pytest.mark.asyncio
    async def test_generate_makes_correct_request(
        self, provider, mock_gemini_response
    ):
        """Should make correct API request."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_gemini_response
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            provider.client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = mock_response

            result = await provider.generate("Hello")

            assert result == "Hello from Gemini!"
            mock_post.assert_called_once()


class TestOllamaProvider:
    """Test Ollama provider."""

    @pytest.fixture
    def provider(self):
        return OllamaProvider(
            host="http://localhost:11434",
            model="llama3.2",
            max_tokens=100,
        )

    def test_provider_metadata(self, provider):
        """Should have correct metadata."""
        assert provider.provider_name == "ollama"
        assert provider.supports_streaming is True

    def test_get_info(self, provider):
        """Should return provider info."""
        info = provider.get_info()
        assert info["provider"] == "ollama"
        assert info["supports_streaming"] is True
