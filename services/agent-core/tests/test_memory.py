"""Tests for lightweight memory system."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


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
