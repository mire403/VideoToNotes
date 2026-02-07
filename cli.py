import argparse
from pathlib import Path

from videotonotes.generator import generate_markdown_notes
from videotonotes.loader import load_source
from videotonotes.segmenter import segment_transcript
from videotonotes.summarizer import summarize_segments
from videotonotes.utils import is_url


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="videotonotes",
        description="Turn a video into structured study notes (Markdown).",
    )
    p.add_argument("source", help="YouTube URL or local video file path.")
    p.add_argument("--out", required=True, help="Output markdown file path.")
    p.add_argument("--title", default=None, help="Optional title override.")
    p.add_argument("--lang", default="auto", help="Language hint: auto/en/zh/ja/...")
    p.add_argument(
        "--model",
        default="small",
        help="faster-whisper model size: tiny/base/small/medium/large-v3...",
    )
    p.add_argument(
        "--max-seg-min",
        type=float,
        default=6.0,
        help="Max topic segment length in minutes.",
    )
    p.add_argument(
        "--min-seg-min",
        type=float,
        default=1.5,
        help="Min topic segment length in minutes.",
    )
    p.add_argument(
        "--llm",
        default="auto",
        choices=["auto", "on", "off"],
        help="Use LLM for note generation: auto (if OPENAI_API_KEY), on, off.",
    )
    return p


def main():
    args = build_arg_parser().parse_args()

    source = args.source.strip()
    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    loaded = load_source(
        source=source,
        lang=args.lang,
        whisper_model=args.model,
    )

    segments = segment_transcript(
        transcript=loaded.transcript,
        min_segment_seconds=int(args.min_seg_min * 60),
        max_segment_seconds=int(args.max_seg_min * 60),
    )

    notes = summarize_segments(
        title=args.title or loaded.title or ("YouTube Video" if is_url(source) else Path(source).stem),
        segments=segments,
        source_url=loaded.source_url if is_url(source) else None,
        llm_mode=args.llm,
        lang=args.lang,
    )

    md = generate_markdown_notes(notes)
    out_path.write_text(md, encoding="utf-8")

    print(f"Wrote notes to: {out_path}")


if __name__ == "__main__":
    main()

