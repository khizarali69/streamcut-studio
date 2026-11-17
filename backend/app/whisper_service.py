import os
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from app.config import settings

# Global model cache to avoid re-loading weights on every job
_cached_model = None
_cached_model_name = None

def extract_audio_for_transcription(video_path: Path, output_audio_path: Path) -> Path:
    """Extract 16kHz mono 16-bit PCM WAV for Whisper processing."""
    output_audio_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        settings.FFMPEG_PATH,
        "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(output_audio_path)
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return output_audio_path

def get_whisper_model(model_name: str = "base.en", device: str = "cpu", compute_type: str = "int8"):
    """Load or retrieve cached faster-whisper model."""
    global _cached_model, _cached_model_name
    from faster_whisper import WhisperModel

    if _cached_model is not None and _cached_model_name == f"{model_name}_{device}_{compute_type}":
        return _cached_model

    print(f"Loading Whisper model '{model_name}' on {device} ({compute_type})...")
    # faster-whisper downloads the model to huggingface cache automatically
    model = WhisperModel(
        model_name,
        device=device,
        compute_type=compute_type,
        download_root=str(settings.STORAGE_DIR / "models")
    )
    _cached_model = model
    _cached_model_name = f"{model_name}_{device}_{compute_type}"
    return model

def transcribe_audio(
    video_path: Path,
    language: Optional[str] = "en",
    model_name: Optional[str] = None,
    progress_callback = None
) -> Tuple[List[Dict[str, Any]], str, str]:
    """
    Transcribes audio from a video file with segment and word timestamps.
    Returns: (segments_list, detected_language, raw_text)
    """
    selected_model_name = model_name or settings.WHISPER_MODEL
    temp_audio_path = settings.TEMP_DIR / f"temp_{os.getpid()}_{video_path.stem}.wav"

    try:
        if progress_callback:
            progress_callback(10.0, "Extracting audio track...")
        
        extract_audio_for_transcription(video_path, temp_audio_path)

        if progress_callback:
            progress_callback(25.0, f"Loading Whisper model ({selected_model_name})...")

        model = get_whisper_model(
            model_name=selected_model_name,
            device=settings.WHISPER_DEVICE,
            compute_type=settings.WHISPER_COMPUTE_TYPE
        )

        if progress_callback:
            progress_callback(40.0, "Transcribing speech and word timestamps...")

        segments_generator, info = model.transcribe(
            str(temp_audio_path),
            language=language if language and language != "auto" else None,
            word_timestamps=True,
            vad_filter=True, # filter out non-speech silence
            vad_parameters=dict(min_silence_duration_ms=500)
        )

        detected_lang = info.language or "en"
        raw_text_parts = []
        segments_output = []

        seg_idx = 0
        for seg in segments_generator:
            seg_idx += 1
            words_list = []
            if seg.words:
                for w in seg.words:
                    words_list.append({
                        "word": w.word.strip(),
                        "start": round(w.start, 3),
                        "end": round(w.end, 3),
                        "score": round(w.probability, 3)
                    })
            else:
                # If word timestamps are missing for some reason, interpolate
                raw_words = seg.text.strip().split()
                if raw_words:
                    word_duration = (seg.end - seg.start) / len(raw_words)
                    for i, rw in enumerate(raw_words):
                        words_list.append({
                            "word": rw,
                            "start": round(seg.start + i * word_duration, 3),
                            "end": round(seg.start + (i + 1) * word_duration, 3),
                            "score": 0.95
                        })

            segment_data = {
                "id": seg_idx,
                "start": round(seg.start, 3),
                "end": round(seg.end, 3),
                "text": seg.text.strip(),
                "words": words_list
            }
            segments_output.append(segment_data)
            raw_text_parts.append(seg.text.strip())

        raw_text = " ".join(raw_text_parts)
        if progress_callback:
            progress_callback(90.0, f"Transcription complete: {len(segments_output)} segments found")

        return segments_output, detected_lang, raw_text

    except Exception as e:
        # Check if error was due to no audio
        if "does not contain any audio" in str(e).lower() or not temp_audio_path.exists():
            return [], "none", ""
        raise e
    finally:
        if temp_audio_path.exists():
            try:
                temp_audio_path.unlink()
            except Exception:
                pass
