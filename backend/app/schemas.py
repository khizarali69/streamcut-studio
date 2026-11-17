from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    source_url: Optional[str] = None
    creator: Optional[str] = None
    rights_status: str = Field("owned", pattern="^(owned|permission_granted|licensed|unknown)$")
    rights_notes: Optional[str] = None

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    source_url: Optional[str] = None
    creator: Optional[str] = None
    rights_status: Optional[str] = None
    rights_notes: Optional[str] = None

class SourceMediaResponse(BaseModel):
    id: str
    project_id: str
    filename: str
    file_size: int
    duration: float
    width: int
    height: int
    fps: float
    aspect_ratio: str
    video_codec: Optional[str]
    audio_codec: Optional[str]
    audio_channels: int
    sample_rate: int
    is_vfr: bool
    rotation: int
    thumbnail_path: Optional[str]
    proxy_path: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class ProjectResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    source_url: Optional[str]
    creator: Optional[str]
    rights_status: str
    rights_notes: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    source_media: Optional[SourceMediaResponse] = None

    class Config:
        from_attributes = True

class WordTimestamp(BaseModel):
    word: str
    start: float
    end: float
    score: Optional[float] = 1.0

class TranscriptSegment(BaseModel):
    id: int
    start: float
    end: float
    text: str
    words: List[WordTimestamp] = []

class TranscriptResponse(BaseModel):
    id: str
    project_id: str
    language: str
    is_user_edited: bool
    raw_text: str
    segments: List[TranscriptSegment] = []
    created_at: datetime
    updated_at: datetime

class TranscriptUpdateRequest(BaseModel):
    segments: List[TranscriptSegment]

class AnalyzeRequest(BaseModel):
    min_duration: float = Field(15.0, ge=5.0, le=180.0)
    max_duration: float = Field(60.0, ge=10.0, le=300.0)
    target_count: int = Field(5, ge=1, le=20)
    content_type: str = Field("general", pattern="^(gaming|reaction|conversation|podcast|tutorial|general)$")
    user_instruction: Optional[str] = None

class ClipCandidateResponse(BaseModel):
    id: str
    project_id: str
    title: str
    start_time: float
    end_time: float
    duration: float
    highlight_score: float
    reason: Optional[str]
    tags: List[str] = []
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class RectNorm(BaseModel):
    x: float = Field(..., ge=0.0, le=1.0)
    y: float = Field(..., ge=0.0, le=1.0)
    w: float = Field(..., ge=0.01, le=1.0)
    h: float = Field(..., ge=0.01, le=1.0)

class ClipEditUpdate(BaseModel):
    trim_start: Optional[float] = None
    trim_end: Optional[float] = None
    layout_type: Optional[str] = None
    aspect_ratio: Optional[str] = None
    facecam_rect: Optional[RectNorm] = None
    gameplay_rect: Optional[RectNorm] = None
    caption_style_id: Optional[str] = None
    caption_enabled: Optional[bool] = None
    volume_multiplier: Optional[float] = None
    loudness_norm: Optional[bool] = None
    silence_trim_enabled: Optional[bool] = None
    filler_word_removal: Optional[bool] = None
    custom_transcript_edits: Optional[List[Dict[str, Any]]] = None

class ClipEditResponse(BaseModel):
    id: str
    clip_id: str
    project_id: str
    trim_start: float
    trim_end: float
    layout_type: str
    aspect_ratio: str
    facecam_rect: Dict[str, Any]
    gameplay_rect: Dict[str, Any]
    caption_style_id: str
    caption_enabled: bool
    volume_multiplier: float
    loudness_norm: bool
    silence_trim_enabled: bool
    filler_word_removal: bool
    version: int
    updated_at: datetime

class CaptionStyleResponse(BaseModel):
    id: str
    name: str
    is_preset: bool
    font_family: str
    font_size: int
    primary_color: str
    highlight_color: str
    outline_color: str
    outline_width: float
    shadow_color: str
    shadow_offset: float
    bg_color: str
    bg_alpha: float
    position_v: str
    margin_v: int
    words_per_line: int
    max_lines: int
    animation_style: str

    class Config:
        from_attributes = True

class LayoutPresetResponse(BaseModel):
    id: str
    name: str
    layout_type: str
    aspect_ratio: str
    facecam_rect: Dict[str, Any]
    gameplay_rect: Dict[str, Any]
    description: Optional[str]
    is_system: bool

class JobResponse(BaseModel):
    id: str
    job_type: str
    project_id: str
    target_id: Optional[str]
    status: str
    progress: float
    progress_stage: str
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True

class ExportRequest(BaseModel):
    resolution: str = Field("1080p", pattern="^(720p|1080p|original)$")
    quality: str = Field("high", pattern="^(standard|high|ultra)$")
    burn_captions: bool = True
    export_srt: bool = True
    export_vtt: bool = True

class ExportArtifactResponse(BaseModel):
    id: str
    project_id: str
    clip_id: str
    job_id: Optional[str]
    filename: str
    file_size: int
    duration: float
    width: int
    height: int
    format: str
    has_burned_captions: bool
    download_url: str
    srt_url: Optional[str]
    vtt_url: Optional[str]
    thumbnail_url: Optional[str]
    ffprobe_valid: bool
    created_at: datetime

class StorageStats(BaseModel):
    total_space_bytes: int
    free_space_bytes: int
    used_by_app_bytes: int
    projects_count: int
    exports_count: int
