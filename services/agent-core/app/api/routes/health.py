from fastapi import APIRouter

from app.providers.ollama import ollama_provider

router = APIRouter()


@router.get("/health")
async def health_check():
    ollama_status = await ollama_provider.health_check()

    return {
        "status": "ok",
        "services": {
            "ollama": "connected" if ollama_status else "disconnected",
        },
    }
