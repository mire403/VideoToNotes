<div align="center">

# VideoToNotes（视频直接变学习笔记）📼➡️📝

一句话：**Turn a video into structured study notes.**

</div>

> 你只管看视频，其余交给它：自动提炼结构、重点、结论，并附上时间戳，复习时直接定位回看。⏱️

## 为什么这是学生/自学的“刚需”？🎯

视频学习的真实痛点：

- **信息密度高**：倍速看也难抓住重点
- **手动记笔记慢**：边听边记会打断理解
- **看完难回顾**：没有结构与索引，复习成本爆炸

VideoToNotes 的目标很明确：

- **不是逐字转写**（那只是“文字版视频”）
- **而是学习级笔记**：结构化章节 + 关键结论 + 逻辑关系 + 时间戳定位

你第一次用就应该有这种感觉：**“我以后不想再自己记笔记了。”** 😭🙏

---

## 你会得到什么输出？✨（学习级笔记）

- **结构化章节**：按主题切分，像一本小书的目录
- **小节标题**：每段“在讲什么”一眼看懂
- **Bullet points**：只写可复习的要点（概念/定义/结论/因果/步骤）
- **时间戳定位**：每个重点都能回到原视频验证/加深理解
- **Key Takeaways（3–5 条）**：考前 2 分钟快速过一遍

示例见：`examples/sample_notes.md` ✅

---

## 适用场景（高频！）📚

- **课程视频**：课后复习、期末冲刺
- **技术分享**：提炼概念、结论、最佳实践（只基于视频内容）
- **学术报告/会议**：按贡献点与结论结构化
- **长教程**：把“连续视频”变成“可查的知识卡片”

---

## 工作流（端到端）🧠🔧

输入：

- YouTube 链接（优先用字幕）
- 或本地视频文件（抽音频后转写）

输出：

- 一份 Markdown 学习笔记 `notes.md`

流程图：

```text
YouTube URL / Local Video
        |
        v
loader.py  (字幕优先 / 本地抽音频)
        |
        v
transcriber.py  (faster-whisper 转写 -> 带时间戳文本段)
        |
        v
segmenter.py  (按 时间 + 语义切分主题段)
        |
        v
summarizer.py  (逐段生成学习笔记 + Key Takeaways)
        |
        v
generator.py  (输出 Markdown)
```

---

## 快速开始（CLI）🚀

### 1) 安装依赖

建议 Python 3.10+。

```bash
pip install -r videotonotes/requirements.txt
```

### 2) 安装系统依赖：ffmpeg（本地视频必需）🎬

- **ffmpeg**：用于本地视频抽音频（请先把 `ffmpeg` 加到 PATH）
  - Windows 可用：`winget install Gyan.FFmpeg`（安装后重新打开终端）

### 3)（可选）启用更强“学习笔记生成”🤖

- 设置环境变量 `OPENAI_API_KEY`
- LLM 只做：**总结 / 结构化 / 学习导向表达**
- LLM 不做：**逐字复述 / 编造内容 / 延伸视频之外的信息**

---

## 用法示例（建议直接复制）🧪

### YouTube（优先字幕）

```bash
cd videotonotes
python cli.py "https://youtube.com/watch?v=xxxx" --out notes.md
```

### 本地视频（抽音频 + 转写）

```bash
cd videotonotes
python cli.py "lecture.mp4" --out notes.md
```

### 我想强制不用 LLM（纯规则提炼）🧱

```bash
cd videotonotes
python cli.py "lecture.mp4" --out notes.md --llm off
```

### 我想指定语言/模型（更稳）🧩

```bash
cd videotonotes
python cli.py "lecture.mp4" --out notes.md --lang zh --model small
```

---

## CLI 参数一览（MVP）🧾

- **`source`**：YouTube URL 或本地视频路径
- **`--out`**：输出 Markdown 文件路径（必填）
- **`--title`**：覆盖笔记标题
- **`--lang`**：语言提示（`auto/en/zh/...`）
- **`--model`**：faster-whisper 模型大小（`tiny/base/small/medium/large-v3...`）
- **`--min-seg-min`**：主题段最小时长（分钟）
- **`--max-seg-min`**：主题段最大时长（分钟）
- **`--llm`**：`auto/on/off`（`auto` 会检测 `OPENAI_API_KEY`）

