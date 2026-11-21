"""Experimental, offline, one-turn ASR -> text MT -> TTS adapters.

No speaker identification, streaming, live meeting, voice cloning, or audio upload.
Install optional deps and models explicitly; check external model/voice licenses.
"""
from __future__ import annotations

import io
import time
import wave
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

MAX_AUDIO_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True)
class TurnResult:
    original_text: str
    translated_text: str
    wav_bytes: bytes
    asr_ms: float
    mt_ms: float
    tts_ms: float


@lru_cache(maxsize=2)
def _load_whisper(size: str):
    from faster_whisper import WhisperModel
    # Offline inference: cache the downloaded model beforehand (see docs).
    return WhisperModel(size, device="cpu", compute_type="int8", local_files_only=True)


class WhisperASR:
    def __init__(self, model_size: str = "small"):
        self.model_size = model_size

    def transcribe(self, audio: bytes, language: str) -> str:
        segments, _ = _load_whisper(self.model_size).transcribe(
            io.BytesIO(audio), language=language, beam_size=3, vad_filter=True,
            condition_on_previous_text=False,
        )
        # Actual ASR work happens during iteration.
        return " ".join(seg.text.strip() for seg in segments if seg.text.strip()).strip()


class ArgosMT:
    def translate(self, text: str, src: str, tgt: str) -> str:
        from benchmark_bidirectional import ArgosBackend
        engine = ArgosBackend().get_translator(src, tgt)
        return engine.translate(text)


@lru_cache(maxsize=4)
def _load_piper(voice_file: str):
    from piper import PiperVoice
    return PiperVoice.load(voice_file)


class PiperTTS:
    def __init__(self, model: Path):
        self.model = Path(model)
        if not self.model.is_file() or not self.model.with_suffix(".onnx.json").is_file():
            raise FileNotFoundError("Piper requires .onnx and matching .onnx.json voice files")

    def synthesize(self, text: str, language: str) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav:
            _load_piper(str(self.model.resolve())).synthesize_wav(text, wav)
        return buf.getvalue()


def process_turn(audio: bytes, src: str, tgt: str, asr, mt, tts) -> TurnResult:
    """Dependency-injected pipeline for deterministic unit tests."""
    if src == tgt or src not in {"pt", "en"} or tgt not in {"pt", "en"}:
        raise ValueError("Voice pilot currently supports only pt<->en")
    if not audio or len(audio) > MAX_AUDIO_BYTES:
        raise ValueError(f"Audio must contain 1..{MAX_AUDIO_BYTES} bytes")
    t0 = time.perf_counter()
    text = asr.transcribe(audio, src)
    asr_ms = (time.perf_counter() - t0) * 1000
    if not isinstance(text, str) or not text.strip():
        raise ValueError("NO_SPEECH_DETECTED")
    t0 = time.perf_counter()
    translated = mt.translate(text, src, tgt)
    mt_ms = (time.perf_counter() - t0) * 1000
    if not isinstance(translated, str) or not translated.strip():
        raise ValueError("EMPTY_TRANSLATION")
    t0 = time.perf_counter()
    wav_bytes = tts.synthesize(translated, tgt)
    tts_ms = (time.perf_counter() - t0) * 1000
    if not isinstance(wav_bytes, bytes) or not wav_bytes.startswith(b"RIFF"):
        raise ValueError("INVALID_TTS_WAV")
    return TurnResult(text, translated, wav_bytes,
                      round(asr_ms, 3), round(mt_ms, 3), round(tts_ms, 3))
