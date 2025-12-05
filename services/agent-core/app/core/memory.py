"""Lightweight memory system for conversation context."""

import hashlib
import time
from datetime import datetime
from threading import Lock

import httpx
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Memory, MemoryType, StructuredMemory


class EmbeddingCache:
    """Thread-safe LRU cache with TTL for embeddings."""

    def __init__(self, max_size: int = 10000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl = ttl_seconds
        self.cache: dict[str, tuple[list[float], float]] = {}  # hash -> (embedding, timestamp)
        self.access_order: list[str] = []  # For LRU eviction
        self.lock = Lock()
        self.hits = 0
        self.misses = 0

    def _hash_content(self, content: str) -> str:
        """Create a hash key for content."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get(self, content: str) -> list[float] | None:
        """Get embedding from cache if exists and not expired."""
        key = self._hash_content(content)
        with self.lock:
            if key in self.cache:
                embedding, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl:
                    # Move to end for LRU
                    self.access_order.remove(key)
                    self.access_order.append(key)
                    self.hits += 1
                    return embedding
                else:
                    # Expired
                    del self.cache[key]
                    self.access_order.remove(key)
            self.misses += 1
            return None

    def set(self, content: str, embedding: list[float]) -> None:
        """Store embedding in cache."""
        key = self._hash_content(content)
        with self.lock:
            # Evict oldest if at capacity
            while len(self.cache) >= self.max_size and self.access_order:
                oldest_key = self.access_order.pop(0)
                self.cache.pop(oldest_key, None)

            self.cache[key] = (embedding, time.time())
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)

    def stats(self) -> dict:
        """Get cache statistics."""
        total = self.hits + self.misses
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / total if total > 0 else 0,
        }


# Global embedding cache
_embedding_cache = EmbeddingCache(
    max_size=settings.memory_embedding_cache_size,
    ttl_seconds=settings.memory_embedding_cache_ttl,
)


async def generate_embedding(content: str, use_cache: bool = True) -> list[float]:
    """Generate embedding vector using Ollama's embedding endpoint.

    Uses nomic-embed-text model which produces 384-dimensional vectors.
    Caches results for repeated content to reduce latency at scale.
    """
    # Check cache first
    if use_cache:
        cached = _embedding_cache.get(content)
        if cached is not None:
            return cached

    # Generate new embedding
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
        embedding = data["embedding"]

    # Cache the result
    if use_cache:
        _embedding_cache.set(content, embedding)

    return embedding


def get_embedding_cache_stats() -> dict:
    """Get embedding cache statistics for monitoring."""
    return _embedding_cache.stats()


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

    async def recall_high_importance(
        self,
        app_token_id: int,
        threshold: float | None = None,
        application_group: str | None = None,
    ) -> list[StructuredMemory]:
        """Recall high-importance structured memories that should always be injected.

        Args:
            app_token_id: Filter memories by app token
            threshold: Minimum importance (defaults to config)
            application_group: Optional filter by application group

        Returns:
            List of StructuredMemory objects above the importance threshold
        """
        importance_threshold = threshold or settings.memory_high_importance_threshold

        # Build query for high-importance, non-expired memories
        stmt = (
            select(StructuredMemory)
            .where(StructuredMemory.app_token_id == app_token_id)
            .where(StructuredMemory.importance >= importance_threshold)
            .where(
                or_(
                    StructuredMemory.expires_at.is_(None),
                    StructuredMemory.expires_at > datetime.utcnow(),
                )
            )
            .order_by(StructuredMemory.importance.desc())
        )

        if application_group:
            stmt = stmt.where(StructuredMemory.application_group == application_group)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def recall_structured(
        self,
        app_token_id: int,
        query: str,
        limit: int = 5,
        min_similarity: float = 0.5,
        application_group: str | None = None,
        predicate: str | None = None,
    ) -> list[StructuredMemory]:
        """Recall structured memories using semantic similarity on natural_language.

        Args:
            app_token_id: Filter memories by app token
            query: The query text to find similar memories for
            limit: Maximum number of memories to return
            min_similarity: Minimum cosine similarity threshold
            application_group: Optional filter by application group
            predicate: Optional filter by predicate type

        Returns:
            List of StructuredMemory objects with similarity scores
        """
        query_embedding = await generate_embedding(query)

        # Build similarity search on natural_language embeddings
        similarity_expr = 1 - StructuredMemory.embedding.cosine_distance(query_embedding)

        stmt = (
            select(StructuredMemory, similarity_expr.label("similarity"))
            .where(StructuredMemory.app_token_id == app_token_id)
            .where(StructuredMemory.embedding.isnot(None))
            .where(similarity_expr >= min_similarity)
            .where(
                or_(
                    StructuredMemory.expires_at.is_(None),
                    StructuredMemory.expires_at > datetime.utcnow(),
                )
            )
            .order_by(similarity_expr.desc())
            .limit(limit)
        )

        if application_group:
            stmt = stmt.where(StructuredMemory.application_group == application_group)

        if predicate:
            stmt = stmt.where(StructuredMemory.predicate == predicate)

        result = await self.db.execute(stmt)
        rows = result.all()

        memories = []
        for memory, similarity in rows:
            memory.similarity = similarity
            memories.append(memory)

        return memories

    async def recall_combined(
        self,
        app_token_id: int,
        query: str,
        limit: int = 5,
        min_similarity: float = 0.5,
        application_group: str | None = None,
    ) -> dict:
        """Recall both vector and structured memories.

        Returns combined results from:
        1. High-importance structured memories (always included if enabled)
        2. Semantically similar basic memories
        3. Semantically similar structured memories

        Args:
            app_token_id: Filter memories by app token
            query: The query text for semantic search
            limit: Max memories per category
            min_similarity: Minimum similarity threshold
            application_group: Optional app group filter

        Returns:
            Dict with 'high_importance', 'basic', and 'structured' memory lists
        """
        results = {
            "high_importance": [],
            "basic": [],
            "structured": [],
        }

        # 1. Always recall high-importance memories if enabled
        if settings.memory_always_inject_high_importance:
            results["high_importance"] = await self.recall_high_importance(
                app_token_id=app_token_id,
                application_group=application_group,
            )

        # 2. Recall basic vector memories
        results["basic"] = await self.recall(
            app_token_id=app_token_id,
            query=query,
            limit=limit,
            min_similarity=min_similarity,
        )

        # 3. Recall structured memories (excluding high-importance already included)
        high_importance_ids = {m.id for m in results["high_importance"]}
        structured = await self.recall_structured(
            app_token_id=app_token_id,
            query=query,
            limit=limit,
            min_similarity=min_similarity,
            application_group=application_group,
        )
        results["structured"] = [m for m in structured if m.id not in high_importance_ids]

        return results


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


def format_structured_memories_for_prompt(memories: list[StructuredMemory]) -> str:
    """Format structured memories as context for the prompt.

    Args:
        memories: List of StructuredMemory objects to format

    Returns:
        Formatted string with memory facts
    """
    if not memories:
        return ""

    lines = []
    for memory in memories:
        # Use the natural language representation
        lines.append(f"- {memory.natural_language}")

    return "\n".join(lines)


def format_combined_memories_for_prompt(combined: dict) -> str:
    """Format combined memory results for the prompt.

    Args:
        combined: Dict with 'high_importance', 'basic', and 'structured' lists

    Returns:
        Formatted context string
    """
    sections = []

    # High importance memories get their own section
    if combined.get("high_importance"):
        lines = ["[Critical information about the user:]"]
        for mem in combined["high_importance"]:
            lines.append(f"- {mem.natural_language}")
        sections.append("\n".join(lines))

    # Combine basic and structured memories
    context_memories = []
    if combined.get("basic"):
        for mem in combined["basic"]:
            context_memories.append(f"- {mem.content}")
    if combined.get("structured"):
        for mem in combined["structured"]:
            context_memories.append(f"- {mem.natural_language}")

    if context_memories:
        sections.append("[Relevant context from previous conversations:]\n" + "\n".join(context_memories))

    return "\n\n".join(sections)


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
