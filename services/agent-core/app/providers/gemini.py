import json
from typing import AsyncGenerator

import httpx

from app.providers.base import BaseProvider


class GeminiProvider(BaseProvider):
    """Google Gemini API provider"""

    provider_name = "gemini"
    supports_streaming = True

    API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
    DEFAULT_MODEL = "gemini-1.5-flash"

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

    def _get_url(self, stream: bool = False) -> str:
        action = "streamGenerateContent" if stream else "generateContent"
        return f"{self.API_BASE}/{self.model}:{action}?key={self.api_key}"

    def _format_contents(
        self,
        prompt: str,
        system_prompt: str | None = None,
        messages: list[dict] | None = None,
    ) -> tuple[list[dict], dict | None]:
        """Format messages for Gemini API."""
        contents = []
        system_instruction = None

        # System prompt is handled separately in Gemini
        if system_prompt:
            system_instruction = {"parts": [{"text": system_prompt}]}

        # Add conversation history
        if messages:
            for msg in messages:
                role = msg.get("role", "user")
                # Gemini uses "user" and "model" roles
                if role == "assistant":
                    role = "model"
                elif role == "system":
                    continue  # Skip system messages in history

                contents.append({
                    "role": role,
                    "parts": [{"text": msg.get("content", "")}],
                })

        # Add the current prompt
        contents.append({
            "role": "user",
            "parts": [{"text": prompt}],
        })

        return contents, system_instruction

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        messages: list[dict] | None = None,
    ) -> str:
        contents, system_instruction = self._format_contents(
            prompt, system_prompt, messages
        )

        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": self.max_tokens,
                "temperature": self.temperature,
            },
        }

        if system_instruction:
            payload["systemInstruction"] = system_instruction

        response = await self.client.post(
            self._get_url(stream=False),
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        # Extract text from response
        candidates = data.get("candidates", [])
        if candidates:
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if parts:
                return parts[0].get("text", "")
        return ""

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        messages: list[dict] | None = None,
    ) -> AsyncGenerator[str, None]:
        contents, system_instruction = self._format_contents(
            prompt, system_prompt, messages
        )

        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": self.max_tokens,
                "temperature": self.temperature,
            },
        }

        if system_instruction:
            payload["systemInstruction"] = system_instruction

        # Gemini streaming uses alt=sse parameter
        url = self._get_url(stream=True) + "&alt=sse"

        async with self.client.stream("POST", url, json=payload) as response:
            response.raise_for_status()

            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue

                data_str = line[6:]  # Remove "data: " prefix

                try:
                    data = json.loads(data_str)
                    candidates = data.get("candidates", [])
                    if candidates:
                        content = candidates[0].get("content", {})
                        parts = content.get("parts", [])
                        if parts:
                            text = parts[0].get("text", "")
                            if text:
                                yield text

                except json.JSONDecodeError:
                    continue

    async def health_check(self) -> bool:
        """Check if we can reach the Gemini API."""
        try:
            # List models endpoint
            response = await self.client.get(
                f"{self.API_BASE}?key={self.api_key}"
            )
            return response.status_code == 200
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
