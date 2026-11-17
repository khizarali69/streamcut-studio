import os
import time
import json
import asyncio
import threading
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from app.config import settings
from app.database import SessionLocal
from app.models import (
    Project, SourceMedia, Transcript, ClipCandidate, ClipEdit,
    CaptionStyle, Job, ExportArtifact
)
from app.media_probe import probe_video_file, generate_thumbnail, generate_preview_proxy
from app.whisper_service import transcribe_audio
from app.highlight_service import generate_heuristic_candidates, generate_llm_candidates
from app.subtitle_service import generate_ass_subtitle_file, generate_srt_file, generate_vtt_file
from app.render_service import render_clip_export

# Active subprocesses mapping for safe cancellation
_active_jobs: Dict[str, Any] = {}
_worker_running = False
_worker_thread = None

def recover_interrupted_jobs():
    """Detect jobs stuck in 'processing' state from a prior crash or restart."""
    db = SessionLocal()
    try:
        stuck_jobs = db.query(Job).filter(Job.status == "processing").all()
        for job in stuck_jobs:
            job.status = "failed"
            job.error_message = "Processing interrupted by application restart. You can retry this job."
            job.completed_at = datetime.utcnow()
        if stuck_jobs:
            db.commit()
            print(f"Recovered {len(stuck_jobs)} interrupted jobs from prior session.")
    except Exception as e:
        print(f"Error during job recovery: {e}")
    finally:
        db.close()

def cancel_running_job(job_id: str) -> bool:
    """Safely terminates any running process associated with the job."""
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return False
        
        job.status = "canceled"
        job.progress_stage = "Canceled by user"
        job.completed_at = datetime.utcnow()
        db.commit()

        # Terminate active process if registered
        proc = _active_jobs.get(job_id)
        if proc and hasattr(proc, "terminate"):
            try:
                proc.terminate()
            except Exception:
                pass
        return True
    finally:
        db.close()

def process_probe_and_proxy_job(job: Job, db):
    """Processes newly uploaded media: probes streams, creates thumbnail and proxy."""
    project = db.query(Project).filter(Project.id == job.project_id).first()
    media = db.query(SourceMedia).filter(SourceMedia.project_id == job.project_id).first()
    if not media:
        raise ValueError("Source media record not found")

    file_path = Path(media.file_path)
    job.progress = 20.0
    job.progress_stage = "Probing video streams..."
    db.commit()

    meta = probe_video_file(file_path)
    media.duration = meta["duration"]
    media.width = meta["width"]
    media.height = meta["height"]
    media.fps = meta["fps"]
    media.aspect_ratio = meta["aspect_ratio"]
    media.video_codec = meta["video_codec"]
    media.audio_codec = meta["audio_codec"]
    media.audio_channels = meta["audio_channels"]
    media.sample_rate = meta["sample_rate"]
    media.is_vfr = meta["is_vfr"]
    media.rotation = meta["rotation"]

    job.progress = 50.0
    job.progress_stage = "Generating poster thumbnail..."
    db.commit()

    thumb_path = settings.THUMBNAILS_DIR / f"{media.id}_thumb.jpg"
    generate_thumbnail(file_path, thumb_path, timestamp=min(1.0, max(0.1, meta["duration"] * 0.1)))
    media.thumbnail_path = f"/storage/thumbnails/{thumb_path.name}"

    job.progress = 75.0
    job.progress_stage = "Generating lightweight preview proxy..."
    db.commit()

    proxy_path = settings.PROXIES_DIR / f"{media.id}_proxy.mp4"
    generate_preview_proxy(file_path, proxy_path)
    media.proxy_path = f"/storage/proxies/{proxy_path.name}"

    project.status = "ingested"
    job.progress = 100.0
    job.progress_stage = "Ingestion complete"
    db.commit()

def process_transcribe_job(job: Job, db):
    """Transcribes audio using faster-whisper."""
    project = db.query(Project).filter(Project.id == job.project_id).first()
    media = db.query(SourceMedia).filter(SourceMedia.project_id == job.project_id).first()
    if not media:
        raise ValueError("Source media not found")

    file_path = Path(media.file_path)
    def update_prog(pct, stage):
        job.progress = pct
        job.progress_stage = stage
        db.commit()

    segments, detected_lang, raw_text = transcribe_audio(
        video_path=file_path,
        language="en",
        progress_callback=update_prog
    )

    # Save transcript
    transcript = db.query(Transcript).filter(Transcript.project_id == project.id).first()
    if not transcript:
        transcript = Transcript(
            project_id=project.id,
            language=detected_lang,
            raw_text=raw_text,
            segments_json=json.dumps(segments),
            original_segments_json=json.dumps(segments)
        )
        db.add(transcript)
    else:
        transcript.language = detected_lang
        transcript.raw_text = raw_text
        transcript.segments_json = json.dumps(segments)
        transcript.original_segments_json = json.dumps(segments)

    project.status = "transcribed"
    job.progress = 100.0
    job.progress_stage = "Transcription complete"
    db.commit()

