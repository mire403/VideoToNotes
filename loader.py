from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Optional

import webvtt

from videotonotes.transcriber import transcribe_audio
from videotonotes.utils import (
    LoadedSource,
    TranscriptChunk,
    ensure_ffmpeg_available,
    is_url,
    run_cmd,
    sanitize_filename,
)


def _parse_vtt_to_chunks(vtt_path: Path) -> list[TranscriptChunk]:
    chunks: list[TranscriptChunk] = []
    vtt = webvtt.read(str(vtt_path))
    for caption in vtt:
        text = " ".join([x.strip() for x in caption.text.splitlines() if x.strip()])
        if not text:
            continue
        chunks.append(
            TranscriptChunk(
                start=_ts_to_seconds(caption.start),
                end=_ts_to_seconds(caption.end),
                text=text,
            )
        )
    return chunks


def _ts_to_seconds(ts: str) -> float:
    # VTT: HH:MM:SS.mmm or MM:SS.mmm
    parts = ts.replace(",", ".").split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    m, s = parts
    return int(m) * 60 + float(s)


def _extract_audio_to_wav(video_path: Path, wav_path: Path) -> None:
    ensure_ffmpeg_available()
    # mono 16k wav for whisper
    run_cmd(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "wav",
            str(wav_path),
        ]
    )


def _yt_dlp_fetch_subtitles(url: str, lang: str, workdir: Path) -> tuple[Optional[str], Optional[Path]]:
    """
    Returns (title, vtt_path) if subtitles exist (manual/auto). Otherwise (title, None).
    """
    # 1) Get metadata (title) + available subs (optional)
    info_json = workdir / "info.json"
    run_cmd(["yt-dlp", "--skip-download", "--write-info-json", "-o", "info.%(ext)s", url])
    if info_json.exists():
        info = json.loads(info_json.read_text(encoding="utf-8"))
        title = info.get("title")
    else:
        title = None

    # 2) Try download subtitles (prefer provided subs, fallback to auto subs)
    # We always request VTT for easy parsing.
    sub_langs = []
    if lang and lang != "auto":
        sub_langs.append(lang)
    # common fallbacks
    sub_langs.extend(["en", "zh-Hans", "zh", "zh-Hant"])
    sub_langs_str = ",".join(dict.fromkeys(sub_langs).keys())  # keep order unique

    # Manual subs
    run_cmd(
        [
            "yt-dlp",
            "--skip-download",
            "--write-subs",
            "--sub-format",
            "vtt",
            "--sub-langs",
            sub_langs_str,
            "-o",
            "sub.%(ext)s",
            url,
        ]
    )
    vtts = sorted(workdir.glob("sub.*.vtt"))
    if vtts:
        return title, vtts[0]

    # Auto subs
    run_cmd(
        [
            "yt-dlp",
            "--skip-download",
            "--write-auto-subs",
            "--sub-format",
            "vtt",
            "--sub-langs",
            sub_langs_str,
            "-o",
            "autosub.%(ext)s",
            url,
        ]
    )
    vtts = sorted(workdir.glob("autosub.*.vtt"))
    if vtts:
        return title, vtts[0]

    return title, None


def load_source(source: str, lang: str = "auto", whisper_model: str = "small") -> LoadedSource:
    """
    Load transcript with timestamps from:
    - YouTube URL: prefer subtitles (manual > auto). If none, fallback to audio + whisper.
    - Local file: extract audio and whisper.
    """
    if is_url(source):
        with tempfile.TemporaryDirectory(prefix="vtn_yt_") as td:
            workdir = Path(td)
            # Ensure yt-dlp runs in workdir (so we can find outputs)
            run_cmd(["yt-dlp", "--version"])  # quick sanity check

            # yt-dlp writes to current directory; run in workdir via cwd not supported by run_cmd, so use subprocess directly here
            import subprocess

            def _run(cmd: list[str]) -> None:
                subprocess.run(cmd, check=True, cwd=str(workdir), capture_output=True, text=True)

            info_json = workdir / "info.json"
            _run(["yt-dlp", "--skip-download", "--write-info-json", "-o", "info.%(ext)s", source])
            title = None
            if info_json.exists():
                info = json.loads(info_json.read_text(encoding="utf-8"))
                title = info.get("title")

            # Subtitles
            # Re-implement using cwd runner
            sub_langs = []
            if lang and lang != "auto":
                sub_langs.append(lang)
            sub_langs.extend(["en", "zh-Hans", "zh", "zh-Hant"])
            sub_langs_str = ",".join(dict.fromkeys(sub_langs).keys())

            _run(
                [
                    "yt-dlp",
                    "--skip-download",
                    "--write-subs",
                    "--sub-format",
                    "vtt",
                    "--sub-langs",
                    sub_langs_str,
                    "-o",
                    "sub.%(ext)s",
                    source,
                ]
            )
            vtts = sorted(workdir.glob("sub.*.vtt"))
            if not vtts:
                _run(
                    [
                        "yt-dlp",
                        "--skip-download",
                        "--write-auto-subs",
                        "--sub-format",
                        "vtt",
                        "--sub-langs",
                        sub_langs_str,
                        "-o",
                        "autosub.%(ext)s",
                        source,
                    ]
                )
                vtts = sorted(workdir.glob("autosub.*.vtt"))

            if vtts:
                transcript = _parse_vtt_to_chunks(vtts[0])
                return LoadedSource(source=source, source_url=source, title=title, transcript=transcript)

            # Fallback: download bestaudio, whisper
            audio_out = workdir / "audio.m4a"
            _run(["yt-dlp", "-f", "bestaudio/best", "-o", str(audio_out), source])
            wav = workdir / "audio.wav"
            _extract_audio_to_wav(audio_out, wav)
            transcript = transcribe_audio(wav, model_size=whisper_model, lang=lang)
            return LoadedSource(source=source, source_url=source, title=title, transcript=transcript)

    # Local video/audio file
    video_path = Path(source).expanduser().resolve()
    if not video_path.exists():
        raise FileNotFoundError(f"File not found: {video_path}")

    with tempfile.TemporaryDirectory(prefix="vtn_local_") as td:
        workdir = Path(td)
        wav = workdir / f"{sanitize_filename(video_path.stem)}.wav"
        _extract_audio_to_wav(video_path, wav)
        transcript = transcribe_audio(wav, model_size=whisper_model, lang=lang)
        return LoadedSource(source=str(video_path), source_url=None, title=video_path.stem, transcript=transcript)

