# StreamCut Studio 🎬

**Autonomous, Self-Hosted AI Video Clipping & Reframing Application**  
*Inspired by the core workflow of OpusClip — built independently without proprietary code, subscriptions, watermarks, or artificial export quotas.*

---

## 🌟 Overview & Key Capabilities

StreamCut Studio turns long-form podcasts, gaming streams, tutorials, and interviews into high-retention vertical short clips tailored for TikTok, YouTube Shorts, and Instagram Reels:

- **100% Self-Hosted & Local**: Zero monthly subscriptions, no artificial credit systems, and no watermarks.
- **Offline Transcription**: Runs `faster-whisper` (CTranslate2 int8) locally for rapid speech-to-text with word-level timestamps.
- **Multi-Signal Highlight Generation**: Intelligent candidate generator evaluating speech hooks, reactions, question-and-answer pairs, topic shifts, and sentence completeness.
- **Streamer Multi-Layer Layouts**:
  1. Full-frame 9:16 vertical crop.
  2. Facecam above gameplay (top 35% webcam, bottom 65% game).
  3. Gameplay above facecam (top 65% game, bottom 35% webcam).
  4. Side-by-side dual reaction.
  5. Original 16:9 landscape over blurred ambient vertical background.
  6. Custom bounding box framing.
- **ASS/libass Burned-in Subtitles**: Exact pixel-level subtitles with active word karaoke highlighting, custom fonts, outlines, and drop shadows, plus standalone `.srt` and `.vtt` downloads.
- **Broadcast Audio**: Integrated volume adjustments and EBU R128 (`loudnorm`) loudness normalization (-16 LUFS).
- **Durable Background Queue**: SQLite-backed job queue with automatic restart recovery and safe FFmpeg subprocess cancellation.

---

## 🚀 Quick Start & Development Setup

### Prerequisites
- **Python**: 3.11+
- **Node.js**: 20+ and npm
- **FFmpeg & ffprobe**: 6.0+ compiled with `--enable-libass`

### 1. Automated Start (Windows)
Run the consolidated startup script:
```powershell
.\start_all.ps1
```
This automatically boots the FastAPI backend on `http://127.0.0.1:8000` and the Vite frontend on `http://127.0.0.1:3000`.

### 2. Manual Startup Commands

#### Backend:
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### Frontend:
```powershell
cd frontend
npm install
npm run dev
```
Open your browser at `http://localhost:3000`.

---

## 🐳 Docker Compose Setup

StreamCut Studio provides a reproducible Docker Compose configuration:

```bash
# Build and start services
docker-compose up --build

# Backend will run on http://localhost:8000
# Frontend will run on http://localhost:3000
```

---

## 🧠 Model Downloads & Hardware Considerations

### Whisper Speech-to-Text Weights
- StreamCut Studio uses `faster-whisper` models, downloaded on-demand to `backend/storage/models/`:
  - `tiny.en` (~75 MB): Ultra-fast, minimal memory (~1GB RAM).
  - `base.en` (~140 MB, **Default**): Balanced speed and accuracy (~1.5GB RAM).
  - `small.en` (~460 MB): Higher accuracy for technical or rapid speech (~2.5GB RAM).
  - `medium` (~1.5 GB): Multilingual support (~5GB RAM).
- **CPU vs GPU**: By default, int8 quantized CPU execution is used. If an NVIDIA GPU with CUDA is detected, set `WHISPER_DEVICE=cuda` and `WHISPER_COMPUTE_TYPE=float16` in `.env` for 4x acceleration.

---

## 🧪 Testing & Verification

Run the comprehensive automated test suite:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1

# Run unit tests (timestamps, crop math, filter graphs, subtitle escaping, recovery)
pytest tests/test_streamcut.py -v

# Run full end-to-end integration test with synthetic video footage
pytest tests/test_e2e_pipeline.py -v -s
```

### Verified Pipeline Results:
- Ingestion of 1920x1080 30fps sample video.
- ffprobe stream inspection & proxy generation.
- Transcription with `faster-whisper` extracting word timestamps.
- Candidate generation snapping to sentence boundaries with internal highlight score.
- Rendered 9:16 vertical MP4 (1080x1920) with burned-in ASS captions and AAC audio.
- ffprobe validation passed: `Valid video stream`, `Expected dimensions (1080x1920)`, `Audio verified`.

A verified sample export is persisted at:
- `backend/storage/exports/test_export_357ee2c8.mp4`

---

## ⚖️ Dependency & Model Licenses

- **FastAPI**: MIT License
- **Uvicorn**: BSD 3-Clause
- **SQLAlchemy**: MIT License
- **faster-whisper / CTranslate2**: MIT License
- **OpenAI Whisper Weights**: MIT License
- **FFmpeg & libass**: LGPL / GPL v3
- **React & Vite**: MIT License
- **Tailwind CSS**: MIT License
- **Lucide Icons**: ISC License

---

## 🛡️ Security, Privacy, and Content Rights

- **Local-First**: Binds strictly to `127.0.0.1` by default.
- **SSRF Hardening**: URL imports block private-network destinations (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.1).
- **Safe Subprocesses**: All FFmpeg executions use safe argument arrays; no raw shell interpolation.
- **No Virality Guarantees**: Highlight scores are internal heuristic ranking estimates.
- **Rights Disclosure**: Users must explicitly classify rights status (`owned`, `permission granted`, `licensed`, or `unknown`).
