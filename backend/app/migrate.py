"""
StreamCut Studio Database Migration & Initialization Script.
Handles schema initialization, indexing, and default preset seeding.
"""
from app.database import engine, Base, SessionLocal
from app.models import Project, SourceMedia, Transcript, ClipCandidate, ClipEdit, CaptionStyle, LayoutPreset, Job, ExportArtifact, AppSettings
from app.api.settings import seed_default_presets

def run_migrations():
    print("Running database migrations for StreamCut Studio...")
    # Create all tables if they don't exist
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully.")

    # Seed default system presets
    db = SessionLocal()
    try:
        seed_default_presets(db)
        print("Default caption styles and layout presets seeded.")
    finally:
        db.close()

    print("Migration complete!")

if __name__ == "__main__":
    run_migrations()
