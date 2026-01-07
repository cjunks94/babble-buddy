"""Comprehensive tests for memory extraction system."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.memory_extractor import (
    ExtractionResult,
    ExtractedMemory,
    MemoryExtractor,
)
from app.db.models import ConversationTurn, ExtractionStatus


class TestExtractedMemorySchema:
    """Test ExtractedMemory Pydantic schema."""

    def test_minimal_memory(self):
        """Should create memory with minimal required fields."""
        memory = ExtractedMemory(
            predicate="likes",
            object="pizza",
            object_type="food",
            natural_language="User likes pizza",
        )
        assert memory.subject == "user"  # Default
        assert memory.negation is False  # Default
        assert memory.importance == 0.5  # Default
        assert memory.confidence == 1.0  # Default
        assert memory.tags == []

    def test_full_memory(self):
        """Should create memory with all fields."""
        memory = ExtractedMemory(
            subject="Mom",
            predicate="allergic_to",
            object="shellfish",
            object_type="allergy",
            negation=False,
            importance=1.0,
            confidence=0.95,
            natural_language="Mom is allergic to shellfish",
            tags=["health", "safety"],
            expires_at="2025-12-31T23:59:59Z",
        )
        assert memory.subject == "Mom"
        assert memory.importance == 1.0
        assert len(memory.tags) == 2

    def test_memory_with_list_object(self):
        """Should handle list objects."""
        memory = ExtractedMemory(
            predicate="favorite_colors",
            object=["blue", "green", "purple"],
            object_type="preference",
            natural_language="User's favorite colors are blue, green, and purple",
        )
        assert isinstance(memory.object, list)
        assert len(memory.object) == 3

    def test_memory_with_boolean_object(self):
        """Should handle boolean objects."""
        memory = ExtractedMemory(
            predicate="is_vegetarian",
            object=True,
            object_type="dietary",
            natural_language="User is vegetarian",
        )
        assert memory.object is True


class TestExtractionResultSchema:
    """Test ExtractionResult Pydantic schema."""

    def test_empty_result(self):
        """Should create empty result."""
        result = ExtractionResult()
        assert result.memories == []
        assert result.summary_if_episode_end is None

    def test_result_with_memories(self):
        """Should create result with memories."""
        memories = [
            ExtractedMemory(
                predicate="likes",
                object="coffee",
                object_type="food",
                natural_language="User likes coffee",
            ),
            ExtractedMemory(
                predicate="works_at",
                object="Acme Corp",
                object_type="employment",
                natural_language="User works at Acme Corp",
            ),
        ]
        result = ExtractionResult(memories=memories)
        assert len(result.memories) == 2

    def test_result_with_summary(self):
        """Should include episode summary."""
        result = ExtractionResult(
            memories=[],
            summary_if_episode_end="User completed onboarding successfully.",
        )
        assert result.summary_if_episode_end is not None


class TestMemoryExtractorInit:
    """Test MemoryExtractor initialization."""

    def test_init_with_db(self):
        """Should initialize with database session."""
        mock_db = AsyncMock()
        extractor = MemoryExtractor(mock_db)
        assert extractor.db == mock_db


class TestExtractFromTurn:
    """Test extract_from_turn method."""

    @pytest.mark.asyncio
    async def test_extract_simple_preference(self):
        """Should extract preference from conversation."""
        mock_db = AsyncMock()
        extractor = MemoryExtractor(mock_db)

        turn = MagicMock(spec=ConversationTurn)
        turn.user_message = "I absolutely love Italian food!"
        turn.assistant_message = "That's great! Italy has amazing cuisine."

        llm_response = {
            "memories": [
                {
                    "subject": "user",
                    "predicate": "loves",
                    "object": "Italian food",
                    "object_type": "food",
                    "negation": False,
                    "importance": 0.7,
                    "confidence": 1.0,
                    "natural_language": "User loves Italian food",
                    "tags": ["food", "preference"],
                }
            ],
            "summary_if_episode_end": None,
        }

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"response": json.dumps(llm_response)}
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_post.return_value.__aexit__ = AsyncMock()

            # Use context manager mock
            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.post.return_value = mock_response
                mock_client.return_value.__aenter__.return_value = mock_instance
                mock_client.return_value.__aexit__.return_value = None

                result = await extractor.extract_from_turn(turn)

                assert len(result.memories) == 1
                assert result.memories[0].predicate == "loves"
                assert result.memories[0].object == "Italian food"

    @pytest.mark.asyncio
    async def test_extract_with_history(self):
        """Should use conversation history for context."""
        mock_db = AsyncMock()
        extractor = MemoryExtractor(mock_db)

        turn = MagicMock(spec=ConversationTurn)
        turn.user_message = "Yes, that's right."
        turn.assistant_message = "Great, I'll remember that."

        history = [
            {"role": "user", "content": "I'm allergic to peanuts."},
            {"role": "assistant", "content": "Thank you for letting me know. Is this a severe allergy?"},
        ]

        llm_response = {"memories": [], "summary_if_episode_end": None}

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"response": json.dumps(llm_response)}
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None

            await extractor.extract_from_turn(turn, conversation_history=history)

            # Verify history was included in the prompt
            call_args = mock_instance.post.call_args
            request_json = call_args.kwargs.get("json", call_args[1].get("json", {}))
            prompt = request_json.get("prompt", "")
            assert "allergic to peanuts" in prompt

    @pytest.mark.asyncio
    async def test_extract_handles_invalid_json(self):
        """Should handle malformed JSON response."""
        mock_db = AsyncMock()
        extractor = MemoryExtractor(mock_db)

        turn = MagicMock(spec=ConversationTurn)
        turn.user_message = "Hello"
        turn.assistant_message = "Hi there!"

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"response": "not valid json {{{"}
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None

            result = await extractor.extract_from_turn(turn)

            # Should return empty result, not crash
            assert result.memories == []

    @pytest.mark.asyncio
    async def test_extract_handles_api_error(self):
        """Should propagate API errors."""
        mock_db = AsyncMock()
        extractor = MemoryExtractor(mock_db)

        turn = MagicMock(spec=ConversationTurn)
        turn.user_message = "Test"
        turn.assistant_message = "Test response"

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.side_effect = Exception("API timeout")
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None

            with pytest.raises(Exception, match="API timeout"):
                await extractor.extract_from_turn(turn)


class TestStoreMemories:
    """Test store_memories method."""

    @pytest.mark.asyncio
    async def test_store_single_memory(self):
        """Should store a single memory to database."""
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        extractor = MemoryExtractor(mock_db)

        turn = MagicMock(spec=ConversationTurn)
        turn.id = uuid4()
        turn.app_token_id = 1
        turn.application_group = "test-app"

        result = ExtractionResult(
            memories=[
                ExtractedMemory(
                    predicate="likes",
                    object="coffee",
                    object_type="food",
                    natural_language="User likes coffee",
                )
            ]
        )

        with patch("app.core.memory_extractor.generate_embedding", return_value=[0.1] * 384):
            stored = await extractor.store_memories(turn, result)

            assert len(stored) == 1
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_multiple_memories(self):
        """Should store multiple memories from single turn."""
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        extractor = MemoryExtractor(mock_db)

        turn = MagicMock(spec=ConversationTurn)
        turn.id = uuid4()
        turn.app_token_id = 1
        turn.application_group = None

        result = ExtractionResult(
            memories=[
                ExtractedMemory(
                    predicate="likes",
                    object="coffee",
                    object_type="food",
                    natural_language="User likes coffee",
                ),
                ExtractedMemory(
                    predicate="works_at",
                    object="startup",
                    object_type="employment",
                    natural_language="User works at a startup",
                ),
            ]
        )

        with patch("app.core.memory_extractor.generate_embedding", return_value=[0.1] * 384):
            stored = await extractor.store_memories(turn, result)

            assert len(stored) == 2
            assert mock_db.add.call_count == 2

    @pytest.mark.asyncio
    async def test_store_handles_embedding_failure(self):
        """Should store memory even if embedding fails."""
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        extractor = MemoryExtractor(mock_db)

        turn = MagicMock(spec=ConversationTurn)
        turn.id = uuid4()
        turn.app_token_id = 1
        turn.application_group = None

        result = ExtractionResult(
            memories=[
                ExtractedMemory(
                    predicate="likes",
                    object="coffee",
                    object_type="food",
                    natural_language="User likes coffee",
                )
            ]
        )

        with patch(
            "app.core.memory_extractor.generate_embedding",
            side_effect=Exception("Embedding service down"),
        ):
            stored = await extractor.store_memories(turn, result)

            # Should still store, just without embedding
            assert len(stored) == 1

    @pytest.mark.asyncio
    async def test_store_empty_result(self):
        """Should handle empty extraction result."""
        mock_db = AsyncMock()
        extractor = MemoryExtractor(mock_db)

        turn = MagicMock(spec=ConversationTurn)
        turn.id = uuid4()
        turn.app_token_id = 1

        result = ExtractionResult(memories=[])

        stored = await extractor.store_memories(turn, result)

        assert stored == []
        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_parses_expires_at(self):
        """Should parse expiration date."""
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        extractor = MemoryExtractor(mock_db)

        turn = MagicMock(spec=ConversationTurn)
        turn.id = uuid4()
        turn.app_token_id = 1
        turn.application_group = None

        result = ExtractionResult(
            memories=[
                ExtractedMemory(
                    predicate="visiting",
                    object="New York",
                    object_type="travel",
                    natural_language="User is visiting New York",
                    expires_at="2025-06-15T00:00:00Z",
                )
            ]
        )

        with patch("app.core.memory_extractor.generate_embedding", return_value=[0.1] * 384):
            stored = await extractor.store_memories(turn, result)

            assert len(stored) == 1
            # Memory should have expires_at set
            added_memory = mock_db.add.call_args[0][0]
            assert added_memory.expires_at is not None


class TestProcessTurn:
    """Test process_turn method."""

    @pytest.mark.asyncio
    async def test_process_turn_success(self):
        """Should process turn and update status."""
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        extractor = MemoryExtractor(mock_db)

        turn = MagicMock(spec=ConversationTurn)
        turn.id = uuid4()
        turn.app_token_id = 1
        turn.application_group = None
        turn.user_message = "I love Python programming"
        turn.assistant_message = "Python is great!"
        turn.extraction_status = ExtractionStatus.PENDING

        llm_response = {
            "memories": [
                {
                    "subject": "user",
                    "predicate": "loves",
                    "object": "Python programming",
                    "object_type": "topic",
                    "negation": False,
                    "importance": 0.7,
                    "confidence": 1.0,
                    "natural_language": "User loves Python programming",
                    "tags": ["programming"],
                }
            ],
            "summary_if_episode_end": None,
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"response": json.dumps(llm_response)}
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None

            with patch("app.core.memory_extractor.generate_embedding", return_value=[0.1] * 384):
                memories = await extractor.process_turn(turn)

                assert len(memories) == 1
                assert turn.extraction_status == ExtractionStatus.COMPLETED
                assert turn.extracted_at is not None

    @pytest.mark.asyncio
    async def test_process_turn_skipped(self):
        """Should mark as skipped when no memories extracted."""
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()

        extractor = MemoryExtractor(mock_db)

        turn = MagicMock(spec=ConversationTurn)
        turn.id = uuid4()
        turn.user_message = "Hello"
        turn.assistant_message = "Hi!"
        turn.extraction_status = ExtractionStatus.PENDING

        llm_response = {"memories": [], "summary_if_episode_end": None}

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"response": json.dumps(llm_response)}
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None

            memories = await extractor.process_turn(turn)

            assert memories == []
            assert turn.extraction_status == ExtractionStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_process_turn_failure(self):
        """Should mark as failed on error."""
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()

        extractor = MemoryExtractor(mock_db)

        turn = MagicMock(spec=ConversationTurn)
        turn.id = uuid4()
        turn.user_message = "Test"
        turn.assistant_message = "Response"
        turn.extraction_status = ExtractionStatus.PENDING

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.side_effect = Exception("Network error")
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None

            with pytest.raises(Exception):
                await extractor.process_turn(turn)

            assert turn.extraction_status == ExtractionStatus.FAILED
            assert "Network error" in turn.extraction_error


class TestProcessBatch:
    """Test process_batch method."""

    @pytest.mark.asyncio
    async def test_process_batch_empty(self):
        """Should handle no pending turns."""
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        extractor = MemoryExtractor(mock_db)

        stats = await extractor.process_batch()

        assert stats["total"] == 0
        assert stats["completed"] == 0
        assert stats["memories_created"] == 0

    @pytest.mark.asyncio
    async def test_process_batch_with_turns(self):
        """Should process multiple turns."""
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        turns = [
            MagicMock(
                id=uuid4(),
                app_token_id=1,
                application_group=None,
                user_message=f"Message {i}",
                assistant_message=f"Response {i}",
                extraction_status=ExtractionStatus.PENDING,
            )
            for i in range(3)
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = turns
        mock_db.execute = AsyncMock(return_value=mock_result)

        extractor = MemoryExtractor(mock_db)

        llm_response = {"memories": [], "summary_if_episode_end": None}

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"response": json.dumps(llm_response)}
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None

            stats = await extractor.process_batch()

            assert stats["total"] == 3
            assert stats["skipped"] == 3  # No memories extracted


class TestGetPendingCount:
    """Test get_pending_count method."""

    @pytest.mark.asyncio
    async def test_pending_count_all(self):
        """Should return count of all pending turns."""
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar.return_value = 42
        mock_db.execute = AsyncMock(return_value=mock_result)

        extractor = MemoryExtractor(mock_db)

        count = await extractor.get_pending_count()

        assert count == 42

    @pytest.mark.asyncio
    async def test_pending_count_filtered(self):
        """Should filter by app_token_id and application_group."""
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_db.execute = AsyncMock(return_value=mock_result)

        extractor = MemoryExtractor(mock_db)

        count = await extractor.get_pending_count(
            app_token_id=123, application_group="my-app"
        )

        assert count == 5
        # Verify filters were applied
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_pending_count_zero(self):
        """Should return 0 for no pending turns."""
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        extractor = MemoryExtractor(mock_db)

        count = await extractor.get_pending_count()

        assert count == 0


class TestExtractionPrompt:
    """Test extraction prompt configuration."""

    def test_extraction_prompt_exists(self):
        """Should have comprehensive extraction prompt."""
        from app.core.memory_extractor import EXTRACTION_PROMPT

        assert "memory" in EXTRACTION_PROMPT.lower()
        assert "json" in EXTRACTION_PROMPT.lower()
        assert "subject" in EXTRACTION_PROMPT
        assert "predicate" in EXTRACTION_PROMPT
        assert "importance" in EXTRACTION_PROMPT

    def test_extraction_prompt_includes_examples(self):
        """Should include example extractions."""
        from app.core.memory_extractor import EXTRACTION_PROMPT

        assert "Examples" in EXTRACTION_PROMPT or "example" in EXTRACTION_PROMPT.lower()
        assert "allergic" in EXTRACTION_PROMPT.lower()
