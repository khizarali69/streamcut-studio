import os
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from app.config import settings

def escape_ffmpeg_filter_path(path: Path) -> str:
    """Escapes Windows paths for FFmpeg filter arguments (colons and backslashes)."""
    p = str(path.resolve()).replace("\\", "/")
    return p.replace(":", "\\:")

def get_target_dimensions(aspect_ratio: str, resolution: str = "1080p") -> Tuple[int, int]:
    """Returns (width, height) for target aspect ratio and resolution preset."""
    is_720 = resolution == "720p"
    if aspect_ratio == "9:16":
        return (720, 1280) if is_720 else (1080, 1920)
    elif aspect_ratio == "1:1":
        return (720, 720) if is_720 else (1080, 1080)
    elif aspect_ratio == "4:5":
        return (720, 900) if is_720 else (1080, 1350)
    elif aspect_ratio == "16:9":
        return (1280, 720) if is_720 else (1920, 1080)
    else:
        # Default to 9:16
        return (720, 1280) if is_720 else (1080, 1920)

def build_video_filter_graph(
    source_w: int,
    source_h: int,
    target_w: int,
    target_h: int,
    layout_type: str,
    facecam_rect: Dict[str, float],
    gameplay_rect: Dict[str, float],
    ass_subtitles_path: Optional[Path] = None
) -> str:
    """Constructs the FFmpeg video filtergraph string."""
    filters = []

    if layout_type == "split_facecam_gameplay":
        # Top = facecam (35% of target_h), Bottom = gameplay (65% of target_h)
        h_top = int(round(target_h * 0.35))
        if h_top % 2 != 0:
            h_top += 1
        h_bot = target_h - h_top

        # Pixel coords for facecam
        fx = int(round(facecam_rect.get("x", 0.05) * source_w))
        fy = int(round(facecam_rect.get("y", 0.05) * source_h))
        fw = max(2, int(round(facecam_rect.get("w", 0.35) * source_w)))
        fh = max(2, int(round(facecam_rect.get("h", 0.35) * source_h)))
        fw = min(fw, source_w - fx)
        fh = min(fh, source_h - fy)

        # Pixel coords for gameplay
        gx = int(round(gameplay_rect.get("x", 0.0) * source_w))
        gy = int(round(gameplay_rect.get("y", 0.0) * source_h))
        gw = max(2, int(round(gameplay_rect.get("w", 1.0) * source_w)))
        gh = max(2, int(round(gameplay_rect.get("h", 1.0) * source_h)))
        gw = min(gw, source_w - gx)
        gh = min(gh, source_h - gy)

        filter_str = (
            f"[0:v]split=2[in_f][in_g];"
            f"[in_f]crop={fw}:{fh}:{fx}:{fy},scale={target_w}:{h_top}:force_original_aspect_ratio=increase,crop={target_w}:{h_top}[top];"
            f"[in_g]crop={gw}:{gh}:{gx}:{gy},scale={target_w}:{h_bot}:force_original_aspect_ratio=increase,crop={target_w}:{h_bot}[bot];"
            f"[top][bot]vstack=inputs=2[vbase]"
        )
        current_out = "[vbase]"

    elif layout_type == "split_gameplay_facecam":
        # Top = gameplay (65%), Bottom = facecam (35%)
        h_top = int(round(target_h * 0.65))
        if h_top % 2 != 0:
            h_top += 1
        h_bot = target_h - h_top

        fx = int(round(facecam_rect.get("x", 0.05) * source_w))
        fy = int(round(facecam_rect.get("y", 0.05) * source_h))
        fw = max(2, int(round(facecam_rect.get("w", 0.35) * source_w)))
        fh = max(2, int(round(facecam_rect.get("h", 0.35) * source_h)))

        gx = int(round(gameplay_rect.get("x", 0.0) * source_w))
        gy = int(round(gameplay_rect.get("y", 0.0) * source_h))
        gw = max(2, int(round(gameplay_rect.get("w", 1.0) * source_w)))
        gh = max(2, int(round(gameplay_rect.get("h", 1.0) * source_h)))

        filter_str = (
            f"[0:v]split=2[in_g][in_f];"
            f"[in_g]crop={gw}:{gh}:{gx}:{gy},scale={target_w}:{h_top}:force_original_aspect_ratio=increase,crop={target_w}:{h_top}[top];"
            f"[in_f]crop={fw}:{fh}:{fx}:{fy},scale={target_w}:{h_bot}:force_original_aspect_ratio=increase,crop={target_w}:{h_bot}[bot];"
            f"[top][bot]vstack=inputs=2[vbase]"
        )
        current_out = "[vbase]"

    elif layout_type == "side_by_side":
        # Left and Right halves
        w_half = target_w // 2
        filter_str = (
            f"[0:v]split=2[in_l][in_r];"
            f"[in_l]scale={w_half}:{target_h}:force_original_aspect_ratio=increase,crop={w_half}:{target_h}[left];"
            f"[in_r]scale={w_half}:{target_h}:force_original_aspect_ratio=increase,crop={w_half}:{target_h}[right];"
            f"[left][right]hstack=inputs=2[vbase]"
        )
        current_out = "[vbase]"

    elif layout_type == "blurred_background":
        # Centered original landscape video over blurred background
        filter_str = (
            f"[0:v]split=2[in_bg][in_fg];"
            f"[in_bg]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h},boxblur=20:5[bg];"
            f"[in_fg]scale={target_w}:-2:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2[vbase]"
        )
        current_out = "[vbase]"

    else:
        # full_frame (centered crop or bounding box)
        gx = int(round(gameplay_rect.get("x", 0.0) * source_w))
        gy = int(round(gameplay_rect.get("y", 0.0) * source_h))
        gw = max(2, int(round(gameplay_rect.get("w", 1.0) * source_w)))
        gh = max(2, int(round(gameplay_rect.get("h", 1.0) * source_h)))

        # If full 1.0 rect was given, center-crop to target aspect ratio
        if gw >= source_w and gh >= source_h:
            target_aspect = target_w / target_h
            source_aspect = source_w / source_h
            if source_aspect > target_aspect:
                crop_w = int(round(source_h * target_aspect))
                crop_h = source_h
                crop_x = (source_w - crop_w) // 2
                crop_y = 0
            else:
                crop_w = source_w
                crop_h = int(round(source_w / target_aspect))
                crop_x = 0
                crop_y = (source_h - crop_h) // 2
            filter_str = f"[0:v]crop={crop_w}:{crop_h}:{crop_x}:{crop_y},scale={target_w}:{target_h}[vbase]"
        else:
            filter_str = f"[0:v]crop={gw}:{gh}:{gx}:{gy},scale={target_w}:{target_h}:force_original_aspect_ratio=increase,crop={target_w}:{target_h}[vbase]"
        current_out = "[vbase]"

    # Subtitles burning
    if ass_subtitles_path and ass_subtitles_path.exists():
        escaped_ass = escape_ffmpeg_filter_path(ass_subtitles_path)
        filter_str += f";{current_out}ass='{escaped_ass}'[vout]"
        current_out = "[vout]"

    return filter_str, current_out

