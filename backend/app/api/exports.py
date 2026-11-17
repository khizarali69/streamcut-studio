import io
import zipfile
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Project, ClipCandidate, ClipEdit, Job, ExportArtifact
from app.schemas import ExportRequest, ExportArtifactResponse

router = APIRouter(prefix="/api", tags=["exports"])

@router.post("/clips/{clip_id}/export", status_code=status.HTTP_202_ACCEPTED)
def export_single_clip(
    clip_id: str,
    data: ExportRequest,
    db: Session = Depends(get_db)
):
    """Enqueues an export job for a clip candidate."""
    clip = db.query(ClipCandidate).filter(ClipCandidate.id == clip_id).first()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    # Check if an identical active job already exists
    existing = db.query(Job).filter(
        Job.job_type == "export_clip",
        Job.target_id == clip_id,
        Job.status.in_(["queued", "processing"])
    ).first()
    if existing:
        return {"message": "Export job already in progress", "job_id": existing.id}

    job = Job(
        job_type="export_clip",
        project_id=clip.project_id,
        target_id=clip.id,
        status="queued",
        progress=0.0,
        progress_stage="Queued for video rendering..."
    )
    db.add(job)
    db.commit()

    return {"message": "Export job enqueued", "job_id": job.id}

@router.post("/projects/{project_id}/batch-export", status_code=status.HTTP_202_ACCEPTED)
def batch_export_clips(
    project_id: str,
    clip_ids: List[str],
    db: Session = Depends(get_db)
):
    """Enqueues batch export jobs for multiple selected clips."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    job_ids = []
    for cid in clip_ids:
        clip = db.query(ClipCandidate).filter(ClipCandidate.id == cid, ClipCandidate.project_id == project_id).first()
        if not clip:
            continue
        
        # Check existing active job
        existing = db.query(Job).filter(
            Job.job_type == "export_clip",
            Job.target_id == cid,
            Job.status.in_(["queued", "processing"])
        ).first()
        if existing:
            job_ids.append(existing.id)
            continue

        job = Job(
            job_type="export_clip",
            project_id=project_id,
            target_id=cid,
            status="queued",
            progress=0.0,
            progress_stage="Queued for batch rendering..."
        )
        db.add(job)
        db.flush()
        job_ids.append(job.id)

    db.commit()
    return {"message": f"Queued {len(job_ids)} exports", "job_ids": job_ids}

@router.get("/projects/{project_id}/exports", response_model=List[ExportArtifactResponse])
def list_project_exports(project_id: str, db: Session = Depends(get_db)):
    """List completed export artifacts for a project."""
    exports = db.query(ExportArtifact).filter(ExportArtifact.project_id == project_id).order_by(ExportArtifact.created_at.desc()).all()
    
    result = []
    for exp in exports:
        result.append(ExportArtifactResponse(
            id=exp.id,
            project_id=exp.project_id,
            clip_id=exp.clip_id,
            job_id=exp.job_id,
            filename=exp.filename,
            file_size=exp.file_size,
            duration=exp.duration,
            width=exp.width,
            height=exp.height,
            format=exp.format,
            has_burned_captions=exp.has_burned_captions,
            download_url=f"/api/exports/{exp.id}/download",
            srt_url=f"/api/exports/{exp.id}/srt" if exp.srt_path else None,
            vtt_url=f"/api/exports/{exp.id}/vtt" if exp.vtt_path else None,
            thumbnail_url=exp.thumbnail_path,
            ffprobe_valid=exp.ffprobe_valid,
            created_at=exp.created_at
        ))
    return result

@router.get("/exports/{export_id}/download")
def download_export_video(export_id: str, db: Session = Depends(get_db)):
    """Download the finalized, validated MP4 video file."""
    exp = db.query(ExportArtifact).filter(ExportArtifact.id == export_id).first()
    if not exp or not Path(exp.file_path).exists():
        raise HTTPException(status_code=404, detail="Export file not found")

    return FileResponse(
        path=exp.file_path,
        media_type="video/mp4",
        filename=exp.filename
    )

@router.get("/exports/{export_id}/srt")
def download_export_srt(export_id: str, db: Session = Depends(get_db)):
    """Download the SRT subtitle file for an export."""
    exp = db.query(ExportArtifact).filter(ExportArtifact.id == export_id).first()
    if not exp or not exp.srt_path:
        raise HTTPException(status_code=404, detail="SRT file not found")
    
    local_p = Path(exp.srt_path.replace("/storage/", str(settings.STORAGE_DIR) + "/"))
    if not local_p.exists():
        raise HTTPException(status_code=404, detail="SRT file not found on disk")

    return FileResponse(path=str(local_p), media_type="text/plain", filename=f"{Path(exp.filename).stem}.srt")

@router.get("/exports/{export_id}/vtt")
def download_export_vtt(export_id: str, db: Session = Depends(get_db)):
    """Download the WebVTT subtitle file for an export."""
    exp = db.query(ExportArtifact).filter(ExportArtifact.id == export_id).first()
    if not exp or not exp.vtt_path:
        raise HTTPException(status_code=404, detail="VTT file not found")
    
    local_p = Path(exp.vtt_path.replace("/storage/", str(settings.STORAGE_DIR) + "/"))
    if not local_p.exists():
        raise HTTPException(status_code=404, detail="VTT file not found on disk")

    return FileResponse(path=str(local_p), media_type="text/vtt", filename=f"{Path(exp.filename).stem}.vtt")

@router.get("/projects/{project_id}/exports/zip")
def download_all_exports_zip(project_id: str, db: Session = Depends(get_db)):
    """Downloads all completed video exports for a project bundled in a single ZIP file."""
    exports = db.query(ExportArtifact).filter(ExportArtifact.project_id == project_id).all()
    if not exports:
        raise HTTPException(status_code=404, detail="No completed exports found for this project")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for exp in exports:
            fpath = Path(exp.file_path)
            if fpath.exists():
                zip_file.write(fpath, arcname=exp.filename)
            if exp.srt_path:
                srt_p = Path(exp.srt_path.replace("/storage/", str(settings.STORAGE_DIR) + "/"))
                if srt_p.exists():
                    zip_file.write(srt_p, arcname=f"subtitles/{srt_p.name}")

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=streamcut_{project_id[:8]}_exports.zip"}
    )
