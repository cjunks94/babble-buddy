"""Pydantic schemas for Agent CRUD operations."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    """Supported AI provider types."""

    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GEMINI = "gemini"


class AgentRole(str, Enum):
    """Agent roles for multi-agent orchestration."""

    LEADER = "leader"  # Coordinates other agents, makes decisions
    CODER = "coder"  # Writes and generates code
    REVIEWER = "reviewer"  # Reviews code and provides feedback
    RESEARCHER = "researcher"  # Gathers information and context


class AgentCreate(BaseModel):
    """Schema for creating a new agent."""

    app_id: UUID = Field(..., description="Application ID this agent belongs to")
    name: str = Field(..., min_length=1, max_length=100, description="Agent name")
    provider_type: ProviderType = Field(..., description="AI provider type")
    api_key: str | None = Field(
        None, description="API key for external providers (not needed for Ollama)"
    )
    model: str = Field(..., min_length=1, max_length=100, description="Model identifier")
    role: AgentRole = Field(..., description="Agent role in orchestration")
    system_prompt: str | None = Field(None, description="Custom system prompt")
    max_tokens: int = Field(default=1024, ge=1, le=32768, description="Max tokens for response")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")


class AgentUpdate(BaseModel):
    """Schema for updating an existing agent."""

    name: str | None = Field(None, min_length=1, max_length=100)
    api_key: str | None = Field(None, description="New API key (will be encrypted)")
    model: str | None = Field(None, min_length=1, max_length=100)
    role: AgentRole | None = None
    system_prompt: str | None = None
    max_tokens: int | None = Field(None, ge=1, le=32768)
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    is_active: bool | None = None


class AgentResponse(BaseModel):
    """Full agent response including the API key (for create only)."""

    id: UUID
    app_id: UUID
    name: str
    provider_type: ProviderType
    model: str
    role: AgentRole
    system_prompt: str | None
    max_tokens: int
    temperature: float
    is_active: bool
    has_api_key: bool = Field(..., description="Whether an API key is configured")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentListResponse(BaseModel):
    """Agent response for list operations (no sensitive data)."""

    id: UUID
    app_id: UUID
    name: str
    provider_type: ProviderType
    model: str
    role: AgentRole
    is_active: bool
    has_api_key: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
