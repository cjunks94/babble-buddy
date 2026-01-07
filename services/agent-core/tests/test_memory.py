"""Tests for lightweight memory system."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestEmbeddingCache:
    """Test embedding cache functionality."""

    def test_cache_initialization(self):
        """Should initialize with correct settings."""
        from app.core.memory import EmbeddingCache

        cache = EmbeddingCache(max_size=100, ttl_seconds=600)
        assert cache.max_size == 100
        assert cache.ttl == 600
        assert cache.hits == 0
        assert cache.misses == 0

    def test_cache_set_and_get(self):
        """Should store and retrieve embeddings."""
        from app.core.memory import EmbeddingCache

        cache = EmbeddingCache(max_size=10, ttl_seconds=3600)
        embedding = [0.1, 0.2, 0.3]

        cache.set("test content", embedding)
        result = cache.get("test content")

        assert result == embedding
        assert cache.hits == 1

    def test_cache_miss(self):
        """Should return None and track misses."""
        from app.core.memory import EmbeddingCache

        cache = EmbeddingCache()
        result = cache.get("nonexistent")

        assert result is None
        assert cache.misses == 1

    def test_cache_ttl_expiration(self):
        """Should expire entries after TTL."""
        from app.core.memory import EmbeddingCache

        cache = EmbeddingCache(max_size=10, ttl_seconds=1)
        cache.set("test", [0.1, 0.2])

        # Should exist immediately
        assert cache.get("test") is not None

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired
        result = cache.get("test")
        assert result is None

    def test_cache_lru_eviction(self):
        """Should evict least recently used when full."""
        from app.core.memory import EmbeddingCache

        cache = EmbeddingCache(max_size=2, ttl_seconds=3600)

        cache.set("first", [0.1])
        cache.set("second", [0.2])

        # Access first to make it more recent
        cache.get("first")

        # Add third, should evict second
        cache.set("third", [0.3])

        assert cache.get("first") is not None
        assert cache.get("second") is None
        assert cache.get("third") is not None

    def test_cache_stats(self):
        """Should track statistics correctly."""
        from app.core.memory import EmbeddingCache

        cache = EmbeddingCache(max_size=10, ttl_seconds=3600)

        cache.set("test", [0.1])
        cache.get("test")  # Hit
        cache.get("test")  # Hit
        cache.get("missing")  # Miss

        stats = cache.stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["size"] == 1
        assert stats["hit_rate"] == 2 / 3

    def test_cache_hash_consistency(self):
        """Same content should produce same hash."""
        from app.core.memory import EmbeddingCache

        cache = EmbeddingCache()
        content = "test content here"

        cache.set(content, [0.1, 0.2])

        # Should retrieve with same content
        result = cache.get(content)
        assert result == [0.1, 0.2]


class TestStructuredMemoryModel:
    """Test StructuredMemory database model."""

    def test_structured_memory_has_required_fields(self):
        """StructuredMemory model should have all required fields."""
        from app.db.models import StructuredMemory

        columns = {c.name for c in StructuredMemory.__table__.columns}
        assert "id" in columns
        assert "app_token_id" in columns
        assert "subject" in columns
        assert "predicate" in columns
        assert "object_value" in columns
        assert "object_type" in columns
        assert "negation" in columns
        assert "importance" in columns
        assert "confidence" in columns
        assert "natural_language" in columns
        assert "embedding" in columns
        assert "expires_at" in columns


class TestConversationTurnModel:
    """Test ConversationTurn database model."""

    def test_conversation_turn_has_required_fields(self):
        """ConversationTurn model should have all required fields."""
        from app.db.models import ConversationTurn

        columns = {c.name for c in ConversationTurn.__table__.columns}
        assert "id" in columns
        assert "app_token_id" in columns
        assert "session_id" in columns
        assert "user_message" in columns
        assert "assistant_message" in columns
        assert "extraction_status" in columns

    def test_extraction_status_enum(self):
        """ExtractionStatus should have all states."""
        from app.db.models import ExtractionStatus

        assert ExtractionStatus.PENDING.value == "pending"
        assert ExtractionStatus.PROCESSING.value == "processing"
        assert ExtractionStatus.COMPLETED.value == "completed"
        assert ExtractionStatus.FAILED.value == "failed"
        assert ExtractionStatus.SKIPPED.value == "skipped"


class TestMemoryModel:
    """Test Memory database model."""

    def test_memory_has_required_fields(self):
        """Memory model should have all required fields."""
        from app.db.models import Memory

        columns = {c.name for c in Memory.__table__.columns}
        assert "id" in columns
        assert "app_token_id" in columns
        assert "session_id" in columns
        assert "content" in columns
        assert "embedding" in columns
        assert "memory_type" in columns
        assert "created_at" in columns

    def test_memory_type_enum(self):
        """Memory type should be one of: fact, preference, summary."""
        from app.db.models import MemoryType

        assert MemoryType.FACT.value == "fact"
        assert MemoryType.PREFERENCE.value == "preference"
        assert MemoryType.SUMMARY.value == "summary"


class TestEmbeddingService:
    """Test embedding generation via Ollama."""

    @pytest.mark.asyncio
    async def test_generate_embedding_returns_vector(self):
        """Should return a list of floats from Ollama embeddings endpoint."""
        from app.core.memory import generate_embedding

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"embedding": [0.1, 0.2, 0.3] * 128}
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            embedding = await generate_embedding("Hello world")

            assert isinstance(embedding, list)
            assert len(embedding) == 384  # nomic-embed-text dimension
            assert all(isinstance(x, float) for x in embedding)

    @pytest.mark.asyncio
    async def test_generate_embedding_calls_ollama(self):
        """Should call Ollama's embedding endpoint with correct payload."""
        from app.core.memory import generate_embedding

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"embedding": [0.1] * 384}
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            await generate_embedding("Test content")

            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "embeddings" in call_args[0][0] or "embed" in call_args[0][0]


