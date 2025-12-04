import json
from collections.abc import AsyncGenerator

import httpx

from app.providers.base import BaseProvider


class OpenAIProvider(BaseProvider):
    """OpenAI GPT API provider"""

    provider_name = "openai"
    supports_streaming = True

    API_URL = "https://api.openai.com/v1/chat/completions"
    DEFAULT_MODEL = "gpt-4o"

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        base_url: str | None = None,  # For OpenAI-compatible APIs
    ):
        self.api_key = api_key
        self.model = model or self.DEFAULT_MODEL
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.base_url = base_url or self.API_URL
        self.client = httpx.AsyncClient(timeout=120.0)

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _format_messages(
        self,
        prompt: str,
        system_prompt: str | None = None,
        messages: list[dict] | None = None,
    ) -> list[dict]:
        """Format messages for OpenAI API."""
        formatted = []

        # Add system prompt first
        if system_prompt:
            formatted.append({"role": "system", "content": system_prompt})

        # Add conversation history
        if messages:
            for msg in messages:
                formatted.append(
                    {
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", ""),
                    }
                )

        # Add the current prompt
        formatted.append({"role": "user", "content": prompt})

        return formatted

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        messages: list[dict] | None = None,
    ) -> str:
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": self._format_messages(prompt, system_prompt, messages),
        }

        response = await self.client.post(
            self.base_url,
            headers=self._get_headers(),
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        # Extract message content
        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")
        return ""

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        messages: list[dict] | None = None,
    ) -> AsyncGenerator[str, None]:
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": self._format_messages(prompt, system_prompt, messages),
            "stream": True,
        }

        async with self.client.stream(
            "POST",
            self.base_url,
            headers=self._get_headers(),
            json=payload,
        ) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue

                data_str = line[6:]  # Remove "data: " prefix
                if data_str == "[DONE]":
                    break

                try:
                    data = json.loads(data_str)
                    choices = data.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content

                except json.JSONDecodeError:
                    continue

    async def health_check(self) -> bool:
        """Check if we can reach the OpenAI API."""
        try:
            response = await self.client.get(
                "https://api.openai.com/v1/models",
                headers=self._get_headers(),
            )
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def close(self):
        await self.client.aclose()

    def get_info(self) -> dict:
        return {
            **super().get_info(),
            "model": self.model,
            "max_tokens": self.max_tokens,
            "base_url": self.base_url,
        }