def render_clip_export(
    source_media_path: Path,
    output_media_path: Path,
    trim_start: float,
    trim_end: float,
    layout_type: str = "full_frame",
    aspect_ratio: str = "9:16",
    resolution: str = "1080p",
    quality: str = "high",
    facecam_rect: Optional[Dict[str, float]] = None,
    gameplay_rect: Optional[Dict[str, float]] = None,
    ass_subtitles_path: Optional[Path] = None,
    volume_multiplier: float = 1.0,
    loudness_norm: bool = True,
    has_audio: bool = True,
    progress_callback = None
) -> Path:
    """Executes FFmpeg export pipeline with precise timing, filter graph, and audio mixing."""
    source_probe = settings.FFPROBE_PATH
    output_media_path.parent.mkdir(parents=True, exist_ok=True)
    temp_output_path = settings.TEMP_DIR / f"temp_render_{os.getpid()}_{output_media_path.name}"

    # Get source dimensions
    from app.media_probe import probe_video_file
    meta = probe_video_file(source_media_path)
    source_w = meta["width"]
    source_h = meta["height"]

    target_w, target_h = get_target_dimensions(aspect_ratio, resolution)
    duration = max(0.5, trim_end - trim_start)

    facecam_rect = facecam_rect or {"x": 0.05, "y": 0.05, "w": 0.35, "h": 0.35}
    gameplay_rect = gameplay_rect or {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}

    video_filter, video_out_label = build_video_filter_graph(
        source_w=source_w,
        source_h=source_h,
        target_w=target_w,
        target_h=target_h,
        layout_type=layout_type,
        facecam_rect=facecam_rect,
        gameplay_rect=gameplay_rect,
        ass_subtitles_path=ass_subtitles_path
    )

    # Audio filters
    audio_filters = []
    if volume_multiplier != 1.0:
        audio_filters.append(f"volume={volume_multiplier:.2f}")
    if loudness_norm:
        audio_filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")
    audio_filter_str = ",".join(audio_filters) if audio_filters else "anull"

    # Encoding quality preset
    crf = "20" if quality == "high" else ("18" if quality == "ultra" else "23")
    preset = "medium" if quality == "high" else ("slow" if quality == "ultra" else "veryfast")

    cmd = [
        settings.FFMPEG_PATH,
        "-y",
        "-ss", str(trim_start),
        "-t", str(duration),
        "-i", str(source_media_path)
    ]

    # Handle media without audio
    if not has_audio or meta["audio_channels"] == 0:
        # Generate silent audio stream
        cmd.extend([
            "-f", "lavfi",
            "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-filter_complex", f"{video_filter};[1:a]{audio_filter_str}[aout]",
            "-map", video_out_label,
            "-map", "[aout]"
        ])
    else:
        cmd.extend([
            "-filter_complex", f"{video_filter};[0:a]{audio_filter_str}[aout]",
            "-map", video_out_label,
            "-map", "[aout]"
        ])

    cmd.extend([
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", crf,
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(temp_output_path)
    ])

    if progress_callback:
        progress_callback(10.0, "Rendering video stream and styling captions...")

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = proc.communicate()

    if proc.returncode != 0:
        if temp_output_path.exists():
            temp_output_path.unlink()
        raise RuntimeError(f"FFmpeg rendering failed: {stderr[-500:] if stderr else 'Unknown error'}")

    # Atomic publication: rename temp file to final output path
    if output_media_path.exists():
        output_media_path.unlink()
    temp_output_path.rename(output_media_path)

    if progress_callback:
        progress_callback(90.0, "Validating exported media with ffprobe...")

    # Validate output with ffprobe
    validation = validate_export(output_media_path, expected_w=target_w, expected_h=target_h, expected_dur=duration)
    if not validation["valid"]:
        raise ValueError(f"Export validation failed: {validation['errors']}")

    if progress_callback:
        progress_callback(100.0, "Export completed and validated.")

    return output_media_path

def validate_export(
    file_path: Path,
    expected_w: int,
    expected_h: int,
    expected_dur: float,
    tolerance_sec: float = 1.5
) -> Dict[str, Any]:
    """Validates finished output using ffprobe to ensure playability and spec adherence."""
    if not file_path.exists() or file_path.stat().st_size == 0:
        return {"valid": False, "errors": ["Export file does not exist or is empty"]}

    from app.media_probe import probe_video_file
    try:
        info = probe_video_file(file_path)
    except Exception as e:
        return {"valid": False, "errors": [f"Cannot probe output: {str(e)}"]}

    errors = []
    # Verify dimensions
    if abs(info["width"] - expected_w) > 4 or abs(info["height"] - expected_h) > 4:
        errors.append(f"Dimensions mismatch: got {info['width']}x{info['height']}, expected {expected_w}x{expected_h}")

    # Verify duration
    if abs(info["duration"] - expected_dur) > tolerance_sec:
        errors.append(f"Duration mismatch: got {info['duration']:.2f}s, expected {expected_dur:.2f}s")

    # Verify video stream
    if not info.get("video_codec"):
        errors.append("No valid video codec found in output")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "metadata": info
    }
