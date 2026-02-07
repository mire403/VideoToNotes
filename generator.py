from __future__ import annotations

from typing import Optional

from videotonotes.utils import NotesDocument, format_timestamp


def _timestamp_link(source_url: Optional[str], seconds: float) -> str:
    ts = format_timestamp(seconds)
    if not source_url:
        return ts
    # YouTube supports ?t=SECONDS
    return f"[{ts}]({source_url}&t={int(seconds)})" if "?" in source_url else f"[{ts}]({source_url}?t={int(seconds)})"


def generate_markdown_notes(doc: NotesDocument) -> str:
    lines: list[str] = []
    lines.append(f"# {doc.title}")
    lines.append("")
    lines.append(f"- Source: `{doc.source}`")
    lines.append(f"- Generated with LLM: `{doc.meta.get('llm')}`")
    lines.append("")

    lines.append("## Key Takeaways")
    lines.append("")
    for t in doc.key_takeaways:
        lines.append(f"- {t}")
    if not doc.key_takeaways:
        lines.append("- (No takeaways produced)")
    lines.append("")

    lines.append("## Notes")
    lines.append("")

    source_url = doc.source if doc.source.startswith("http") else None
    for i, sec in enumerate(doc.sections, start=1):
        start = _timestamp_link(source_url, sec.start_time)
        end = format_timestamp(sec.end_time)
        lines.append(f"### {i}. {sec.title}")
        lines.append("")
        lines.append(f"- Time: {start} - {end}")
        lines.append("")
        for b in sec.bullets:
            lines.append(f"- {b}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"

