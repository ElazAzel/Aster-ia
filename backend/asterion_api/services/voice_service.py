from __future__ import annotations

import asyncio
import importlib.util
import re
from pathlib import Path
from typing import Any, Mapping

from asterion_api.harness import BaseHarness
from asterion_api.structured_logging import StructuredLogger


class VoiceService(BaseHarness):
    """Local-first voice transcription and note structuring service."""

    privacy_level = "local"
    supported_formats = {".mp3", ".wav", ".m4a", ".webm", ".ogg", ".flac"}

    def __init__(
        self,
        *,
        model_name: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self._state: dict[str, Any] = {
            "model_name": model_name,
            "device": device,
            "compute_type": compute_type,
        }
        self.logger = StructuredLogger("voice", self.privacy_level)

    async def execute(self, payload: Mapping[str, Any] | None = None) -> Any:
        payload = payload or {}
        action = str(payload.get("action") or "status")
        if action == "status":
            return self.status()
        if action == "transcribe":
            file_path = payload.get("file_path")
            if not file_path:
                raise ValueError("file_path is required for voice transcription")
            return await self.transcribe(Path(str(file_path)), language=payload.get("language"))
        if action == "meeting":
            transcript = payload.get("transcript")
            if transcript is None:
                raise ValueError("transcript is required for meeting analysis")
            return self.analyze_meeting(transcript)
        if action == "structure":
            text = str(payload.get("text") or "")
            return self.structure_text(text, mode=str(payload.get("mode") or "notes"))
        raise ValueError(f"Unsupported voice harness action: {action}")

    def get_state(self) -> dict[str, Any]:
        return dict(self._state)

    def set_state(self, state: Mapping[str, Any]) -> None:
        self._state.update(dict(state))
        self.model_name = str(self._state.get("model_name") or self.model_name)
        self.device = str(self._state.get("device") or self.device)
        self.compute_type = str(self._state.get("compute_type") or self.compute_type)

    def status(self) -> dict[str, Any]:
        available = self._check_availability()
        return {
            "ok": True,
            "privacy_level": self.privacy_level,
            "engine": "faster-whisper" if available else "fallback",
            "whisper_available": available,
            "model_name": self.model_name,
            "device": self.device,
            "supported_formats": sorted(self.supported_formats),
            "note": (
                "Transcription runs locally when faster-whisper is installed. "
                "Fallback mode keeps files local and returns a setup hint."
            ),
        }

    async def transcribe(
        self,
        audio_path: Path,
        *,
        language: str | None = None,
        diarize: bool = False,
    ) -> dict[str, Any]:
        suffix = audio_path.suffix.lower()
        if suffix not in self.supported_formats:
            raise ValueError(f"Unsupported audio format: {suffix or 'unknown'}")

        if not self._check_availability():
            return self._fallback_transcription(audio_path)

        def run_transcription() -> tuple[list[dict[str, Any]], float | None, str | None]:
            model = self._load_model()
            segments, info = model.transcribe(
                str(audio_path),
                language=language,
                vad_filter=True,
                beam_size=1,
            )
            rows = [
                {
                    "start": float(segment.start),
                    "end": float(segment.end),
                    "text": str(segment.text).strip(),
                }
                for segment in segments
            ]
            duration = getattr(info, "duration", None)
            detected_language = getattr(info, "language", None)
            return rows, duration, detected_language

        segments, duration, detected_language = await asyncio.to_thread(run_transcription)
        text = " ".join(segment["text"] for segment in segments if segment["text"]).strip()
        payload = {
            "text": text,
            "segments": segments,
            "language": detected_language or language,
            "duration": duration,
            "diarization": "not_available" if diarize else "disabled",
            "privacy_level": self.privacy_level,
            "engine": "faster-whisper",
        }
        self.logger.emit("voice.transcribed", chars=len(text), segments=len(segments))
        return payload

    def analyze_meeting(self, transcript: Mapping[str, Any] | str) -> dict[str, Any]:
        text = self._coerce_text(transcript)
        payload = {
            "summary": self._extract_summary(text),
            "action_items": self._extract_action_items(text),
            "decisions": self._extract_decisions(text),
            "questions": self._extract_questions(text),
            "privacy_level": self.privacy_level,
        }
        self.logger.emit("voice.meeting_structured", chars=len(text))
        return payload

    def structure_text(self, text: str, *, mode: str = "notes") -> dict[str, Any]:
        text = text.strip()
        payload = {
            "mode": mode,
            "summary": self._extract_summary(text),
            "action_items": self._extract_action_items(text),
            "decisions": self._extract_decisions(text),
            "questions": self._extract_questions(text),
            "markdown": self._to_markdown(text, mode=mode),
            "privacy_level": self.privacy_level,
        }
        self.logger.emit("voice.text_structured", chars=len(text), mode=mode)
        return payload

    def _check_availability(self) -> bool:
        cached = self._state.get("whisper_available")
        if isinstance(cached, bool):
            return cached
        available = importlib.util.find_spec("faster_whisper") is not None
        self._state["whisper_available"] = available
        return available

    def _load_model(self) -> Any:
        from faster_whisper import WhisperModel

        return WhisperModel(self.model_name, device=self.device, compute_type=self.compute_type)

    def _fallback_transcription(self, audio_path: Path) -> dict[str, Any]:
        message = (
            "Local transcription engine is not installed. "
            "Install with: uv sync --extra voice, then restart the backend."
        )
        self.logger.emit("voice.fallback", file=audio_path.name)
        return {
            "text": "",
            "segments": [],
            "language": None,
            "duration": None,
            "diarization": "not_available",
            "privacy_level": self.privacy_level,
            "engine": "fallback",
            "error": message,
        }

    @staticmethod
    def _coerce_text(transcript: Mapping[str, Any] | str) -> str:
        if isinstance(transcript, str):
            return transcript
        text = transcript.get("text")
        if isinstance(text, str):
            return text
        segments = transcript.get("segments")
        if isinstance(segments, list):
            return " ".join(
                str(segment.get("text", "")).strip()
                for segment in segments
                if isinstance(segment, Mapping)
            ).strip()
        return ""

    @staticmethod
    def _sentences(text: str) -> list[str]:
        return [
            part.strip()
            for part in re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
            if part.strip()
        ]

    def _extract_summary(self, text: str, max_sentences: int = 3) -> list[str]:
        sentences = self._sentences(text)
        if not sentences:
            return []
        meaningful = [sentence for sentence in sentences if len(sentence) > 20]
        return (meaningful or sentences)[:max_sentences]

    def _extract_action_items(self, text: str) -> list[str]:
        keywords = (
            "todo",
            "action",
            "follow up",
            "deadline",
            "task",
            "нужно",
            "надо",
            "сделать",
            "задача",
            "дедлайн",
        )
        return [
            sentence
            for sentence in self._sentences(text)
            if any(keyword in sentence.lower() for keyword in keywords)
        ]

    def _extract_decisions(self, text: str) -> list[str]:
        keywords = ("decided", "decision", "agreed", "решили", "решение", "согласовали")
        return [
            sentence
            for sentence in self._sentences(text)
            if any(keyword in sentence.lower() for keyword in keywords)
        ]

    def _extract_questions(self, text: str) -> list[str]:
        return [sentence for sentence in self._sentences(text) if sentence.endswith("?")]

    def _to_markdown(self, text: str, *, mode: str) -> str:
        summary = self._extract_summary(text)
        actions = self._extract_action_items(text)
        decisions = self._extract_decisions(text)
        questions = self._extract_questions(text)
        lines = [f"# Voice {mode.title()}"]
        if summary:
            lines.extend(["", "## Summary", *[f"- {item}" for item in summary]])
        if decisions:
            lines.extend(["", "## Decisions", *[f"- {item}" for item in decisions]])
        if actions:
            lines.extend(["", "## Action Items", *[f"- {item}" for item in actions]])
        if questions:
            lines.extend(["", "## Questions", *[f"- {item}" for item in questions]])
        if text:
            lines.extend(["", "## Transcript", text])
        return "\n".join(lines)
