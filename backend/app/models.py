import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    source_url = Column(String(1024), nullable=True)
    creator = Column(String(255), nullable=True)
    rights_status = Column(String(50), default="owned")  # owned, permission_granted, licensed, unknown
    rights_notes = Column(Text, nullable=True)
    status = Column(String(50), default="created")  # created, ingested, analyzing, ready, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    source_media = relationship("SourceMedia", back_populates="project", uselist=False, cascade="all, delete-orphan")
    transcript = relationship("Transcript", back_populates="project", uselist=False, cascade="all, delete-orphan")
    candidates = relationship("ClipCandidate", back_populates="project", cascade="all, delete-orphan")
    edits = relationship("ClipEdit", back_populates="project", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="project", cascade="all, delete-orphan")
    exports = relationship("ExportArtifact", back_populates="project", cascade="all, delete-orphan")

class SourceMedia(Base):
    __tablename__ = "source_media"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(1024), nullable=False)
    file_size = Column(Integer, nullable=False)
    content_hash = Column(String(64), nullable=True, index=True)
    duration = Column(Float, default=0.0)
    width = Column(Integer, default=0)
    height = Column(Integer, default=0)
    fps = Column(Float, default=0.0)
    aspect_ratio = Column(String(20), default="16:9")
    video_codec = Column(String(50), nullable=True)
    audio_codec = Column(String(50), nullable=True)
    audio_channels = Column(Integer, default=0)
    sample_rate = Column(Integer, default=0)
    is_vfr = Column(Boolean, default=False)
    rotation = Column(Integer, default=0)
    thumbnail_path = Column(String(1024), nullable=True)
    proxy_path = Column(String(1024), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="source_media")

class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True)
    language = Column(String(10), default="en")
    is_user_edited = Column(Boolean, default=False)
    raw_text = Column(Text, default="")
    segments_json = Column(Text, default="[]")  # List of segment dictionaries with word timestamps
    original_segments_json = Column(Text, default="[]")  # Preserves raw transcription
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="transcript")

class ClipCandidate(Base):
    __tablename__ = "clip_candidates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    duration = Column(Float, nullable=False)
    highlight_score = Column(Float, default=80.0)
    reason = Column(Text, nullable=True)
    tags_json = Column(String(512), default="[]")
    status = Column(String(50), default="suggested")  # suggested, accepted, rejected
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="candidates")
    edit = relationship("ClipEdit", back_populates="candidate", uselist=False, cascade="all, delete-orphan")
    exports = relationship("ExportArtifact", back_populates="candidate", cascade="all, delete-orphan")

class ClipEdit(Base):
    __tablename__ = "clip_edits"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    clip_id = Column(String(36), ForeignKey("clip_candidates.id", ondelete="CASCADE"), nullable=False, unique=True)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    trim_start = Column(Float, nullable=False)
    trim_end = Column(Float, nullable=False)
    layout_type = Column(String(50), default="full_frame")  
    # full_frame, split_facecam_gameplay, split_gameplay_facecam, side_by_side, blurred_background, custom
    aspect_ratio = Column(String(20), default="9:16")  # 9:16, 1:1, 4:5, 16:9
    facecam_rect = Column(Text, default='{"x": 0.05, "y": 0.05, "w": 0.35, "h": 0.35}')
    gameplay_rect = Column(Text, default='{"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}')
    caption_style_id = Column(String(50), default="bold_neon")
    caption_enabled = Column(Boolean, default=True)
    volume_multiplier = Column(Float, default=1.0)
    loudness_norm = Column(Boolean, default=True)
    silence_trim_enabled = Column(Boolean, default=False)
    filler_word_removal = Column(Boolean, default=False)
    custom_transcript_edits = Column(Text, default="[]")
    undo_stack = Column(Text, default="[]")
    redo_stack = Column(Text, default="[]")
    version = Column(Integer, default=1)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="edits")
    candidate = relationship("ClipCandidate", back_populates="edit")

class CaptionStyle(Base):
    __tablename__ = "caption_styles"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    is_preset = Column(Boolean, default=True)
    font_family = Column(String(100), default="Arial")
    font_size = Column(Integer, default=24)
    primary_color = Column(String(20), default="&H00FFFFFF")  # ASS format &HBBGGRR or hex
    highlight_color = Column(String(20), default="&H0000FFFF")  # yellow in ASS &H00FFFF
    outline_color = Column(String(20), default="&H00000000")
    outline_width = Column(Float, default=2.5)
    shadow_color = Column(String(20), default="&H80000000")
    shadow_offset = Column(Float, default=1.5)
    bg_color = Column(String(20), default="&H00000000")
    bg_alpha = Column(Float, default=0.0)
    position_v = Column(String(20), default="bottom")  # top, middle, bottom
    margin_v = Column(Integer, default=70)
    words_per_line = Column(Integer, default=4)
    max_lines = Column(Integer, default=2)
    animation_style = Column(String(50), default="karaoke")  # none, karaoke, word_highlight

class LayoutPreset(Base):
    __tablename__ = "layout_presets"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    layout_type = Column(String(50), nullable=False)
    aspect_ratio = Column(String(20), default="9:16")
    facecam_rect = Column(Text, default='{"x": 0.05, "y": 0.05, "w": 0.35, "h": 0.35}')
    gameplay_rect = Column(Text, default='{"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}')
    description = Column(String(255), nullable=True)
    is_system = Column(Boolean, default=True)

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_type = Column(String(50), nullable=False)  # probe_and_proxy, transcribe, analyze_highlights, export_clip
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    target_id = Column(String(36), nullable=True)  # e.g., clip_id for export_clip
    status = Column(String(50), default="queued", index=True)  # queued, processing, completed, failed, canceled
    progress = Column(Float, default=0.0)
    progress_stage = Column(String(100), default="Queued")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    project = relationship("Project", back_populates="jobs")

class ExportArtifact(Base):
    __tablename__ = "export_artifacts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    clip_id = Column(String(36), ForeignKey("clip_candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(String(36), nullable=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(1024), nullable=False)
    file_size = Column(Integer, default=0)
    duration = Column(Float, default=0.0)
    width = Column(Integer, default=0)
    height = Column(Integer, default=0)
    format = Column(String(20), default="mp4")
    has_burned_captions = Column(Boolean, default=True)
    srt_path = Column(String(1024), nullable=True)
    vtt_path = Column(String(1024), nullable=True)
    thumbnail_path = Column(String(1024), nullable=True)
    ffprobe_valid = Column(Boolean, default=False)
    ffprobe_metadata = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="exports")
    candidate = relationship("ClipCandidate", back_populates="exports")

class AppSettings(Base):
    __tablename__ = "app_settings"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
