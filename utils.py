from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


def is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")


def ensure_ffmpeg_available() -> None:
    try:
        subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True, text=True)
    except Exception as e:
        raise RuntimeError(
            "ffmpeg is required but not found on PATH. Install ffmpeg and retry."
        ) from e


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def format_timestamp(seconds: float) -> str:
    s = int(max(0, seconds))
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{sec:02d}"
    return f"{m:02d}:{sec:02d}"


def sanitize_filename(name: str) -> str:
    name = re.sub(r"[\\/:*?\"<>|]+", "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:180] if len(name) > 180 else name


def env_has_openai_key() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


@dataclass
class TranscriptChunk:
    start: float
    end: float
    text: str


@dataclass
class TopicSegment:
    start_time: float
    end_time: float
    text: str


@dataclass
class LoadedSource:
    source: str
    source_url: Optional[str]
    title: Optional[str]
    transcript: list[TranscriptChunk]


@dataclass
class NotesSection:
    title: str
    start_time: float
    end_time: float
    bullets: list[str]


@dataclass
class NotesDocument:
    title: str
    source: str
    sections: list[NotesSection]
    key_takeaways: list[str]
    meta: dict


def iter_nonempty(lines: Iterable[str]) -> list[str]:
    out: list[str] = []
    for ln in lines:
        x = ln.strip()
        if x:
            out.append(x)
    return out


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

