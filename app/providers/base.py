"""Vision provayderlar uchun umumiy interfeys (SPI).

Yangi provayder qo'shish = shu klassdan meros olish + registrga yozish.
Qolgan kod o'zgarmaydi.
"""
from abc import ABC, abstractmethod

from app.schema import LabelData


class VisionError(Exception):
    """Provayder ishlamaganda tashlanadi — jimgina bo'sh natija qaytarilmaydi."""


class VisionProvider(ABC):
    name: str = "base"

    @property
    @abstractmethod
    def model(self) -> str:
        """Ishlatilayotgan model nomi (hisobot va loglar uchun)."""

    @abstractmethod
    async def extract(self, image_bytes: bytes, mime_type: str) -> LabelData:
        """Suratdan yorliq ma'lumotlarini ajratib oladi.

        Xatolikda VisionError tashlaydi — bo'sh LabelData qaytarmaydi,
        aks holda noto'g'ri ma'lumot jimgina hisobotga tushib ketadi.
        """

    @abstractmethod
    async def health(self) -> bool:
        """Provayder hozir ishlashga tayyormi."""
