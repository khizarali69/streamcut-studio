import json
import shutil
import subprocess
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import CaptionStyle, LayoutPreset, AppSettings
from app.schemas import CaptionStyleResponse, LayoutPresetResponse
from app.config import settings

router = APIRouter(prefix="/api/settings", tags=["settings"])

DEFAULT_CAPTION_STYLES = [
    {
        "id": "bold_neon",
        "name": "Bold Neon",
        "is_preset": True,
        "font_family": "Arial",
        "font_size": 26,
        "primary_color": "&H00FFFFFF",      # White
        "highlight_color": "&H0000FFFF",    # Yellow
        "outline_color": "&H00000000",      # Black
        "outline_width": 3.0,
        "shadow_color": "&H80000000",
        "shadow_offset": 2.0,
        "bg_color": "&H00000000",
        "bg_alpha": 0.0,
        "position_v": "bottom",
        "margin_v": 80,
        "words_per_line": 3,
        "max_lines": 2,
        "animation_style": "karaoke"
    },
    {
        "id": "clean_modern",
        "name": "Clean Modern",
        "is_preset": True,
        "font_family": "Arial",
        "font_size": 24,
        "primary_color": "&H00FFFFFF",
        "highlight_color": "&H00FFFF00",    # Cyan
        "outline_color": "&H001A1A1A",
        "outline_width": 1.5,
        "shadow_color": "&H60000000",
        "shadow_offset": 1.5,
        "bg_color": "&H00000000",
        "bg_alpha": 0.0,
        "position_v": "bottom",
        "margin_v": 70,
        "words_per_line": 4,
        "max_lines": 2,
        "animation_style": "word_highlight"
    },
    {
        "id": "karaoke_pop",
        "name": "Karaoke Pop",
        "is_preset": True,
        "font_family": "Arial",
        "font_size": 25,
        "primary_color": "&H00FFFFFF",
        "highlight_color": "&H0000FF00",    # Neon Green
        "outline_color": "&H00000000",
        "outline_width": 2.5,
        "shadow_color": "&H90000000",
        "shadow_offset": 2.0,
        "bg_color": "&H00000000",
        "bg_alpha": 0.0,
        "position_v": "bottom",
        "margin_v": 75,
        "words_per_line": 3,
        "max_lines": 1,
        "animation_style": "karaoke"
    },
    {
        "id": "minimal",
        "name": "Minimalist",
        "is_preset": True,
        "font_family": "Arial",
        "font_size": 22,
        "primary_color": "&H00FFFFFF",
        "highlight_color": "&H00FFFFFF",
        "outline_color": "&H00000000",
        "outline_width": 1.0,
        "shadow_color": "&H40000000",
        "shadow_offset": 1.0,
        "bg_color": "&H00000000",
        "bg_alpha": 0.4,
        "position_v": "bottom",
        "margin_v": 60,
        "words_per_line": 5,
        "max_lines": 2,
        "animation_style": "none"
    }
]

DEFAULT_LAYOUT_PRESETS = [
    {
        "id": "full_frame",
        "name": "Full-Frame 9:16",
        "layout_type": "full_frame",
        "aspect_ratio": "9:16",
        "facecam_rect": '{"x": 0.05, "y": 0.05, "w": 0.35, "h": 0.35}',
        "gameplay_rect": '{"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}',
        "description": "Centered or cropped vertical frame filling the 9:16 screen",
        "is_system": True
    },
    {
        "id": "split_facecam_gameplay",
        "name": "Facecam Above Gameplay",
        "layout_type": "split_facecam_gameplay",
        "aspect_ratio": "9:16",
        "facecam_rect": '{"x": 0.05, "y": 0.05, "w": 0.35, "h": 0.35}',
        "gameplay_rect": '{"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}',
        "description": "Top 35% focused on streamer facecam, bottom 65% on gameplay",
        "is_system": True
    },
    {
        "id": "split_gameplay_facecam",
        "name": "Gameplay Above Facecam",
        "layout_type": "split_gameplay_facecam",
        "aspect_ratio": "9:16",
        "facecam_rect": '{"x": 0.05, "y": 0.05, "w": 0.35, "h": 0.35}',
        "gameplay_rect": '{"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}',
        "description": "Top 65% focused on gameplay, bottom 35% on streamer facecam",
        "is_system": True
    },
    {
        "id": "blurred_background",
        "name": "Original Landscape on Blur",
        "layout_type": "blurred_background",
        "aspect_ratio": "9:16",
        "facecam_rect": '{"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}',
        "gameplay_rect": '{"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}',
        "description": "Preserves complete original landscape view over an ambient blurred vertical background",
        "is_system": True
    },
    {
        "id": "side_by_side",
        "name": "Side-by-Side Dual",
        "layout_type": "side_by_side",
        "aspect_ratio": "1:1",
        "facecam_rect": '{"x": 0.0, "y": 0.0, "w": 0.5, "h": 1.0}',
        "gameplay_rect": '{"x": 0.5, "y": 0.0, "w": 0.5, "h": 1.0}',
        "description": "Split horizontally for dual reaction or conversation framing",
        "is_system": True
    }
]

