from __future__ import annotations


SYSTEM_PROMPT = """You are a senior learning-notes assistant.
Your job is to help a student truly understand and review the video.

Rules:
- Only use the provided transcript segment content; do NOT invent facts.
- Do NOT do word-for-word restatement; summarize and structure for learning.
- Prefer concepts, conclusions, definitions, and causal/step-by-step logic.
- Output must be concise and review-friendly.
"""


SEGMENT_NOTES_PROMPT = """You will be given a transcript segment with a time range.
Create learning notes for THIS segment.

Return JSON with:
- section_title: short, specific (<= 10 words)
- bullets: 3-8 bullets. Each bullet must be a learnable point:
  - concept/definition
  - key claim or conclusion
  - important steps/logic
  - common pitfall / clarification (only if present)

Constraints:
- Do NOT add information not in the transcript.
- No filler, no generic advice.
- Bullets should be crisp and concrete.

Time range: {start_ts} - {end_ts}
Transcript:
{text}
"""


GLOBAL_TAKEAWAYS_PROMPT = """Given the full set of section notes for a video,
produce 3-5 key takeaways that a student can review before an exam.

Return JSON with:
- key_takeaways: array of 3-5 strings

Constraints:
- Only use information from the notes.
- Make them high-signal (conclusions, frameworks, core definitions).

Notes:
{notes}
"""