def process_analyze_job(job: Job, db):
    """Analyzes transcript and media to generate highlight candidates."""
    project = db.query(Project).filter(Project.id == job.project_id).first()
    media = db.query(SourceMedia).filter(SourceMedia.project_id == job.project_id).first()
    transcript = db.query(Transcript).filter(Transcript.project_id == job.project_id).first()

    segments = json.loads(transcript.segments_json) if transcript and transcript.segments_json else []
    duration = media.duration if media else 60.0

    job.progress = 30.0
    job.progress_stage = "Evaluating speech dynamics and narrative flow..."
    db.commit()

    candidates_data = generate_heuristic_candidates(
        segments=segments,
        source_duration=duration,
        min_duration=15.0,
        max_duration=60.0,
        target_count=5
    )

    job.progress = 75.0
    job.progress_stage = "Generating candidate clip records and edit settings..."
    db.commit()

    # Clear previous candidates if any
    db.query(ClipCandidate).filter(ClipCandidate.project_id == project.id).delete()
    db.commit()

    for cand_info in candidates_data:
        candidate = ClipCandidate(
            project_id=project.id,
            title=cand_info["title"],
            start_time=cand_info["start_time"],
            end_time=cand_info["end_time"],
            duration=cand_info["duration"],
            highlight_score=cand_info["highlight_score"],
            reason=cand_info["reason"],
            tags_json=json.dumps(cand_info.get("tags", [])),
            status="suggested"
        )
        db.add(candidate)
        db.flush()

        # Create default ClipEdit for this candidate
        clip_edit = ClipEdit(
            clip_id=candidate.id,
            project_id=project.id,
            trim_start=candidate.start_time,
            trim_end=candidate.end_time,
            layout_type="full_frame",
            aspect_ratio="9:16",
            caption_style_id="bold_neon",
            caption_enabled=True,
            volume_multiplier=1.0,
            loudness_norm=True
        )
        db.add(clip_edit)

    project.status = "ready"
    job.progress = 100.0
    job.progress_stage = "Highlight analysis complete"
    db.commit()

