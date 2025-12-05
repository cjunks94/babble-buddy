"""Suggested prompts API - context-aware quick actions."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import get_current_token
from app.db.models import AppToken

router = APIRouter()


class Suggestion(BaseModel):
    label: str  # Short button text
    prompt: str  # Full prompt to send


class SuggestionsRequest(BaseModel):
    context: dict | None = None


class SuggestionsResponse(BaseModel):
    suggestions: list[Suggestion]
    context_summary: str | None = None  # For debug mode


# Default suggestions per app (keyed by lowercase app name)
APP_SUGGESTIONS: dict[str, list[Suggestion]] = {
    "exportee": [
        Suggestion(label="Write SQL", prompt="Help me write a SQL query for this export"),
        Suggestion(label="Mask PII", prompt="What fields should I mask for compliance?"),
        Suggestion(label="Explain widgets", prompt="Explain the available widget types"),
    ],
    "default": [
        Suggestion(label="Get started", prompt="How do I get started?"),
        Suggestion(label="Help", prompt="What can you help me with?"),
    ],
}

# Page-specific suggestions (app:page)
PAGE_SUGGESTIONS: dict[str, list[Suggestion]] = {
    "exportee:exports": [
        Suggestion(label="Write SQL", prompt="Help me write a SQL query for this export"),
        Suggestion(label="Filter data", prompt="How do I filter the data in my query?"),
        Suggestion(label="Join tables", prompt="How do I join multiple tables?"),
    ],
    "exportee:export-builder": [
        Suggestion(label="Write SQL", prompt="Help me write a SQL query based on the available tables"),
        Suggestion(label="Mask PII", prompt="What fields should I mask for compliance?"),
        Suggestion(label="Test query", prompt="Help me test and validate my query"),
    ],
    "exportee:mappings": [
        Suggestion(label="Add widget", prompt="What widget should I use for this field?"),
        Suggestion(label="Mask SSN", prompt="How do I mask SSN fields?"),
        Suggestion(label="Rename field", prompt="How do I rename a field in the output?"),
    ],
}


def get_context_summary(context: dict | None) -> str | None:
    """Generate a human-readable summary of the current context."""
    if not context:
        return None

    parts = []
    if context.get("app"):
        parts.append(f"App: {context['app']}")
    if context.get("page"):
        parts.append(f"Page: {context['page']}")
    if context.get("schema"):
        schema = context["schema"]
        if isinstance(schema, list):
            parts.append(f"Schema: {', '.join(schema[:5])}")
        elif isinstance(schema, str):
            parts.append(f"Schema: {schema[:100]}")
    if context.get("user"):
        user = context["user"]
        if isinstance(user, dict) and user.get("name"):
            parts.append(f"User: {user['name']}")

    return " | ".join(parts) if parts else None


@router.post("/suggestions", response_model=SuggestionsResponse)
async def get_suggestions(
    body: SuggestionsRequest,
    token: AppToken = Depends(get_current_token),
):
    """Get context-aware suggested prompts.

    Priority:
    1. Page-specific suggestions (app:page)
    2. App-specific suggestions
    3. Default suggestions
    """
    context = body.context or {}
    app_name = (context.get("app") or "").lower()
    page = (context.get("page") or "").lower()

    # Try page-specific first
    page_key = f"{app_name}:{page}" if app_name and page else None
    if page_key and page_key in PAGE_SUGGESTIONS:
        suggestions = PAGE_SUGGESTIONS[page_key]
    # Fall back to app-specific
    elif app_name in APP_SUGGESTIONS:
        suggestions = APP_SUGGESTIONS[app_name]
    # Default suggestions
    else:
        suggestions = APP_SUGGESTIONS["default"]

    return SuggestionsResponse(
        suggestions=suggestions,
        context_summary=get_context_summary(context),
    )
