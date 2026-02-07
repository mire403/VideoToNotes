from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from videotonotes.utils import TopicSegment, TranscriptChunk


def _join_text(chunks: list[TranscriptChunk]) -> str:
    return " ".join([c.text.strip() for c in chunks if c.text and c.text.strip()]).strip()


def segment_transcript(
    transcript: list[TranscriptChunk],
    min_segment_seconds: int = 90,
    max_segment_seconds: int = 360,
    similarity_threshold: float = 0.35,
) -> list[TopicSegment]:
    """
    Segment transcript by time + light-weight semantic shift detection.

    Strategy:
    - Start accumulating chunks
    - Close a segment when:
      - duration >= max_segment_seconds, OR
      - duration >= min_segment_seconds AND semantic similarity with previous segment drops
    """
    if not transcript:
        return []

    # Ensure chronological order
    transcript = sorted(transcript, key=lambda c: (c.start, c.end))

    segments_chunks: list[list[TranscriptChunk]] = []
    current: list[TranscriptChunk] = []

    def _current_duration() -> float:
        if not current:
            return 0.0
        return float(current[-1].end - current[0].start)

    for ch in transcript:
        if not current:
            current = [ch]
            continue

        current.append(ch)
        dur = _current_duration()
        if dur >= max_segment_seconds:
            segments_chunks.append(current)
            current = []
            continue

        if dur < min_segment_seconds or not segments_chunks:
            continue

        # Semantic shift check against last finalized segment
        prev_text = _join_text(segments_chunks[-1])
        cur_text = _join_text(current)
        if not prev_text or not cur_text:
            continue

        sim = _tfidf_similarity(prev_text, cur_text)
        if sim < similarity_threshold:
            segments_chunks.append(current)
            current = []

    if current:
        segments_chunks.append(current)

    out: list[TopicSegment] = []
    for seg_chunks in segments_chunks:
        text = _join_text(seg_chunks)
        if not text:
            continue
        out.append(
            TopicSegment(
                start_time=float(seg_chunks[0].start),
                end_time=float(seg_chunks[-1].end),
                text=text,
            )
        )
    return out


def _tfidf_similarity(a: str, b: str) -> float:
    vec = TfidfVectorizer(stop_words="english")
    X = vec.fit_transform([a, b])
    sim = cosine_similarity(X[0], X[1])[0][0]
    if np.isnan(sim):
        return 1.0
    return float(sim)