def seed_default_presets(db: Session):
    """Seeds default caption styles and layout presets if not present."""
    for style_data in DEFAULT_CAPTION_STYLES:
        existing = db.query(CaptionStyle).filter(CaptionStyle.id == style_data["id"]).first()
        if not existing:
            db.add(CaptionStyle(**style_data))

    for layout_data in DEFAULT_LAYOUT_PRESETS:
        existing = db.query(LayoutPreset).filter(LayoutPreset.id == layout_data["id"]).first()
        if not existing:
            db.add(LayoutPreset(**layout_data))

    db.commit()

@router.get("/caption-styles", response_model=List[CaptionStyleResponse])
def get_caption_styles(db: Session = Depends(get_db)):
    """Retrieve all available caption styles."""
    styles = db.query(CaptionStyle).all()
    if not styles:
        seed_default_presets(db)
        styles = db.query(CaptionStyle).all()
    return styles

@router.get("/layout-presets", response_model=List[LayoutPresetResponse])
def get_layout_presets(db: Session = Depends(get_db)):
    """Retrieve all layout presets."""
    layouts = db.query(LayoutPreset).all()
    if not layouts:
        seed_default_presets(db)
        layouts = db.query(LayoutPreset).all()

    result = []
    for l in layouts:
        result.append(LayoutPresetResponse(
            id=l.id,
            name=l.name,
            layout_type=l.layout_type,
            aspect_ratio=l.aspect_ratio,
            facecam_rect=json.loads(l.facecam_rect) if l.facecam_rect else {},
            gameplay_rect=json.loads(l.gameplay_rect) if l.gameplay_rect else {},
            description=l.description,
            is_system=l.is_system
        ))
    return result

@router.get("/system")
def get_system_diagnostics():
    """Returns local system diagnostics, FFmpeg presence, and Whisper hardware status."""
    # Check ffmpeg version
    ffmpeg_ver = "unknown"
    try:
        res = subprocess.run([settings.FFMPEG_PATH, "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        ffmpeg_ver = res.stdout.splitlines()[0] if res.stdout else "Available"
    except Exception as e:
        ffmpeg_ver = f"Error: {e}"

    # Check GPU availability (CUDA)
    gpu_available = False
    gpu_name = "None (CPU Mode)"
    try:
        import torch
        if torch.cuda.is_available():
            gpu_available = True
            gpu_name = torch.cuda.get_device_name(0)
    except Exception:
        pass

    total, used, free = shutil.disk_usage(settings.STORAGE_DIR)

    return {
        "ffmpeg": ffmpeg_ver,
        "whisper_model": settings.WHISPER_MODEL,
        "whisper_device": settings.WHISPER_DEVICE,
        "whisper_compute_type": settings.WHISPER_COMPUTE_TYPE,
        "gpu_available": gpu_available,
        "gpu_name": gpu_name,
        "disk_free_gb": round(free / (1024**3), 2),
        "disk_total_gb": round(total / (1024**3), 2),
        "disk_warning": free < (10 * 1024**3), # warn if < 10GB free
        "llm_enabled": settings.LLM_ENABLED,
        "llm_provider": settings.LLM_PROVIDER
    }
