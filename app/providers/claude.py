"""Ixtiyoriy provayder: Anthropic Claude (vision).

Aniqroq, lekin pullik va ma'lumot tashqariga chiqadi.
Shuning uchun default emas — maxfiylik muhim bo'lgan joyda ollama ishlatiladi.
"""
import base64
import json
import os

import httpx

from app.providers.base import VisionError, VisionProvider
from app.providers.prompt import SYSTEM_PROMPT, USER_PROMPT
from app.schema import LabelData, llm_schema

API_URL = "https://api.anthropic.com/v1/messages"


class ClaudeProvider(VisionProvider):
    name = "claude"

    def __init__(self) -> None:
        self.api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        self._model = os.getenv("CLAUDE_MODEL", "claude-sonnet-5")

    @property
    def model(self) -> str:
        return self._model

    async def health(self) -> bool:
        return bool(self.api_key)

    async def extract(self, image_bytes: bytes, mime_type: str) -> LabelData:
        if not self.api_key:
            raise VisionError("ANTHROPIC_API_KEY berilmagan")

        tool = {
            "name": "save_label",
            "description": "Yorliqdan ajratilgan maydonlarni saqlaydi",
            "input_schema": llm_schema(),
        }
        payload = {
            "model": self._model,
            "max_tokens": 1024,
            "system": SYSTEM_PROMPT,
            "tools": [tool],
            "tool_choice": {"type": "tool", "name": "save_label"},
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image", "source": {
                        "type": "base64",
                        "media_type": mime_type,
                        "data": base64.b64encode(image_bytes).decode(),
                    }},
                    {"type": "text", "text": USER_PROMPT},
                ],
            }],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(API_URL, json=payload, headers=headers)
                r.raise_for_status()
                body = r.json()
        except httpx.HTTPStatusError as e:
            raise VisionError(f"Claude API xatosi {e.response.status_code}") from e
        except httpx.HTTPError as e:
            raise VisionError(f"Claude bilan aloqa xatosi: {e}") from e

        for block in body.get("content", []):
            if block.get("type") == "tool_use":
                return LabelData.from_llm(block.get("input", {}))
        raise VisionError("Claude tool javobini qaytarmadi")
