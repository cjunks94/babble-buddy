"""Prompt engineering configuration and context building.

References:
- https://www.promptingguide.ai/introduction/settings
- https://learnprompting.org/docs/intermediate/configuration_hyperparameters
"""

from dataclasses import dataclass
from typing import Literal

from app.config import settings

ResponseStyle = Literal["default", "brief", "detailed", "technical", "creative"]


@dataclass
class ModelParams:
    """LLM generation parameters."""

    max_tokens: int
    temperature: float
    top_p: float
    repeat_penalty: float
    num_ctx: int


# Preset configurations for different response styles
STYLE_PRESETS: dict[ResponseStyle, ModelParams] = {
    "default": ModelParams(
        max_tokens=512,
        temperature=0.7,
        top_p=0.9,
        repeat_penalty=1.1,
        num_ctx=2048,
    ),
    "brief": ModelParams(
        max_tokens=256,
        temperature=0.3,
        top_p=0.9,
        repeat_penalty=1.2,
        num_ctx=2048,
    ),
    "detailed": ModelParams(
        max_tokens=1024,
        temperature=0.5,
        top_p=0.95,
        repeat_penalty=1.1,
        num_ctx=4096,
    ),
    "technical": ModelParams(
        max_tokens=512,
        temperature=0.2,
        top_p=0.85,
        repeat_penalty=1.15,
        num_ctx=4096,
    ),
    "creative": ModelParams(
        max_tokens=768,
        temperature=0.8,
        top_p=0.95,
        repeat_penalty=1.0,
        num_ctx=2048,
    ),
}


# System prompt templates per style
STYLE_PROMPTS: dict[ResponseStyle, str] = {
    "default": "You are a helpful AI assistant.",
    "brief": """You are a helpful AI assistant. Be concise and direct.
- Keep responses to 2-3 sentences unless more detail is needed
- Use bullet points for lists
- Skip unnecessary preamble""",
    "detailed": """You are a helpful AI assistant providing thorough explanations.
- Give comprehensive answers with context
- Include relevant examples when helpful
- Structure long responses with headers""",
    "technical": """You are a technical AI assistant for developers.
- Be precise and accurate
- Use proper terminology
- Include code examples in markdown when relevant
- Skip basic explanations unless asked""",
    "creative": """You are a creative AI assistant.
- Be engaging and conversational
- Use varied language and expressions
- Feel free to use analogies and examples""",
}


# App-specific personas (keyed by lowercase app name)
APP_PERSONAS: dict[str, str] = {
    "exportee": """You are the AI assistant for Exportee, a data export and transformation platform.

When helping with SQL queries:
- Write safe, read-only SELECT queries only
- Use proper JOIN syntax for multi-table queries
- Suggest WHERE clauses for filtering
- Explain query logic briefly

When helping with field mappings:
- Suggest transformations (rename, mask, filter)
- Warn about PII data that should be masked (SSN, email, phone)
- Recommend data type conversions when needed

When helping with widgets:
- Available types: mask_ssn, mask_email, filter, rename, redact, hash_pii, truncate_date
- Explain what each widget does
- Suggest widget chains for common use cases (e.g., mask PII before export)

Be concise and technical. Use code blocks for SQL and JSON examples.""",
}


def get_model_params(style: ResponseStyle | None = None) -> ModelParams:
    """Get model parameters for the given style or from settings."""
    style = style or settings.response_style

    if style in STYLE_PRESETS:
        return STYLE_PRESETS[style]

    # Fall back to settings values
    return ModelParams(
        max_tokens=settings.ollama_max_tokens,
        temperature=settings.ollama_temperature,
        top_p=settings.ollama_top_p,
        repeat_penalty=settings.ollama_repeat_penalty,
        num_ctx=settings.ollama_num_ctx,
    )


def build_system_prompt(
    context: dict | None = None,
    style: ResponseStyle | None = None,
) -> str:
    """Build system prompt from context and style.

    Context structure from frontend:
    {
        "app": "MyApp",           # App name for personalization
        "page": "checkout",       # Current page/section
        "role": "support",        # Assistant role/persona
        "instructions": "...",    # Custom instructions from app owner
        "schema": [...],          # Data schema hints
        "user": {                 # Optional user context
            "name": "John",
            "plan": "premium"
        }
    }
    """
    style = style or settings.response_style
    base_prompt = STYLE_PROMPTS.get(style, STYLE_PROMPTS["default"])

    if not context:
        return base_prompt

    parts = []

    # Check for app-specific persona first
    app_name = context.get("app")
    app_key = app_name.lower() if app_name else None

    if app_key and app_key in APP_PERSONAS:
        # Use full app persona as base
        parts.append(APP_PERSONAS[app_key])
    elif app_name:
        # Generic app personalization
        parts.append(f"You are the AI assistant for {app_name}.")
    else:
        parts.append(base_prompt.split("\n")[0])

    # Role/persona
    role = context.get("role")
    if role:
        role_prompts = {
            "support": "You help users with questions and troubleshooting.",
            "sales": "You help users understand products and make decisions.",
            "onboarding": "You guide new users through getting started.",
            "technical": "You provide technical assistance and documentation help.",
        }
        parts.append(role_prompts.get(role, f"Your role is {role}."))

    # Page context
    page = context.get("page")
    if page:
        parts.append(f"The user is currently on the {page} page.")

    # Custom instructions from app owner
    instructions = context.get("instructions")
    if instructions:
        parts.append(instructions)

    # Schema/data hints
    schema = context.get("schema")
    if schema:
        if isinstance(schema, list):
            parts.append(f"Available data: {', '.join(schema)}.")
        elif isinstance(schema, str):
            parts.append(schema)

    # User context
    user = context.get("user")
    if user and isinstance(user, dict):
        user_parts = []
        if user.get("name"):
            user_parts.append(f"name is {user['name']}")
        if user.get("plan"):
            user_parts.append(f"on {user['plan']} plan")
        if user_parts:
            parts.append(f"The user's {', '.join(user_parts)}.")

    # Add style-specific instructions
    style_instructions = STYLE_PROMPTS.get(style, "").split("\n", 1)
    if len(style_instructions) > 1:
        parts.append(style_instructions[1].strip())

    return " ".join(parts)
