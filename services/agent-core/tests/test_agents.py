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


class TestAgentSchemas:
    """Test Agent Pydantic schemas."""

    def test_agent_create_schema_valid(self):
        """AgentCreate should accept valid data."""
        from app.schemas.agent import AgentCreate, AgentRole, ProviderType

        agent = AgentCreate(
            app_id=uuid4(),
            name="test-claude",
            provider_type=ProviderType.ANTHROPIC,
            api_key="sk-ant-test-key",
            model="claude-3-5-sonnet-20241022",
            role=AgentRole.REVIEWER,
            system_prompt="You are a code reviewer.",
        )

        assert agent.name == "test-claude"
        assert agent.provider_type == ProviderType.ANTHROPIC
        assert agent.role == AgentRole.REVIEWER

    def test_agent_create_schema_defaults(self):
        """AgentCreate should have sensible defaults."""
        from app.schemas.agent import AgentCreate, AgentRole, ProviderType

        agent = AgentCreate(
            app_id=uuid4(),
            name="test-agent",
            provider_type=ProviderType.OLLAMA,
            model="llama3.2",
            role=AgentRole.CODER,
        )

        assert agent.max_tokens == 1024
        assert agent.temperature == 0.7
        assert agent.api_key is None

    def test_provider_type_enum_values(self):
        """ProviderType should have all supported providers."""
        from app.schemas.agent import ProviderType

        assert ProviderType.OLLAMA.value == "ollama"
        assert ProviderType.ANTHROPIC.value == "anthropic"
        assert ProviderType.OPENAI.value == "openai"
        assert ProviderType.GEMINI.value == "gemini"

    def test_agent_role_enum_values(self):
        """AgentRole should have all defined roles."""
        from app.schemas.agent import AgentRole

        assert AgentRole.LEADER.value == "leader"
        assert AgentRole.CODER.value == "coder"
        assert AgentRole.REVIEWER.value == "reviewer"
        assert AgentRole.RESEARCHER.value == "researcher"