class TestMemoryService:
    """Test memory store and recall operations."""

    @pytest.mark.asyncio
    async def test_store_memory_creates_record(self):
        """Should create a memory record with content and embedding."""
        from app.core.memory import MemoryService
        from app.db.models import MemoryType

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        service = MemoryService(mock_db)

        with patch("app.core.memory.generate_embedding", return_value=[0.1] * 384):
            memory = await service.store(
                app_token_id=1,
                session_id="sess-123",
                content="User prefers Python code examples",
                memory_type=MemoryType.PREFERENCE,
            )

        assert memory.content == "User prefers Python code examples"
        assert memory.memory_type == MemoryType.PREFERENCE
        assert memory.embedding is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_recall_returns_relevant_memories(self):
        """Should return memories ranked by semantic similarity."""
        from app.core.memory import MemoryService

        mock_db = AsyncMock()

        # Mock query results - returns tuples of (memory, similarity)
        mock_memory1 = MagicMock(content="User likes Python")
        mock_memory2 = MagicMock(content="User works on web apps")
        mock_rows = [
            (mock_memory1, 0.95),
            (mock_memory2, 0.85),
        ]
        mock_result = MagicMock()
        mock_result.all.return_value = mock_rows
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = MemoryService(mock_db)

        with patch("app.core.memory.generate_embedding", return_value=[0.1] * 384):
            memories = await service.recall(
                app_token_id=1,
                query="What programming language?",
                limit=5,
            )

        assert len(memories) == 2
        # Should be sorted by similarity (highest first)
        assert memories[0].similarity >= memories[1].similarity

    @pytest.mark.asyncio
    async def test_recall_filters_by_app_token(self):
        """Should only return memories for the specified app token."""
        from app.core.memory import MemoryService

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = MemoryService(mock_db)

        with patch("app.core.memory.generate_embedding", return_value=[0.1] * 384):
            await service.recall(app_token_id=42, query="test")

        # Verify the query included app_token_id filter
        call_args = mock_db.execute.call_args
        query_str = str(call_args[0][0])
        assert "app_token_id" in query_str

    @pytest.mark.asyncio
    async def test_recall_with_min_similarity(self):
        """Should filter out memories below similarity threshold."""
        from app.core.memory import MemoryService

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = MemoryService(mock_db)

        with patch("app.core.memory.generate_embedding", return_value=[0.1] * 384):
            await service.recall(
                app_token_id=1,
                query="test",
                min_similarity=0.7,
            )

        # Query should include similarity threshold
        mock_db.execute.assert_called_once()


class TestMemoryAugmentation:
    """Test prompt augmentation with memories."""

    def test_format_memories_for_prompt(self):
        """Should format recalled memories as context string."""
        from app.core.memory import format_memories_for_prompt

        memories = [
            MagicMock(
                content="User prefers concise answers",
                memory_type=MagicMock(value="preference"),
            ),
            MagicMock(
                content="User is a Python developer",
                memory_type=MagicMock(value="fact"),
            ),
        ]

        result = format_memories_for_prompt(memories)

        assert "User prefers concise answers" in result
        assert "User is a Python developer" in result
        assert isinstance(result, str)

    def test_format_memories_empty_list(self):
        """Should return empty string for no memories."""
        from app.core.memory import format_memories_for_prompt

        result = format_memories_for_prompt([])

        assert result == ""

    def test_augment_system_prompt(self):
        """Should inject memory context into system prompt."""
        from app.core.memory import augment_system_prompt

        base_prompt = "You are a helpful assistant."
        memory_context = "User prefers Python examples."

        result = augment_system_prompt(base_prompt, memory_context)

        assert base_prompt in result
        assert memory_context in result
        # Memory context should come before main prompt
        assert result.index(memory_context) < result.index(base_prompt)


