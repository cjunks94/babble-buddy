"""Tests for feature flag system."""

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.utils.features import (
    get_enabled_features,
    is_external_providers_enabled,
    is_feature_enabled,
    is_multi_agent_enabled,
    require_feature,
)


class TestFeatureFlags:
    """Test feature flag utilities."""

    def test_multi_agent_disabled_by_default(self):
        """Multi-agent should be disabled by default."""
        assert not is_multi_agent_enabled()

    def test_external_providers_disabled_by_default(self):
        """External providers should be disabled by default."""
        assert not is_external_providers_enabled()

    def test_is_feature_enabled_returns_false_for_unknown(self):
        """Unknown features should return False."""
        assert not is_feature_enabled("nonexistent_feature")

    def test_get_enabled_features_memory_by_default(self):
        """Memory feature should be enabled by default."""
        features = get_enabled_features()
        assert "memory" in features
        # multi_agent and external_providers should be disabled by default
        assert "multi_agent" not in features
        assert "external_providers" not in features

    @patch("app.utils.features.settings")
    def test_multi_agent_enabled_via_settings(self, mock_settings):
        """Multi-agent can be enabled via settings."""
        mock_settings.feature_multi_agent = True
        assert is_multi_agent_enabled()

    @patch("app.utils.features.settings")
    def test_external_providers_enabled_via_settings(self, mock_settings):
        """External providers can be enabled via settings."""
        mock_settings.feature_external_providers = True
        assert is_external_providers_enabled()


class TestRequireFeatureDecorator:
    """Test the require_feature decorator."""

    @pytest.mark.asyncio
    async def test_raises_403_when_feature_disabled(self):
        """Should raise 403 when feature is disabled."""

        @require_feature("multi_agent")
        async def protected_endpoint():
            return {"status": "ok"}

        with pytest.raises(HTTPException) as exc_info:
            await protected_endpoint()

        assert exc_info.value.status_code == 403
        assert "multi_agent" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.utils.features.is_feature_enabled", return_value=True)
    async def test_allows_when_feature_enabled(self, mock_enabled):
        """Should allow access when feature is enabled."""

        @require_feature("multi_agent")
        async def protected_endpoint():
            return {"status": "ok"}

        result = await protected_endpoint()
        assert result == {"status": "ok"}

    @pytest.mark.asyncio
    @patch("app.utils.features.is_feature_enabled", return_value=True)
    async def test_passes_args_through(self, mock_enabled):
        """Should pass arguments through to decorated function."""

        @require_feature("multi_agent")
        async def protected_endpoint(name: str, count: int = 1):
            return {"name": name, "count": count}

        result = await protected_endpoint("test", count=5)
        assert result == {"name": "test", "count": 5}
