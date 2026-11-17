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
from collections import Counter
from typing import Any, Dict, List

import httpx

from app.providers.base import VisionError, VisionProvider
from app.imaging import variants
from app.providers.prompt import (
    READ_PROMPT, RECONCILE_USER, STRUCTURE_SYSTEM, STRUCTURE_USER,
)
from app.schema import FIELDS, LabelData, llm_schema


class OllamaProvider(VisionProvider):
    name = "ollama"

    def __init__(self) -> None:
        self.host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
        self._model = os.getenv("OLLAMA_MODEL", "qwen2.5vl:7b")
        self.timeout = float(os.getenv("OLLAMA_TIMEOUT", "180"))
        # Qo'lyozma aniqlansa shu burchaklarda qayta o'qiladi.
        # Bosma matnda qo'shimcha o'qish qilinmaydi — tez qoladi.
        raw = os.getenv("DESKEW_ANGLES", "35,-35").strip()
        self.deskew = [int(a) for a in raw.split(",") if a.strip()] if raw else []

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

    async def _structure(self, text=None, user=None) -> LabelData:
        """2-bosqich: o'qilgan matnni sxemaga solish (rasmsiz)."""
        user = user or STRUCTURE_USER.format(text=text)
        content = await self._chat({
            "model": self._model,
            "stream": False,
            "format": llm_schema(),
            "options": {"temperature": 0},
            "messages": [
                {"role": "system", "content": STRUCTURE_SYSTEM},
                {"role": "user", "content": user},
            ],
        }, "tartiblash")

        try:
            return LabelData.from_llm(json.loads(content))
        except (json.JSONDecodeError, ValueError) as e:
            raise VisionError(f"[tartiblash] Javobni sxemaga moslab bo'lmadi: {e}") from e

    async def extract(self, image_bytes: bytes, mime_type: str) -> LabelData:
        text, handwritten = self._split_marker(
            await self._read_text(base64.b64encode(image_bytes).decode())
        )

        # Bosma matn: bitta o'qish yetarli.
        if not (handwritten and self.deskew):
            data = await self._structure(text)
            if handwritten:
                data.uncertain_fields = [f for f in FIELDS if getattr(data, f)]
            return data

        # Qo'lyozma: qiyshiq yozuv yomon o'qiladi. To'g'ri burchak noma'lum,
        # shuning uchun bir nechta burchakda o'qib, HAR BIRINI alohida
        # tartiblaymiz va natijalarni KODDA ovoz berish bilan birlashtiramiz.
        #
        # Avval birlashtirishni modeldan so'radim — bo'sh javob qaytardi.
        # Determinizm kerak bo'lgan joyda modelga tayanmaslik kerak.
        results = [await self._structure(text)]
        for _, data_bytes in variants(image_bytes, self.deskew):
            raw = await self._read_text(base64.b64encode(data_bytes).decode())
            body, _ = self._split_marker(raw)
            if body.strip():
                results.append(await self._structure(body))
        return self._vote(results)

    @staticmethod
    def _vote(results: List[LabelData]) -> LabelData:
        """Bir nechta o'qish natijasini maydon bo'yicha ovoz berish bilan birlashtiradi.

        Hamma variant bir xil desa — ishonchli. Farq qilsa — eng ko'p
        uchragani olinadi va maydon operator uchun belgilanadi.
        """
        merged: Dict[str, Any] = {}
        uncertain: List[str] = []
        for field in FIELDS:
            values = [v for r in results if (v := getattr(r, field))]
            if not values:
                continue
            counts = Counter(values)
            top = max(counts.values())
            # Ovoz teng bo'lsa — eng to'liq (uzun) o'qishni tanlaymiz:
            # qisqasi odatda yarim o'qilgan variant bo'ladi.
            best = max((v for v, c in counts.items() if c == top), key=len)
            hits = top
            merged[field] = best
            # Hamma o'qishda bir xil chiqmagan bo'lsa — tekshirilsin
            if hits < len(results):
                uncertain.append(field)
        merged["uncertain_fields"] = uncertain
        return LabelData.model_validate(merged)

    @staticmethod
    def _split_marker(text: str) -> tuple:
        """Matndan qo'lyozma belgisini ajratib oladi."""
        handwritten, kept = False, []
        for ln in text.splitlines():
            flat = ln.strip().upper().replace("'", "").replace("\u2019", "")
            if flat in {"QOLYOZMA", "YOZUV: QOLYOZMA", "YOZUV: BOSMA"}:
                handwritten = "QOLYOZMA" in flat
                continue
            kept.append(ln)
        return "\n".join(kept).strip(), handwritten
