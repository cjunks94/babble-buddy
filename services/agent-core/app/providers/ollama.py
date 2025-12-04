import json
from typing import AsyncGenerator

import httpx

from app.config import settings
from app.providers.base import BaseProvider


class OllamaProvider(BaseProvider):
    provider_name = "ollama"
    supports_streaming = True

    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        repeat_penalty: float | None = None,
        num_ctx: int | None = None,
    ):
        self.host = host or settings.ollama_host
        self.model = model or settings.ollama_model
        self.max_tokens = max_tokens or settings.ollama_max_tokens
        self.temperature = temperature or settings.ollama_temperature
        self.top_p = top_p or settings.ollama_top_p
        self.repeat_penalty = repeat_penalty or settings.ollama_repeat_penalty
        self.num_ctx = num_ctx or settings.ollama_num_ctx
        self.client = httpx.AsyncClient(timeout=120.0)

    def _build_options(self) -> dict:
        """Build Ollama options from parameters."""
        return {
            "num_predict": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "repeat_penalty": self.repeat_penalty,
            "num_ctx": self.num_ctx,
        }

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        messages: list[dict] | None = None,
    ) -> str:
        payload = {
            "model": self.model,
            "stream": False,
            "options": self._build_options(),
        }

        if messages:
            formatted_messages = []
            if system_prompt:
                formatted_messages.append({"role": "system", "content": system_prompt})
            formatted_messages.extend(messages)
            formatted_messages.append({"role": "user", "content": prompt})
            payload["messages"] = formatted_messages
            endpoint = f"{self.host}/api/chat"
        else:
            payload["prompt"] = prompt
            if system_prompt:
                payload["system"] = system_prompt
            endpoint = f"{self.host}/api/generate"

        response = await self.client.post(endpoint, json=payload)
        response.raise_for_status()
        data = response.json()

        if messages:
            return data.get("message", {}).get("content", "")
        return data.get("response", "")

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        messages: list[dict] | None = None,
    ) -> AsyncGenerator[str, None]:
        payload = {
            "model": self.model,
            "stream": True,
            "options": self._build_options(),
        }

        if messages:
            formatted_messages = []
            if system_prompt:
                formatted_messages.append({"role": "system", "content": system_prompt})
            formatted_messages.extend(messages)
            formatted_messages.append({"role": "user", "content": prompt})
            payload["messages"] = formatted_messages
            endpoint = f"{self.host}/api/chat"
        else:
            payload["prompt"] = prompt
            if system_prompt:
                payload["system"] = system_prompt
            endpoint = f"{self.host}/api/generate"

        async with self.client.stream("POST", endpoint, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    data = json.loads(line)
                    if messages:
                        content = data.get("message", {}).get("content", "")
                    else:
                        content = data.get("response", "")
                    if content:
                        yield content

    async def health_check(self) -> bool:
        try:
            response = await self.client.get(f"{self.host}/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    async def close(self):
        await self.client.aclose()


ollama_provider = OllamaProvider()
