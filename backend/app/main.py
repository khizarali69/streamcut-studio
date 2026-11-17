from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.job_worker import start_background_worker, stop_background_worker, recover_interrupted_jobs
from app.api.settings import seed_default_presets
from app.api import projects, media, transcripts, clips, jobs, exports, settings as api_settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database tables
    Base.metadata.create_all(bind=engine)
    
    # Seed default styles and layouts
    db = SessionLocal()
    try:
        seed_default_presets(db)
    finally:
        db.close()

    # Recover any jobs interrupted during prior runs
    recover_interrupted_jobs()

    # Start background processing worker thread
    start_background_worker()
    
    yield

    # Clean shutdown
    stop_background_worker()

app = FastAPI(
    title="StreamCut Studio API",
    description="Autonomous local AI video clipping & reframing engine",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount local storage folder for serving proxies, thumbnails, and exports
app.mount("/storage", StaticFiles(directory=str(settings.STORAGE_DIR)), name="storage")

# Include Routers
app.include_router(projects.router)
app.include_router(media.router)
app.include_router(transcripts.router)
app.include_router(clips.router)
app.include_router(jobs.router)
app.include_router(exports.router)
app.include_router(api_settings.router)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "app": "StreamCut Studio",
        "version": "1.0.0"
    }