---

## 深度解析：为什么“不是转写”而是“学习级笔记”？🧠

逐字稿的问题：**没有结构、没有重点、没有复习入口**。

学习级笔记要解决的其实是三件事：

- **结构（Structure）**：这段在讲什么？与上一段关系是什么？
- **重点（Signal）**：哪些句子值得记？哪些是铺垫/重复？
- **定位（Retrieval）**：复习时如何快速回到原视频？

VideoToNotes 的设计就是围绕这三点：

- 先拿到**带时间戳**的文本（字幕/转写）
- 再按“主题”切段（时间 + 语义）
- 最后对每段提炼：**概念/结论/逻辑关系**（而不是复述）

---

## 关键代码解读（带代码段）🔍

### 1) `loader.py`：YouTube 字幕优先，没字幕才转写 📺

```132:219:videotonotes/videotonotes/loader.py
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
            ...
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
    ...
```

**为什么这样做？**

- 有字幕就用字幕：速度快、成本低、时间戳天然准确 ✅
- 没字幕才转写：保证“任何视频都能用”✅

---

### 2) `segmenter.py`：按“时间 + 语义变化”切主题段 🧩

```17:87:videotonotes/videotonotes/segmenter.py
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
    ...
```

**这段的产品意义：**

- 你复习时要的是“按主题的块”，而不是连续长文本
- 每块 1.5–6 分钟更像课堂笔记：不会太碎，也不会一大坨

---

### 3) `summarizer.py`：LLM 只做“学习导向总结”，并且可降级 🧠🤖

```20:56:videotonotes/videotonotes/summarizer.py
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
    ...
```

**你关心的点（防止“编造”）：**

- Prompt 明确要求：**只用 transcript，不许 invent**（统一在 `prompts.py`）
- 没有 API Key 时：自动切到规则型提炼，输出更保守但稳定 ✅

---

### 4) `generator.py`：输出 Markdown + YouTube 时间戳链接 ⏱️🔗

```16:47:videotonotes/videotonotes/generator.py
def generate_markdown_notes(doc: NotesDocument) -> str:
    lines: list[str] = []
    lines.append(f"# {doc.title}")
    ...
    source_url = doc.source if doc.source.startswith("http") else None
    for i, sec in enumerate(doc.sections, start=1):
        start = _timestamp_link(source_url, sec.start_time)
        end = format_timestamp(sec.end_time)
        lines.append(f"### {i}. {sec.title}")
        ...
```

---

## 输入/输出示例 📌

- 输入：`examples/input_video.txt`
- 输出：`examples/sample_notes.md`

---

## 常见问题（FAQ）🧯

### Q1：为什么我跑不起来？提示找不到 `python` 😵

你的系统可能没装 Python 或没加 PATH。请安装 Python 3.10+ 后重开终端再试。

### Q2：本地视频报错 ffmpeg 找不到

请先安装 ffmpeg，并确保命令行执行 `ffmpeg -version` 有输出。

### Q3：YouTube 没字幕会怎样？

会自动下载音频并转写（速度更慢，但保证可用）。

### Q4：LLM 会不会胡说八道？

设计上尽量避免：

- Prompt 强制“只基于 transcript”
- JSON 结构输出（失败会降级到规则型 bullets）

---

## 路线图（下一步想做的）🗺️

- 章节标题更稳（结合关键词 + topic modeling）
- 输出支持 Obsidian/Notion（双向链接/块引用）
- 支持“复习卡片模式”（Q/A、填空、Anki 导出）
- 支持多语言字幕合并（中英双语对照）

---

## 👤 作者 (Author)

**Haoze Zheng**

*   🎓 **School**: Xinjiang University (XJU)
*   📧 **Email**: zhenghaoze@stu.xju.edu.cn
*   🐱 **GitHub**: [mire403](https://github.com/mire403)

---

<div align="center">

**如果这个项目对你有帮助，请给个 ⭐ Star！**

<sub>Made by Haoze Zheng. 2026 Deadline.</sub>

</div>


