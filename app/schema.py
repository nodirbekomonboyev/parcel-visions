"""Yorliqdan ajratib olinadigan ma'lumot sxemasi.

MUHIM: modelga beriladigan sxema API kontraktidan boshqa.

Pydantic `Optional[str]` uchun `anyOf: [string, null]` hosil qiladi, Ollama'ning
grammatik dekodlashi esa buni eplay olmaydi — model maydonlarni chalkashtirib,
hammasini bitta katakka tiqib yuboradi (o'lchab tekshirilgan).

Shuning uchun modelga TEKIS sxema beriladi: har maydon oddiy `string`, topilmasa
bo'sh satr. Bo'sh satr keyin kod darajasida `None` ga aylantiriladi — ya'ni
tashqi API kontrakti o'zgarmaydi.
"""
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

FIELDS: Dict[str, str] = {
    "tracking_number": "Kuzatuv / trek raqami",
    "recipient_name": "Qabul qiluvchining ism-sharifi",
    "recipient_phone": "Qabul qiluvchining telefon raqami",
    "recipient_address": "Qabul qiluvchining to'liq manzili",
    "sender_name": "Jo'natuvchining ism-sharifi",
    "sender_phone": "Jo'natuvchining telefon raqami",
    "sender_address": "Jo'natuvchining to'liq manzili",
    "weight": "Og'irlik, masalan '2.4 kg'",
    "service_type": "Xizmat turi, masalan 'EXPRESS'",
}

# Model ba'zan bo'sh satr o'rniga shu so'zlarni yozib yuboradi
EMPTY_VALUES = {"", "null", "none", "n/a", "na", "-", "\u2014", "yo'q", "topilmadi", "unknown"}

FieldName = Literal[
    "tracking_number", "recipient_name", "recipient_phone", "recipient_address",
    "sender_name", "sender_phone", "sender_address", "weight", "service_type",
]


def llm_schema() -> Dict[str, Any]:
    """Modelga beriladigan tekis sxema — anyOf yo'q, hamma maydon majburiy."""
    props: Dict[str, Any] = {
        key: {"type": "string", "description": f"{desc}. Topilmasa bo'sh satr qoldir."}
        for key, desc in FIELDS.items()
    }
    props["uncertain_fields"] = {
        "type": "array",
        "items": {"type": "string", "enum": list(FIELDS)},
        "description": "Ishonch past bo'lgan MAYDON NOMLARI. Qiymat emas, faqat nom.",
    }
    return {"type": "object", "properties": props, "required": list(props)}


class LabelData(BaseModel):
    """API kontrakti: topilmagan maydon `null` bo'ladi."""

    tracking_number: Optional[str] = Field(None, description=FIELDS["tracking_number"])
    recipient_name: Optional[str] = Field(None, description=FIELDS["recipient_name"])
    recipient_phone: Optional[str] = Field(None, description=FIELDS["recipient_phone"])
    recipient_address: Optional[str] = Field(None, description=FIELDS["recipient_address"])
    sender_name: Optional[str] = Field(None, description=FIELDS["sender_name"])
    sender_phone: Optional[str] = Field(None, description=FIELDS["sender_phone"])
    sender_address: Optional[str] = Field(None, description=FIELDS["sender_address"])
    weight: Optional[str] = Field(None, description=FIELDS["weight"])
    service_type: Optional[str] = Field(None, description=FIELDS["service_type"])

    uncertain_fields: List[FieldName] = Field(default_factory=list)

    @classmethod
    def from_llm(cls, raw: Dict[str, Any]) -> "LabelData":
        """Model javobini kontraktga keltiradi: bo'sh va soxta qiymatlar -> None."""
        clean: Dict[str, Any] = {}
        for key in FIELDS:
            value = raw.get(key)
            value = value.strip() if isinstance(value, str) else None
            if value and value.lower() in EMPTY_VALUES:
                value = None
            clean[key] = value or None
        # Bo'sh maydonni "ishonchsiz" deb belgilashning ma'nosi yo'q —
        # operator tekshiradigan narsa yo'q. Faqat to'ldirilganlari qoladi.
        clean["uncertain_fields"] = [
            f for f in (raw.get("uncertain_fields") or [])
            if f in FIELDS and clean.get(f)
        ]
        return cls.model_validate(clean)

    def filled_count(self) -> int:
        return sum(1 for k in FIELDS if getattr(self, k))


class ExtractionResult(BaseModel):
    id: Optional[int] = None
    provider: str
    model: str
    filename: str
    took_ms: int
    data: LabelData
    created_at: Optional[str] = None
