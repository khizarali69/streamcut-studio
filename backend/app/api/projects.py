import shutil
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Project, SourceMedia, ExportArtifact, Job
from app.schemas import ProjectCreate, ProjectUpdate, ProjectResponse, StorageStats
from app.config import settings

router = APIRouter(prefix="/api/projects", tags=["projects"])

@router.get("", response_model=List[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    """List all projects ordered by most recent."""
    return db.query(Project).order_by(Project.created_at.desc()).all()

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
    """Creates a new project record."""
    project = Project(
        title=data.title.strip(),
        description=data.description,
        source_url=data.source_url,
        creator=data.creator,
        rights_status=data.rights_status,
        rights_notes=data.rights_notes,
        status="created"
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    """Retrieve project metadata."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: str, data: ProjectUpdate, db: Session = Depends(get_db)):
    """Update project details."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if data.title is not None:
        project.title = data.title.strip()
    if data.description is not None:
        project.description = data.description
    if data.source_url is not None:
        project.source_url = data.source_url
    if data.creator is not None:
        project.creator = data.creator
    if data.rights_status is not None:
        project.rights_status = data.rights_status
    if data.rights_notes is not None:
        project.rights_notes = data.rights_notes

    db.commit()
    db.refresh(project)
    return project

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, db: Session = Depends(get_db)):
    """Deletes a project and cleans up its media files."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Remove source media file
    if project.source_media and project.source_media.file_path:
        p = Path(project.source_media.file_path)
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass

    # Remove associated exports
    for exp in project.exports:
        if exp.file_path and Path(exp.file_path).exists():
            try:
                Path(exp.file_path).unlink()
            except Exception:
                pass

    db.delete(project)
    db.commit()

@router.get("/storage/stats", response_model=StorageStats)
def get_storage_stats(db: Session = Depends(get_db)):
    """Returns local disk and app storage usage metrics."""
    total, used, free = shutil.disk_usage(settings.STORAGE_DIR)
    
    # Calculate app storage size
    app_used = 0
    for p in settings.STORAGE_DIR.rglob("*"):
        if p.is_file():
            try:
                app_used += p.stat().st_size
            except Exception:
                pass

    projects_count = db.query(Project).count()
    exports_count = db.query(ExportArtifact).count()

    return StorageStats(
        total_space_bytes=total,
        free_space_bytes=free,
        used_by_app_bytes=app_used,
        projects_count=projects_count,
        exports_count=exports_count
    )
