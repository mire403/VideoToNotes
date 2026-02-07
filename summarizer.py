from __future__ import annotations

import json
import re
from typing import Optional

from openai import OpenAI

from videotonotes.prompts import GLOBAL_TAKEAWAYS_PROMPT, SEGMENT_NOTES_PROMPT, SYSTEM_PROMPT
from videotonotes.utils import (
    NotesDocument,
    NotesSection,
    TopicSegment,
    env_has_openai_key,
    format_timestamp,
    iter_nonempty,
)


def summarize_segments(
    title: str,
    segments: list[TopicSegment],
    source_url: Optional[str],
    llm_mode: str = "auto",
    lang: str = "auto",
) -> NotesDocument:
    use_llm = _should_use_llm(llm_mode)

    sections: list[NotesSection] = []
    for seg in segments:
        if use_llm:
            sec = _llm_section(seg)
        else:
            sec = _heuristic_section(seg)
        sections.append(sec)

    if use_llm:
        key_takeaways = _llm_takeaways(sections)
    else:
        key_takeaways = _heuristic_takeaways(sections)

    return NotesDocument(
        title=title,
        source=source_url or "local_file",
        sections=sections,
        key_takeaways=key_takeaways,
        meta={"llm": use_llm, "lang": lang},
    )


def _should_use_llm(mode: str) -> bool:
    if mode == "on":
        return True
    if mode == "off":
        return False
    return env_has_openai_key()


def _llm_section(seg: TopicSegment) -> NotesSection:
    client = OpenAI()
    start_ts = format_timestamp(seg.start_time)
    end_ts = format_timestamp(seg.end_time)
    prompt = SEGMENT_NOTES_PROMPT.format(start_ts=start_ts, end_ts=end_ts, text=seg.text)

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    content = resp.choices[0].message.content or ""
    data = _extract_json(content) or {}
    section_title = str(data.get("section_title") or f"Section {start_ts}")
    bullets = iter_nonempty(data.get("bullets") or [])
    if not bullets:
        bullets = _heuristic_bullets(seg.text)
    return NotesSection(
        title=section_title,
        start_time=seg.start_time,
        end_time=seg.end_time,
        bullets=bullets,
    )


def _llm_takeaways(sections: list[NotesSection]) -> list[str]:
    client = OpenAI()
    notes = []
    for s in sections:
        notes.append(f"{s.title}\n" + "\n".join([f"- {b}" for b in s.bullets]))
    prompt = GLOBAL_TAKEAWAYS_PROMPT.format(notes="\n\n".join(notes))

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    content = resp.choices[0].message.content or ""
    data = _extract_json(content) or {}
    return iter_nonempty(data.get("key_takeaways") or [])[:5]


def _heuristic_section(seg: TopicSegment) -> NotesSection:
    start_ts = format_timestamp(seg.start_time)
    end_ts = format_timestamp(seg.end_time)
    title = _guess_title(seg.text) or f"Topic ({start_ts}-{end_ts})"
    bullets = _heuristic_bullets(seg.text)
    return NotesSection(title=title, start_time=seg.start_time, end_time=seg.end_time, bullets=bullets)


def _guess_title(text: str) -> str:
    # First strong sentence fragment as title
    t = re.sub(r"\s+", " ", text).strip()
    if not t:
        return ""
    # Prefer patterns: "X is ..." / "Today we'll ..." / "The key idea ..."
    m = re.search(r"(.{10,80}?)([。.!?]|$)", t)
    if not m:
        return t[:60]
    cand = m.group(1).strip()
    return cand[:60]


def _heuristic_bullets(text: str) -> list[str]:
    # Conservative: pick 4-7 high-signal sentences, lightly cleaned.
    sentences = _split_sentences(text)
    sentences = [s.strip() for s in sentences if len(s.strip()) >= 12]
    if not sentences:
        return []

    # Score by presence of "definition/contrast/conclusion" markers
    markers = [
        "is ",
        "means",
        "therefore",
        "so ",
        "in other words",
        "关键",
        "总结",
        "结论",
        "本质",
        "因此",
        "所以",
        "也就是说",
        "注意",
        "区别",
        "原因",
        "步骤",
    ]
    scored = []
    for s in sentences:
        s_low = s.lower()
        score = 0
        for mk in markers:
            score += 2 if mk in s_low else 0
        score += min(6, len(s) // 40)
        scored.append((score, s))
    scored.sort(key=lambda x: x[0], reverse=True)

    top = [s for _sc, s in scored[:7]]
    # De-duplicate (simple)
    dedup = []
    seen = set()
    for s in top:
        key = re.sub(r"\W+", "", s.lower())[:80]
        if key in seen:
            continue
        seen.add(key)
        dedup.append(_clean_bullet(s))
    return dedup[:8]


def _heuristic_takeaways(sections: list[NotesSection]) -> list[str]:
    # Pick the first bullet of the top 3-5 sections (by bullet count)
    ordered = sorted(sections, key=lambda s: len(s.bullets), reverse=True)
    takeaways = []
    for s in ordered:
        if s.bullets:
            takeaways.append(s.bullets[0])
        if len(takeaways) >= 5:
            break
    return takeaways[:5]


def _split_sentences(text: str) -> list[str]:
    # Works for both EN/ZH roughly
    t = re.sub(r"\s+", " ", text).strip()
    if not t:
        return []
    parts = re.split(r"(?<=[。！？.!?])\s+", t)
    return [p.strip() for p in parts if p.strip()]


def _clean_bullet(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    s = s.strip("-•* ").strip()
    return s


def _extract_json(text: str) -> Optional[dict]:
    """
    Robustly extract a JSON object from an LLM response.
    Accepts:
    - pure JSON
    - JSON inside code fences
    """
    t = text.strip()
    if not t:
        return None
    # Code fence
    m = re.search(r"\{[\s\S]*\}", t)
    if not m:
        return None
    blob = m.group(0)
    try:
        return json.loads(blob)
    except Exception:
        return None

