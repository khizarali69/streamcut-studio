import pytest
import os
import json
from pathlib import Path

from app.subtitle_service import (
    escape_ass_text, format_ass_time, format_srt_time, format_vtt_time,
    chunk_words_into_caption_events, generate_ass_subtitle_file
)
from app.render_service import get_target_dimensions, build_video_filter_graph, validate_export
from app.highlight_service import score_window, generate_heuristic_candidates
from app.media_probe import probe_video_file
from app.database import SessionLocal, Base, engine
from app.models import Job, Project
from app.job_worker import recover_interrupted_jobs

def test_timestamp_conversions():
    # 0.0s
    assert format_ass_time(0.0) == "0:00:00.00"
    assert format_srt_time(0.0) == "00:00:00,000"
    assert format_vtt_time(0.0) == "00:00:00.000"

    # 65.42s -> 1 min, 5 sec, 42 cs
    assert format_ass_time(65.42) == "0:01:05.42"
    assert format_srt_time(65.42) == "00:01:05,420"
    assert format_vtt_time(65.42) == "00:01:05.420"

    # 3661.125s -> 1 hr, 1 min, 1.125s
    assert format_ass_time(3661.125) == "1:01:01.12"
    assert format_srt_time(3661.125) == "01:01:01,125"
    assert format_vtt_time(3661.125) == "01:01:01.125"

def test_caption_escaping():
    raw = r"Look at this {amazing} trick\hack!"
    escaped = escape_ass_text(raw)
    assert "{" not in escaped
    assert "}" not in escaped
    assert "\\" not in escaped
    assert "(" in escaped
    assert ")" in escaped
    assert "/" in escaped

def test_crop_dimensions():
    # 9:16
    assert get_target_dimensions("9:16", "1080p") == (1080, 1920)
    assert get_target_dimensions("9:16", "720p") == (720, 1280)
    # 1:1
    assert get_target_dimensions("1:1", "1080p") == (1080, 1080)
    assert get_target_dimensions("1:1", "720p") == (720, 720)
    # 4:5
    assert get_target_dimensions("4:5", "1080p") == (1080, 1350)
    assert get_target_dimensions("4:5", "720p") == (720, 900)
    # 16:9
    assert get_target_dimensions("16:9", "1080p") == (1920, 1080)

def test_filter_graph_generation():
    # Full frame
    f_str, out_lbl = build_video_filter_graph(
        source_w=1920, source_h=1080, target_w=1080, target_h=1920,
        layout_type="full_frame",
        facecam_rect={"x": 0.05, "y": 0.05, "w": 0.35, "h": 0.35},
        gameplay_rect={"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}
    )
    assert "crop=" in f_str
    assert "scale=1080:1920" in f_str
    assert out_lbl == "[vbase]"

    # Split facecam + gameplay
    f_str2, out_lbl2 = build_video_filter_graph(
        source_w=1920, source_h=1080, target_w=1080, target_h=1920,
        layout_type="split_facecam_gameplay",
        facecam_rect={"x": 0.05, "y": 0.05, "w": 0.35, "h": 0.35},
        gameplay_rect={"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}
    )
    assert "vstack=inputs=2" in f_str2

    # Blurred background
    f_str3, out_lbl3 = build_video_filter_graph(
        source_w=1920, source_h=1080, target_w=1080, target_h=1920,
        layout_type="blurred_background",
        facecam_rect={"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0},
        gameplay_rect={"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}
    )
    assert "boxblur=" in f_str3
    assert "overlay=" in f_str3

def test_highlight_scoring_and_clamping():
    segments = [
        {"id": 1, "start": 0.0, "end": 4.5, "text": "Why does nobody talk about this crazy secret?", "ends_sentence": True},
        {"id": 2, "start": 4.5, "end": 12.0, "text": "It turns out the whole game changes when you unlock this.", "ends_sentence": True},
        {"id": 3, "start": 12.0, "end": 22.0, "text": "Bro, no way! That is insane!", "ends_sentence": True}
    ]

    score, reason, tags = score_window(segments, content_type="gaming")
    assert score > 75.0
    assert "hook" in tags
    assert "reaction" in tags

    candidates = generate_heuristic_candidates(
        segments=segments,
        source_duration=25.0,
        min_duration=10.0,
        max_duration=30.0,
        target_count=3
    )
    assert len(candidates) >= 1
    assert candidates[0]["start_time"] >= 0.0
    assert candidates[0]["end_time"] <= 25.0
    assert candidates[0]["duration"] >= 10.0

def test_ass_subtitle_generation(tmp_path):
    segments = [
        {
            "id": 1, "start": 1.0, "end": 4.0, "text": "Hello world welcome",
            "words": [
                {"word": "Hello", "start": 1.0, "end": 1.8},
                {"word": "world", "start": 1.9, "end": 2.8},
                {"word": "welcome", "start": 2.9, "end": 4.0}
            ]
        }
    ]

    out_file = tmp_path / "test.ass"
    generate_ass_subtitle_file(
        segments=segments,
        output_path=out_file,
        trim_start=0.5,
        trim_end=5.0,
        target_width=1080,
        target_height=1920
    )

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "[Script Info]" in content
    assert "PlayResX: 1080" in content
    assert "PlayResY: 1920" in content
    assert "Dialogue:" in content
    assert "HELLO" in content

def test_job_state_recovery():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Create test project and job
    proj = Project(title="Recovery Test Project", status="analyzing")
    db.add(proj)
    db.commit()

    stuck_job = Job(
        job_type="export_clip",
        project_id=proj.id,
        status="processing",
        progress=45.0,
        progress_stage="Rendering in progress"
    )
    db.add(stuck_job)
    db.commit()

    # Run recovery
    recover_interrupted_jobs()

    db.refresh(stuck_job)
    assert stuck_job.status == "failed"
    assert "interrupted by application restart" in stuck_job.error_message.lower()

    # Cleanup
    db.delete(stuck_job)
    db.delete(proj)
    db.commit()
    db.close()

def test_invalid_media_probe():
    with pytest.raises(FileNotFoundError):
        probe_video_file(Path("non_existent_file.mp4"))
