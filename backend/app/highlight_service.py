import re
import json
import httpx
from typing import List, Dict, Any, Optional, Tuple
from app.config import settings

# Hook keywords commonly found at start of compelling short-form moments
HOOK_KEYWORDS = {
    "why", "how", "what", "secret", "never", "always", "stop", "imagine",
    "watch", "look", "listen", "everybody", "nobody", "truth", "crazy",
    "insane", "mistake", "hack", "tip", "reason", "actually", "believe",
    "did you know", "wait", "check this", "you won't believe"
}

REACTION_KEYWORDS = {
    "wow", "no way", "oh my god", "omg", "what", "haha", "bro", "dude",
    "insane", "crazy", "let's go", "boom", "unbelievable", "huge", "perfect",
    "rekt", "clutch", "fail", "win", "genius", "impossible"
}

def detect_sentence_boundaries(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Groups or tags segments by sentence ending punctuation or silence pauses."""
    punctuated = []
    for i, seg in enumerate(segments):
        text = seg.get("text", "").strip()
        ends_sentence = text.endswith((".", "!", "?"))
        pause_after = 0.0
        if i + 1 < len(segments):
            pause_after = max(0.0, segments[i + 1]["start"] - seg["end"])
            if pause_after > 0.4:
                ends_sentence = True
        punctuated.append({
            **seg,
            "ends_sentence": ends_sentence,
            "pause_after": pause_after
        })
    return punctuated

def score_window(
    window_segments: List[Dict[str, Any]],
    content_type: str = "general",
    user_instruction: Optional[str] = None
) -> Tuple[float, str, List[str]]:
    """Calculates heuristic highlight score (0-100) based on speech dynamics."""
    if not window_segments:
        return 50.0, "Baseline window", []

    first_seg = window_segments[0]
    last_seg = window_segments[-1]
    all_text = " ".join(s.get("text", "") for s in window_segments).lower()
    first_text = first_seg.get("text", "").lower()

    score = 65.0
    reasons = []
    tags = []

    # 1. Hook score in opening
    hook_found = any(k in first_text for k in HOOK_KEYWORDS)
    if hook_found or first_text.endswith("?"):
        score += 12.0
        reasons.append("Strong hook / question opening")
        tags.append("hook")

    # 2. Reaction / Punchline detection
    reaction_count = sum(1 for k in REACTION_KEYWORDS if k in all_text)
    if reaction_count > 0:
        score += min(10.0, reaction_count * 3.5)
        reasons.append("High-energy reaction / punchline")
        tags.append("reaction")

    # 3. Content-type specific weightings
    if content_type == "gaming":
        if any(w in all_text for w in ["kill", "shot", "win", "died", "boss", "play", "game", "clutch"]):
            score += 6.0
            tags.append("gaming")
    elif content_type == "podcast" or content_type == "conversation":
        if "?" in all_text and ("yes" in all_text or "no" in all_text or "think" in all_text):
            score += 6.0
            reasons.append("Self-contained Q&A topic")
            tags.append("discussion")
    elif content_type == "tutorial":
        if any(w in all_text for w in ["step", "first", "next", "how to", "make sure"]):
            score += 7.0
            reasons.append("Actionable instructional moment")
            tags.append("tutorial")

    # 4. User instruction match (if provided)
    if user_instruction:
        keywords = [k.lower().strip() for k in user_instruction.split() if len(k) > 3]
        match_count = sum(1 for k in keywords if k in all_text)
        if match_count > 0:
            score += min(10.0, match_count * 3.0)
            reasons.append(f"Matches instruction prompt: '{user_instruction[:30]}...'")
            tags.append("custom_match")

    # 5. Completeness bonus
    if last_seg.get("ends_sentence", False):
        score += 5.0
    else:
        score -= 5.0  # penalty for awkward mid-sentence cut

    # Clamp score to reasonable range
    final_score = max(55.0, min(97.0, round(score, 1)))
    reason_str = " • ".join(reasons) if reasons else "Cohesive conversational segment (heuristic estimate)"
    return final_score, reason_str, tags

def generate_heuristic_candidates(
    segments: List[Dict[str, Any]],
    source_duration: float,
    min_duration: float = 15.0,
    max_duration: float = 60.0,
    target_count: int = 5,
    content_type: str = "general",
    user_instruction: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Generates candidate clip suggestions using speech signals and boundary clamping."""
    if not segments or source_duration < min_duration:
        # If source is shorter than min_duration, create one full clip if possible
        if source_duration >= 5.0:
            return [{
                "title": "Full Source Highlight",
                "start_time": 0.0,
                "end_time": round(source_duration, 2),
                "duration": round(source_duration, 2),
                "highlight_score": 85.0,
                "reason": "Complete source media clip (source shorter than requested preset)",
                "tags": ["full_source"],
                "status": "suggested"
            }]
        return []

    punctuated = detect_sentence_boundaries(segments)
    raw_candidates = []

    # Slide a window across segments snapping to sentence beginnings
    n = len(punctuated)
    for i in range(n):
        start_seg = punctuated[i]
        start_t = start_seg["start"]

        for j in range(i, n):
            end_seg = punctuated[j]
            end_t = end_seg["end"]
            dur = end_t - start_t

            if dur < min_duration:
                continue
            if dur > max_duration:
                break

            # Prefer ending on a sentence boundary
            if end_seg.get("ends_sentence", False) or (dur >= (min_duration + max_duration) / 2):
                win_segs = punctuated[i:j+1]
                score, reason, tags = score_window(win_segs, content_type, user_instruction)
                
                # Derive punchy title from first segment or key hook
                first_text = start_seg.get("text", "").strip()
                title_words = first_text.split()[:7]
                title = " ".join(title_words)
                if len(title) > 40:
                    title = title[:37] + "..."
                if not title:
                    title = f"Clip at {int(start_t)}s"

                raw_candidates.append({
                    "title": title.title(),
                    "start_time": round(max(0.0, start_t), 2),
                    "end_time": round(min(source_duration, end_t), 2),
                    "duration": round(end_t - start_t, 2),
                    "highlight_score": score,
                    "reason": f"{reason} (Internal ranking estimate)",
                    "tags": tags,
                    "status": "suggested"
                })

    # Sort raw candidates by score descending
    raw_candidates.sort(key=lambda c: c["highlight_score"], reverse=True)

    # Non-maximum suppression (NMS) to avoid excessive overlaps
    selected = []
    for cand in raw_candidates:
        c_start = cand["start_time"]
        c_end = cand["end_time"]
        
        # Check overlap with already selected
        overlap = False
        for s in selected:
            s_start = s["start_time"]
            s_end = s["end_time"]
            inter_start = max(c_start, s_start)
            inter_end = min(c_end, s_end)
            if inter_end > inter_start:
                inter_dur = inter_end - inter_start
                if inter_dur / cand["duration"] > 0.35 or inter_dur / s["duration"] > 0.35:
                    overlap = True
                    break
        
        if not overlap:
            selected.append(cand)
            if len(selected) >= target_count:
                break

    # If NMS was too strict, backfill with top non-identical
    if len(selected) < min(target_count, len(raw_candidates)):
        for cand in raw_candidates:
            if cand not in selected:
                selected.append(cand)
                if len(selected) >= target_count:
                    break

    selected.sort(key=lambda c: c["start_time"])
    return selected

async def generate_llm_candidates(
    segments: List[Dict[str, Any]],
    source_duration: float,
    min_duration: float = 15.0,
    max_duration: float = 60.0,
    target_count: int = 5,
    content_type: str = "general",
    user_instruction: Optional[str] = None
) -> Optional[List[Dict[str, Any]]]:
    """Optional local LLM analysis via Ollama or OpenAI-compatible endpoint."""
    if not settings.LLM_ENABLED or not segments:
        return None

    # Compact transcript lines with timestamps
    lines = []
    for s in segments:
        lines.append(f"[{s['start']:.1f}s - {s['end']:.1f}s] {s['text']}")
    full_text = "\n".join(lines[:120])  # limit tokens for local models

    system_prompt = (
        "You are an AI video editor assistant. Analyze the transcript below to identify "
        f"up to {target_count} engaging viral short video clips. "
        f"Each clip duration must be between {min_duration} and {max_duration} seconds. "
        "Strict Rule: You must return ONLY a valid JSON array of objects with keys: "
        "'title' (string), 'start_time' (float), 'end_time' (float), 'reason' (string), 'score' (float 0-100), 'tags' (array of strings). "
        "Do not invent timestamps outside the provided range. Do not return any other markdown or text."
    )

    user_prompt = (
        f"Content type: {content_type}\n"
        f"User instruction: {user_instruction or 'Select the best standalone highlights with strong hooks'}\n\n"
        f"<transcript>\n{full_text}\n</transcript>"
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if settings.LLM_PROVIDER == "ollama":
                endpoint = f"{settings.LLM_BASE_URL.rstrip('/')}/api/generate"
                payload = {
                    "model": settings.LLM_MODEL,
                    "prompt": f"{system_prompt}\n\n{user_prompt}",
                    "stream": False,
                    "format": "json"
                }
                res = await client.post(endpoint, json=payload)
                if res.status_code == 200:
                    raw_resp = res.json().get("response", "[]")
                    parsed = json.loads(raw_resp)
                    if isinstance(parsed, dict) and "clips" in parsed:
                        parsed = parsed["clips"]
                    if isinstance(parsed, list):
                        validated = []
                        for item in parsed:
                            st = float(item.get("start_time", 0.0))
                            et = float(item.get("end_time", 0.0))
                            if 0.0 <= st < et <= source_duration and (et - st) >= 5.0:
                                validated.append({
                                    "title": str(item.get("title", f"Highlight at {int(st)}s")),
                                    "start_time": round(st, 2),
                                    "end_time": round(et, 2),
                                    "duration": round(et - st, 2),
                                    "highlight_score": float(item.get("score", 85.0)),
                                    "reason": f"{item.get('reason', 'Selected by local LLM')} (Internal ranking estimate)",
                                    "tags": item.get("tags", ["llm_suggested"]),
                                    "status": "suggested"
                                })
                        if validated:
                            return validated[:target_count]
    except Exception as e:
        print(f"LLM candidate generation error: {e}, falling back to heuristic baseline.")

    return None
