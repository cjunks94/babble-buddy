import json
from typing import AsyncGenerator

import httpx

from app.providers.base import BaseProvider


class AnthropicProvider(BaseProvider):
    """Claude API provider (Anthropic)"""

    provider_name = "anthropic"
    supports_streaming = True

    API_URL = "https://api.anthropic.com/v1/messages"
    DEFAULT_MODEL = "claude-3-5-sonnet-20241022"

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ):
        self.api_key = api_key
        self.model = model or self.DEFAULT_MODEL
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.client = httpx.AsyncClient(timeout=120.0)

    def _get_headers(self) -> dict:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    def _format_messages(
        self,
        prompt: str,
        messages: list[dict] | None = None,
    ) -> list[dict]:
        """Format messages for Claude API."""
        formatted = []

        if messages:
            for msg in messages:
                role = msg.get("role", "user")
                # Claude uses "user" and "assistant" roles
                if role == "system":
                    continue  # System is handled separately
                formatted.append({
                    "role": role,
                    "content": msg.get("content", ""),
                })

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
            "messages": self._format_messages(prompt, messages),
        }

        if system_prompt:
            payload["system"] = system_prompt

        response = await self.client.post(
            self.API_URL,
            headers=self._get_headers(),
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        # Extract text from content blocks
        content = data.get("content", [])
        if content and isinstance(content, list):
            return content[0].get("text", "")
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
            "messages": self._format_messages(prompt, messages),
            "stream": True,
        }

        if system_prompt:
            payload["system"] = system_prompt

        async with self.client.stream(
            "POST",
            self.API_URL,
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
                    event_type = data.get("type", "")

                    if event_type == "content_block_delta":
                        delta = data.get("delta", {})
                        text = delta.get("text", "")
                        if text:
                            yield text

                except json.JSONDecodeError:
                    continue

    async def health_check(self) -> bool:
        """Check if we can reach the Anthropic API."""
        try:
            # Make a minimal request to check API key validity
            response = await self.client.post(
                self.API_URL,
                headers=self._get_headers(),
                json={
                    "model": self.model,
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "hi"}],
                },
            )
            return response.status_code in (200, 400)  # 400 = valid key, bad request
        except Exception:
            return False

    async def close(self):
        await self.client.aclose()

    def get_info(self) -> dict:
        return {
            **super().get_info(),
            "model": self.model,
            "max_tokens": self.max_tokens,
        }
