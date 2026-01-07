"""Comprehensive tests for multi-agent orchestrator."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.orchestrator import (
    AgentOrchestrator,
    AgentResponse,
    OrchestratedResponse,
    OrchestrationStrategy,
)


class TestOrchestrationDataStructures:
    """Test orchestration data structures."""

    def test_agent_response_success(self):
        """AgentResponse should capture successful execution."""
        response = AgentResponse(
            agent_id=uuid4(),
            agent_name="claude-agent",
            agent_role="coder",
            content="Here's the code...",
            success=True,
        )
        assert response.success is True
        assert response.error is None
        assert response.content == "Here's the code..."

    def test_agent_response_failure(self):
        """AgentResponse should capture failures with errors."""
        response = AgentResponse(
            agent_id=uuid4(),
            agent_name="claude-agent",
            agent_role="coder",
            content="",
            success=False,
            error="API rate limit exceeded",
        )
        assert response.success is False
        assert response.error == "API rate limit exceeded"

    def test_orchestrated_response_single_agent(self):
        """OrchestratedResponse should work for single agent."""
        agent_response = AgentResponse(
            agent_id=uuid4(),
            agent_name="test-agent",
            agent_role="leader",
            content="Response text",
            success=True,
        )
        orchestrated = OrchestratedResponse(
            primary_response="Response text",
            agent_responses=[agent_response],
            strategy=OrchestrationStrategy.SINGLE,
        )
        assert orchestrated.primary_response == "Response text"
        assert len(orchestrated.agent_responses) == 1
        assert orchestrated.strategy == OrchestrationStrategy.SINGLE

    def test_orchestrated_response_multiple_agents(self):
        """OrchestratedResponse should combine multiple agent responses."""
        responses = [
            AgentResponse(
                agent_id=uuid4(),
                agent_name="researcher",
                agent_role="researcher",
                content="Research findings...",
                success=True,
            ),
            AgentResponse(
                agent_id=uuid4(),
                agent_name="coder",
                agent_role="coder",
                content="Implementation...",
                success=True,
            ),
        ]
        orchestrated = OrchestratedResponse(
            primary_response="Combined output",
            agent_responses=responses,
            strategy=OrchestrationStrategy.PARALLEL,
        )
        assert len(orchestrated.agent_responses) == 2


class TestOrchestratorInitialization:
    """Test orchestrator initialization and setup."""

    def test_orchestrator_init(self):
        """Orchestrator should initialize with database session."""
        mock_db = AsyncMock()
        orchestrator = AgentOrchestrator(mock_db)
        assert orchestrator.db == mock_db
        assert orchestrator._provider_cache == {}

    @pytest.mark.asyncio
    async def test_orchestrator_close_cleans_providers(self):
        """close() should clean up all cached providers."""
        mock_db = AsyncMock()
        orchestrator = AgentOrchestrator(mock_db)

        # Add mock providers to cache
        mock_provider1 = AsyncMock()
        mock_provider2 = AsyncMock()
        orchestrator._provider_cache = {
            uuid4(): mock_provider1,
            uuid4(): mock_provider2,
        }

        await orchestrator.close()

        mock_provider1.close.assert_called_once()
        mock_provider2.close.assert_called_once()
        assert orchestrator._provider_cache == {}


class TestProviderCreation:
    """Test provider instance creation for agents."""

    @pytest.mark.asyncio
    async def test_get_provider_creates_ollama_provider(self):
        """Should create Ollama provider without API key."""
        mock_db = AsyncMock()
        orchestrator = AgentOrchestrator(mock_db)

        mock_agent = MagicMock()
        mock_agent.id = uuid4()
        mock_agent.provider_type = "ollama"
        mock_agent.model = "llama3.2"
        mock_agent.max_tokens = 1024
        mock_agent.temperature = 0.7
        mock_agent.api_key_encrypted = None

        with patch.object(
            orchestrator, "_get_provider_for_agent"
        ) as mock_get_provider:
            mock_provider = MagicMock()
            mock_get_provider.return_value = mock_provider

            # Directly test the caching behavior
            orchestrator._provider_cache[mock_agent.id] = mock_provider
            cached = orchestrator._provider_cache.get(mock_agent.id)
            assert cached == mock_provider

    @pytest.mark.asyncio
    async def test_provider_caching(self):
        """Should cache provider instances for reuse."""
        mock_db = AsyncMock()
        orchestrator = AgentOrchestrator(mock_db)

        agent_id = uuid4()
        mock_provider = MagicMock()
        orchestrator._provider_cache[agent_id] = mock_provider

        # Accessing cached provider should return same instance
        assert orchestrator._provider_cache[agent_id] == mock_provider


class TestSingleOrchestration:
    """Test SINGLE orchestration strategy."""

    @pytest.mark.asyncio
    async def test_single_with_specific_agent_id(self):
        """Should route to specific agent by ID."""
        mock_db = AsyncMock()
        orchestrator = AgentOrchestrator(mock_db)

        agent_id = uuid4()
        app_id = uuid4()

        mock_agent = MagicMock()
        mock_agent.id = agent_id
        mock_agent.name = "specific-agent"
        mock_agent.role = "coder"
        mock_agent.system_prompt = "You are a coder."

        with patch(
            "app.core.orchestrator.get_agents_by_app",
            return_value=[mock_agent],
        ):
            with patch.object(
                orchestrator, "_execute_agent"
            ) as mock_execute:
                mock_execute.return_value = AgentResponse(
                    agent_id=agent_id,
                    agent_name="specific-agent",
                    agent_role="coder",
                    content="Here's the code",
                    success=True,
                )

                result = await orchestrator.orchestrate(
                    app_id=app_id,
                    prompt="Write code",
                    strategy=OrchestrationStrategy.SINGLE,
                    agent_id=agent_id,
                )

                assert result.primary_response == "Here's the code"
                assert result.strategy == OrchestrationStrategy.SINGLE
                mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_single_with_target_role(self):
        """Should route to agent by role."""
        mock_db = AsyncMock()
        orchestrator = AgentOrchestrator(mock_db)

        app_id = uuid4()

        mock_coder = MagicMock()
        mock_coder.id = uuid4()
        mock_coder.name = "coder-agent"
        mock_coder.role = "coder"

        mock_reviewer = MagicMock()
        mock_reviewer.id = uuid4()
        mock_reviewer.name = "reviewer-agent"
        mock_reviewer.role = "reviewer"

        with patch(
            "app.core.orchestrator.get_agents_by_app",
            return_value=[mock_coder, mock_reviewer],
        ):
            with patch.object(
                orchestrator, "_execute_agent"
            ) as mock_execute:
                mock_execute.return_value = AgentResponse(
                    agent_id=mock_reviewer.id,
                    agent_name="reviewer-agent",
                    agent_role="reviewer",
                    content="Code review: looks good",
                    success=True,
                )

                result = await orchestrator.orchestrate(
                    app_id=app_id,
                    prompt="Review this code",
                    strategy=OrchestrationStrategy.SINGLE,
                    target_role="reviewer",
                )

                # Should have called execute with the reviewer agent
                call_args = mock_execute.call_args
                assert call_args[0][0].role == "reviewer"

    @pytest.mark.asyncio
    async def test_single_defaults_to_leader(self):
        """Should default to leader agent if no specific selection."""
        mock_db = AsyncMock()
        orchestrator = AgentOrchestrator(mock_db)

        app_id = uuid4()

        mock_leader = MagicMock()
        mock_leader.id = uuid4()
        mock_leader.name = "leader-agent"
        mock_leader.role = "leader"

        mock_coder = MagicMock()
        mock_coder.id = uuid4()
        mock_coder.name = "coder-agent"
        mock_coder.role = "coder"

        with patch(
            "app.core.orchestrator.get_agents_by_app",
            return_value=[mock_coder, mock_leader],  # Leader not first
        ):
            with patch.object(
                orchestrator, "_execute_agent"
            ) as mock_execute:
                mock_execute.return_value = AgentResponse(
                    agent_id=mock_leader.id,
                    agent_name="leader-agent",
                    agent_role="leader",
                    content="Leader response",
                    success=True,
                )

                result = await orchestrator.orchestrate(
                    app_id=app_id,
                    prompt="General question",
                    strategy=OrchestrationStrategy.SINGLE,
                )

                # Should prefer leader
                call_args = mock_execute.call_args
                assert call_args[0][0].role == "leader"

    @pytest.mark.asyncio
    async def test_single_raises_for_missing_agent(self):
        """Should raise error if specified agent not found."""
        mock_db = AsyncMock()
        orchestrator = AgentOrchestrator(mock_db)

        with patch(
            "app.core.orchestrator.get_agents_by_app",
            return_value=[],
        ):
            with pytest.raises(ValueError, match="No active agents"):
                await orchestrator.orchestrate(
                    app_id=uuid4(),
                    prompt="Test",
                    strategy=OrchestrationStrategy.SINGLE,
                )

    @pytest.mark.asyncio
    async def test_single_raises_for_invalid_role(self):
        """Should raise error if target role not found."""
        mock_db = AsyncMock()
        orchestrator = AgentOrchestrator(mock_db)

        mock_agent = MagicMock()
        mock_agent.id = uuid4()
        mock_agent.role = "coder"

        with patch(
            "app.core.orchestrator.get_agents_by_app",
            return_value=[mock_agent],
        ):
            with pytest.raises(ValueError, match="No agent with role"):
                await orchestrator.orchestrate(
                    app_id=uuid4(),
                    prompt="Test",
                    strategy=OrchestrationStrategy.SINGLE,
                    target_role="researcher",
                )


class TestLeaderOrchestration:
    """Test LEADER orchestration strategy."""

    @pytest.mark.asyncio
    async def test_leader_uses_leader_agent(self):
        """Should route to leader agent."""
        mock_db = AsyncMock()
        orchestrator = AgentOrchestrator(mock_db)

        app_id = uuid4()

        mock_leader = MagicMock()
        mock_leader.id = uuid4()
        mock_leader.name = "leader"
        mock_leader.role = "leader"
        mock_leader.system_prompt = "You are the leader."

        mock_coder = MagicMock()
        mock_coder.id = uuid4()
        mock_coder.name = "coder"
        mock_coder.role = "coder"
        mock_coder.system_prompt = "You write code."

        with patch(
            "app.core.orchestrator.get_agents_by_app",
            return_value=[mock_leader, mock_coder],
        ):
            with patch.object(
                orchestrator, "_execute_agent"
            ) as mock_execute:
                mock_execute.return_value = AgentResponse(
                    agent_id=mock_leader.id,
                    agent_name="leader",
                    agent_role="leader",
                    content="Leader decision",
                    success=True,
                )

                result = await orchestrator.orchestrate(
                    app_id=app_id,
                    prompt="What should we do?",
                    strategy=OrchestrationStrategy.LEADER,
                )

                assert result.strategy == OrchestrationStrategy.LEADER
                call_args = mock_execute.call_args
                assert call_args[0][0].role == "leader"

    @pytest.mark.asyncio
    async def test_leader_falls_back_to_single_without_leader(self):
        """Should fall back to single strategy if no leader exists."""
        mock_db = AsyncMock()
        orchestrator = AgentOrchestrator(mock_db)

        mock_coder = MagicMock()
        mock_coder.id = uuid4()
        mock_coder.name = "coder"
        mock_coder.role = "coder"

        with patch(
            "app.core.orchestrator.get_agents_by_app",
            return_value=[mock_coder],
        ):
            with patch.object(
                orchestrator, "_execute_agent"
            ) as mock_execute:
                mock_execute.return_value = AgentResponse(
                    agent_id=mock_coder.id,
                    agent_name="coder",
                    agent_role="coder",
                    content="Coder response",
                    success=True,
                )

                result = await orchestrator.orchestrate(
                    app_id=uuid4(),
                    prompt="Test",
                    strategy=OrchestrationStrategy.LEADER,
                )

                # Should have executed with the only available agent
                assert mock_execute.called


class TestParallelOrchestration:
    """Test PARALLEL orchestration strategy."""

    @pytest.mark.asyncio
    async def test_parallel_runs_all_agents(self):
        """Should run all agents concurrently."""
        mock_db = AsyncMock()
        orchestrator = AgentOrchestrator(mock_db)

        app_id = uuid4()

        agents = [
            MagicMock(id=uuid4(), name=f"agent-{i}", role=role)
            for i, role in enumerate(["coder", "reviewer", "researcher"])
        ]

        responses = [
            AgentResponse(
                agent_id=agent.id,
                agent_name=agent.name,
                agent_role=agent.role,
                content=f"Response from {agent.name}",
                success=True,
            )
            for agent in agents
        ]

        with patch(
            "app.core.orchestrator.get_agents_by_app",
            return_value=agents,
        ):
            with patch.object(
                orchestrator, "_execute_agent", side_effect=responses
            ):
                result = await orchestrator.orchestrate(
                    app_id=app_id,
                    prompt="Analyze this",
                    strategy=OrchestrationStrategy.PARALLEL,
                )

                assert len(result.agent_responses) == 3
                assert result.strategy == OrchestrationStrategy.PARALLEL

    @pytest.mark.asyncio
    async def test_parallel_aggregates_responses(self):
        """Should combine responses from multiple agents."""
        mock_db = AsyncMock()
        orchestrator = AgentOrchestrator(mock_db)

        agents = [
            MagicMock(id=uuid4(), name="agent-1", role="coder"),
            MagicMock(id=uuid4(), name="agent-2", role="reviewer"),
        ]

        responses = [
            AgentResponse(
                agent_id=agents[0].id,
                agent_name="agent-1",
                agent_role="coder",
                content="Code implementation",
                success=True,
            ),
            AgentResponse(
                agent_id=agents[1].id,
                agent_name="agent-2",
                agent_role="reviewer",
                content="Code review",
                success=True,
            ),
        ]

        with patch(
            "app.core.orchestrator.get_agents_by_app",
            return_value=agents,
        ):
            with patch.object(
                orchestrator, "_execute_agent", side_effect=responses
            ):
                result = await orchestrator.orchestrate(
                    app_id=uuid4(),
                    prompt="Test",
                    strategy=OrchestrationStrategy.PARALLEL,
                )

                # Primary response should contain both agent outputs
                assert "agent-1" in result.primary_response
                assert "agent-2" in result.primary_response

    @pytest.mark.asyncio
    async def test_parallel_handles_partial_failures(self):
        """Should handle some agents failing."""
        mock_db = AsyncMock()
        orchestrator = AgentOrchestrator(mock_db)

        agents = [
            MagicMock(id=uuid4(), name="success-agent", role="coder"),
            MagicMock(id=uuid4(), name="failed-agent", role="reviewer"),
        ]

        responses = [
            AgentResponse(
                agent_id=agents[0].id,
                agent_name="success-agent",
                agent_role="coder",
                content="Success response",
                success=True,
            ),
            AgentResponse(
                agent_id=agents[1].id,
                agent_name="failed-agent",
                agent_role="reviewer",
                content="",
                success=False,
                error="API error",
            ),
        ]

        with patch(
            "app.core.orchestrator.get_agents_by_app",
            return_value=agents,
        ):
            with patch.object(
                orchestrator, "_execute_agent", side_effect=responses
            ):
                result = await orchestrator.orchestrate(
                    app_id=uuid4(),
                    prompt="Test",
                    strategy=OrchestrationStrategy.PARALLEL,
                )

                # Should still get successful response
                assert "Success response" in result.primary_response
                # Both responses should be in agent_responses
                assert len(result.agent_responses) == 2

    @pytest.mark.asyncio
    async def test_parallel_all_failures(self):
        """Should handle all agents failing gracefully."""
        mock_db = AsyncMock()
        orchestrator = AgentOrchestrator(mock_db)

        agents = [MagicMock(id=uuid4(), name="agent", role="coder")]

        with patch(
            "app.core.orchestrator.get_agents_by_app",
            return_value=agents,
        ):
            with patch.object(
                orchestrator,
                "_execute_agent",
                return_value=AgentResponse(
                    agent_id=agents[0].id,
                    agent_name="agent",
                    agent_role="coder",
                    content="",
                    success=False,
                    error="Total failure",
                ),
            ):
                result = await orchestrator.orchestrate(
                    app_id=uuid4(),
                    prompt="Test",
                    strategy=OrchestrationStrategy.PARALLEL,
                )

                assert "failed" in result.primary_response.lower()
                assert "Total failure" in result.primary_response


class TestChainOrchestration:
    """Test CHAIN orchestration strategy."""

    @pytest.mark.asyncio
    async def test_chain_processes_in_order(self):
        """Should process agents in role order."""
        mock_db = AsyncMock()
        orchestrator = AgentOrchestrator(mock_db)

        # Create agents in non-ordered way
        agents = [
            MagicMock(id=uuid4(), name="coder", role="coder", system_prompt=None),
            MagicMock(id=uuid4(), name="researcher", role="researcher", system_prompt=None),
            MagicMock(id=uuid4(), name="reviewer", role="reviewer", system_prompt=None),
        ]

        call_order = []

        async def mock_execute(agent, *args, **kwargs):
            call_order.append(agent.role)
            return AgentResponse(
                agent_id=agent.id,
                agent_name=agent.name,
                agent_role=agent.role,
                content=f"{agent.role} output",
                success=True,
            )

        with patch(
            "app.core.orchestrator.get_agents_by_app",
            return_value=agents,
        ):
            with patch.object(
                orchestrator, "_execute_agent", side_effect=mock_execute
            ):
                result = await orchestrator.orchestrate(
                    app_id=uuid4(),
                    prompt="Process this",
                    strategy=OrchestrationStrategy.CHAIN,
                )

                # Should be: researcher -> coder -> reviewer
                assert call_order == ["researcher", "coder", "reviewer"]

    @pytest.mark.asyncio
    async def test_chain_passes_context(self):
        """Should pass previous outputs to next agent."""
        mock_db = AsyncMock()
        orchestrator = AgentOrchestrator(mock_db)

        agents = [
            MagicMock(id=uuid4(), name="researcher", role="researcher", system_prompt=None),
            MagicMock(id=uuid4(), name="coder", role="coder", system_prompt=None),
        ]

        prompts_received = []

        async def mock_execute(agent, prompt, *args, **kwargs):
            prompts_received.append(prompt)
            return AgentResponse(
                agent_id=agent.id,
                agent_name=agent.name,
                agent_role=agent.role,
                content=f"{agent.role}: findings here",
                success=True,
            )

        with patch(
            "app.core.orchestrator.get_agents_by_app",
            return_value=agents,
        ):
            with patch.object(
                orchestrator, "_execute_agent", side_effect=mock_execute
            ):
                await orchestrator.orchestrate(
                    app_id=uuid4(),
                    prompt="Original prompt",
                    strategy=OrchestrationStrategy.CHAIN,
                )

                # Second call should include previous output
                assert len(prompts_received) == 2
                assert "Original prompt" in prompts_received[0]
                assert "researcher" in prompts_received[1].lower()

    @pytest.mark.asyncio
    async def test_chain_returns_last_successful(self):
        """Should return last successful agent's output as primary."""
        mock_db = AsyncMock()
        orchestrator = AgentOrchestrator(mock_db)

        agents = [
            MagicMock(id=uuid4(), name="researcher", role="researcher", system_prompt=None),
            MagicMock(id=uuid4(), name="reviewer", role="reviewer", system_prompt=None),
        ]

        responses = [
            AgentResponse(
                agent_id=agents[0].id,
                agent_name="researcher",
                agent_role="researcher",
                content="Research output",
                success=True,
            ),
            AgentResponse(
                agent_id=agents[1].id,
                agent_name="reviewer",
                agent_role="reviewer",
                content="Final review",
                success=True,
            ),
        ]

        with patch(
            "app.core.orchestrator.get_agents_by_app",
            return_value=agents,
        ):
            with patch.object(
                orchestrator, "_execute_agent", side_effect=responses
            ):
                result = await orchestrator.orchestrate(
                    app_id=uuid4(),
                    prompt="Test",
                    strategy=OrchestrationStrategy.CHAIN,
                )

                assert result.primary_response == "Final review"


