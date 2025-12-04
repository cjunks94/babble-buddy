"""Shared test fixtures."""

import os
import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def reset_settings():
    """Reset settings between tests."""
    # Clear any cached settings
    from app import config

    # Store original
    original = config.settings

    yield

    # Restore (in case tests modified it)
    config.settings = original


@pytest.fixture
def enable_multi_agent():
    """Enable multi-agent feature for a test."""
    with patch.dict(os.environ, {"FEATURE_MULTI_AGENT": "true"}):
        # Reload settings
        from app.config import Settings
        with patch("app.config.settings", Settings()):
            yield


@pytest.fixture
def enable_external_providers():
    """Enable external providers feature for a test."""
    with patch.dict(os.environ, {"FEATURE_EXTERNAL_PROVIDERS": "true"}):
        from app.config import Settings
        with patch("app.config.settings", Settings()):
            yield


@pytest.fixture
def mock_anthropic_response():
    """Mock Anthropic API response."""
    return {
        "content": [{"type": "text", "text": "Hello from Claude!"}],
        "model": "claude-3-5-sonnet-20241022",
        "stop_reason": "end_turn",
    }


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    return {
        "choices": [
            {
                "message": {"role": "assistant", "content": "Hello from GPT!"},
                "finish_reason": "stop",
            }
        ],
        "model": "gpt-4o",
    }


@pytest.fixture
def mock_gemini_response():
    """Mock Gemini API response."""
    return {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "Hello from Gemini!"}],
                    "role": "model",
                }
            }
        ]
    }
