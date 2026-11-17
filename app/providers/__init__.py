"""Provayder registri — Spring'dagi List-injection naqshining Python varianti."""
import os
from typing import Dict, Type

from app.providers.base import VisionError, VisionProvider
from app.providers.claude import ClaudeProvider
from app.providers.ollama import OllamaProvider

# Yangi provayder qo'shish: shu lug'atga bitta qator
REGISTRY: Dict[str, Type[VisionProvider]] = {
    OllamaProvider.name: OllamaProvider,
    ClaudeProvider.name: ClaudeProvider,
}


def get_provider() -> VisionProvider:
    key = os.getenv("VISION_PROVIDER", "ollama").strip().lower()
    if key not in REGISTRY:
        raise VisionError(
            f"Noma'lum provayder '{key}'. Mavjudlari: {', '.join(REGISTRY)}"
        )
    return REGISTRY[key]()


__all__ = ["VisionProvider", "VisionError", "get_provider", "REGISTRY"]
