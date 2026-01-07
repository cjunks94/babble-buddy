"""Agent management API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import verify_admin_key
from app.crud.agent import (
    create_agent,
    delete_agent,
    get_agent,
    get_agents_by_app,
    list_agents,
    update_agent,
)
from app.db.database import get_db
from app.schemas.agent import (
    AgentCreate,
    AgentListResponse,
    AgentResponse,
    AgentRole,
    AgentUpdate,
    ProviderType,
)
from app.utils.features import require_feature

router = APIRouter()


def _agent_to_response(agent) -> AgentResponse:
    """Convert Agent model to response schema."""
    return AgentResponse(
        id=agent.id,
        app_id=agent.app_id,
        name=agent.name,
        provider_type=ProviderType(agent.provider_type),
        model=agent.model,
        role=AgentRole(agent.role),
        system_prompt=agent.system_prompt,
        max_tokens=agent.max_tokens,
        temperature=agent.temperature,
        is_active=agent.is_active,
        has_api_key=agent.api_key_encrypted is not None,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


def _agent_to_list_response(agent) -> AgentListResponse:
    """Convert Agent model to list response schema."""
    return AgentListResponse(
        id=agent.id,
        app_id=agent.app_id,
        name=agent.name,
        provider_type=ProviderType(agent.provider_type),
        model=agent.model,
        role=AgentRole(agent.role),
        is_active=agent.is_active,
        has_api_key=agent.api_key_encrypted is not None,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


@router.post("/agents", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
@require_feature("multi_agent")
async def create_agent_endpoint(
    body: AgentCreate,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key),
):
    """
    Create a new agent.

    Requires the `multi_agent` feature flag to be enabled.
    Requires admin API key authentication.
    """
    # Validate that external providers have an API key
    if body.provider_type != ProviderType.OLLAMA and not body.api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"API key is required for provider type '{body.provider_type.value}'",
        )

    agent = await create_agent(db, body)
    return _agent_to_response(agent)


@router.get("/agents", response_model=list[AgentListResponse])
@require_feature("multi_agent")
async def list_agents_endpoint(
    app_id: UUID | None = Query(None, description="Filter by application ID"),
    role: AgentRole | None = Query(None, description="Filter by agent role"),
    active_only: bool = Query(False, description="Only return active agents"),
    limit: int = Query(100, ge=1, le=1000, description="Max agents to return"),
    offset: int = Query(0, ge=0, description="Number of agents to skip"),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key),
):
    """
    List agents with optional filtering.

    Requires the `multi_agent` feature flag to be enabled.
    Requires admin API key authentication.
    """
    if app_id:
        agents = await get_agents_by_app(
            db,
            app_id,
            active_only=active_only,
            role=role.value if role else None,
        )
        # Apply pagination manually for app-filtered results
        agents = agents[offset : offset + limit]
    else:
        agents = await list_agents(db, active_only=active_only, limit=limit, offset=offset)
        # Apply role filter if specified
        if role:
            agents = [a for a in agents if a.role == role.value]

    return [_agent_to_list_response(a) for a in agents]


@router.get("/agents/{agent_id}", response_model=AgentResponse)
@require_feature("multi_agent")
async def get_agent_endpoint(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key),
):
    """
    Get a specific agent by ID.

    Requires the `multi_agent` feature flag to be enabled.
    Requires admin API key authentication.
    """
    agent = await get_agent(db, agent_id)

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    return _agent_to_response(agent)


@router.patch("/agents/{agent_id}", response_model=AgentResponse)
@require_feature("multi_agent")
async def update_agent_endpoint(
    agent_id: UUID,
    body: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key),
):
    """
    Update an existing agent.

    Requires the `multi_agent` feature flag to be enabled.
    Requires admin API key authentication.
    """
    agent = await update_agent(db, agent_id, body)

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    return _agent_to_response(agent)


@router.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_feature("multi_agent")
async def delete_agent_endpoint(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_key),
):
    """
    Delete an agent.

    Requires the `multi_agent` feature flag to be enabled.
    Requires admin API key authentication.
    """
    deleted = await delete_agent(db, agent_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    return None
