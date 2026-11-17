from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Job
from app.schemas import JobResponse
from app.job_worker import cancel_running_job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

@router.get("", response_model=List[JobResponse])
def list_jobs(project_id: Optional[str] = None, db: Session = Depends(get_db)):
    """List recent background processing jobs."""
    query = db.query(Job)
    if project_id:
        query = query.filter(Job.project_id == project_id)
    return query.order_by(Job.created_at.desc()).limit(50).all()

@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Retrieve status, live progress, and stage message of a specific job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/{job_id}/cancel")
def cancel_job(job_id: str, db: Session = Depends(get_db)):
    """Cancels a queued or currently executing job."""
    success = cancel_running_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot cancel this job")
    return {"message": "Job cancellation initiated", "job_id": job_id}

@router.post("/{job_id}/retry", response_model=JobResponse)
def retry_job(job_id: str, db: Session = Depends(get_db)):
    """Reschedules a failed or canceled job back to queued status."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = "queued"
    job.progress = 0.0
    job.progress_stage = "Re-queued for processing"
    job.error_message = None
    job.started_at = None
    job.completed_at = None
    db.commit()
    db.refresh(job)
    return job
