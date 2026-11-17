import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Project, Transcript, Job
from app.schemas import TranscriptResponse, TranscriptUpdateRequest

router = APIRouter(prefix="/api/projects/{project_id}/transcript", tags=["transcript"])

@router.get("", response_model=TranscriptResponse)
def get_transcript(project_id: str, db: Session = Depends(get_db)):
    """Retrieve full transcript with word-level timestamps."""
    transcript = db.query(Transcript).filter(Transcript.project_id == project_id).first()
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not generated yet")

    segments = json.loads(transcript.segments_json) if transcript.segments_json else []
    return TranscriptResponse(
        id=transcript.id,
        project_id=transcript.project_id,
        language=transcript.language,
        is_user_edited=transcript.is_user_edited,
        raw_text=transcript.raw_text,
        segments=segments,
        created_at=transcript.created_at,
        updated_at=transcript.updated_at
    )

@router.put("", response_model=TranscriptResponse)
def update_transcript(project_id: str, data: TranscriptUpdateRequest, db: Session = Depends(get_db)):
    """Save user edits to transcript text while preserving original timing timestamps."""
    transcript = db.query(Transcript).filter(Transcript.project_id == project_id).first()
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    updated_segments = [s.model_dump() for s in data.segments]
    full_text = " ".join(s["text"].strip() for s in updated_segments)

    transcript.segments_json = json.dumps(updated_segments)
    transcript.raw_text = full_text
    transcript.is_user_edited = True
    db.commit()
    db.refresh(transcript)

    return TranscriptResponse(
        id=transcript.id,
        project_id=transcript.project_id,
        language=transcript.language,
        is_user_edited=transcript.is_user_edited,
        raw_text=transcript.raw_text,
        segments=updated_segments,
        created_at=transcript.created_at,
        updated_at=transcript.updated_at
    )

@router.post("/transcribe", status_code=status.HTTP_202_ACCEPTED)
def trigger_transcription(project_id: str, db: Session = Depends(get_db)):
    """Enqueues a transcription job for the project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    job = Job(
        job_type="transcribe",
        project_id=project_id,
        status="queued",
        progress=0.0,
        progress_stage="Queued for speech-to-text..."
    )
    db.add(job)
    project.status = "transcribing"
    db.commit()
    return {"message": "Transcription job enqueued", "job_id": job.id}
