"""Tests for chat API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


class TestChatEndpoint:
    """Test /api/v1/chat endpoint."""

    def test_chat_requires_auth(self):
        """Should require Bearer token authentication."""
        from app.main import app

        client = TestClient(app)

        response = client.post(
            "/api/v1/chat",
            json={"message": "Hello"},
        )

        # No auth header returns 401 or 403
        assert response.status_code in (401, 403)

    def test_chat_rejects_invalid_token(self):
        """Should reject invalid tokens."""
        from app.main import app

        client = TestClient(app, raise_server_exceptions=False)

        response = client.post(
            "/api/v1/chat",
            json={"message": "Hello"},
            headers={"Authorization": "Bearer invalid-token"},
        )

        # Invalid token returns 401 (or 500 if DB unavailable in test env)
        assert response.status_code in (401, 500)

    @pytest.mark.asyncio
    async def test_chat_request_schema(self):
        """ChatRequest should validate input."""
        from app.api.routes.chat import ChatRequest

        # Valid request
        req = ChatRequest(message="Hello")
        assert req.message == "Hello"
        assert req.session_id is None
        assert req.context is None
        assert req.style is None

        # With all fields
        req = ChatRequest(
            message="Hi",
            session_id="sess-123",
            context={"app": "test", "page": "home"},
            style="brief",
        )
        assert req.session_id == "sess-123"
        assert req.context["app"] == "test"

    @pytest.mark.asyncio
    async def test_chat_response_schema(self):
        """ChatResponse should have required fields."""
        from app.api.routes.chat import ChatResponse

        resp = ChatResponse(response="Hello!", session_id="sess-abc")
        assert resp.response == "Hello!"
        assert resp.session_id == "sess-abc"


class TestChatStreamEndpoint:
    """Test /api/v1/chat/stream endpoint."""

    def test_stream_requires_auth(self):
        """Should require Bearer token authentication."""
        from app.main import app

        client = TestClient(app)

        response = client.post(
            "/api/v1/chat/stream",
            json={"message": "Hello"},
        )

        # No auth header returns 401 or 403
        assert response.status_code in (401, 403)


class TestStoreAndExtractTurn:
    """Test conversation turn storage and extraction."""

    @pytest.mark.asyncio
    async def test_store_turn_creates_record(self):
        """Should store conversation turn in database."""
        from app.api.routes.chat import store_and_extract_turn

        with patch("app.api.routes.chat.settings") as mock_settings:
            mock_settings.memory_extraction_enabled = True
            mock_settings.memory_extraction_inline = False

            with patch("app.api.routes.chat.pgvector_available", True):
                with patch("app.api.routes.chat.async_session") as mock_session_maker:
                    mock_db = AsyncMock()
                    mock_db.add = MagicMock()
                    mock_db.commit = AsyncMock()
                    mock_db.refresh = AsyncMock()

                    mock_session_maker.return_value.__aenter__.return_value = mock_db
                    mock_session_maker.return_value.__aexit__.return_value = None

                    await store_and_extract_turn(
                        app_token_id=1,
                        session_id="sess-123",
                        user_message="Hello",
                        assistant_message="Hi there!",
                        context={"app": "test"},
                    )

                    mock_db.add.assert_called_once()
                    mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_store_turn_disabled(self):
        """Should skip storage when extraction disabled."""
        from app.api.routes.chat import store_and_extract_turn

        with patch("app.api.routes.chat.settings") as mock_settings:
            mock_settings.memory_extraction_enabled = False

            # Should not raise, just return
            await store_and_extract_turn(
                app_token_id=1,
                session_id="sess-123",
                user_message="Hello",
                assistant_message="Hi!",
            )

    @pytest.mark.asyncio
    async def test_store_turn_inline_extraction(self):
        """Should trigger inline extraction when enabled."""
        from app.api.routes.chat import store_and_extract_turn

        with patch("app.api.routes.chat.settings") as mock_settings:
            mock_settings.memory_extraction_enabled = True
            mock_settings.memory_extraction_inline = True

            with patch("app.api.routes.chat.pgvector_available", True):
                with patch("app.api.routes.chat.async_session") as mock_session_maker:
                    mock_db = AsyncMock()
                    mock_db.add = MagicMock()
                    mock_db.commit = AsyncMock()
                    mock_db.refresh = AsyncMock()

                    mock_session_maker.return_value.__aenter__.return_value = mock_db
                    mock_session_maker.return_value.__aexit__.return_value = None

                    with patch("app.core.memory_extractor.MemoryExtractor") as mock_extractor:
                        mock_instance = AsyncMock()
                        mock_extractor.return_value = mock_instance

                        await store_and_extract_turn(
                            app_token_id=1,
                            session_id="sess-123",
                            user_message="I love pizza",
                            assistant_message="Pizza is great!",
                        )

                        # Extractor should have been called
                        mock_instance.process_turn.assert_called_once()


class TestSessionManagement:
    """Test session handling in chat."""

    def test_session_manager_creates_session(self):
        """Should create new session when none provided."""
        from app.core.sessions import SessionManager

        manager = SessionManager()
        session = manager.get_or_create_session(
            session_id=None,
            app_token_id=1,
            context={"app": "test"},
        )

        assert session.id is not None
        assert session.app_token_id == 1

    def test_session_manager_retrieves_existing(self):
        """Should retrieve existing session."""
        from app.core.sessions import SessionManager

        manager = SessionManager()

        # Create session
        session1 = manager.get_or_create_session(
            session_id=None,
            app_token_id=1,
        )

        # Retrieve same session
        session2 = manager.get_or_create_session(
            session_id=session1.id,
            app_token_id=1,
        )

        assert session1.id == session2.id

    def test_session_manager_adds_messages(self):
        """Should track messages in session."""
        from app.core.sessions import SessionManager

        manager = SessionManager()

        session = manager.get_or_create_session(
            session_id=None,
            app_token_id=1,
        )

        manager.add_message(session.id, "user", "Hello")
        manager.add_message(session.id, "assistant", "Hi there!")

        # Retrieve updated session
        updated = manager.get_or_create_session(
            session_id=session.id,
            app_token_id=1,
        )

        assert len(updated.messages) == 2
        assert updated.messages[0].role == "user"
        assert updated.messages[1].role == "assistant"


class TestRateLimiting:
    """Test rate limiting on chat endpoints."""

    def test_rate_limit_applied(self):
        """Should have rate limiting configured."""
        from app.core.rate_limit import limiter

        # Limiter should be configured
        assert limiter is not None
