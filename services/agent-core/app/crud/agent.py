"""CRUD operations for Agent model."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Agent
from app.schemas.agent import AgentCreate, AgentUpdate
from app.utils.encryption import decrypt_api_key, encrypt_api_key


async def create_agent(db: AsyncSession, agent_data: AgentCreate) -> Agent:
    """
    Create a new agent.

    Args:
        db: Database session
        agent_data: Agent creation data

    Returns:
        Created Agent instance
    """
    # Encrypt API key if provided
    encrypted_key = None
    if agent_data.api_key:
        encrypted_key = encrypt_api_key(agent_data.api_key)

    agent = Agent(
        app_id=agent_data.app_id,
        name=agent_data.name,
        provider_type=agent_data.provider_type.value,
        api_key_encrypted=encrypted_key,
        model=agent_data.model,
        role=agent_data.role.value,
        system_prompt=agent_data.system_prompt,
        max_tokens=agent_data.max_tokens,
        temperature=agent_data.temperature,
    )

    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    return agent


async def get_agent(db: AsyncSession, agent_id: UUID) -> Agent | None:
    """
    Get an agent by ID.

    Args:
        db: Database session
        agent_id: Agent UUID

    Returns:
        Agent if found, None otherwise
    """
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    return result.scalar_one_or_none()


async def get_agents_by_app(
    db: AsyncSession,
    app_id: UUID,
    *,
    active_only: bool = False,
    role: str | None = None,
) -> list[Agent]:
    """
    Get all agents for a specific app.

    Args:
        db: Database session
        app_id: Application UUID
        active_only: If True, only return active agents
        role: Filter by specific role

    Returns:
        List of agents for the app
    """
    query = select(Agent).where(Agent.app_id == app_id)

    if active_only:
        query = query.where(Agent.is_active == True)  # noqa: E712

    if role:
        query = query.where(Agent.role == role)

    query = query.order_by(Agent.created_at.desc())
    result = await db.execute(query)

    return list(result.scalars().all())


async def list_agents(
    db: AsyncSession,
    *,
    active_only: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> list[Agent]:
    """
    List all agents with pagination.

    Args:
        db: Database session
        active_only: If True, only return active agents
        limit: Max number of agents to return
        offset: Number of agents to skip

    Returns:
        List of agents
    """
    query = select(Agent)

    if active_only:
        query = query.where(Agent.is_active == True)  # noqa: E712

    query = query.order_by(Agent.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)

    return list(result.scalars().all())


async def update_agent(
    db: AsyncSession,
    agent_id: UUID,
    agent_data: AgentUpdate,
) -> Agent | None:
    """
    Update an existing agent.

    Args:
        db: Database session
        agent_id: Agent UUID
        agent_data: Update data

    Returns:
        Updated Agent if found, None otherwise
    """
    agent = await get_agent(db, agent_id)
    if not agent:
        return None

    # Update only provided fields
    update_data = agent_data.model_dump(exclude_unset=True)

    # Handle API key encryption separately
    if "api_key" in update_data:
        api_key = update_data.pop("api_key")
        if api_key:
            agent.api_key_encrypted = encrypt_api_key(api_key)
        else:
            agent.api_key_encrypted = None

    # Handle enum values
    if "role" in update_data and update_data["role"]:
        update_data["role"] = update_data["role"].value

    for field, value in update_data.items():
        setattr(agent, field, value)

    await db.commit()
    await db.refresh(agent)

    return agent


async def delete_agent(db: AsyncSession, agent_id: UUID) -> bool:
    """
    Delete an agent.

    Args:
        db: Database session
        agent_id: Agent UUID

    Returns:
        True if deleted, False if not found
    """
    agent = await get_agent(db, agent_id)
    if not agent:
        return False

    await db.delete(agent)
    await db.commit()

    return True


async def get_agent_with_decrypted_key(db: AsyncSession, agent_id: UUID) -> tuple[Agent, str | None] | None:
    """
    Get an agent with its decrypted API key.

    This should only be used when the key is needed for making API calls.

    Args:
        db: Database session
        agent_id: Agent UUID

    Returns:
        Tuple of (Agent, decrypted_api_key) if found, None otherwise
    """
    agent = await get_agent(db, agent_id)
    if not agent:
        return None

    decrypted_key = None
    if agent.api_key_encrypted:
        decrypted_key = decrypt_api_key(agent.api_key_encrypted)

    return agent, decrypted_key
