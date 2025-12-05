from fastapi import APIRouter

from app.core.memory import get_embedding_cache_stats
from app.db.database import pgvector_available
from app.providers.ollama import ollama_provider

router = APIRouter()


@router.get("/health")
async def health_check():
    ollama_status = await ollama_provider.health_check()

    return {
        "status": "ok",
        "services": {
            "ollama": "connected" if ollama_status else "disconnected",
            "pgvector": "enabled" if pgvector_available else "disabled",
        },
        "cache": {
            "embedding": get_embedding_cache_stats(),
        },
    }
