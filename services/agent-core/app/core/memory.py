"""Lightweight memory system for conversation context."""

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Memory, MemoryType


async def generate_embedding(content: str) -> list[float]:
    """Generate embedding vector using Ollama's embedding endpoint.

    Uses nomic-embed-text model which produces 384-dimensional vectors.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.ollama_host}/api/embeddings",
            json={
                "model": settings.memory_embedding_model,
                "prompt": content,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["embedding"]


class MemoryService:
    """Service for storing and recalling semantic memories."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def store(
        self,
        app_token_id: int,
        session_id: str | None,
        content: str,
        memory_type: MemoryType = MemoryType.FACT,
    ) -> Memory:
        """Store a new memory with its embedding.

        Args:
            app_token_id: The app token this memory belongs to
            session_id: Optional session ID for session-scoped memories
            content: The text content to store
            memory_type: Type of memory (fact, preference, summary)

        Returns:
            The created Memory object
        """
        embedding = await generate_embedding(content)

        memory = Memory(
            app_token_id=app_token_id,
            session_id=session_id,
            content=content,
            embedding=embedding,
            memory_type=memory_type,
        )

        self.db.add(memory)
        await self.db.commit()
        await self.db.refresh(memory)

        return memory

    async def recall(
        self,
        app_token_id: int,
        query: str,
        limit: int = 5,
        min_similarity: float = 0.5,
        session_id: str | None = None,
    ) -> list:
        """Recall relevant memories using semantic similarity search.

        Args:
            app_token_id: Filter memories by app token
            query: The query text to find similar memories for
            limit: Maximum number of memories to return
            min_similarity: Minimum cosine similarity threshold (0-1)
            session_id: Optional filter by session

        Returns:
            List of Memory objects with similarity scores, ordered by relevance
        """
        query_embedding = await generate_embedding(query)

        # Build the similarity search query using pgvector's cosine distance
        # cosine_distance = 1 - cosine_similarity, so we convert
        similarity_expr = 1 - Memory.embedding.cosine_distance(query_embedding)

        stmt = (
            select(Memory, similarity_expr.label("similarity"))
            .where(Memory.app_token_id == app_token_id)
            .where(similarity_expr >= min_similarity)
            .order_by(similarity_expr.desc())
            .limit(limit)
        )

        if session_id:
            stmt = stmt.where(Memory.session_id == session_id)

        result = await self.db.execute(stmt)
        rows = result.all()

        # Attach similarity score to each memory object
        memories = []
        for memory, similarity in rows:
            memory.similarity = similarity
            memories.append(memory)

        return memories

    async def clear(self, app_token_id: int, session_id: str | None = None) -> int:
        """Clear memories for an app token, optionally filtered by session.

        Returns:
            Number of memories deleted
        """
        stmt = select(Memory).where(Memory.app_token_id == app_token_id)

        if session_id:
            stmt = stmt.where(Memory.session_id == session_id)

        result = await self.db.execute(stmt)
        memories = result.scalars().all()

        for memory in memories:
            await self.db.delete(memory)

        await self.db.commit()
        return len(memories)


def format_memories_for_prompt(memories: list) -> str:
    """Format recalled memories as a context string for the prompt.

    Args:
        memories: List of Memory objects to format

    Returns:
        Formatted string with memory contents, or empty string if no memories
    """
    if not memories:
        return ""

    lines = ["[Relevant context from previous conversations:]"]
    for memory in memories:
        mem_type = memory.memory_type
        type_str = mem_type.value if hasattr(mem_type, "value") else str(mem_type)
        lines.append(f"- ({type_str}) {memory.content}")

    return "\n".join(lines)


def augment_system_prompt(base_prompt: str, memory_context: str) -> str:
    """Inject memory context into the system prompt.

    Memory context is placed before the base prompt so the LLM considers
    it as background context.

    Args:
        base_prompt: The original system prompt
        memory_context: Formatted memory context string

    Returns:
        Augmented system prompt with memory context
    """
    if not memory_context:
        return base_prompt

    return f"{memory_context}\n\n{base_prompt}"
