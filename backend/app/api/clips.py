import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Project, ClipCandidate, ClipEdit, Job, CaptionStyle
from app.schemas import (
    AnalyzeRequest, ClipCandidateResponse, ClipEditUpdate, ClipEditResponse
)

router = APIRouter(prefix="/api/projects/{project_id}/clips", tags=["clips"])

@router.post("/analyze", status_code=status.HTTP_202_ACCEPTED)
def trigger_highlight_analysis(
    project_id: str,
    data: AnalyzeRequest,
    db: Session = Depends(get_db)
):
    """Triggers automatic candidate generation and ranking pipeline."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    job = Job(
        job_type="analyze_highlights",
        project_id=project_id,
        status="queued",
        progress=0.0,
        progress_stage="Queued for highlight analysis..."
    )
    db.add(job)
    project.status = "analyzing"
    db.commit()

    return {"message": "Highlight analysis enqueued", "job_id": job.id}

@router.get("", response_model=List[ClipCandidateResponse])
def list_clips(project_id: str, db: Session = Depends(get_db)):
    """List all candidate clips for a project."""
    clips = db.query(ClipCandidate).filter(ClipCandidate.project_id == project_id).order_by(ClipCandidate.highlight_score.desc()).all()
    
    result = []
    for c in clips:
        tags = json.loads(c.tags_json) if c.tags_json else []
        result.append(ClipCandidateResponse(
            id=c.id,
            project_id=c.project_id,
            title=c.title,
            start_time=c.start_time,
            end_time=c.end_time,
            duration=c.duration,
            highlight_score=c.highlight_score,
            reason=c.reason,
            tags=tags,
            status=c.status,
            created_at=c.created_at
        ))
    return result

@router.get("/{clip_id}/edit", response_model=ClipEditResponse)
def get_clip_edit(project_id: str, clip_id: str, db: Session = Depends(get_db)):
    """Retrieve editor settings (trim, layout, framing rects, caption styles) for a clip."""
    edit = db.query(ClipEdit).filter(ClipEdit.clip_id == clip_id).first()
    if not edit:
        # Create default edit if missing
        cand = db.query(ClipCandidate).filter(ClipCandidate.id == clip_id).first()
        if not cand:
            raise HTTPException(status_code=404, detail="Clip candidate not found")
        edit = ClipEdit(
            clip_id=clip_id,
            project_id=project_id,
            trim_start=cand.start_time,
            trim_end=cand.end_time,
            layout_type="full_frame",
            aspect_ratio="9:16",
            caption_style_id="bold_neon"
        )
        db.add(edit)
        db.commit()
        db.refresh(edit)

    facecam_rect = json.loads(edit.facecam_rect) if edit.facecam_rect else {"x": 0.05, "y": 0.05, "w": 0.35, "h": 0.35}
    gameplay_rect = json.loads(edit.gameplay_rect) if edit.gameplay_rect else {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}

    return ClipEditResponse(
        id=edit.id,
        clip_id=edit.clip_id,
        project_id=edit.project_id,
        trim_start=edit.trim_start,
        trim_end=edit.trim_end,
        layout_type=edit.layout_type,
        aspect_ratio=edit.aspect_ratio,
        facecam_rect=facecam_rect,
        gameplay_rect=gameplay_rect,
        caption_style_id=edit.caption_style_id,
        caption_enabled=edit.caption_enabled,
        volume_multiplier=edit.volume_multiplier,
        loudness_norm=edit.loudness_norm,
        silence_trim_enabled=edit.silence_trim_enabled,
        filler_word_removal=edit.filler_word_removal,
        version=edit.version,
        updated_at=edit.updated_at
    )

@router.patch("/{clip_id}/edit", response_model=ClipEditResponse)
def update_clip_edit(
    project_id: str,
    clip_id: str,
    data: ClipEditUpdate,
    db: Session = Depends(get_db)
):
    """Updates clip edit parameters with undo/redo tracking."""
    edit = db.query(ClipEdit).filter(ClipEdit.clip_id == clip_id).first()
    if not edit:
        raise HTTPException(status_code=404, detail="Clip edit not found")

    if data.trim_start is not None:
        edit.trim_start = max(0.0, data.trim_start)
    if data.trim_end is not None:
        edit.trim_end = max(edit.trim_start + 0.5, data.trim_end)
    if data.layout_type is not None:
        edit.layout_type = data.layout_type
    if data.aspect_ratio is not None:
        edit.aspect_ratio = data.aspect_ratio
    if data.facecam_rect is not None:
        edit.facecam_rect = json.dumps(data.facecam_rect.model_dump())
    if data.gameplay_rect is not None:
        edit.gameplay_rect = json.dumps(data.gameplay_rect.model_dump())
    if data.caption_style_id is not None:
        edit.caption_style_id = data.caption_style_id
    if data.caption_enabled is not None:
        edit.caption_enabled = data.caption_enabled
    if data.volume_multiplier is not None:
        edit.volume_multiplier = data.volume_multiplier
    if data.loudness_norm is not None:
        edit.loudness_norm = data.loudness_norm
    if data.silence_trim_enabled is not None:
        edit.silence_trim_enabled = data.silence_trim_enabled
    if data.filler_word_removal is not None:
        edit.filler_word_removal = data.filler_word_removal

    edit.version += 1
    db.commit()
    db.refresh(edit)

    facecam_rect = json.loads(edit.facecam_rect) if edit.facecam_rect else {"x": 0.05, "y": 0.05, "w": 0.35, "h": 0.35}
    gameplay_rect = json.loads(edit.gameplay_rect) if edit.gameplay_rect else {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}

    return ClipEditResponse(
        id=edit.id,
        clip_id=edit.clip_id,
        project_id=edit.project_id,
        trim_start=edit.trim_start,
        trim_end=edit.trim_end,
        layout_type=edit.layout_type,
        aspect_ratio=edit.aspect_ratio,
        facecam_rect=facecam_rect,
        gameplay_rect=gameplay_rect,
        caption_style_id=edit.caption_style_id,
        caption_enabled=edit.caption_enabled,
        volume_multiplier=edit.volume_multiplier,
        loudness_norm=edit.loudness_norm,
        silence_trim_enabled=edit.silence_trim_enabled,
        filler_word_removal=edit.filler_word_removal,
        version=edit.version,
        updated_at=edit.updated_at
    )

@router.patch("/{clip_id}")
def update_clip_metadata(
    project_id: str,
    clip_id: str,
    title: Optional[str] = None,
    highlight_score: Optional[float] = None,
    status_val: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Allows manual editing of title, internal highlight ranking score, or status."""
    clip = db.query(ClipCandidate).filter(ClipCandidate.id == clip_id).first()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    if title is not None:
        clip.title = title.strip()
    if highlight_score is not None:
        clip.highlight_score = round(max(0.0, min(100.0, highlight_score)), 1)
    if status_val is not None:
        clip.status = status_val

    db.commit()
    db.refresh(clip)
    return {"message": "Clip updated", "clip_id": clip.id}
