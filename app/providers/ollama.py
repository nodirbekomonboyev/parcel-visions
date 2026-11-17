"""Lokal provayder: Ollama + Qwen2.5-VL.

Ma'lumot mashinadan chiqmaydi, API kaliti va to'lov kerak emas.

IKKI BOSQICHLI YONDASHUV
------------------------
  1) ko'rish    — VLM suratdagi matnni erkin o'qiydi (sxema cheklovisiz)
  2) tartiblash — o'sha MATN ustida sxemaga solish (rasm ishtirok etmaydi)

Ikkinchi bosqich rasmsiz bo'lgani uchun tezroq va barqarorroq.
"""
import base64
import json
import os
from typing import Any, Dict

import httpx

from app.providers.base import VisionError, VisionProvider
from app.providers.prompt import READ_PROMPT, STRUCTURE_SYSTEM, STRUCTURE_USER
from app.schema import FIELDS, LabelData, llm_schema


class OllamaProvider(VisionProvider):
    name = "ollama"

    def __init__(self) -> None:
        self.host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
        self._model = os.getenv("OLLAMA_MODEL", "qwen2.5vl:7b")
        self.timeout = float(os.getenv("OLLAMA_TIMEOUT", "180"))

    @property
    def model(self) -> str:
        return self._model

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{self.host}/api/tags")
                r.raise_for_status()
                return self._model in [m.get("name", "") for m in r.json().get("models", [])]
        except Exception:
            return False

    async def _chat(self, payload: Dict[str, Any], stage: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.post(f"{self.host}/api/chat", json=payload)
                r.raise_for_status()
                body = r.json()
        except httpx.TimeoutException as e:
            raise VisionError(f"[{stage}] Ollama {self.timeout:.0f}s ichida javob bermadi") from e
        except httpx.HTTPError as e:
            raise VisionError(f"[{stage}] Ollama bilan aloqa xatosi: {e}") from e

        content = (body.get("message") or {}).get("content", "")
        if not content.strip():
            raise VisionError(f"[{stage}] Ollama bo'sh javob qaytardi")
        return content

    @staticmethod
    def _clean(text: str) -> str:
        """Model qo'shib yuborgan ``` belgilarini olib tashlaydi."""
        lines = [ln for ln in text.splitlines() if not ln.strip().startswith("```")]
        return "\n".join(lines).strip()

    async def _read_text(self, image_b64: str) -> str:
        """1-bosqich: suratdagi matnni erkin o'qish."""
        raw = await self._chat({
            "model": self._model,
            "stream": False,
            "options": {"temperature": 0},
            "messages": [{"role": "user", "content": READ_PROMPT, "images": [image_b64]}],
        }, "o'qish")
        return self._clean(raw)

    async def _structure(self, text: str) -> LabelData:
        """2-bosqich: o'qilgan matnni sxemaga solish (rasmsiz)."""
        content = await self._chat({
            "model": self._model,
            "stream": False,
            "format": llm_schema(),
            "options": {"temperature": 0},
            "messages": [
                {"role": "system", "content": STRUCTURE_SYSTEM},
                {"role": "user", "content": STRUCTURE_USER.format(text=text)},
            ],
        }, "tartiblash")

        try:
            return LabelData.from_llm(json.loads(content))
        except (json.JSONDecodeError, ValueError) as e:
            raise VisionError(f"[tartiblash] Javobni sxemaga moslab bo'lmadi: {e}") from e

    async def extract(self, image_bytes: bytes, mime_type: str) -> LabelData:
        text = await self._read_text(base64.b64encode(image_bytes).decode())

        # Qo'lyozma aniqlanishi -> ishonchsizlik belgisi KODDA qo'yiladi.
        # Avval buni modeldan so'radim: ko'rsatmada aniq yozilgan bo'lsa ham
        # bajarmadi. Kafolat kerak bo'lgan qoidani modelga ishonib bo'lmaydi.
        handwritten = False
        kept = []
        for ln in text.splitlines():
            flat = ln.strip().upper().replace("'", "").replace("\u2019", "")
            if flat in {"QOLYOZMA", "YOZUV: QOLYOZMA", "YOZUV: BOSMA"}:
                handwritten = "QOLYOZMA" in flat
                continue          # belgi qatori 2-bosqichga o'tmaydi
            kept.append(ln)
        text = "\n".join(kept).strip()

        data = await self._structure(text)
        if handwritten:
            data.uncertain_fields = [f for f in FIELDS if getattr(data, f)]
        return data
