from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from asterion_api.dependencies import get_voice_service
from asterion_api.services.voice_service import VoiceService

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.get("/status")
async def voice_status(
    voice: VoiceService = Depends(get_voice_service),
) -> dict[str, object]:
    return voice.status()


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    mode: str = Form("note"),
    language: str | None = Form(None),
    diarize: bool = Form(False),
    voice: VoiceService = Depends(get_voice_service),
) -> dict[str, object]:
    filename = file.filename or "audio"
    suffix = Path(filename).suffix.lower()
    if suffix not in voice.supported_formats:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported audio format: {suffix or 'unknown'}",
        )

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            tmp_path = Path(temp_file.name)
            temp_file.write(await file.read())

        transcript = await voice.transcribe(tmp_path, language=language, diarize=diarize)
        if mode == "meeting":
            transcript["meeting"] = voice.analyze_meeting(transcript)
        return transcript
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await file.close()
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


@router.post("/meeting")
async def analyze_meeting(
    transcript: dict[str, object],
    voice: VoiceService = Depends(get_voice_service),
) -> dict[str, object]:
    return voice.analyze_meeting(transcript)


@router.post("/transcribe/text")
async def structure_voice_text(
    text: str = Form(...),
    mode: str = Form("notes"),
    voice: VoiceService = Depends(get_voice_service),
) -> dict[str, object]:
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text is required")
    return voice.structure_text(text, mode=mode)
