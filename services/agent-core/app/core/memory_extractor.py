"""Structured memory extraction from conversations using LLM."""

import json
from datetime import datetime

import httpx
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import logger
from app.core.memory import generate_embedding
from app.db.models import ConversationTurn, ExtractionStatus, StructuredMemory

EXTRACTION_PROMPT = """You are an expert personal memory system running in production.
Your only goal is to extract structured, atomic, reusable memory tuples from the latest user message, using the full conversation history for disambiguation.

Rules (non-negotiable):
- Extract zero or more memory nodes. It is common and expected to extract 0 nodes.
- Never hallucinate facts not explicitly or strongly implied in the conversation.
- Every node must be directly grounded in something the user said or confirmed.
- Prefer narrow, specific predicates over vague ones.
- Negations are first-class (e.g., "does_not_like", "never", "allergic_to").
- Importance is 0.0-1.0. 1.0 = life-changing or safety-critical (allergies, core values, medical). Most things are ≤0.7.
- Confidence <1.0 only when genuinely ambiguous.

Output format: ALWAYS respond with valid JSON matching this schema (no extra text):
{
  "memories": [
    {
      "subject": "string (almost always 'user'; can be a named entity like 'Mom' if clear)",
      "predicate": "string (verb phrase in snake_case: loves, hates, allergic_to, works_at, has_goal)",
      "object": "string | bool | int | float | list[string] (keep atomic; use list only for clear enumerations)",
      "object_type": "string (food, person, place, topic, temperature, allergy, etc.)",
      "negation": "boolean (true if predicate is negated)",
      "importance": "float 0.0-1.0",
      "confidence": "float 0.0-1.0 (almost always 1.0 unless truly ambiguous)",
      "natural_language": "string (short, human-readable version of this fact)",
      "tags": ["optional", "short", "tags"]
    }
  ],
  "summary_if_episode_end": "string | null (only if closing a major topic, otherwise null)"
}

Examples:
User: "I absolutely hate olives, but pineapple on pizza is the best."
-> [{"subject":"user","predicate":"hates","object":"olives","object_type":"food","negation":false,"importance":0.65,"confidence":1.0,"natural_language":"User hates olives","tags":["food"]},{"subject":"user","predicate":"loves","object":"pineapple on pizza","object_type":"food","negation":false,"importance":0.75,"confidence":1.0,"natural_language":"User loves pineapple on pizza","tags":["food"]}]

User: "I'm deathly allergic to shellfish."
-> importance: 1.0, predicate: "allergic_to", object_type: "allergy"

Now extract from the conversation below. Only output JSON. No explanations."""


class ExtractedMemory(BaseModel):
    """Schema for a single extracted memory."""

    subject: str = "user"
    predicate: str
    object: str | bool | int | float | list[str] = Field(alias="object")
    object_type: str
    negation: bool = False
    importance: float = 0.5
    confidence: float = 1.0
    natural_language: str
    tags: list[str] = Field(default_factory=list)
    expires_at: str | None = None


class ExtractionResult(BaseModel):
    """Schema for the extraction response."""

    memories: list[ExtractedMemory] = Field(default_factory=list)
    summary_if_episode_end: str | None = None


