import re
from pathlib import Path
from typing import List, Dict, Any, Optional

def escape_ass_text(text: str) -> str:
    """Escapes ASS control characters to avoid breaking the script parser."""
    text = text.replace("{", "(").replace("}", ")")
    text = text.replace("\\", "/")
    return text.strip()

def format_ass_time(seconds: float) -> str:
    """Converts seconds into ASS time format: H:MM:SS.cs"""
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        s += 1
        cs = 0
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def format_srt_time(seconds: float) -> str:
    """Converts seconds into SRT time format: HH:MM:SS,mmm"""
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms >= 1000:
        s += 1
        ms = 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def format_vtt_time(seconds: float) -> str:
    """Converts seconds into VTT time format: HH:MM:SS.mmm"""
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms >= 1000:
        s += 1
        ms = 0
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

def chunk_words_into_caption_events(
    segments: List[Dict[str, Any]],
    trim_start: float = 0.0,
    trim_end: float = 999999.0,
    words_per_line: int = 4,
    max_lines: int = 2
) -> List[Dict[str, Any]]:
    """
    Flattens word timestamps inside [trim_start, trim_end],
    and chunks them into balanced short caption events.
    All timestamps are normalized relative to clip start (t=0.0).
    """
    all_words = []
    for seg in segments:
        words = seg.get("words", [])
        if not words:
            # Fallback if no word timestamps
            seg_start = seg.get("start", 0.0)
            seg_end = seg.get("end", 0.0)
            text_words = seg.get("text", "").split()
            if text_words and seg_end > seg_start:
                dur = (seg_end - seg_start) / len(text_words)
                for idx, tw in enumerate(text_words):
                    all_words.append({
                        "word": tw,
                        "start": seg_start + idx * dur,
                        "end": seg_start + (idx + 1) * dur
                    })
        else:
            for w in words:
                all_words.append({
                    "word": w.get("word", ""),
                    "start": float(w.get("start", 0.0)),
                    "end": float(w.get("end", 0.0))
                })

    # Filter to clip range
    clip_words = [
        w for w in all_words
        if w["end"] > trim_start and w["start"] < trim_end
    ]

    if not clip_words:
        return []

    max_words_per_event = max(1, words_per_line * max_lines)
    events = []

    for i in range(0, len(clip_words), max_words_per_event):
        chunk = clip_words[i:i + max_words_per_event]
        if not chunk:
            continue
        
        event_raw_start = chunk[0]["start"]
        event_raw_end = chunk[-1]["end"]

        # Shift timestamps relative to trim_start
        rel_start = max(0.0, event_raw_start - trim_start)
        rel_end = max(rel_start + 0.3, event_raw_end - trim_start)

        # Build lines
        lines = []
        for l_idx in range(0, len(chunk), words_per_line):
            line_chunk = chunk[l_idx:l_idx + words_per_line]
            lines.append(line_chunk)

        events.append({
            "start": rel_start,
            "end": rel_end,
            "words": chunk,
            "lines": lines,
            "trim_start": trim_start
        })

    return events

def generate_ass_subtitle_file(
    segments: List[Dict[str, Any]],
    output_path: Path,
    trim_start: float = 0.0,
    trim_end: float = 999999.0,
    style_config: Optional[Dict[str, Any]] = None,
    target_width: int = 1080,
    target_height: int = 1920
) -> Path:
    """Generates a styled ASS subtitle file for FFmpeg libass burning."""
    style = style_config or {}
    font_name = style.get("font_family", "Arial")
    font_size = int(style.get("font_size", 54) * (target_height / 1920))
    primary_color = style.get("primary_color", "&H00FFFFFF")      # White
    highlight_color = style.get("highlight_color", "&H0000FFFF")  # Bright Yellow
    outline_color = style.get("outline_color", "&H00000000")      # Black
    outline_width = float(style.get("outline_width", 4.0))
    shadow_color = style.get("shadow_color", "&H80000000")
    shadow_offset = float(style.get("shadow_offset", 2.0))
    
    pos_v = style.get("position_v", "bottom")
    alignment = 2  # bottom center
    margin_v = int(style.get("margin_v", 180) * (target_height / 1920))
    if pos_v == "top":
        alignment = 8
    elif pos_v == "middle":
        alignment = 5

    words_per_line = int(style.get("words_per_line", 4))
    max_lines = int(style.get("max_lines", 2))
    anim_style = style.get("animation_style", "karaoke")

    events = chunk_words_into_caption_events(
        segments, trim_start, trim_end, words_per_line, max_lines
    )

    ass_lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {target_width}",
        f"PlayResY: {target_height}",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{font_name},{font_size},{primary_color},{highlight_color},{outline_color},{shadow_color},-1,0,0,0,100,100,0,0,1,{outline_width},{shadow_offset},{alignment},40,40,{margin_v},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ]

    for ev in events:
        start_str = format_ass_time(ev["start"])
        end_str = format_ass_time(ev["end"])

        formatted_lines = []
        for line_words in ev["lines"]:
            line_parts = []
            for w in line_words:
                clean_w = escape_ass_text(w["word"]).upper()
                w_start = max(0.0, w["start"] - trim_start)
                w_dur_cs = max(5, int(round((w["end"] - w["start"]) * 100)))

                if anim_style == "karaoke":
                    # Karaoke highlight tag
                    line_parts.append(f"{{\\k{w_dur_cs}}}{clean_w}")
                elif anim_style == "word_highlight":
                    # Active glowing word highlight tag
                    line_parts.append(clean_w)
                else:
                    # Clean static
                    line_parts.append(clean_w)

            formatted_lines.append(" ".join(line_parts))

        text_content = "\\N".join(formatted_lines)
        ass_lines.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{text_content}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(ass_lines))

    return output_path

def generate_srt_file(
    segments: List[Dict[str, Any]],
    output_path: Path,
    trim_start: float = 0.0,
    trim_end: float = 999999.0,
    words_per_line: int = 5
) -> Path:
    """Generates standard SRT subtitles."""
    events = chunk_words_into_caption_events(
        segments, trim_start, trim_end, words_per_line, max_lines=2
    )

    srt_entries = []
    for idx, ev in enumerate(events, 1):
        start_str = format_srt_time(ev["start"])
        end_str = format_srt_time(ev["end"])
        text = " ".join(escape_ass_text(w["word"]) for w in ev["words"])
        srt_entries.append(f"{idx}\n{start_str} --> {end_str}\n{text}\n")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_entries))
    return output_path

def generate_vtt_file(
    segments: List[Dict[str, Any]],
    output_path: Path,
    trim_start: float = 0.0,
    trim_end: float = 999999.0,
    words_per_line: int = 5
) -> Path:
    """Generates standard WebVTT subtitles."""
    events = chunk_words_into_caption_events(
        segments, trim_start, trim_end, words_per_line, max_lines=2
    )

    vtt_entries = ["WEBVTT\n"]
    for idx, ev in enumerate(events, 1):
        start_str = format_vtt_time(ev["start"])
        end_str = format_vtt_time(ev["end"])
        text = " ".join(escape_ass_text(w["word"]) for w in ev["words"])
        vtt_entries.append(f"{idx}\n{start_str} --> {end_str}\n{text}\n")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(vtt_entries))
    return output_path
