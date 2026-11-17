"""Pochta yorlig'idan ma'lumot ajratib oluvchi xizmat.

Surat -> VLM -> strukturali JSON -> baza.
"""
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

from app import storage                                  # noqa: E402
from app.providers import VisionError, get_provider      # noqa: E402
from app.schema import ExtractionResult                  # noqa: E402

MAX_BYTES = 8 * 1024 * 1024
ALLOWED = {"image/jpeg", "image/png", "image/webp"}
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="Parcel Vision", version="1.0.0")


@app.on_event("startup")
def _startup() -> None:
    storage.init()


@app.get("/api/health")
async def health() -> dict:
    provider = get_provider()
    ok = await provider.health()
    return {
        "status": "ok" if ok else "degraded",
        "provider": provider.name,
        "model": provider.model,
        "provider_ready": ok,
    }


@app.post("/api/extract", response_model=ExtractionResult)
async def extract(file: UploadFile = File(...)) -> ExtractionResult:
    if file.content_type not in ALLOWED:
        raise HTTPException(415, f"Faqat {', '.join(sorted(ALLOWED))} qabul qilinadi")

    image = await file.read()
    if not image:
        raise HTTPException(400, "Fayl bo'sh")
    if len(image) > MAX_BYTES:
        raise HTTPException(413, f"Fayl {MAX_BYTES // 1024 // 1024} MB dan katta")

    provider = get_provider()
    started = time.perf_counter()
    try:
        data = await provider.extract(image, file.content_type)
    except VisionError as e:
        # Jimgina bo'sh natija emas — aniq xato. Noto'g'ri ma'lumot hisobotga tushmasin.
        raise HTTPException(502, str(e)) from e
    took_ms = int((time.perf_counter() - started) * 1000)

    result = ExtractionResult(
        provider=provider.name, model=provider.model,
        filename=file.filename or "yuklangan", took_ms=took_ms, data=data,
    )
    result.id = storage.save(result)
    return result


@app.get("/api/extractions", response_model=list[ExtractionResult])
def extractions(limit: int = 50) -> list[ExtractionResult]:
    return storage.recent(min(max(limit, 1), 200))


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
