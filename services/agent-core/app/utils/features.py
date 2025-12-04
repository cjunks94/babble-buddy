"""Feature flag utilities for conditional feature access."""

from collections.abc import Callable
from functools import wraps

from fastapi import HTTPException, status

from app.config import settings


class FeatureDisabledError(Exception):
    """Raised when a feature is accessed but disabled."""

    def __init__(self, feature: str):
        self.feature = feature
        super().__init__(f"Feature '{feature}' is disabled")


def require_feature(feature_name: str):
    """
    Decorator to require a feature flag to be enabled.

    Usage:
        @require_feature("multi_agent")
        async def my_endpoint():
            ...
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not is_feature_enabled(feature_name):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Feature '{feature_name}' is not enabled",
                )
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def is_feature_enabled(feature_name: str) -> bool:
    """
    Check if a feature flag is enabled.

    Args:
        feature_name: Name of the feature (without 'feature_' prefix)

    Returns:
        True if the feature is enabled, False otherwise
    """
    attr_name = f"feature_{feature_name}"
    return getattr(settings, attr_name, False)


def get_enabled_features() -> list[str]:
    """Return list of all enabled feature flags."""
    features = []
    for attr in dir(settings):
        if attr.startswith("feature_") and getattr(settings, attr, False):
            features.append(attr.replace("feature_", ""))
    return features


# Convenience functions for specific features
def is_multi_agent_enabled() -> bool:
    """Check if multi-agent orchestration is enabled."""
    return settings.feature_multi_agent


def is_external_providers_enabled() -> bool:
    """Check if external providers (Claude, OpenAI, Gemini) are enabled."""
    return settings.feature_external_providers
