"""Translation endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class TranslateRequest(BaseModel):
    """Translation request body."""

    text: str
    source_lang: str = "auto"
    target_lang: str


class TranslateResponse(BaseModel):
    """Translation response."""

    translated_text: str
    source_lang: str
    target_lang: str
    latency_ms: float


class BatchTranslateRequest(BaseModel):
    """Batch translation request."""

    texts: list[str]
    source_lang: str = "auto"
    target_lang: str


class BatchTranslateResponse(BaseModel):
    """Batch translation response."""

    translations: list[TranslateResponse]
    total_latency_ms: float


@router.post("", response_model=TranslateResponse)
async def translate(request: TranslateRequest) -> TranslateResponse:
    """Translate text.

    TODO: Integrate with Service.ML for actual translation.
    """
    raise HTTPException(
        status_code=501,
        detail="Translation service not yet implemented. Will integrate with Service.ML.",
    )


@router.post("/batch", response_model=BatchTranslateResponse)
async def translate_batch(request: BatchTranslateRequest) -> BatchTranslateResponse:
    """Translate multiple texts in a batch.

    TODO: Implement batch translation with Service.ML.
    """
    raise HTTPException(
        status_code=501,
        detail="Batch translation not yet implemented.",
    )


@router.get("/languages")
async def list_languages() -> dict[str, list[dict[str, str]]]:
    """List supported languages.

    Returns a list of language codes and names supported by the translation service.
    """
    # MADLAD-400 supports 400+ languages, listing common ones
    languages = [
        {"code": "en", "name": "English"},
        {"code": "zh", "name": "Chinese"},
        {"code": "ja", "name": "Japanese"},
        {"code": "ko", "name": "Korean"},
        {"code": "es", "name": "Spanish"},
        {"code": "fr", "name": "French"},
        {"code": "de", "name": "German"},
        {"code": "ru", "name": "Russian"},
        {"code": "pt", "name": "Portuguese"},
        {"code": "it", "name": "Italian"},
        {"code": "ar", "name": "Arabic"},
        {"code": "hi", "name": "Hindi"},
        {"code": "th", "name": "Thai"},
        {"code": "vi", "name": "Vietnamese"},
    ]
    return {"languages": languages}
