"""Multi-agent orchestration for coordinating AI agents."""

import asyncio
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.crud.agent import get_agent_with_decrypted_key, get_agents_by_app
from app.db.models import Agent
from app.providers.base import BaseProvider
from app.providers.factory import ProviderFactory


class OrchestrationStrategy(str, Enum):
    """Strategies for routing messages to agents."""

    SINGLE = "single"  # Route to a single agent
    LEADER = "leader"  # Leader agent coordinates, may delegate
    PARALLEL = "parallel"  # Run multiple agents in parallel, aggregate
    CHAIN = "chain"  # Sequential processing through agents


@dataclass
class AgentResponse:
    """Response from a single agent."""

    agent_id: UUID
    agent_name: str
    agent_role: str
    content: str
    success: bool
    error: str | None = None


@dataclass
class OrchestratedResponse:
    """Combined response from orchestration."""

    primary_response: str
    agent_responses: list[AgentResponse]
    strategy: OrchestrationStrategy


class AgentOrchestrator:
    """
    Orchestrates multiple AI agents for complex tasks.

    Supports various strategies:
    - SINGLE: Route to best matching agent
    - LEADER: Leader agent makes decisions, delegates to specialists
    - PARALLEL: Run multiple agents, aggregate responses
    - CHAIN: Sequential processing through a chain of agents
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._provider_cache: dict[UUID, BaseProvider] = {}

    async def _get_provider_for_agent(self, agent: Agent) -> BaseProvider:
        """Get or create a provider instance for an agent."""
        if agent.id in self._provider_cache:
            return self._provider_cache[agent.id]

        # Get decrypted API key
        result = await get_agent_with_decrypted_key(self.db, agent.id)
        if not result:
            raise ValueError(f"Agent {agent.id} not found")

        _, api_key = result

        # Build provider kwargs
        kwargs = {
            "model": agent.model,
            "max_tokens": agent.max_tokens,
            "temperature": agent.temperature,
        }

        # Add API key for external providers
        if agent.provider_type != "ollama":
            if not api_key:
                raise ValueError(f"Agent {agent.name} requires an API key for {agent.provider_type}")
            kwargs["api_key"] = api_key

        provider = ProviderFactory.create(agent.provider_type, **kwargs)
        self._provider_cache[agent.id] = provider

        return provider

    async def _execute_agent(
        self,
        agent: Agent,
        prompt: str,
        system_prompt: str | None = None,
        messages: list[dict] | None = None,
    ) -> AgentResponse:
        """Execute a single agent and return its response."""
        try:
            provider = await self._get_provider_for_agent(agent)

            # Use agent's system prompt if available, otherwise use provided one
            effective_system_prompt = agent.system_prompt or system_prompt

            response = await provider.generate(
                prompt=prompt,
                system_prompt=effective_system_prompt,
                messages=messages,
            )

            return AgentResponse(
                agent_id=agent.id,
                agent_name=agent.name,
                agent_role=agent.role,
                content=response,
                success=True,
            )
        except Exception as e:
            logger.error(f"Agent {agent.name} failed: {e}")
            return AgentResponse(
                agent_id=agent.id,
                agent_name=agent.name,
                agent_role=agent.role,
                content="",
                success=False,
                error=str(e),
            )

    async def _execute_agent_stream(
        self,
        agent: Agent,
        prompt: str,
        system_prompt: str | None = None,
        messages: list[dict] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Execute a single agent with streaming."""
        provider = await self._get_provider_for_agent(agent)
        effective_system_prompt = agent.system_prompt or system_prompt

        async for chunk in provider.generate_stream(
            prompt=prompt,
            system_prompt=effective_system_prompt,
            messages=messages,
        ):
            yield chunk

    async def orchestrate(
        self,
        app_id: UUID,
        prompt: str,
        strategy: OrchestrationStrategy = OrchestrationStrategy.SINGLE,
        system_prompt: str | None = None,
        messages: list[dict] | None = None,
        target_role: str | None = None,
        agent_id: UUID | None = None,
    ) -> OrchestratedResponse:
        """
        Orchestrate agents to respond to a prompt.

        Args:
            app_id: Application ID to get agents for
            prompt: User prompt
            strategy: Orchestration strategy to use
            system_prompt: Optional system prompt override
            messages: Conversation history
            target_role: Specific role to target (for SINGLE strategy)
            agent_id: Specific agent ID to use (for SINGLE strategy)

        Returns:
            OrchestratedResponse with combined results
        """
        agents = await get_agents_by_app(self.db, app_id, active_only=True)

        if not agents:
            raise ValueError(f"No active agents found for app {app_id}")

        if strategy == OrchestrationStrategy.SINGLE:
            return await self._orchestrate_single(
                agents=agents,
                prompt=prompt,
                system_prompt=system_prompt,
                messages=messages,
                target_role=target_role,
                agent_id=agent_id,
            )
        elif strategy == OrchestrationStrategy.LEADER:
            return await self._orchestrate_leader(
                agents=agents,
                prompt=prompt,
                system_prompt=system_prompt,
                messages=messages,
            )
        elif strategy == OrchestrationStrategy.PARALLEL:
            return await self._orchestrate_parallel(
                agents=agents,
                prompt=prompt,
                system_prompt=system_prompt,
                messages=messages,
            )
        elif strategy == OrchestrationStrategy.CHAIN:
            return await self._orchestrate_chain(
                agents=agents,
                prompt=prompt,
                system_prompt=system_prompt,
                messages=messages,
            )
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    async def _orchestrate_single(
        self,
        agents: list[Agent],
        prompt: str,
        system_prompt: str | None = None,
        messages: list[dict] | None = None,
        target_role: str | None = None,
        agent_id: UUID | None = None,
    ) -> OrchestratedResponse:
        """Route to a single agent based on criteria."""
        # Select agent
        agent = None

        if agent_id:
            agent = next((a for a in agents if a.id == agent_id), None)
            if not agent:
                raise ValueError(f"Agent {agent_id} not found or not active")
        elif target_role:
            agent = next((a for a in agents if a.role == target_role), None)
            if not agent:
                raise ValueError(f"No agent with role '{target_role}' found")
        else:
            # Default: use leader if available, otherwise first agent
            agent = next((a for a in agents if a.role == "leader"), agents[0])

        response = await self._execute_agent(agent, prompt, system_prompt, messages)

        return OrchestratedResponse(
            primary_response=response.content,
            agent_responses=[response],
            strategy=OrchestrationStrategy.SINGLE,
        )

    async def _orchestrate_leader(
        self,
        agents: list[Agent],
        prompt: str,
        system_prompt: str | None = None,
        messages: list[dict] | None = None,
    ) -> OrchestratedResponse:
        """
        Leader-based orchestration.

        The leader agent receives the prompt and can delegate to specialists.
        Currently implements simple leader-only response.
        Future: Parse leader response for delegation instructions.
        """
        leader = next((a for a in agents if a.role == "leader"), None)
        if not leader:
            # Fall back to single orchestration with first agent
            return await self._orchestrate_single(agents, prompt, system_prompt, messages)

        # Build leader prompt with available agents info
        available_agents = "\n".join(
            f"- {a.name} ({a.role}): {a.system_prompt[:100] + '...' if a.system_prompt and len(a.system_prompt) > 100 else a.system_prompt or 'General purpose'}"
            for a in agents
            if a.id != leader.id
        )

        leader_system = leader.system_prompt or ""
        if available_agents:
            leader_system += f"\n\nAvailable specialist agents:\n{available_agents}"

        response = await self._execute_agent(leader, prompt, leader_system, messages)

        return OrchestratedResponse(
            primary_response=response.content,
            agent_responses=[response],
            strategy=OrchestrationStrategy.LEADER,
        )

    async def _orchestrate_parallel(
        self,
        agents: list[Agent],
        prompt: str,
        system_prompt: str | None = None,
        messages: list[dict] | None = None,
    ) -> OrchestratedResponse:
        """Run all agents in parallel and aggregate responses."""
        tasks = [
            self._execute_agent(agent, prompt, system_prompt, messages)
            for agent in agents
        ]

        responses = await asyncio.gather(*tasks)

        # Aggregate: combine successful responses
        successful = [r for r in responses if r.success]

        if not successful:
            # All failed, return first error
            return OrchestratedResponse(
                primary_response=f"All agents failed. First error: {responses[0].error}",
                agent_responses=list(responses),
                strategy=OrchestrationStrategy.PARALLEL,
            )

        if len(successful) == 1:
            primary = successful[0].content
        else:
            # Combine responses with agent attribution
            combined = "\n\n".join(
                f"**{r.agent_name}** ({r.agent_role}):\n{r.content}"
                for r in successful
            )
            primary = combined

        return OrchestratedResponse(
            primary_response=primary,
            agent_responses=list(responses),
            strategy=OrchestrationStrategy.PARALLEL,
        )

    async def _orchestrate_chain(
        self,
        agents: list[Agent],
        prompt: str,
        system_prompt: str | None = None,
        messages: list[dict] | None = None,
    ) -> OrchestratedResponse:
        """
        Chain orchestration: pass output through agents sequentially.

        Order: researcher -> coder -> reviewer -> leader (if present)
        Each agent receives the previous agent's output as context.
        """
        role_order = ["researcher", "coder", "reviewer", "leader"]
        ordered_agents = []

        for role in role_order:
            matching = [a for a in agents if a.role == role]
            ordered_agents.extend(matching)

        # Add any remaining agents
        remaining = [a for a in agents if a not in ordered_agents]
        ordered_agents.extend(remaining)

        responses: list[AgentResponse] = []
        current_prompt = prompt
        accumulated_context = ""

        for agent in ordered_agents:
            # Build prompt with context from previous agents
            if accumulated_context:
                chain_prompt = f"{current_prompt}\n\nContext from previous analysis:\n{accumulated_context}"
            else:
                chain_prompt = current_prompt

            response = await self._execute_agent(agent, chain_prompt, system_prompt, messages)
            responses.append(response)

            if response.success:
                accumulated_context += f"\n\n[{agent.name} ({agent.role})]:\n{response.content}"

        # Primary response is the last successful agent's response
        successful = [r for r in responses if r.success]
        primary = successful[-1].content if successful else f"Chain failed: {responses[-1].error}"

        return OrchestratedResponse(
            primary_response=primary,
            agent_responses=responses,
            strategy=OrchestrationStrategy.CHAIN,
        )

    async def stream_single(
        self,
        app_id: UUID,
        prompt: str,
        system_prompt: str | None = None,
        messages: list[dict] | None = None,
        target_role: str | None = None,
        agent_id: UUID | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream response from a single agent.

        For streaming, only single-agent mode is supported.
        """
        agents = await get_agents_by_app(self.db, app_id, active_only=True)

        if not agents:
            raise ValueError(f"No active agents found for app {app_id}")

        # Select agent
        agent = None

        if agent_id:
            agent = next((a for a in agents if a.id == agent_id), None)
            if not agent:
                raise ValueError(f"Agent {agent_id} not found or not active")
        elif target_role:
            agent = next((a for a in agents if a.role == target_role), None)
            if not agent:
                raise ValueError(f"No agent with role '{target_role}' found")
        else:
            agent = next((a for a in agents if a.role == "leader"), agents[0])

        async for chunk in self._execute_agent_stream(agent, prompt, system_prompt, messages):
            yield chunk

    async def close(self):
        """Clean up provider resources."""
        for provider in self._provider_cache.values():
            await provider.close()
        self._provider_cache.clear()