class TestMemoryServiceClear:
    """Test memory clearing operations."""

    @pytest.mark.asyncio
    async def test_clear_all_memories_for_token(self):
        """Should delete all memories for an app token."""
        from app.core.memory import MemoryService

        mock_db = AsyncMock()

        mock_memories = [MagicMock(), MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_memories
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        service = MemoryService(mock_db)
        count = await service.clear(app_token_id=1)

        assert count == 3
        assert mock_db.delete.call_count == 3

    @pytest.mark.asyncio
    async def test_clear_session_memories(self):
        """Should only delete memories for specific session."""
        from app.core.memory import MemoryService

        mock_db = AsyncMock()

        mock_memories = [MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_memories
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        service = MemoryService(mock_db)
        count = await service.clear(app_token_id=1, session_id="sess-123")

        assert count == 1

    @pytest.mark.asyncio
    async def test_clear_no_memories(self):
        """Should handle no memories to clear."""
        from app.core.memory import MemoryService

        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        service = MemoryService(mock_db)
        count = await service.clear(app_token_id=1)

        assert count == 0


class TestStructuredMemoryRecall:
    """Test structured memory recall operations."""

    @pytest.mark.asyncio
    async def test_recall_high_importance(self):
        """Should recall high-importance memories."""
        from app.core.memory import MemoryService

        mock_db = AsyncMock()

        mock_memory = MagicMock(importance=0.95, natural_language="User is allergic to peanuts")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_memory]
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = MemoryService(mock_db)
        memories = await service.recall_high_importance(app_token_id=1)

        assert len(memories) == 1
        assert memories[0].importance == 0.95

    @pytest.mark.asyncio
    async def test_recall_high_importance_with_threshold(self):
        """Should use custom importance threshold."""
        from app.core.memory import MemoryService

        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = MemoryService(mock_db)
        await service.recall_high_importance(app_token_id=1, threshold=0.8)

        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_recall_structured_with_similarity(self):
        """Should recall structured memories by semantic similarity."""
        from app.core.memory import MemoryService

        mock_db = AsyncMock()

        mock_memory = MagicMock(natural_language="User works at Acme Corp")
        mock_rows = [(mock_memory, 0.88)]
        mock_result = MagicMock()
        mock_result.all.return_value = mock_rows
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = MemoryService(mock_db)

        with patch("app.core.memory.generate_embedding", return_value=[0.1] * 384):
            memories = await service.recall_structured(
                app_token_id=1,
                query="Where does the user work?",
                limit=5,
            )

        assert len(memories) == 1
        assert memories[0].similarity == 0.88

    @pytest.mark.asyncio
    async def test_recall_structured_with_predicate_filter(self):
        """Should filter by predicate type."""
        from app.core.memory import MemoryService

        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = MemoryService(mock_db)

        with patch("app.core.memory.generate_embedding", return_value=[0.1] * 384):
            await service.recall_structured(
                app_token_id=1,
                query="test",
                predicate="allergic_to",
            )

        mock_db.execute.assert_called_once()
        # Verify predicate filter was included
        call_args = mock_db.execute.call_args
        query_str = str(call_args[0][0])
        assert "predicate" in query_str


class TestCombinedMemoryRecall:
    """Test combined memory recall operations."""

    @pytest.mark.asyncio
    async def test_recall_combined_structure(self):
        """Should return dict with all memory categories."""
        from app.core.memory import MemoryService

        mock_db = AsyncMock()

        # Mock all the underlying recall methods
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = MemoryService(mock_db)

        with patch("app.core.memory.generate_embedding", return_value=[0.1] * 384):
            with patch.object(service, "recall_high_importance", return_value=[]):
                with patch.object(service, "recall", return_value=[]):
                    with patch.object(service, "recall_structured", return_value=[]):
                        result = await service.recall_combined(
                            app_token_id=1,
                            query="test query",
                        )

        # Should have all three categories
        assert "high_importance" in result
        assert "basic" in result
        assert "structured" in result


class TestFormatCombinedMemories:
    """Test formatting combined memories for prompts."""

    def test_format_combined_memories_for_prompt(self):
        """Should format all memory types for injection."""
        from app.core.memory import format_combined_memories_for_prompt

        combined = {
            "high_importance": [
                MagicMock(
                    natural_language="User is allergic to shellfish",
                    importance=1.0,
                ),
            ],
            "basic": [
                MagicMock(
                    content="User prefers Python",
                    memory_type=MagicMock(value="preference"),
                ),
            ],
            "structured": [
                MagicMock(
                    natural_language="User works at a startup",
                    importance=0.7,
                ),
            ],
        }

        result = format_combined_memories_for_prompt(combined)

        assert isinstance(result, str)
        # Should include high importance memories prominently
        if combined["high_importance"]:
            assert "allergic" in result.lower() or "shellfish" in result.lower()

    def test_format_combined_memories_empty(self):
        """Should handle empty combined results."""
        from app.core.memory import format_combined_memories_for_prompt

        combined = {
            "high_importance": [],
            "basic": [],
            "structured": [],
        }

        result = format_combined_memories_for_prompt(combined)

        assert result == "" or result is None or len(result) < 10


class TestGlobalEmbeddingCache:
    """Test global embedding cache functions."""

    def test_get_embedding_cache_stats(self):
        """Should return cache statistics."""
        from app.core.memory import get_embedding_cache_stats

        stats = get_embedding_cache_stats()

        assert "size" in stats
        assert "max_size" in stats
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats
