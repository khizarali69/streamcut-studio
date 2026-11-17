import os
import json
import hashlib
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from app.config import settings

def compute_file_hash(file_path: Path, block_size: int = 65536) -> str:
    """Compute SHA-256 hash of a file for deduplication."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(block_size), b""):
            hasher.update(block)
    return hasher.hexdigest()

def probe_video_file(file_path: Path) -> Dict[str, Any]:
    """Inspect video file streams and metadata using ffprobe."""
    if not file_path.exists():
        raise FileNotFoundError(f"Media file not found: {file_path}")

    cmd = [
        settings.FFPROBE_PATH,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(file_path)
    ]

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        probe_data = json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        raise ValueError(f"Corrupt or unreadable media file: {e.stderr.strip() or 'ffprobe failed'}")
    except json.JSONDecodeError:
        raise ValueError("Failed to parse ffprobe output")

    format_info = probe_data.get("format", {})
    streams = probe_data.get("streams", [])

    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    if not video_stream:
        raise ValueError("No video stream found in uploaded media")

    # Duration parsing
    try:
        duration = float(format_info.get("duration") or video_stream.get("duration") or 0.0)
    except (ValueError, TypeError):
        duration = 0.0

    width = int(video_stream.get("width") or 0)
    height = int(video_stream.get("height") or 0)
    video_codec = video_stream.get("codec_name", "unknown")

    # Rotation detection from tags or side data
    rotation = 0
    tags = video_stream.get("tags", {})
    if "rotate" in tags:
        try:
            rotation = int(tags["rotate"])
        except ValueError:
            rotation = 0
    for side_data in video_stream.get("side_data_list", []):
        if "rotation" in side_data:
            try:
                rotation = int(side_data["rotation"])
            except ValueError:
                pass

    # FPS calculation
    fps = 30.0
    r_frame_rate = video_stream.get("r_frame_rate", "30/1")
    avg_frame_rate = video_stream.get("avg_frame_rate", "30/1")
    is_vfr = False

    try:
        if "/" in r_frame_rate:
            num, den = map(float, r_frame_rate.split("/"))
            r_val = num / den if den != 0 else 30.0
        else:
            r_val = float(r_frame_rate)
        
        if "/" in avg_frame_rate:
            num, den = map(float, avg_frame_rate.split("/"))
            avg_val = num / den if den != 0 else 30.0
        else:
            avg_val = float(avg_frame_rate)

        fps = avg_val if avg_val > 0 else r_val
        if abs(r_val - avg_val) > 0.5 and avg_val > 0:
            is_vfr = True
    except Exception:
        fps = 30.0

    # Audio stream info
    audio_codec = None
    audio_channels = 0
    sample_rate = 0
    if audio_stream:
        audio_codec = audio_stream.get("codec_name")
        audio_channels = int(audio_stream.get("channels") or 1)
        sample_rate = int(audio_stream.get("sample_rate") or 44100)

    # Compute Aspect Ratio
    if width > 0 and height > 0:
        ratio_val = width / height
        if abs(ratio_val - (16 / 9)) < 0.05:
            aspect_ratio = "16:9"
        elif abs(ratio_val - (9 / 16)) < 0.05:
            aspect_ratio = "9:16"
        elif abs(ratio_val - 1.0) < 0.05:
            aspect_ratio = "1:1"
        elif abs(ratio_val - (4 / 5)) < 0.05:
            aspect_ratio = "4:5"
        else:
            aspect_ratio = f"{width}:{height}"
    else:
        aspect_ratio = "16:9"

    file_size = int(format_info.get("size") or file_path.stat().st_size)

    return {
        "duration": duration,
        "width": width,
        "height": height,
        "fps": round(fps, 2),
        "aspect_ratio": aspect_ratio,
        "video_codec": video_codec,
        "audio_codec": audio_codec,
        "audio_channels": audio_channels,
        "sample_rate": sample_rate,
        "is_vfr": is_vfr,
        "rotation": rotation,
        "file_size": file_size,
        "raw_format": format_info
    }

def generate_thumbnail(file_path: Path, output_path: Path, timestamp: float = 1.0) -> Path:
    """Generate a JPEG thumbnail at the specified timestamp."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        settings.FFMPEG_PATH,
        "-y",
        "-ss", str(max(0.0, timestamp)),
        "-i", str(file_path),
        "-frames:v", "1",
        "-q:v", "3",
        "-vf", "scale='min(640,iw)':-2",
        str(output_path)
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return output_path

def generate_preview_proxy(file_path: Path, output_path: Path) -> Path:
    """Generate a 480p lightweight fast-seeking H.264 proxy for fluid browser editing."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        settings.FFMPEG_PATH,
        "-y",
        "-i", str(file_path),
        "-vf", "scale='min(854,iw)':-2,format=yuv420p",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "28",
        "-c:a", "aac",
        "-b:a", "96k",
        "-movflags", "+faststart",
        str(output_path)
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return output_path
