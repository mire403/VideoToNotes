from __future__ import annotations

from pathlib import Path

from faster_whisper import WhisperModel

from videotonotes.utils import TranscriptChunk


def transcribe_audio(
    wav_path: Path,
    model_size: str = "small",
    lang: str = "auto",
) -> list[TranscriptChunk]:
    """
    Transcribe audio to timestamped chunks.
    Output is readable, not perfect — optimized for note generation.
    """
    if not wav_path.exists():
        raise FileNotFoundError(f"Audio not found: {wav_path}")

    # Prefer CPU-friendly defaults; users can set CUDA via env/ct2 if desired.
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    language = None if (not lang or lang == "auto") else lang

    segments, _info = model.transcribe(
        str(wav_path),
        language=language,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
        beam_size=5,
    )

    out: list[TranscriptChunk] = []
    for seg in segments:
        text = (seg.text or "").strip()
        if not text:
            continue
        out.append(TranscriptChunk(start=float(seg.start), end=float(seg.end), text=text))
    return out

