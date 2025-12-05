import enum
import secrets
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ExtractionStatus(enum.Enum):
    """Status of memory extraction for a conversation turn."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"  # No memories to extract


class AppToken(Base):
    __tablename__ = "app_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    @classmethod
    def generate_token(cls) -> str:
        return f"bb_{secrets.token_urlsafe(32)}"


class Agent(Base):
    """AI Agent configuration for multi-agent orchestration."""

    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    provider_type: Mapped[str] = mapped_column(String(50))  # ollama, anthropic, openai, gemini
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)  # Encrypted
    model: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(50))  # leader, coder, reviewer, researcher
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_tokens: Mapped[int] = mapped_column(default=1024)
    temperature: Mapped[float] = mapped_column(default=0.7)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class MemoryType(enum.Enum):
    """Types of memories that can be stored."""

    FACT = "fact"  # Extracted facts about user/context
    PREFERENCE = "preference"  # User preferences
    SUMMARY = "summary"  # Conversation summaries


class Memory(Base):
    """Semantic memory storage for conversation context."""

    __tablename__ = "memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    app_token_id: Mapped[int] = mapped_column(Integer, ForeignKey("app_tokens.id"), index=True)
    session_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(384))  # nomic-embed-text dimension
    memory_type: Mapped[MemoryType] = mapped_column(Enum(MemoryType), default=MemoryType.FACT)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class StructuredMemory(Base):
    """Knowledge graph-style structured memory tuples."""

    __tablename__ = "structured_memories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_token_id: Mapped[int] = mapped_column(Integer, ForeignKey("app_tokens.id"), index=True)
    application_group: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Core tuple fields
    subject: Mapped[str] = mapped_column(String(200), index=True)  # "user", "Mom", etc.
    predicate: Mapped[str] = mapped_column(String(100), index=True)  # "loves", "allergic_to"
    object_value: Mapped[dict] = mapped_column(JSONB)  # Flexible: str, bool, int, float, list
    object_type: Mapped[str] = mapped_column(String(50), index=True)  # "food", "allergy", etc.
    negation: Mapped[bool] = mapped_column(Boolean, default=False)

    # Scoring
    importance: Mapped[float] = mapped_column(Float, default=0.5, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    # Human readable + embedding for semantic search
    natural_language: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)

    # Provenance
    source_turn_ids: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    # Lifecycle
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class ConversationTurn(Base):
    """Stores conversation turns for batch memory extraction."""

    __tablename__ = "conversation_turns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_token_id: Mapped[int] = mapped_column(Integer, ForeignKey("app_tokens.id"), index=True)
    session_id: Mapped[str] = mapped_column(String(100), index=True)
    application_group: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Conversation content
    user_message: Mapped[str] = mapped_column(Text)
    assistant_message: Mapped[str] = mapped_column(Text)
    context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # Page context, etc.

    # Extraction tracking
    extraction_status: Mapped[ExtractionStatus] = mapped_column(
        Enum(ExtractionStatus), default=ExtractionStatus.PENDING, index=True
    )
    extracted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    extraction_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
