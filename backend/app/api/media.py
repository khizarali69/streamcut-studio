import os
import shutil
import ipaddress
import socket
from urllib.parse import urlparse
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
import httpx

from app.database import get_db
from app.models import Project, SourceMedia, Job
from app.schemas import SourceMediaResponse
from app.config import settings
from app.media_probe import compute_file_hash

router = APIRouter(prefix="/api/projects/{project_id}/media", tags=["media"])

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}

def is_safe_url(url: str) -> bool:
    """SSRF Protection: Rejects private/loopback/link-local IP addresses."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        
        hostname = parsed.hostname
        if not hostname:
            return False

        # Resolve IP
        ip_str = socket.gethostbyname(hostname)
        ip = ipaddress.ip_address(ip_str)

        # Disallow loopback, private, link-local, multicast
        if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_multicast or ip.is_reserved:
            return False

        return True
    except Exception:
        return False

@router.post("/upload", response_model=SourceMediaResponse)
async def upload_video_file(
    project_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Uploads a video file, computes SHA256, and enqueues probe & proxy generation."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Sanitize filename and prevent path traversal
    safe_filename = Path(file.filename).name
    dest_path = settings.SOURCES_DIR / f"{project.id}_{safe_filename}"

    # Stream file to disk in chunks to prevent high memory usage
    chunk_size = 1024 * 1024  # 1MB
    bytes_written = 0
    with open(dest_path, "wb") as f:
        while chunk := await file.read(chunk_size):
            bytes_written += len(chunk)
            if bytes_written > (settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024):
                dest_path.unlink()
                raise HTTPException(status_code=413, detail="File exceeds maximum upload size limit")
            f.write(chunk)

    # Content hash deduplication check
    file_hash = compute_file_hash(dest_path)

    # Create or update SourceMedia record
    media = db.query(SourceMedia).filter(SourceMedia.project_id == project_id).first()
    if not media:
        media = SourceMedia(
            project_id=project_id,
            filename=safe_filename,
            file_path=str(dest_path),
            file_size=bytes_written,
            content_hash=file_hash
        )
        db.add(media)
    else:
        media.filename = safe_filename
        media.file_path = str(dest_path)
        media.file_size = bytes_written
        media.content_hash = file_hash

    project.status = "uploaded"
    db.commit()

    # Enqueue probe & proxy generation job
    job = Job(
        job_type="probe_and_proxy",
        project_id=project_id,
        status="queued",
        progress=0.0,
        progress_stage="Queued for stream analysis..."
    )
    db.add(job)
    db.commit()
    db.refresh(media)

    return media

@router.post("/url-import", response_model=SourceMediaResponse)
async def import_video_from_url(
    project_id: str,
    source_url: str = Form(...),
    db: Session = Depends(get_db)
):
    """Direct media URL import with strict SSRF validation."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not is_safe_url(source_url):
        raise HTTPException(
            status_code=400,
            detail="Forbidden URL. Private or internal network destinations are blocked."
        )

    # Download direct stream
    dest_path = settings.SOURCES_DIR / f"{project.id}_imported.mp4"
    try:
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.get(source_url)
            if resp.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Failed to fetch media from URL (HTTP {resp.status_code})")
            
            content_type = resp.headers.get("content-type", "")
            if "video" not in content_type and "octet-stream" not in content_type:
                raise HTTPException(status_code=400, detail="URL does not point to a valid direct video stream")

            with open(dest_path, "wb") as f:
                f.write(resp.content)

        file_hash = compute_file_hash(dest_path)
        media = SourceMedia(
            project_id=project_id,
            filename="imported.mp4",
            file_path=str(dest_path),
            file_size=dest_path.stat().st_size,
            content_hash=file_hash
        )
        db.add(media)
        project.status = "uploaded"
        project.source_url = source_url

        job = Job(
            job_type="probe_and_proxy",
            project_id=project_id,
            status="queued"
        )
        db.add(job)
        db.commit()
        db.refresh(media)
        return media

    except Exception as e:
        if dest_path.exists():
            dest_path.unlink()
        raise HTTPException(status_code=400, detail=f"URL import failed: {str(e)}")
