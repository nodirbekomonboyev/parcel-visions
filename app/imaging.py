"""Surat tayyorlash: qiyshiq matnni to'g'rilash uchun variantlar yasaydi.

NEGA KERAK
----------
Qo'lda yozilgan qog'oz suratga qiyshiq tushadi. O'lchab ko'rilgan:
qog'oz ~40 daraja burilgan bo'lsa, model ko'cha nomini `shato` deb,
uy raqamini `412` deb o'qiydi; to'g'rilangandan keyin `Shota` va `112`.

To'g'ri burchakni oldindan bilib bo'lmaydi, shuning uchun bir nechta
burchakda o'qiladi va natijalar solishtiriladi: mos kelgan qiymat
ishonchli, farq qilgani operatorga belgilanadi.
"""
import io
from typing import List, Tuple

from PIL import Image

MAX_SIDE = 1600  # kattaroq surat Ollama so'rovini sindiradi


def variants(image_bytes: bytes, angles: List[int]) -> List[Tuple[int, bytes]]:
    """Har burchak uchun bitta JPEG variant qaytaradi."""
    out: List[Tuple[int, bytes]] = []
    with Image.open(io.BytesIO(image_bytes)) as src:
        base = src.convert("RGB")
        if max(base.size) > MAX_SIDE:
            base.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
        for angle in angles:
            img = base if angle % 360 == 0 else base.rotate(
                -angle, expand=True, fillcolor=(255, 255, 255), resample=Image.BICUBIC
            )
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=92)
            out.append((angle, buf.getvalue()))
    return out