class MemoryExtractor:
    """Service for extracting structured memories from conversations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def extract_from_turn(
        self,
        turn: ConversationTurn,
        conversation_history: list[dict] | None = None,
    ) -> ExtractionResult:
        """Extract structured memories from a conversation turn.

        Args:
            turn: The conversation turn to extract from
            conversation_history: Optional prior conversation context

        Returns:
            ExtractionResult with extracted memories
        """
        # Build the conversation context
        messages = []
        if conversation_history:
            for msg in conversation_history:
                messages.append(f"{msg['role'].title()}: {msg['content']}")

        messages.append(f"User: {turn.user_message}")
        messages.append(f"Assistant: {turn.assistant_message}")

        conversation_text = "\n".join(messages)

        # Call the LLM for extraction
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{settings.ollama_host}/api/generate",
                    json={
                        "model": settings.memory_extraction_model,
                        "prompt": f"{EXTRACTION_PROMPT}\n\n{conversation_text}",
                        "stream": False,
                        "format": "json",
                        "options": {
                            "temperature": 0.1,  # Low temp for consistent extraction
                            "num_predict": 2048,
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()

            # Parse the JSON response
            response_text = data.get("response", "{}").strip()
            parsed = json.loads(response_text)
            return ExtractionResult(**parsed)

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse extraction response: {e}")
            return ExtractionResult()
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            raise

    async def store_memories(
        self,
        turn: ConversationTurn,
        result: ExtractionResult,
    ) -> list[StructuredMemory]:
        """Store extracted memories in the database.

        Args:
            turn: The source conversation turn
            result: The extraction result with memories

        Returns:
            List of created StructuredMemory objects
        """
        stored = []

        for mem in result.memories:
            # Generate embedding for the natural language representation
            try:
                embedding = await generate_embedding(mem.natural_language)
            except Exception as e:
                logger.warning(f"Failed to generate embedding: {e}")
                embedding = None

            # Parse expires_at if provided
            expires_at = None
            if mem.expires_at:
                try:
                    expires_at = datetime.fromisoformat(mem.expires_at.replace("Z", "+00:00"))
                except ValueError:
                    pass

            structured_memory = StructuredMemory(
                app_token_id=turn.app_token_id,
                application_group=turn.application_group,
                subject=mem.subject,
                predicate=mem.predicate,
                object_value={"value": mem.object},  # Wrap in dict for JSONB
                object_type=mem.object_type,
                negation=mem.negation,
                importance=mem.importance,
                confidence=mem.confidence,
                natural_language=mem.natural_language,
                embedding=embedding,
                source_turn_ids=[str(turn.id)],
                tags=mem.tags,
                expires_at=expires_at,
            )

            self.db.add(structured_memory)
            stored.append(structured_memory)

        if stored:
            await self.db.commit()
            for mem in stored:
                await self.db.refresh(mem)

        return stored

    async def process_turn(self, turn: ConversationTurn) -> list[StructuredMemory]:
        """Extract and store memories from a single turn.

        Args:
            turn: The conversation turn to process

        Returns:
            List of created StructuredMemory objects
        """
        # Mark as processing
        turn.extraction_status = ExtractionStatus.PROCESSING
        await self.db.commit()

        try:
            result = await self.extract_from_turn(turn)

            if not result.memories:
                turn.extraction_status = ExtractionStatus.SKIPPED
                turn.extracted_at = datetime.utcnow()
                await self.db.commit()
                return []

            memories = await self.store_memories(turn, result)

            turn.extraction_status = ExtractionStatus.COMPLETED
            turn.extracted_at = datetime.utcnow()
            await self.db.commit()

            return memories

        except Exception as e:
            turn.extraction_status = ExtractionStatus.FAILED
            turn.extraction_error = str(e)
            await self.db.commit()
            raise

    async def process_batch(
        self,
        app_token_id: int | None = None,
        application_group: str | None = None,
        limit: int | None = None,
    ) -> dict:
        """Process a batch of pending conversation turns.

        Args:
            app_token_id: Optional filter by app token
            application_group: Optional filter by application group
            limit: Max turns to process (defaults to config)

        Returns:
            Dict with processing statistics
        """
        batch_limit = limit or settings.memory_extraction_batch_size

        # Find pending turns
        stmt = (
            select(ConversationTurn)
            .where(ConversationTurn.extraction_status == ExtractionStatus.PENDING)
            .order_by(ConversationTurn.created_at)
            .limit(batch_limit)
        )

        if app_token_id:
            stmt = stmt.where(ConversationTurn.app_token_id == app_token_id)
        if application_group:
            stmt = stmt.where(ConversationTurn.application_group == application_group)

        result = await self.db.execute(stmt)
        turns = result.scalars().all()

        stats = {
            "total": len(turns),
            "completed": 0,
            "skipped": 0,
            "failed": 0,
            "memories_created": 0,
        }

        for turn in turns:
            try:
                memories = await self.process_turn(turn)
                if memories:
                    stats["completed"] += 1
                    stats["memories_created"] += len(memories)
                else:
                    stats["skipped"] += 1
            except Exception as e:
                logger.error(f"Failed to process turn {turn.id}: {e}")
                stats["failed"] += 1

        return stats

    async def get_pending_count(
        self,
        app_token_id: int | None = None,
        application_group: str | None = None,
    ) -> int:
        """Get count of pending turns awaiting extraction."""
        from sqlalchemy import func

        stmt = select(func.count(ConversationTurn.id)).where(
            ConversationTurn.extraction_status == ExtractionStatus.PENDING
        )

        if app_token_id:
            stmt = stmt.where(ConversationTurn.app_token_id == app_token_id)
        if application_group:
            stmt = stmt.where(ConversationTurn.application_group == application_group)

        result = await self.db.execute(stmt)
        return result.scalar() or 0
