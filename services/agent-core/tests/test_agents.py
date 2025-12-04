"""Tests for agent registry."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestAgentModel:
    """Test Agent database model."""

    def test_agent_has_required_fields(self):
        """Agent model should have all required fields."""
        from app.db.models import Agent

        # Check model has expected columns
        columns = {c.name for c in Agent.__table__.columns}
        assert "id" in columns
        assert "app_id" in columns
        assert "name" in columns
        assert "provider_type" in columns
        assert "model" in columns
        assert "role" in columns
        assert "system_prompt" in columns
        assert "is_active" in columns
        assert "created_at" in columns

    def test_agent_has_encrypted_api_key(self):
        """Agent should store API keys encrypted."""
        from app.db.models import Agent

        columns = {c.name for c in Agent.__table__.columns}
        assert "api_key_encrypted" in columns


class TestAgentEncryption:
    """Test API key encryption utilities."""

    def test_encrypt_decrypt_roundtrip(self):
        """Encrypting then decrypting should return original value."""
        from app.utils.encryption import decrypt_api_key, encrypt_api_key

        original = "sk-ant-api123-test-key"
        encrypted = encrypt_api_key(original)

        # Encrypted should be different from original
        assert encrypted != original

        # Decrypting should return original
        decrypted = decrypt_api_key(encrypted)
        assert decrypted == original

    def test_encrypted_keys_are_different(self):
        """Same key encrypted twice should produce different ciphertexts."""
        from app.utils.encryption import encrypt_api_key

        key = "sk-test-key"
        encrypted1 = encrypt_api_key(key)
        encrypted2 = encrypt_api_key(key)

        # Fernet includes randomness, so encryptions should differ
        assert encrypted1 != encrypted2


@pytest.mark.skip(reason="Agent CRUD not implemented yet - planned for multi-agent feature")
class TestAgentCRUD:
    """Test agent CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_agent(self):
        """Should create a new agent."""
        from app.crud.agent import create_agent
        from app.schemas.agent import AgentCreate

        agent_data = AgentCreate(
            app_id=uuid4(),
            name="test-claude",
            provider_type="anthropic",
            api_key="sk-ant-test-key",
            model="claude-3-5-sonnet-20241022",
            role="reviewer",
            system_prompt="You are a code reviewer.",
        )

        # Mock DB session
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        agent = await create_agent(mock_db, agent_data)

        assert agent.name == "test-claude"
        assert agent.provider_type == "anthropic"
        assert agent.api_key_encrypted is not None
        assert agent.api_key_encrypted != "sk-ant-test-key"  # Should be encrypted

    @pytest.mark.asyncio
    async def test_get_agent_by_id(self):
        """Should retrieve agent by ID."""
        from app.crud.agent import get_agent

        mock_db = AsyncMock()
        agent_id = uuid4()

        # Mock the query result
        mock_agent = MagicMock()
        mock_agent.id = agent_id
        mock_agent.name = "test-agent"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_agent
        mock_db.execute = AsyncMock(return_value=mock_result)

        agent = await get_agent(mock_db, agent_id)

        assert agent is not None
        assert agent.id == agent_id

    @pytest.mark.asyncio
    async def test_list_agents_by_app(self):
        """Should list all agents for an app."""
        from app.crud.agent import list_agents

        mock_db = AsyncMock()
        app_id = uuid4()

        mock_agents = [
            MagicMock(id=uuid4(), name="agent-1"),
            MagicMock(id=uuid4(), name="agent-2"),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_agents
        mock_db.execute = AsyncMock(return_value=mock_result)

        agents = await list_agents(mock_db, app_id)

        assert len(agents) == 2

    @pytest.mark.asyncio
    async def test_delete_agent(self):
        """Should delete an agent."""
        from app.crud.agent import delete_agent

        mock_db = AsyncMock()
        mock_agent = MagicMock()
        mock_agent.id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_agent
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        result = await delete_agent(mock_db, mock_agent.id)

        assert result is True
        mock_db.delete.assert_called_once()


@pytest.mark.skip(reason="Agent API not implemented yet - planned for multi-agent feature")
class TestAgentAPI:
    """Test agent API endpoints."""

    @pytest.mark.asyncio
    async def test_create_agent_requires_feature_flag(self):
        """Should return 403 if multi_agent feature is disabled."""
        from fastapi.testclient import TestClient

        from app.main import app

        # Feature is disabled by default
        client = TestClient(app)

        response = client.post(
            "/api/v1/agents",
            json={
                "name": "test-agent",
                "provider_type": "anthropic",
                "api_key": "sk-test",
                "model": "claude-3-5-sonnet-20241022",
                "role": "coder",
            },
            headers={"Authorization": "Bearer test-admin-key"},
        )

        assert response.status_code == 403
        assert "multi_agent" in response.json()["detail"]

    @pytest.mark.asyncio
    @patch("app.utils.features.is_feature_enabled", return_value=True)
    async def test_create_agent_validates_provider_type(self, mock_feature):
        """Should reject invalid provider types."""
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)

        response = client.post(
            "/api/v1/agents",
            json={
                "name": "test-agent",
                "provider_type": "invalid_provider",
                "api_key": "sk-test",
                "model": "some-model",
                "role": "coder",
            },
            headers={"Authorization": "Bearer test-admin-key"},
        )

        # Should fail validation
        assert response.status_code in (400, 422)

    @pytest.mark.asyncio
    async def test_list_agents_requires_feature_flag(self):
        """Should return 403 if multi_agent feature is disabled."""
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)

        response = client.get(
            "/api/v1/agents",
            headers={"Authorization": "Bearer test-admin-key"},
        )

        assert response.status_code == 403