def process_export_job(job: Job, db):
    """Renders final clip video with reframing, layout, audio filtering, and subtitles."""
    clip = db.query(ClipCandidate).filter(ClipCandidate.id == job.target_id).first()
    if not clip:
        raise ValueError(f"Clip candidate {job.target_id} not found")
    
    project = db.query(Project).filter(Project.id == clip.project_id).first()
    media = db.query(SourceMedia).filter(SourceMedia.project_id == clip.project_id).first()
    edit = db.query(ClipEdit).filter(ClipEdit.clip_id == clip.id).first()
    transcript = db.query(Transcript).filter(Transcript.project_id == clip.project_id).first()

    segments = json.loads(transcript.segments_json) if transcript and transcript.segments_json else []

    facecam_rect = json.loads(edit.facecam_rect) if edit and edit.facecam_rect else {"x": 0.05, "y": 0.05, "w": 0.35, "h": 0.35}
    gameplay_rect = json.loads(edit.gameplay_rect) if edit and edit.gameplay_rect else {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}

    # Fetch caption style
    style_obj = db.query(CaptionStyle).filter(CaptionStyle.id == edit.caption_style_id).first()
    style_dict = {
        "font_family": style_obj.font_family if style_obj else "Arial",
        "font_size": style_obj.font_size if style_obj else 24,
        "primary_color": style_obj.primary_color if style_obj else "&H00FFFFFF",
        "highlight_color": style_obj.highlight_color if style_obj else "&H0000FFFF",
        "outline_color": style_obj.outline_color if style_obj else "&H00000000",
        "outline_width": style_obj.outline_width if style_obj else 2.5,
        "shadow_color": style_obj.shadow_color if style_obj else "&H80000000",
        "shadow_offset": style_obj.shadow_offset if style_obj else 1.5,
        "position_v": style_obj.position_v if style_obj else "bottom",
        "margin_v": style_obj.margin_v if style_obj else 70,
        "words_per_line": style_obj.words_per_line if style_obj else 4,
        "max_lines": style_obj.max_lines if style_obj else 2,
        "animation_style": style_obj.animation_style if style_obj else "karaoke"
    }

    # Generate Subtitle files
    ass_path = None
    srt_path = settings.SUBTITLES_DIR / f"{clip.id}.srt"
    vtt_path = settings.SUBTITLES_DIR / f"{clip.id}.vtt"
    generate_srt_file(segments, srt_path, trim_start=edit.trim_start, trim_end=edit.trim_end)
    generate_vtt_file(segments, vtt_path, trim_start=edit.trim_start, trim_end=edit.trim_end)

    if edit.caption_enabled:
        ass_path = settings.SUBTITLES_DIR / f"{clip.id}.ass"
        generate_ass_subtitle_file(
            segments=segments,
            output_path=ass_path,
            trim_start=edit.trim_start,
            trim_end=edit.trim_end,
            style_config=style_dict
        )

    # Output media path
    safe_title = "".join(c for c in clip.title if c.isalnum() or c in (" ", "_", "-")).rstrip()
    out_filename = f"{clip.id[:8]}_{safe_title.replace(' ', '_')}.mp4"
    out_path = settings.EXPORTS_DIR / out_filename

    def render_prog(pct, stage):
        job.progress = pct
        job.progress_stage = stage
        db.commit()

    rendered_file = render_clip_export(
        source_media_path=Path(media.file_path),
        output_media_path=out_path,
        trim_start=edit.trim_start,
        trim_end=edit.trim_end,
        layout_type=edit.layout_type,
        aspect_ratio=edit.aspect_ratio,
        resolution="1080p",
        facecam_rect=facecam_rect,
        gameplay_rect=gameplay_rect,
        ass_subtitles_path=ass_path if edit.caption_enabled else None,
        volume_multiplier=edit.volume_multiplier,
        loudness_norm=edit.loudness_norm,
        has_audio=(media.audio_channels > 0),
        progress_callback=render_prog
    )

    # Generate clip export thumbnail
    thumb_path = settings.THUMBNAILS_DIR / f"export_{clip.id}.jpg"
    generate_thumbnail(rendered_file, thumb_path, timestamp=0.5)

    # Save export artifact record
    info = probe_video_file(rendered_file)
    artifact = ExportArtifact(
        project_id=project.id,
        clip_id=clip.id,
        job_id=job.id,
        filename=out_filename,
        file_path=str(rendered_file),
        file_size=rendered_file.stat().st_size,
        duration=info["duration"],
        width=info["width"],
        height=info["height"],
        format="mp4",
        has_burned_captions=edit.caption_enabled,
        srt_path=f"/storage/subtitles/{srt_path.name}",
        vtt_path=f"/storage/subtitles/{vtt_path.name}",
        thumbnail_path=f"/storage/thumbnails/{thumb_path.name}",
        ffprobe_valid=True,
        ffprobe_metadata=json.dumps(info)
    )
    db.add(artifact)

    job.progress = 100.0
    job.progress_stage = "Export completed successfully"
    db.commit()

def run_worker_loop():
    """Continuous background loop for processing queued jobs."""
    global _worker_running
    print("StreamCut Studio Job Worker started.")
    
    # Run recovery on startup
    recover_interrupted_jobs()

    while _worker_running:
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.status == "queued").order_by(Job.created_at.asc()).first()
            if not job:
                db.close()
                time.sleep(1.0)
                continue

            job.status = "processing"
            job.started_at = datetime.utcnow()
            job.progress = 5.0
            job.progress_stage = f"Starting {job.job_type}..."
            db.commit()

            try:
                if job.job_type == "probe_and_proxy":
                    process_probe_and_proxy_job(job, db)
                elif job.job_type == "transcribe":
                    process_transcribe_job(job, db)
                elif job.job_type == "analyze_highlights":
                    process_analyze_job(job, db)
                elif job.job_type == "export_clip":
                    process_export_job(job, db)
                else:
                    raise ValueError(f"Unknown job type: {job.job_type}")

                job.status = "completed"
                job.completed_at = datetime.utcnow()
                db.commit()
            except Exception as ex:
                db.rollback()
                job.status = "failed"
                job.error_message = str(ex)
                job.completed_at = datetime.utcnow()
                job.progress_stage = f"Failed: {str(ex)[:100]}"
                db.commit()
                print(f"Job {job.id} failed: {ex}")

        except Exception as e:
            print(f"Worker loop error: {e}")
            time.sleep(2.0)
        finally:
            db.close()

def start_background_worker():
    """Starts the persistent background queue worker in a daemon thread."""
    global _worker_running, _worker_thread
    if not _worker_running:
        _worker_running = True
        _worker_thread = threading.Thread(target=run_worker_loop, daemon=True)
        _worker_thread.start()

def stop_background_worker():
    """Gracefully signals the worker loop to stop."""
    global _worker_running
    _worker_running = False
