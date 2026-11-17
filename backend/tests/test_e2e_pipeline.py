import os
import json
import pytest
from pathlib import Path

from app.config import settings
from app.database import SessionLocal, Base, engine
from app.models import Project, SourceMedia, Transcript, ClipCandidate, ClipEdit, ExportArtifact, CaptionStyle
from app.media_probe import probe_video_file, generate_thumbnail, generate_preview_proxy
from app.whisper_service import transcribe_audio
from app.highlight_service import generate_heuristic_candidates
from app.subtitle_service import generate_ass_subtitle_file, generate_srt_file, generate_vtt_file
from app.render_service import render_clip_export, validate_export

def test_full_end_to_end_pipeline():
    sample_video = settings.STORAGE_DIR / "temp" / "sample_stream.mp4"
    assert sample_video.exists(), f"Sample test video missing at {sample_video}"

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # 1. Project Ingestion
    project = Project(
        title="E2E Pipeline Test Project",
        creator="Test Creator",
        rights_status="owned",
        rights_notes="Synthetic generated audio/video",
        status="created"
    )
    db.add(project)
    db.commit()

    # 2. Probe Media & Metadata Inspection
    meta = probe_video_file(sample_video)
    assert meta["width"] == 1920
    assert meta["height"] == 1080
    assert meta["duration"] > 10.0
    assert meta["video_codec"] == "h264"
    assert meta["audio_codec"] == "aac"

    thumb_path = settings.THUMBNAILS_DIR / f"{project.id}_thumb.jpg"
    generate_thumbnail(sample_video, thumb_path, timestamp=1.0)
    assert thumb_path.exists()
    assert thumb_path.stat().st_size > 0

    proxy_path = settings.PROXIES_DIR / f"{project.id}_proxy.mp4"
    generate_preview_proxy(sample_video, proxy_path)
    assert proxy_path.exists()
    assert proxy_path.stat().st_size > 0

    source_media = SourceMedia(
        project_id=project.id,
        filename="sample_stream.mp4",
        file_path=str(sample_video),
        file_size=sample_video.stat().st_size,
        duration=meta["duration"],
        width=meta["width"],
        height=meta["height"],
        fps=meta["fps"],
        aspect_ratio=meta["aspect_ratio"],
        video_codec=meta["video_codec"],
        audio_codec=meta["audio_codec"],
        audio_channels=meta["audio_channels"],
        sample_rate=meta["sample_rate"],
        thumbnail_path=f"/storage/thumbnails/{thumb_path.name}",
        proxy_path=f"/storage/proxies/{proxy_path.name}"
    )
    db.add(source_media)
    project.status = "ingested"
    db.commit()

    # 3. Speech-to-Text Transcription with faster-whisper
    segments, lang, raw_text = transcribe_audio(sample_video, language="en")
    assert lang == "en"
    assert len(segments) > 0, "Whisper failed to produce speech segments"
    assert len(raw_text) > 10
    print(f"Transcribed Text: {raw_text}")

    transcript = Transcript(
        project_id=project.id,
        language=lang,
        raw_text=raw_text,
        segments_json=json.dumps(segments),
        original_segments_json=json.dumps(segments)
    )
    db.add(transcript)
    project.status = "transcribed"
    db.commit()

    # 4. Highlight Selection & Candidate Generation
    candidates = generate_heuristic_candidates(
        segments=segments,
        source_duration=meta["duration"],
        min_duration=5.0,
        max_duration=30.0,
        target_count=3,
        content_type="gaming"
    )
    assert len(candidates) >= 1
    best_candidate = candidates[0]
    assert best_candidate["start_time"] >= 0.0
    assert best_candidate["end_time"] <= meta["duration"]
    assert best_candidate["duration"] > 0.0

    cand_record = ClipCandidate(
        project_id=project.id,
        title=best_candidate["title"],
        start_time=best_candidate["start_time"],
        end_time=best_candidate["end_time"],
        duration=best_candidate["duration"],
        highlight_score=best_candidate["highlight_score"],
        reason=best_candidate["reason"],
        tags_json=json.dumps(best_candidate["tags"])
    )
    db.add(cand_record)
    db.commit()

    # 5. Clip Edit Configuration: 9:16 Vertical, Facecam Top + Gameplay Bottom, ASS Subtitles
    clip_edit = ClipEdit(
        clip_id=cand_record.id,
        project_id=project.id,
        trim_start=cand_record.start_time,
        trim_end=cand_record.end_time,
        layout_type="split_facecam_gameplay",
        aspect_ratio="9:16",
        facecam_rect='{"x": 0.05, "y": 0.05, "w": 0.35, "h": 0.35}',
        gameplay_rect='{"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}',
        caption_style_id="bold_neon",
        caption_enabled=True,
        volume_multiplier=1.0,
        loudness_norm=True
    )
    db.add(clip_edit)
    db.commit()

    # 6. Generate Subtitle Files (ASS, SRT, VTT)
    ass_path = settings.SUBTITLES_DIR / f"{cand_record.id}.ass"
    srt_path = settings.SUBTITLES_DIR / f"{cand_record.id}.srt"
    vtt_path = settings.SUBTITLES_DIR / f"{cand_record.id}.vtt"

    generate_ass_subtitle_file(
        segments=segments,
        output_path=ass_path,
        trim_start=clip_edit.trim_start,
        trim_end=clip_edit.trim_end,
        target_width=1080,
        target_height=1920
    )
    assert ass_path.exists()
    assert ass_path.stat().st_size > 0

    generate_srt_file(segments, srt_path, trim_start=clip_edit.trim_start, trim_end=clip_edit.trim_end)
    assert srt_path.exists()

    generate_vtt_file(segments, vtt_path, trim_start=clip_edit.trim_start, trim_end=clip_edit.trim_end)
    assert vtt_path.exists()

    # 7. Render 9:16 Vertical Video Export with Burned-In Subtitles
    out_path = settings.EXPORTS_DIR / f"test_export_{cand_record.id[:8]}.mp4"
    rendered_file = render_clip_export(
        source_media_path=sample_video,
        output_media_path=out_path,
        trim_start=clip_edit.trim_start,
        trim_end=clip_edit.trim_end,
        layout_type=clip_edit.layout_type,
        aspect_ratio=clip_edit.aspect_ratio,
        resolution="1080p",
        quality="high",
        facecam_rect={"x": 0.05, "y": 0.05, "w": 0.35, "h": 0.35},
        gameplay_rect={"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0},
        ass_subtitles_path=ass_path,
        volume_multiplier=clip_edit.volume_multiplier,
        loudness_norm=clip_edit.loudness_norm,
        has_audio=True
    )

    # 8. ffprobe Validation of Exported Video
    assert rendered_file.exists()
    assert rendered_file.stat().st_size > 50000

    val = validate_export(
        rendered_file,
        expected_w=1080,
        expected_h=1920,
        expected_dur=(clip_edit.trim_end - clip_edit.trim_start),
        tolerance_sec=1.5
    )
    assert val["valid"] is True, f"Rendered file failed validation: {val['errors']}"
    assert val["metadata"]["width"] == 1080
    assert val["metadata"]["height"] == 1920
    assert val["metadata"]["video_codec"] == "h264"
    assert val["metadata"]["audio_codec"] == "aac"

    # 9. Save Export Artifact
    artifact = ExportArtifact(
        project_id=project.id,
        clip_id=cand_record.id,
        filename=out_path.name,
        file_path=str(out_path),
        file_size=out_path.stat().st_size,
        duration=val["metadata"]["duration"],
        width=1080,
        height=1920,
        format="mp4",
        has_burned_captions=True,
        srt_path=f"/storage/subtitles/{srt_path.name}",
        vtt_path=f"/storage/subtitles/{vtt_path.name}",
        ffprobe_valid=True
    )
    db.add(artifact)
    project.status = "ready"
    db.commit()

    print("\n==========================================")
    print("END-TO-END PIPELINE VALIDATION PASSED!")
    print(f"Exported Video Path: {rendered_file}")
    print(f"Export Dimensions: {val['metadata']['width']}x{val['metadata']['height']}")
    print(f"Export Duration: {val['metadata']['duration']:.2f}s")
    print(f"Burned-in ASS Subtitles: Yes")
    print(f"SRT & VTT Sidecars: Yes")
    print("==========================================\n")

    db.close()