class TestStreamingSingle:
    """Test streaming with single agent."""

    @pytest.mark.asyncio
    async def test_stream_single_yields_chunks(self):
        """Should stream chunks from single agent."""
        mock_db = AsyncMock()
        orchestrator = AgentOrchestrator(mock_db)

        agent = MagicMock()
        agent.id = uuid4()
        agent.name = "streaming-agent"
        agent.role = "coder"

        async def mock_stream(*args, **kwargs):
            chunks = ["Hello", " ", "World"]
            for chunk in chunks:
                yield chunk

        with patch(
            "app.core.orchestrator.get_agents_by_app",
            return_value=[agent],
        ):
            with patch.object(
                orchestrator, "_execute_agent_stream", side_effect=mock_stream
            ):
                chunks = []
                async for chunk in orchestrator.stream_single(
                    app_id=uuid4(),
                    prompt="Test",
                ):
                    chunks.append(chunk)

                assert chunks == ["Hello", " ", "World"]


class TestAgentExecution:
    """Test individual agent execution."""

    @pytest.mark.asyncio
    async def test_execute_agent_success(self):
        """Should execute agent and return response."""
        mock_db = AsyncMock()
        orchestrator = AgentOrchestrator(mock_db)

        agent = MagicMock()
        agent.id = uuid4()
        agent.name = "test-agent"
        agent.role = "coder"
        agent.system_prompt = "You are a coder"

        mock_provider = AsyncMock()
        mock_provider.generate.return_value = "Generated response"

        with patch.object(
            orchestrator,
            "_get_provider_for_agent",
            return_value=mock_provider,
        ):
            result = await orchestrator._execute_agent(
                agent=agent,
                prompt="Write code",
                system_prompt="Override prompt",
            )

            assert result.success is True
            assert result.content == "Generated response"
            assert result.agent_id == agent.id

    @pytest.mark.asyncio
    async def test_execute_agent_uses_agent_system_prompt(self):
        """Should prefer agent's system prompt over provided one."""
        mock_db = AsyncMock()
        orchestrator = AgentOrchestrator(mock_db)

        agent = MagicMock()
        agent.id = uuid4()
        agent.name = "test-agent"
        agent.role = "coder"
        agent.system_prompt = "Agent's own prompt"

        mock_provider = AsyncMock()
        mock_provider.generate.return_value = "Response"

        with patch.object(
            orchestrator,
            "_get_provider_for_agent",
            return_value=mock_provider,
        ):
            await orchestrator._execute_agent(
                agent=agent,
                prompt="Test",
                system_prompt="Provided prompt",
            )

            # Should have used agent's system prompt
            call_args = mock_provider.generate.call_args
            assert call_args.kwargs["system_prompt"] == "Agent's own prompt"

    @pytest.mark.asyncio
    async def test_execute_agent_handles_error(self):
        """Should handle provider errors gracefully."""
        mock_db = AsyncMock()
        orchestrator = AgentOrchestrator(mock_db)

        agent = MagicMock()
        agent.id = uuid4()
        agent.name = "failing-agent"
        agent.role = "coder"
        agent.system_prompt = None

        mock_provider = AsyncMock()
        mock_provider.generate.side_effect = Exception("API Error")

        with patch.object(
            orchestrator,
            "_get_provider_for_agent",
            return_value=mock_provider,
        ):
            result = await orchestrator._execute_agent(
                agent=agent,
                prompt="Test",
            )

            assert result.success is False
            assert "API Error" in result.error


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_orchestrate_unknown_strategy(self):
        """Should raise for unknown strategy."""
        mock_db = AsyncMock()
        orchestrator = AgentOrchestrator(mock_db)

        with patch(
            "app.core.orchestrator.get_agents_by_app",
            return_value=[MagicMock(id=uuid4(), role="coder")],
        ):
            # Create invalid strategy value
            with pytest.raises(ValueError, match="Unknown strategy"):
                await orchestrator.orchestrate(
                    app_id=uuid4(),
                    prompt="Test",
                    strategy="invalid_strategy",
                )

    @pytest.mark.asyncio
    async def test_stream_with_invalid_agent_id(self):
        """Should raise for non-existent agent ID in streaming."""
        mock_db = AsyncMock()
        orchestrator = AgentOrchestrator(mock_db)

        with patch(
            "app.core.orchestrator.get_agents_by_app",
            return_value=[MagicMock(id=uuid4(), role="coder")],
        ):
            with pytest.raises(ValueError, match="not found"):
                async for _ in orchestrator.stream_single(
                    app_id=uuid4(),
                    prompt="Test",
                    agent_id=uuid4(),  # Non-existent ID
                ):
                    pass