class TestAgentCRUD:
    """Test agent CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_agent(self):
        """Should create a new agent with encrypted API key."""
        from app.crud.agent import create_agent
        from app.schemas.agent import AgentCreate, AgentRole, ProviderType

        agent_data = AgentCreate(
            app_id=uuid4(),
            name="test-claude",
            provider_type=ProviderType.ANTHROPIC,
            api_key="sk-ant-test-key",
            model="claude-3-5-sonnet-20241022",
            role=AgentRole.REVIEWER,
            system_prompt="You are a code reviewer.",
        )

        # Mock DB session
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        agent = await create_agent(mock_db, agent_data)

        # Verify agent was created
        assert agent.name == "test-claude"
        assert agent.provider_type == "anthropic"
        assert agent.role == "reviewer"
        assert agent.api_key_encrypted is not None
        assert agent.api_key_encrypted != "sk-ant-test-key"  # Should be encrypted

        # Verify DB operations
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_agent_without_api_key(self):
        """Should create an Ollama agent without API key."""
        from app.crud.agent import create_agent
        from app.schemas.agent import AgentCreate, AgentRole, ProviderType

        agent_data = AgentCreate(
            app_id=uuid4(),
            name="test-ollama",
            provider_type=ProviderType.OLLAMA,
            model="llama3.2",
            role=AgentRole.CODER,
        )

        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        agent = await create_agent(mock_db, agent_data)

        assert agent.provider_type == "ollama"
        assert agent.api_key_encrypted is None

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
    async def test_get_agent_not_found(self):
        """Should return None for non-existent agent."""
        from app.crud.agent import get_agent

        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        agent = await get_agent(mock_db, uuid4())

        assert agent is None

    @pytest.mark.asyncio
    async def test_get_agents_by_app(self):
        """Should list all agents for an app."""
        from app.crud.agent import get_agents_by_app

        mock_db = AsyncMock()
        app_id = uuid4()

        mock_agents = [
            MagicMock(id=uuid4(), name="agent-1"),
            MagicMock(id=uuid4(), name="agent-2"),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_agents
        mock_db.execute = AsyncMock(return_value=mock_result)

        agents = await get_agents_by_app(mock_db, app_id)

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

    @pytest.mark.asyncio
    async def test_delete_agent_not_found(self):
        """Should return False for non-existent agent."""
        from app.crud.agent import delete_agent

        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await delete_agent(mock_db, uuid4())

        assert result is False


class TestAgentAPI:
    """Test agent API endpoints."""

    # Default admin key from config
    ADMIN_AUTH_HEADER = {"Authorization": "Bearer change-me-in-production"}

    def test_create_agent_requires_feature_flag(self):
        """Should return 403 if multi_agent feature is disabled."""
        from fastapi.testclient import TestClient

        from app.main import app

        # Feature is disabled by default
        client = TestClient(app)

        response = client.post(
            "/api/v1/admin/agents",
            json={
                "app_id": str(uuid4()),
                "name": "test-agent",
                "provider_type": "anthropic",
                "api_key": "sk-test",
                "model": "claude-3-5-sonnet-20241022",
                "role": "coder",
            },
            headers=self.ADMIN_AUTH_HEADER,
        )

        assert response.status_code == 403
        assert "multi_agent" in response.json()["detail"]

    def test_list_agents_requires_feature_flag(self):
        """Should return 403 if multi_agent feature is disabled."""
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)

        response = client.get(
            "/api/v1/admin/agents",
            headers=self.ADMIN_AUTH_HEADER,
        )

        assert response.status_code == 403
        assert "multi_agent" in response.json()["detail"]

    def test_create_agent_requires_admin_key(self):
        """Should return 401/403 without admin key."""
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)

        response = client.post(
            "/api/v1/admin/agents",
            json={
                "app_id": str(uuid4()),
                "name": "test-agent",
                "provider_type": "anthropic",
                "api_key": "sk-test",
                "model": "claude-3-5-sonnet-20241022",
                "role": "coder",
            },
        )

        # Should fail auth before feature flag check
        assert response.status_code in (401, 403)

    def test_create_agent_rejects_invalid_admin_key(self):
        """Should return 401 with invalid admin key."""
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)

        response = client.post(
            "/api/v1/admin/agents",
            json={
                "app_id": str(uuid4()),
                "name": "test-agent",
                "provider_type": "anthropic",
                "api_key": "sk-test",
                "model": "claude-3-5-sonnet-20241022",
                "role": "coder",
            },
            headers={"Authorization": "Bearer wrong-key"},
        )

        assert response.status_code == 401

    def test_get_agent_requires_feature_flag(self):
        """Should return 403 if multi_agent feature is disabled."""
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)

        response = client.get(
            f"/api/v1/admin/agents/{uuid4()}",
            headers=self.ADMIN_AUTH_HEADER,
        )

        assert response.status_code == 403

    def test_delete_agent_requires_feature_flag(self):
        """Should return 403 if multi_agent feature is disabled."""
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)

        response = client.delete(
            f"/api/v1/admin/agents/{uuid4()}",
            headers=self.ADMIN_AUTH_HEADER,
        )

        assert response.status_code == 403


class TestOrchestrator:
    """Test agent orchestrator."""

    def test_orchestration_strategy_enum(self):
        """OrchestrationStrategy should have all strategies."""
        from app.core.orchestrator import OrchestrationStrategy

        assert OrchestrationStrategy.SINGLE.value == "single"
        assert OrchestrationStrategy.LEADER.value == "leader"
        assert OrchestrationStrategy.PARALLEL.value == "parallel"
        assert OrchestrationStrategy.CHAIN.value == "chain"

    def test_agent_response_dataclass(self):
        """AgentResponse should store response data."""
        from app.core.orchestrator import AgentResponse

        agent_id = uuid4()
        response = AgentResponse(
            agent_id=agent_id,
            agent_name="test-agent",
            agent_role="coder",
            content="Hello, world!",
            success=True,
        )

        assert response.agent_id == agent_id
        assert response.content == "Hello, world!"
        assert response.success is True
        assert response.error is None

    def test_orchestrated_response_dataclass(self):
        """OrchestratedResponse should combine agent responses."""
        from app.core.orchestrator import (
            AgentResponse,
            OrchestratedResponse,
            OrchestrationStrategy,
        )

        agent_response = AgentResponse(
            agent_id=uuid4(),
            agent_name="test-agent",
            agent_role="coder",
            content="Hello!",
            success=True,
        )

        orchestrated = OrchestratedResponse(
            primary_response="Hello!",
            agent_responses=[agent_response],
            strategy=OrchestrationStrategy.SINGLE,
        )

        assert orchestrated.primary_response == "Hello!"
        assert len(orchestrated.agent_responses) == 1
        assert orchestrated.strategy == OrchestrationStrategy.SINGLE
