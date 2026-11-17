import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "StreamCut Studio"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = False
    
    # Base directories
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    STORAGE_DIR: Path = BASE_DIR / "storage"
    
    # Storage Subdirectories
    SOURCES_DIR: Path = STORAGE_DIR / "sources"
    PROXIES_DIR: Path = STORAGE_DIR / "proxies"
    THUMBNAILS_DIR: Path = STORAGE_DIR / "thumbnails"
    SUBTITLES_DIR: Path = STORAGE_DIR / "subtitles"
    EXPORTS_DIR: Path = STORAGE_DIR / "exports"
    TEMP_DIR: Path = STORAGE_DIR / "temp"
    
    # Database
    DATABASE_URL: str = f"sqlite:///{STORAGE_DIR / 'streamcut.db'}"
    
    # Whisper settings
    WHISPER_MODEL: str = "base.en"  # tiny.en, base.en, small.en, small, medium
    WHISPER_DEVICE: str = "cpu"     # cpu or cuda
    WHISPER_COMPUTE_TYPE: str = "int8"  # int8, float16
    
    # FFmpeg / ffprobe executables
    FFMPEG_PATH: str = "ffmpeg"
    FFPROBE_PATH: str = "ffprobe"
    
    # LLM Settings (optional local or remote)
    LLM_ENABLED: bool = False
    LLM_PROVIDER: str = "ollama"  # "ollama", "openai_compatible", "none"
    LLM_BASE_URL: str = "http://127.0.0.1:11434"
    LLM_MODEL: str = "llama3"
    LLM_API_KEY: str = ""
    
    # Upload limits
    MAX_UPLOAD_SIZE_MB: int = 4096  # 4GB max per file
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

# Ensure directories exist
for path in [
    settings.STORAGE_DIR,
    settings.SOURCES_DIR,
    settings.PROXIES_DIR,
    settings.THUMBNAILS_DIR,
    settings.SUBTITLES_DIR,
    settings.EXPORTS_DIR,
    settings.TEMP_DIR
]:
    path.mkdir(parents=True, exist_ok=True)
